#!/usr/bin/env python3
"""Top up missing benchmark samples in runs 1 and 2."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.utils import (
    BENCHMARK_DEFINITIONS,
    BENCHMARK_STANDARD_DECODE,
    BENCHMARK_STANDARD_PREFILL,
    BENCHMARK_TIME_BEFORE_PREFILL,
    BENCHMARK_TIME_BEFORE_PREFILL_CACHED,
    DEFAULT_BENCHMARKS,
    PHASE_BASELINE,
    PHASE_DECODE,
    PHASE_PREFILL,
    PHASE_PREFILL_PROBE,
    PHASE_SAMPLE,
    RUNS_ROOT,
    BenchmarkConfig,
    annotate_record,
    benchmark_payload,
    benchmark_run_dir,
    decode_output_is_complete,
    get_api_key,
    is_error_record,
    phase_for,
    request_once_async,
    run_benchmark_sample,
    sample_index_for,
    summarize_decode_metrics,
    summarize_prefill_metrics,
    write_result,
)

TARGET_SAMPLES = 10
DEFAULT_RUNS = ("6")
DEFAULT_CONCURRENCY = 80
DEFAULT_MAX_RETRIES = 10

PHASES_BY_BENCHMARK = {
    BENCHMARK_STANDARD_PREFILL: (PHASE_BASELINE, PHASE_PREFILL),
    BENCHMARK_STANDARD_DECODE: (PHASE_BASELINE, PHASE_PREFILL_PROBE, PHASE_DECODE),
}


@dataclass(frozen=True, slots=True)
class LoadedRecord:
    data: dict[str, Any]
    path: Path
    run_root: Path


@dataclass(frozen=True, slots=True)
class RepairTask:
    run_root: Path
    model: str
    endpoint: str
    benchmark: str
    sample_index: int
    phase: str | None = None
    replace_paths: tuple[Path, ...] = ()


def endpoint_key(record: dict[str, Any]) -> tuple[str, str] | None:
    model = record.get("_model")
    endpoint = record.get("_provider_tag")
    if not isinstance(model, str) or not isinstance(endpoint, str):
        return None
    return model, endpoint


def records_from(items: list[LoadedRecord]) -> list[dict[str, Any]]:
    return [item.data for item in items]


def fallback_metric_count(records: list[dict[str, Any]], *, require_complete_decode: bool = False) -> int:
    return sum(
        1
        for record in records
        if phase_for(record) == PHASE_SAMPLE
        and isinstance(record.get("_metric_value"), (int, float))
        and not is_error_record(record)
        and (not require_complete_decode or decode_output_is_complete(record))
    )


def good_sample_count(benchmark: str, records: list[dict[str, Any]]) -> int:
    if benchmark in (BENCHMARK_TIME_BEFORE_PREFILL, BENCHMARK_TIME_BEFORE_PREFILL_CACHED):
        return sum(
            1
            for record in records
            if phase_for(record) == PHASE_SAMPLE and not is_error_record(record)
        )
    if benchmark == BENCHMARK_STANDARD_PREFILL:
        return len(summarize_prefill_metrics(records)) + fallback_metric_count(records)
    if benchmark == BENCHMARK_STANDARD_DECODE:
        return len(summarize_decode_metrics(records)) + fallback_metric_count(
            records,
            require_complete_decode=True,
        )
    raise ValueError(f"Unknown benchmark: {benchmark}")


def next_sample_index(records: list[dict[str, Any]]) -> int:
    indexes = [
        sample_index_for(record)
        for record in records
        if isinstance(record.get("_sample_index"), (int, float))
    ]
    return max(indexes, default=0) + 1


def run_order_value(path: Path) -> int:
    return int(path.name) if path.name.isdigit() else -1


def choose_run_root(counts: Counter[Path], run_roots: list[Path]) -> Path:
    return max(run_roots, key=lambda path: (counts.get(path, 0), run_order_value(path)))


def load_benchmark_records_with_paths(run_root: Path, benchmark: str) -> list[LoadedRecord]:
    definition = BENCHMARK_DEFINITIONS[benchmark]
    run_dir = run_root / definition.directory_name
    if not run_dir.exists():
        return []

    records: list[LoadedRecord] = []
    for path in sorted(run_dir.glob("*.json")):
        data = json.loads(path.read_bytes())
        data.setdefault("_benchmark", benchmark)
        records.append(LoadedRecord(data=data, path=path, run_root=run_root))
    return records


def load_repair_state(
    run_roots: list[Path],
) -> tuple[
    dict[tuple[str, str, str], list[LoadedRecord]],
    dict[tuple[str, str], Counter[Path]],
    dict[tuple[str, str, str], Counter[Path]],
]:
    records_by_combo: dict[tuple[str, str, str], list[LoadedRecord]] = defaultdict(list)
    endpoint_run_counts: dict[tuple[str, str], Counter[Path]] = defaultdict(Counter)
    combo_run_counts: dict[tuple[str, str, str], Counter[Path]] = defaultdict(Counter)

    for run_root in run_roots:
        for benchmark in DEFAULT_BENCHMARKS:
            for item in load_benchmark_records_with_paths(run_root, benchmark):
                key = endpoint_key(item.data)
                if key is None:
                    continue
                combo = (*key, benchmark)
                records_by_combo[combo].append(item)
                endpoint_run_counts[key][run_root] += 1
                combo_run_counts[combo][run_root] += 1

    return records_by_combo, endpoint_run_counts, combo_run_counts


def phase_record_is_good(benchmark: str, phase: str, record: dict[str, Any]) -> bool:
    if is_error_record(record):
        return False
    if benchmark == BENCHMARK_STANDARD_DECODE and phase == PHASE_DECODE:
        return decode_output_is_complete(record)
    return True


def latest_item(items: list[LoadedRecord]) -> LoadedRecord:
    return max(items, key=lambda item: item.path.name)


def bad_phase_paths(benchmark: str, phase: str, items: list[LoadedRecord]) -> tuple[Path, ...]:
    return tuple(
        sorted(
            (
                item.path
                for item in items
                if not phase_record_is_good(benchmark, phase, item.data)
            ),
            key=lambda path: str(path),
        )
    )


def sample_metric_is_good(benchmark: str, records: list[dict[str, Any]]) -> bool:
    if benchmark == BENCHMARK_STANDARD_PREFILL:
        return bool(summarize_prefill_metrics(records))
    if benchmark == BENCHMARK_STANDARD_DECODE:
        return bool(summarize_decode_metrics(records))
    return good_sample_count(benchmark, records) > 0


def phase_repair_groups(
    benchmark: str,
    items: list[LoadedRecord],
) -> list[list[RepairTask]]:
    required_phases = PHASES_BY_BENCHMARK.get(benchmark)
    if not required_phases:
        return []

    grouped: dict[tuple[Path, int], dict[str, list[LoadedRecord]]] = defaultdict(lambda: defaultdict(list))
    for item in items:
        phase = phase_for(item.data)
        if phase == PHASE_SAMPLE:
            continue
        grouped[(item.run_root, sample_index_for(item.data))][phase].append(item)

    repair_groups: list[list[RepairTask]] = []
    for (run_root, sample_index), by_phase in sorted(
        grouped.items(),
        key=lambda entry: (run_order_value(entry[0][0]), entry[0][1]),
    ):
        loaded_records = [item for phase_items in by_phase.values() for item in phase_items]
        records = records_from(loaded_records)
        tasks: list[RepairTask] = []

        for phase in required_phases:
            phase_items = by_phase.get(phase, [])
            if not phase_items:
                seed = latest_item(loaded_records)
                tasks.append(
                    RepairTask(
                        run_root=run_root,
                        model=seed.data["_model"],
                        endpoint=seed.data["_provider_tag"],
                        benchmark=benchmark,
                        sample_index=sample_index,
                        phase=phase,
                    )
                )
                continue

            newest = latest_item(phase_items)
            if not phase_record_is_good(benchmark, phase, newest.data):
                tasks.append(
                    RepairTask(
                        run_root=run_root,
                        model=newest.data["_model"],
                        endpoint=newest.data["_provider_tag"],
                        benchmark=benchmark,
                        sample_index=sample_index,
                        phase=phase,
                        replace_paths=bad_phase_paths(benchmark, phase, phase_items),
                    )
                )

        if not tasks and not sample_metric_is_good(benchmark, records):
            for phase in required_phases:
                phase_items = by_phase[phase]
                newest = latest_item(phase_items)
                tasks.append(
                    RepairTask(
                        run_root=run_root,
                        model=newest.data["_model"],
                        endpoint=newest.data["_provider_tag"],
                        benchmark=benchmark,
                        sample_index=sample_index,
                        phase=phase,
                        replace_paths=tuple(
                            sorted((item.path for item in phase_items), key=lambda path: str(path))
                        ),
                    )
                )

        if tasks:
            repair_groups.append(tasks)

    return repair_groups


def fallback_record_is_bad(benchmark: str, record: dict[str, Any]) -> bool:
    if phase_for(record) != PHASE_SAMPLE:
        return False
    if benchmark in (BENCHMARK_TIME_BEFORE_PREFILL, BENCHMARK_TIME_BEFORE_PREFILL_CACHED):
        return is_error_record(record)
    if benchmark == BENCHMARK_STANDARD_PREFILL:
        return is_error_record(record) or not isinstance(record.get("_metric_value"), (int, float))
    if benchmark == BENCHMARK_STANDARD_DECODE:
        return (
            is_error_record(record)
            or not isinstance(record.get("_metric_value"), (int, float))
            or not decode_output_is_complete(record)
        )
    return False


def fallback_repair_groups(
    benchmark: str,
    items: list[LoadedRecord],
    start_index: int,
) -> list[list[RepairTask]]:
    groups: list[list[RepairTask]] = []
    for item in sorted(items, key=lambda loaded: str(loaded.path)):
        if not fallback_record_is_bad(benchmark, item.data):
            continue
        sample_index = start_index + len(groups)
        groups.append(
            [
                RepairTask(
                    run_root=item.run_root,
                    model=item.data["_model"],
                    endpoint=item.data["_provider_tag"],
                    benchmark=benchmark,
                    sample_index=sample_index,
                    replace_paths=(item.path,),
                )
            ]
        )
    return groups


def plan_repairs(run_roots: list[Path], target_samples: int) -> list[RepairTask]:
    records_by_combo, endpoint_run_counts, combo_run_counts = load_repair_state(run_roots)
    tasks: list[RepairTask] = []

    for model, endpoint in sorted(endpoint_run_counts):
        endpoint_counts = endpoint_run_counts[(model, endpoint)]
        for benchmark in DEFAULT_BENCHMARKS:
            combo = (model, endpoint, benchmark)
            items = records_by_combo.get(combo, [])
            records = records_from(items)
            current = good_sample_count(benchmark, records)
            missing = max(0, target_samples - current)
            if missing == 0:
                continue
            next_full_sample_index = next_sample_index(records)

            for repair_group in phase_repair_groups(benchmark, items):
                if missing == 0:
                    break
                tasks.extend(repair_group)
                missing -= 1

            for repair_group in fallback_repair_groups(benchmark, items, next_full_sample_index):
                if missing == 0:
                    break
                tasks.extend(repair_group)
                next_full_sample_index += 1
                missing -= 1

            if missing == 0:
                continue

            counts = combo_run_counts.get(combo) or endpoint_counts
            run_root = choose_run_root(counts, run_roots)
            for offset in range(missing):
                tasks.append(
                    RepairTask(
                        run_root=run_root,
                        model=model,
                        endpoint=endpoint,
                        benchmark=benchmark,
                        sample_index=next_full_sample_index + offset,
                    )
                )

    return tasks


def print_plan(tasks: list[RepairTask]) -> None:
    print(f"Repair tasks to run: {len(tasks)}")
    replacing = sum(1 for task in tasks if task.replace_paths)
    print(f"  tasks replacing old bad JSONs on success: {replacing}")
    by_action = Counter(f"{task.benchmark}:{task.phase or 'sample'}" for task in tasks)
    for action, count in sorted(by_action.items()):
        print(f"  {action}: {count}")


async def run_benchmark_phase(
    client: httpx.AsyncClient,
    config: BenchmarkConfig,
    api_key: str,
    benchmark: str,
    provider_tag: str,
    sample_index: int,
    phase: str,
    run_dir: Path,
    semaphore: asyncio.Semaphore,
) -> list[dict[str, Any]]:
    if benchmark not in PHASES_BY_BENCHMARK or phase not in PHASES_BY_BENCHMARK[benchmark]:
        raise ValueError(f"Cannot repair phase {phase!r} for benchmark {benchmark!r}.")

    if phase == PHASE_BASELINE:
        prompt = config.latency_prompt
        max_tokens = config.latency_max_tokens
    elif phase in (PHASE_PREFILL, PHASE_PREFILL_PROBE):
        prompt = config.prefill_prompt
        max_tokens = config.prefill_max_tokens
    elif phase == PHASE_DECODE:
        prompt = config.decode_prompt
        max_tokens = config.decode_max_tokens
    else:
        raise ValueError(f"Unknown phase: {phase}")

    async with semaphore:
        data = await request_once_async(
            client,
            api_key=api_key,
            model=config.model,
            provider_tag=provider_tag,
            messages=[{"role": "user", "content": prompt}],
            max_retries=config.max_retries,
            extra_payload=benchmark_payload(max_tokens, config.temperature),
        )

    annotate_record(
        data,
        benchmark=benchmark,
        phase=phase,
        sample_index=sample_index,
    )
    write_result(data, run_dir)
    return [data]


def task_result_is_good(task: RepairTask, records: list[dict[str, Any]]) -> bool:
    if task.phase is not None:
        return bool(records) and phase_record_is_good(task.benchmark, task.phase, records[-1])
    return good_sample_count(task.benchmark, records) > 0


def path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def delete_replaced_paths(paths: tuple[Path, ...], run_roots: list[Path]) -> int:
    allowed_roots = [root.resolve() for root in run_roots]
    deleted = 0
    for path in sorted(set(paths), key=lambda item: str(item)):
        resolved = path.resolve()
        if path.suffix.lower() != ".json" or not any(
            path_is_relative_to(resolved, root) for root in allowed_roots
        ):
            raise RuntimeError(f"Refusing to delete unexpected path: {path}")
        path.unlink(missing_ok=True)
        deleted += 1
    return deleted


async def run_repairs(
    tasks: list[RepairTask],
    *,
    run_roots: list[Path],
    concurrency: int,
    max_retries: int,
) -> None:
    api_key = get_api_key()
    semaphore = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    remaining = len(tasks)
    configs: dict[str, BenchmarkConfig] = {}

    async with httpx.AsyncClient(timeout=120.0) as client:
        async def run_task(task: RepairTask) -> None:
            nonlocal remaining
            config = configs.setdefault(
                task.model,
                BenchmarkConfig(model=task.model, max_retries=max_retries),
            )
            run_dir = benchmark_run_dir(task.run_root, task.benchmark)
            action = task.phase or "sample"
            status = "ok"
            try:
                if task.phase is None:
                    records = await run_benchmark_sample(
                        client,
                        config,
                        api_key,
                        task.benchmark,
                        task.endpoint,
                        task.sample_index,
                        run_dir,
                        semaphore,
                    )
                else:
                    records = await run_benchmark_phase(
                        client,
                        config,
                        api_key,
                        task.benchmark,
                        task.endpoint,
                        task.sample_index,
                        task.phase,
                        run_dir,
                        semaphore,
                    )

                if task_result_is_good(task, records):
                    deleted = delete_replaced_paths(task.replace_paths, run_roots) if task.replace_paths else 0
                    if deleted:
                        status = f"ok; deleted {deleted} old bad json"
                else:
                    status = "bad response; kept old json"
            except Exception as exc:  # noqa: BLE001 - keep repairing other endpoints.
                status = f"failed: {exc}"

            async with lock:
                remaining -= 1
                print(
                    f"{remaining} left | run {task.run_root.name} | {task.model} | "
                    f"{task.endpoint} | {task.benchmark} | {action} {task.sample_index} | {status}",
                    flush=True,
                )

        await asyncio.gather(*(run_task(task) for task in tasks))


def print_remaining(run_roots: list[Path], target_samples: int) -> None:
    remaining = plan_repairs(run_roots, target_samples)
    print(f"Remaining repair tasks after pass: {len(remaining)}")
    by_action = Counter(f"{task.benchmark}:{task.phase or 'sample'}" for task in remaining)
    for action, count in sorted(by_action.items()):
        print(f"  {action}: {count}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="+", default=list(DEFAULT_RUNS))
    parser.add_argument("--target", type=int, default=TARGET_SAMPLES)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_roots = [RUNS_ROOT / str(run_id) for run_id in args.runs]
    missing = [str(path) for path in run_roots if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Run directories not found: {', '.join(missing)}")

    tasks = plan_repairs(run_roots, args.target)
    print_plan(tasks)
    if args.dry_run or not tasks:
        return

    asyncio.run(
        run_repairs(
            tasks,
            run_roots=run_roots,
            concurrency=max(1, args.concurrency),
            max_retries=max(0, args.max_retries),
        )
    )
    print_remaining(run_roots, args.target)


if __name__ == "__main__":
    main()
