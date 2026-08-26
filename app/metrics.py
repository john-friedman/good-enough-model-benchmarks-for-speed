#!/usr/bin/env python3
"""Print median time-before-prefill stats for the latest cold/cached runs."""

import statistics
import sys

try:
    from .utils import (
        BENCHMARK_DEFINITIONS,
        BENCHMARK_TIME_BEFORE_PREFILL,
        BENCHMARK_TIME_BEFORE_PREFILL_CACHED,
        RUNS_ROOT,
        latest_run_root,
        load_elapsed_stats,
    )
except ImportError:  # pragma: no cover - supports `python app/metrics.py`.
    from utils import (
        BENCHMARK_DEFINITIONS,
        BENCHMARK_TIME_BEFORE_PREFILL,
        BENCHMARK_TIME_BEFORE_PREFILL_CACHED,
        RUNS_ROOT,
        latest_run_root,
        load_elapsed_stats,
    )


def main() -> None:
    if len(sys.argv) > 1:
        run_root = RUNS_ROOT / sys.argv[1]
    else:
        run_root = latest_run_root()

    cold_dir = run_root / BENCHMARK_DEFINITIONS[BENCHMARK_TIME_BEFORE_PREFILL].directory_name
    cached_dir = run_root / BENCHMARK_DEFINITIONS[BENCHMARK_TIME_BEFORE_PREFILL_CACHED].directory_name

    cold_stats, cold_cost, cold_errors = load_elapsed_stats(cold_dir)
    cached_stats, cached_cost, cached_errors = load_elapsed_stats(cached_dir)

    endpoints = sorted(set(cold_stats) | set(cached_stats))

    print(f"Cold run:   {cold_dir}")
    print(f"Cached run: {cached_dir}")
    print()
    print(f"{'Endpoint':<25} {'Cold (ms)':>10} {'N':>4} {'Cached (ms)':>12} {'N':>4}")
    for endpoint in endpoints:
        cold_times = cold_stats.get(endpoint, [])
        cached_times = cached_stats.get(endpoint, [])
        cold_median = f"{statistics.median(cold_times):.1f}" if cold_times else "-"
        cached_median = f"{statistics.median(cached_times):.1f}" if cached_times else "-"
        print(f"{endpoint:<25} {cold_median:>10} {len(cold_times):>4} {cached_median:>12} {len(cached_times):>4}")

    print(f"\nTotal cost (cold):   ${cold_cost:.6f}")
    print(f"Total cost (cached): ${cached_cost:.6f}")
    if cold_errors:
        print(f"Skipped errored responses (cold): {cold_errors}")
    if cached_errors:
        print(f"Skipped errored responses (cached): {cached_errors}")


if __name__ == "__main__":
    main()
