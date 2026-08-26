#!/usr/bin/env python3
"""Reusable OpenRouter latency benchmark helpers."""

from __future__ import annotations

import asyncio
import json
import os
import statistics
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_ROOT = PROJECT_ROOT / "prompts"
RUNS_ROOT = PROJECT_ROOT / "runs"
LOAD_WORKERS = min(32, max(4, (os.cpu_count() or 1) * 4))
PARALLEL_LOAD_THRESHOLD = 24

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
ENDPOINTS_URL = "https://openrouter.ai/api/v1/models/{model}/endpoints"

BENCHMARK_TIME_BEFORE_PREFILL = "time_before_prefill"
BENCHMARK_STANDARD_PREFILL = "standard_prefill"
BENCHMARK_STANDARD_DECODE = "standard_decode"
BENCHMARK_TIME_BEFORE_PREFILL_CACHED = "time_before_prefill_prompt_cached"

PHASE_SAMPLE = "sample"
PHASE_BASELINE = "baseline"
PHASE_PREFILL = "prefill"
PHASE_PREFILL_PROBE = "prefill_probe"
PHASE_DECODE = "decode"

DEFAULT_BENCHMARKS = (
    BENCHMARK_TIME_BEFORE_PREFILL,
    BENCHMARK_STANDARD_PREFILL,
    BENCHMARK_STANDARD_DECODE,
    BENCHMARK_TIME_BEFORE_PREFILL_CACHED,
)

DEFAULT_LATENCY_PROMPT_PATH = PROMPTS_ROOT / "on_belay.md"
DEFAULT_PREFILL_PROMPT_PATH = PROMPTS_ROOT / "lorem_ipsum_100_paragraphs.md"
DEFAULT_DECODE_PROMPT_PATH = PROMPTS_ROOT / "lorem_ipsum_1_paragraph.md"


@dataclass(frozen=True, slots=True)
class BenchmarkDefinition:
    label: str
    directory_name: str
    metric_label: str = ""


BENCHMARK_DEFINITIONS = {
    BENCHMARK_TIME_BEFORE_PREFILL: BenchmarkDefinition(
        "Time before prefill",
        BENCHMARK_TIME_BEFORE_PREFILL,
    ),
    BENCHMARK_STANDARD_PREFILL: BenchmarkDefinition(
        "Standard prefill",
        BENCHMARK_STANDARD_PREFILL,
        "standard prefill/s",
    ),
    BENCHMARK_STANDARD_DECODE: BenchmarkDefinition(
        "Standard decode",
        BENCHMARK_STANDARD_DECODE,
        "standard decode/s",
    ),
    BENCHMARK_TIME_BEFORE_PREFILL_CACHED: BenchmarkDefinition(
        "Time before prefill, prompt cached",
        BENCHMARK_TIME_BEFORE_PREFILL_CACHED,
    ),
}


@dataclass(slots=True)
class BenchmarkConfig:
    model: str
    provider_tags: Sequence[str] | None = None
    benchmarks: Sequence[str] = DEFAULT_BENCHMARKS
    samples: int = 3
    concurrency: int = 20
    max_retries: int = 3
    timeout_seconds: float = 120.0
    api_key: str | None = None
    run_root: Path | None = None
    latency_prompt: str = field(default_factory=lambda: read_prompt(DEFAULT_LATENCY_PROMPT_PATH))
    prefill_prompt: str = field(default_factory=lambda: read_prompt(DEFAULT_PREFILL_PROMPT_PATH))
    decode_prompt: str = field(default_factory=lambda: read_prompt(DEFAULT_DECODE_PROMPT_PATH))
    temperature: float = 0.0
    latency_max_tokens: int = 16
    prefill_max_tokens: int = 16
    decode_max_tokens: int = 1000


def read_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def get_api_key(api_key: str | None = None) -> str:
    value = (api_key or os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not value:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")
    return value


def headers_for(api_key: str, *, router_metadata: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if router_metadata:
        headers["X-OpenRouter-Metadata"] = "enabled"
    return headers


def parse_model_slugs(raw: str) -> list[str]:
    seen: set[str] = set()
    slugs: list[str] = []
    for part in raw.replace(",", "\n").splitlines():
        for slug in part.split():
            slug = slug.strip()
            if slug and slug not in seen:
                seen.add(slug)
                slugs.append(slug)
    return slugs


def normalize_benchmarks(benchmarks: Iterable[str] | None) -> list[str]:
    selected = [b for b in benchmarks or DEFAULT_BENCHMARKS if b in BENCHMARK_DEFINITIONS]
    return selected or list(DEFAULT_BENCHMARKS)


def run_sync(awaitable: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    raise RuntimeError("Sync helpers cannot be called from inside an existing event loop.")


async def _fetch_endpoints_with_client(
    client: httpx.AsyncClient,
    model: str,
    api_key: str,
) -> list[dict[str, Any]]:
    resp = await client.get(ENDPOINTS_URL.format(model=model), headers=headers_for(api_key))
    data = resp.json()
    if resp.status_code >= 400:
        message = data.get("error", {}).get("message", resp.text)
        raise RuntimeError(f"Endpoint lookup failed for {model}: {message}")

    section = data.get("data", {})
    endpoints = section.get("endpoints", []) if isinstance(section, dict) else section
    return [ep for ep in endpoints if isinstance(ep, dict) and ep.get("tag")]


async def fetch_endpoints_async(
    model: str,
    api_key: str | None = None,
    timeout_seconds: float = 60.0,
) -> list[dict[str, Any]]:
    key = get_api_key(api_key)
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        return await _fetch_endpoints_with_client(client, model, key)


def fetch_endpoints(
    model: str,
    api_key: str | None = None,
    timeout_seconds: float = 60.0,
) -> list[dict[str, Any]]:
    return run_sync(fetch_endpoints_async(model, api_key, timeout_seconds))


async def fetch_provider_tags_async(
    model: str,
    api_key: str | None = None,
    timeout_seconds: float = 60.0,
) -> list[str]:
    endpoints = await fetch_endpoints_async(model, api_key, timeout_seconds)
    return [ep["tag"] for ep in endpoints]


def fetch_provider_tags(
    model: str,
    api_key: str | None = None,
    timeout_seconds: float = 60.0,
) -> list[str]:
    return run_sync(fetch_provider_tags_async(model, api_key, timeout_seconds))


async def request_once_async(
    client: httpx.AsyncClient,
    *,
    api_key: str,
    model: str,
    provider_tag: str,
    messages: list[dict[str, str]],
    max_retries: int,
    session_id: str | None = None,
    extra_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "provider": {"only": [provider_tag]},
    }
    if session_id is not None:
        payload["session_id"] = session_id
    for key, value in (extra_payload or {}).items():
        if value is not None:
            payload[key] = value

    data: dict[str, Any] = {}
    status_code: int | None = None
    time_start = 0
    time_end = 0
    attempt = 0

    for attempt in range(max_retries + 1):
        time_start = time.time_ns()
        try:
            resp = await client.post(
                CHAT_URL,
                headers=headers_for(api_key, router_metadata=True),
                json=payload,
            )
            time_end = time.time_ns()
            status_code = resp.status_code
            try:
                data = resp.json()
            except ValueError:
                data = {"_error": resp.text}
            if status_code >= 400 and "error" not in data:
                data["error"] = {"message": resp.text, "status_code": status_code}
        except Exception as exc:  # noqa: BLE001 - raw response files should capture failures.
            time_end = time.time_ns()
            data = {"_error": str(exc)}

        if ("error" not in data and "_error" not in data) or attempt == max_retries:
            break

    data["_time_start"] = time_start
    data["_time_end"] = time_end
    data["_model"] = model
    data["_provider_tag"] = provider_tag
    return data


def response_content(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message", {})
    content = message.get("content", "")
    return content if isinstance(content, str) else ""


def elapsed_ms(data: dict[str, Any]) -> float:
    return (data["_time_end"] - data["_time_start"]) / 1_000_000


def elapsed_seconds(data: dict[str, Any]) -> float:
    return elapsed_ms(data) / 1000


def record_elapsed_ms(data: dict[str, Any]) -> float:
    return elapsed_ms(data)


def per_second(seconds: float) -> float | None:
    return 1 / seconds if seconds > 0 else None


def benchmark_payload(max_tokens: int | None, temperature: float) -> dict[str, Any]:
    return {
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


def next_run_root(root: Path = RUNS_ROOT) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    existing = [int(p.name) for p in root.iterdir() if p.is_dir() and p.name.isdigit()]
    run_dir = root / str(max(existing, default=0) + 1)
    run_dir.mkdir(parents=True)
    return run_dir


def latest_run_root(root: Path = RUNS_ROOT) -> Path:
    runs = [p for p in root.iterdir() if p.is_dir() and p.name.isdigit()]
    if not runs:
        raise FileNotFoundError(f"No numbered runs found under {root}.")
    return max(runs, key=lambda p: int(p.name))


def list_run_roots(root: Path = RUNS_ROOT) -> list[Path]:
    if not root.exists():
        return []
    runs = [p for p in root.iterdir() if p.is_dir() and p.name.isdigit()]
    return sorted(runs, key=lambda p: int(p.name), reverse=True)


def benchmark_run_dir(run_root: Path, benchmark: str) -> Path:
    run_dir = run_root / BENCHMARK_DEFINITIONS[benchmark].directory_name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def prepare_benchmark_run_dirs(run_root: Path, benchmarks: Iterable[str]) -> dict[str, Path]:
    return {benchmark: benchmark_run_dir(run_root, benchmark) for benchmark in benchmarks}


def write_result(data: dict[str, Any], run_dir: Path) -> Path:
    filename = f"{time.time_ns()}_{uuid.uuid4()}.json"
    path = run_dir / filename
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def annotate_record(
    data: dict[str, Any],
    *,
    benchmark: str,
    phase: str,
    sample_index: int,
) -> dict[str, Any]:
    data["_benchmark"] = benchmark
    if phase != PHASE_SAMPLE:
        data["_phase"] = phase
        data["_sample_index"] = sample_index
    return data


async def run_time_before_prefill_sample(
    client: httpx.AsyncClient,
    config: BenchmarkConfig,
    api_key: str,
    provider_tag: str,
    sample_index: int,
    run_dir: Path,
) -> list[dict[str, Any]]:
    data = await request_once_async(
        client,
        api_key=api_key,
        model=config.model,
        provider_tag=provider_tag,
        messages=[{"role": "user", "content": config.latency_prompt}],
        max_retries=config.max_retries,
        extra_payload=benchmark_payload(config.latency_max_tokens, config.temperature),
    )
    annotate_record(
        data,
        benchmark=BENCHMARK_TIME_BEFORE_PREFILL,
        phase=PHASE_SAMPLE,
        sample_index=sample_index,
    )
    write_result(data, run_dir)
    return [data]


async def run_cached_time_before_prefill_sample(
    client: httpx.AsyncClient,
    config: BenchmarkConfig,
    api_key: str,
    provider_tag: str,
    sample_index: int,
    run_dir: Path,
) -> list[dict[str, Any]]:
    session_id = str(uuid.uuid4())
    seed = await request_once_async(
        client,
        api_key=api_key,
        model=config.model,
        provider_tag=provider_tag,
        messages=[{"role": "user", "content": config.latency_prompt}],
        max_retries=config.max_retries,
        session_id=session_id,
        extra_payload=benchmark_payload(config.latency_max_tokens, config.temperature),
    )
    messages = [
        {"role": "user", "content": config.latency_prompt},
        {"role": "assistant", "content": response_content(seed)},
        {"role": "user", "content": config.latency_prompt},
    ]
    data = await request_once_async(
        client,
        api_key=api_key,
        model=config.model,
        provider_tag=provider_tag,
        messages=messages,
        max_retries=config.max_retries,
        session_id=session_id,
        extra_payload=benchmark_payload(config.latency_max_tokens, config.temperature),
    )
    annotate_record(
        data,
        benchmark=BENCHMARK_TIME_BEFORE_PREFILL_CACHED,
        phase=PHASE_SAMPLE,
        sample_index=sample_index,
    )
    write_result(data, run_dir)
    return [data]


async def run_standard_prefill_sample(
    client: httpx.AsyncClient,
    config: BenchmarkConfig,
    api_key: str,
    provider_tag: str,
    sample_index: int,
    run_dir: Path,
) -> list[dict[str, Any]]:
    baseline = await request_once_async(
        client,
        api_key=api_key,
        model=config.model,
        provider_tag=provider_tag,
        messages=[{"role": "user", "content": config.latency_prompt}],
        max_retries=config.max_retries,
        extra_payload=benchmark_payload(config.latency_max_tokens, config.temperature),
    )
    data = await request_once_async(
        client,
        api_key=api_key,
        model=config.model,
        provider_tag=provider_tag,
        messages=[{"role": "user", "content": config.prefill_prompt}],
        max_retries=config.max_retries,
        extra_payload=benchmark_payload(config.prefill_max_tokens, config.temperature),
    )
    annotate_record(
        baseline,
        benchmark=BENCHMARK_STANDARD_PREFILL,
        phase=PHASE_BASELINE,
        sample_index=sample_index,
    )
    annotate_record(
        data,
        benchmark=BENCHMARK_STANDARD_PREFILL,
        phase=PHASE_PREFILL,
        sample_index=sample_index,
    )
    write_result(baseline, run_dir)
    write_result(data, run_dir)
    return [baseline, data]


async def run_standard_decode_sample(
    client: httpx.AsyncClient,
    config: BenchmarkConfig,
    api_key: str,
    provider_tag: str,
    sample_index: int,
    run_dir: Path,
) -> list[dict[str, Any]]:
    baseline = await request_once_async(
        client,
        api_key=api_key,
        model=config.model,
        provider_tag=provider_tag,
        messages=[{"role": "user", "content": config.latency_prompt}],
        max_retries=config.max_retries,
        extra_payload=benchmark_payload(config.latency_max_tokens, config.temperature),
    )
    prefill_probe = await request_once_async(
        client,
        api_key=api_key,
        model=config.model,
        provider_tag=provider_tag,
        messages=[{"role": "user", "content": config.prefill_prompt}],
        max_retries=config.max_retries,
        extra_payload=benchmark_payload(config.prefill_max_tokens, config.temperature),
    )
    data = await request_once_async(
        client,
        api_key=api_key,
        model=config.model,
        provider_tag=provider_tag,
        messages=[{"role": "user", "content": config.decode_prompt}],
        max_retries=config.max_retries,
        extra_payload=benchmark_payload(config.decode_max_tokens, config.temperature),
    )
    annotate_record(
        baseline,
        benchmark=BENCHMARK_STANDARD_DECODE,
        phase=PHASE_BASELINE,
        sample_index=sample_index,
    )
    annotate_record(
        prefill_probe,
        benchmark=BENCHMARK_STANDARD_DECODE,
        phase=PHASE_PREFILL_PROBE,
        sample_index=sample_index,
    )
    annotate_record(
        data,
        benchmark=BENCHMARK_STANDARD_DECODE,
        phase=PHASE_DECODE,
        sample_index=sample_index,
    )
    write_result(baseline, run_dir)
    write_result(prefill_probe, run_dir)
    write_result(data, run_dir)
    return [baseline, prefill_probe, data]


async def run_benchmark_sample(
    client: httpx.AsyncClient,
    config: BenchmarkConfig,
    api_key: str,
    benchmark: str,
    provider_tag: str,
    sample_index: int,
    run_dir: Path,
    semaphore: asyncio.Semaphore,
) -> list[dict[str, Any]]:
    async with semaphore:
        if benchmark == BENCHMARK_TIME_BEFORE_PREFILL:
            return await run_time_before_prefill_sample(
                client, config, api_key, provider_tag, sample_index, run_dir
            )
        if benchmark == BENCHMARK_TIME_BEFORE_PREFILL_CACHED:
            return await run_cached_time_before_prefill_sample(
                client, config, api_key, provider_tag, sample_index, run_dir
            )
        if benchmark == BENCHMARK_STANDARD_PREFILL:
            return await run_standard_prefill_sample(
                client, config, api_key, provider_tag, sample_index, run_dir
            )
        if benchmark == BENCHMARK_STANDARD_DECODE:
            return await run_standard_decode_sample(
                client, config, api_key, provider_tag, sample_index, run_dir
            )
        raise ValueError(f"Unknown benchmark: {benchmark}")


async def run_benchmarks_async(config: BenchmarkConfig) -> dict[str, Any]:
    api_key = get_api_key(config.api_key)
    benchmarks = normalize_benchmarks(config.benchmarks)
    samples = max(1, int(config.samples))
    concurrency = max(1, int(config.concurrency))
    run_root = config.run_root or next_run_root()
    run_dirs = prepare_benchmark_run_dirs(run_root, benchmarks)

    async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
        provider_tags = list(config.provider_tags or [])
        if not provider_tags:
            endpoints = await _fetch_endpoints_with_client(client, config.model, api_key)
            provider_tags = [ep["tag"] for ep in endpoints]

        semaphore = asyncio.Semaphore(concurrency)
        tasks = [
            asyncio.create_task(
                run_benchmark_sample(
                    client,
                    config,
                    api_key,
                    benchmark,
                    provider_tag,
                    sample_index,
                    run_dirs[benchmark],
                    semaphore,
                )
            )
            for benchmark in benchmarks
            for provider_tag in provider_tags
            for sample_index in range(1, samples + 1)
        ]
        grouped_results = await asyncio.gather(*tasks)
        results = [record for group in grouped_results for record in group]

    return {
        "model": config.model,
        "provider_tags": provider_tags,
        "benchmarks": benchmarks,
        "run_root": str(run_root),
        "run_dirs": {key: str(path) for key, path in run_dirs.items()},
        "results": results,
        "summary": summarize_records(results),
    }


def run_benchmarks(config: BenchmarkConfig) -> dict[str, Any]:
    return run_sync(run_benchmarks_async(config))


def is_error_record(data: dict[str, Any]) -> bool:
    return "error" in data or "_error" in data


def response_cost(data: dict[str, Any]) -> float:
    return float(data.get("usage", {}).get("cost_details", {}).get("upstream_inference_cost", 0) or 0)


def summary_label(benchmark: str) -> str:
    definition = BENCHMARK_DEFINITIONS.get(benchmark)
    return definition.label if definition else benchmark


def summary_metric_label(benchmark: str) -> str:
    definition = BENCHMARK_DEFINITIONS.get(benchmark)
    return definition.metric_label if definition else ""


def phase_for(data: dict[str, Any]) -> str:
    phase = data.get("_phase")
    return phase if isinstance(phase, str) else PHASE_SAMPLE


def sample_index_for(data: dict[str, Any]) -> int:
    value = data.get("_sample_index")
    return int(value) if isinstance(value, (int, float)) else 0


def summarize_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for data in records:
        benchmark = data.get("_benchmark", "unknown")
        key = (
            data.get("_model", "unknown"),
            data.get("_provider_tag", "unknown"),
            benchmark,
        )
        grouped[key].append(data)

    summary: list[dict[str, Any]] = []
    for (model, endpoint, benchmark), group_records in grouped.items():
        elapsed_values: list[float] = []
        metric_values: list[float] = []

        if benchmark in (BENCHMARK_TIME_BEFORE_PREFILL, BENCHMARK_TIME_BEFORE_PREFILL_CACHED):
            elapsed_values = [
                record_elapsed_ms(data)
                for data in group_records
                if phase_for(data) == PHASE_SAMPLE and not is_error_record(data)
            ]
        elif benchmark == BENCHMARK_STANDARD_PREFILL:
            metric_values = summarize_prefill_metrics(group_records)
        elif benchmark == BENCHMARK_STANDARD_DECODE:
            metric_values = summarize_decode_metrics(group_records)

        # Backward compatibility for older saved runs; new JSONs do not store metrics.
        if not metric_values:
            metric_values = [
                float(data["_metric_value"])
                for data in group_records
                if isinstance(data.get("_metric_value"), (int, float)) and not is_error_record(data)
            ]
        if not elapsed_values and benchmark not in (BENCHMARK_STANDARD_PREFILL, BENCHMARK_STANDARD_DECODE):
            elapsed_values = [record_elapsed_ms(data) for data in group_records if not is_error_record(data)]

        summary.append(
            {
                "model": model,
                "endpoint": endpoint,
                "benchmark": benchmark,
                "benchmark_label": summary_label(benchmark),
                "metric_label": summary_metric_label(benchmark),
                "median_elapsed_ms": statistics.median(elapsed_values) if elapsed_values else None,
                "median_metric": statistics.median(metric_values) if metric_values else None,
                "cost": sum(response_cost(data) for data in group_records),
                "errors": sum(1 for data in group_records if is_error_record(data)),
                "n": len(group_records),
            }
        )

    return sorted(summary, key=lambda item: (item["model"], item["benchmark"], item["endpoint"]))


def summarize_prefill_metrics(records: list[dict[str, Any]]) -> list[float]:
    metrics: list[float] = []
    by_sample: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for data in records:
        by_sample[sample_index_for(data)][phase_for(data)] = data

    for phases in by_sample.values():
        baseline = phases.get(PHASE_BASELINE)
        prefill = phases.get(PHASE_PREFILL)
        if not baseline or not prefill or is_error_record(baseline) or is_error_record(prefill):
            continue
        metric = per_second(max(elapsed_seconds(prefill) - elapsed_seconds(baseline), 0))
        if metric is not None:
            metrics.append(metric)
    return metrics


def summarize_decode_metrics(records: list[dict[str, Any]]) -> list[float]:
    metrics: list[float] = []
    by_sample: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for data in records:
        by_sample[sample_index_for(data)][phase_for(data)] = data

    for phases in by_sample.values():
        baseline = phases.get(PHASE_BASELINE)
        prefill_probe = phases.get(PHASE_PREFILL_PROBE)
        decode = phases.get(PHASE_DECODE)
        if (
            not baseline
            or not prefill_probe
            or not decode
            or is_error_record(baseline)
            or is_error_record(prefill_probe)
            or is_error_record(decode)
        ):
            continue

        baseline_seconds = elapsed_seconds(baseline)
        prefill_seconds = max(elapsed_seconds(prefill_probe) - baseline_seconds, 0)
        decode_seconds = max(elapsed_seconds(decode) - prefill_seconds - baseline_seconds, 0)
        metric = per_second(decode_seconds)
        if metric is not None:
            metrics.append(metric)
    return metrics


def load_json_record(path: Path) -> dict[str, Any]:
    return json.loads(path.read_bytes())


def load_records(run_dir: Path) -> list[dict[str, Any]]:
    paths = sorted(run_dir.glob("*.json"))
    if len(paths) < PARALLEL_LOAD_THRESHOLD:
        return [load_json_record(path) for path in paths]

    with ThreadPoolExecutor(max_workers=LOAD_WORKERS) as executor:
        return list(executor.map(load_json_record, paths))


def load_benchmark_run(run_root: Path, benchmarks: Iterable[str] | None = None) -> list[dict[str, Any]]:
    if not run_root.exists() or not run_root.is_dir():
        raise FileNotFoundError(f"Run not found: {run_root}")

    records: list[dict[str, Any]] = []
    selected = normalize_benchmarks(benchmarks)
    existing = [
        (benchmark, run_root / BENCHMARK_DEFINITIONS[benchmark].directory_name)
        for benchmark in selected
        if (run_root / BENCHMARK_DEFINITIONS[benchmark].directory_name).exists()
    ]

    def load_benchmark_dir(item: tuple[str, Path]) -> list[dict[str, Any]]:
        benchmark, run_dir = item
        benchmark_records = load_records(run_dir)
        for data in benchmark_records:
            data.setdefault("_benchmark", benchmark)
        return benchmark_records

    if len(existing) < 2:
        loaded = [load_benchmark_dir(item) for item in existing]
    else:
        with ThreadPoolExecutor(max_workers=min(len(existing), LOAD_WORKERS)) as executor:
            loaded = list(executor.map(load_benchmark_dir, existing))

    for benchmark_records in loaded:
        records.extend(benchmark_records)
    return records


def summarize_run(run_root: Path, benchmarks: Iterable[str] | None = None) -> list[dict[str, Any]]:
    return summarize_records(load_benchmark_run(run_root, benchmarks))


def load_elapsed_stats(run_dir: Path) -> tuple[dict[str, list[float]], float, int]:
    elapsed_by_endpoint: dict[str, list[float]] = {}
    total_cost = 0.0
    error_count = 0

    for data in load_records(run_dir):
        if is_error_record(data):
            error_count += 1
            continue

        provider_tag = data.get("_provider_tag", "unknown")
        model = data.get("_model")
        endpoint = f"{model} | {provider_tag}" if model else provider_tag
        elapsed_by_endpoint.setdefault(endpoint, []).append(record_elapsed_ms(data))
        total_cost += response_cost(data)

    return elapsed_by_endpoint, total_cost, error_count
