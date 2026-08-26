#!/usr/bin/env python3
"""Flask UI for OpenRouter latency benchmarks."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, redirect, render_template, request, url_for

try:
    from .utils import (
        BENCHMARK_DEFINITIONS,
        BENCHMARK_STANDARD_DECODE,
        BENCHMARK_STANDARD_PREFILL,
        BENCHMARK_TIME_BEFORE_PREFILL,
        BENCHMARK_TIME_BEFORE_PREFILL_CACHED,
        DEFAULT_BENCHMARKS,
        RUNS_ROOT,
        BenchmarkConfig,
        fetch_endpoints,
        list_run_roots,
        load_benchmark_run,
        next_run_root,
        normalize_benchmarks,
        parse_model_slugs,
        run_benchmarks,
        summarize_records,
    )
except ImportError:  # pragma: no cover - supports `python app/app.py`.
    from utils import (
        BENCHMARK_DEFINITIONS,
        BENCHMARK_STANDARD_DECODE,
        BENCHMARK_STANDARD_PREFILL,
        BENCHMARK_TIME_BEFORE_PREFILL,
        BENCHMARK_TIME_BEFORE_PREFILL_CACHED,
        DEFAULT_BENCHMARKS,
        RUNS_ROOT,
        BenchmarkConfig,
        fetch_endpoints,
        list_run_roots,
        load_benchmark_run,
        next_run_root,
        normalize_benchmarks,
        parse_model_slugs,
        run_benchmarks,
        summarize_records,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = PROJECT_ROOT / "ui"

app = Flask(
    __name__,
    template_folder=str(UI_ROOT / "templates"),
    static_folder=str(UI_ROOT / "static"),
    static_url_path="/static",
)

DEFAULT_MODEL_SLUGS = (
    "openai/gpt-oss-120b",
    "deepseek/deepseek-v4-flash-0731",
    "google/gemini-3.7-flash",
    "google/gemini-3.5-flash-lite",
    "openai/gpt-5.6-luna",
    "qwen/qwen3.8-27b",
    "xiaomi/mimo-v2.5",
    "mistralai/mistral-nemo",
    "anthropic/claude-sonnet-5",
)
DEFAULT_MODELS_RAW = "\n".join(DEFAULT_MODEL_SLUGS)


def as_int(value: str | None, default: int) -> int:
    try:
        return max(0, int(value or default))
    except ValueError:
        return default


def selected_endpoints() -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for value in request.form.getlist("endpoint"):
        if "|||" not in value:
            continue
        model, tag = value.split("|||", 1)
        if model and tag:
            grouped[model].append(tag)
    return dict(grouped)


def discover_models(models: list[str]) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    discovered: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []
    for model in models:
        try:
            endpoints = fetch_endpoints(model)
            if endpoints:
                discovered[model] = endpoints
            else:
                errors.append(f"No endpoints returned for {model}.")
        except Exception as exc:  # noqa: BLE001 - render local tool failures in the UI.
            errors.append(str(exc))
    return discovered, errors


def model_display_name(model: str) -> str:
    name = model.split("/")[-1]
    name = re.sub(r"[-_]+", " ", name)
    name = re.sub(r"(?<=\d)(?=[A-Za-z])|(?<=[A-Za-z])(?=\d)", " ", name)
    return re.sub(r"\s+", " ", name).strip().lower()


def format_ms(value: float | None) -> str:
    return f"{value:.1f}" if value is not None else "-"


def format_rate(value: float | None) -> str:
    return f"{value:.3f}" if value is not None else "-"


def format_cost(value: float) -> str:
    if 0 < value < 0.000001:
        return "<$0.000001"
    return f"${value:.6f}"


def numeric_sort_value(value: float | None, *, reverse_missing: bool = False) -> float:
    if value is None:
        return -1 if reverse_missing else 1_000_000_000
    return float(value)


def run_heading(run_id: str, records: list[dict[str, Any]]) -> str:
    for record in records:
        time_start = record.get("_time_start")
        if not isinstance(time_start, (int, float)):
            continue
        started_at = datetime.fromtimestamp(time_start / 1_000_000_000).astimezone()
        return f"Run {run_id}: {started_at:%Y-%m-%d %I:%M:%S %p %Z}".strip()
    return f"Run {run_id}"


def build_result_tables(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_model: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    for summary in summaries:
        model = summary["model"]
        endpoint = summary["endpoint"]
        benchmark = summary["benchmark"]
        by_model[model].setdefault(endpoint, {})[benchmark] = summary

    tables: list[dict[str, Any]] = []
    for index, model in enumerate(sorted(by_model)):
        rows: list[dict[str, Any]] = []
        total_cost = sum(
            float(summary.get("cost") or 0)
            for benchmarks in by_model[model].values()
            for summary in benchmarks.values()
        )
        for endpoint, benchmarks in by_model[model].items():
            cold = benchmarks.get(BENCHMARK_TIME_BEFORE_PREFILL, {})
            cached = benchmarks.get(BENCHMARK_TIME_BEFORE_PREFILL_CACHED, {})
            prefill = benchmarks.get(BENCHMARK_STANDARD_PREFILL, {})
            decode = benchmarks.get(BENCHMARK_STANDARD_DECODE, {})

            cold_ms = cold.get("median_elapsed_ms")
            cached_ms = cached.get("median_elapsed_ms")
            prefill_rate = prefill.get("median_metric")
            decode_rate = decode.get("median_metric")

            rows.append(
                {
                    "endpoint": endpoint,
                    "time_before_prefill": format_ms(cold_ms),
                    "time_before_prefill_sort": numeric_sort_value(cold_ms),
                    "cached": format_ms(cached_ms),
                    "cached_sort": numeric_sort_value(cached_ms),
                    "prefill": format_rate(prefill_rate),
                    "prefill_sort": numeric_sort_value(prefill_rate, reverse_missing=True),
                    "decode": format_rate(decode_rate),
                    "decode_sort": numeric_sort_value(decode_rate, reverse_missing=True),
                }
            )

        rows.sort(key=lambda row: (row["time_before_prefill_sort"], row["endpoint"]))
        tables.append(
            {
                "id": f"results_{index}",
                "model": model,
                "title": model_display_name(model),
                "total_cost": format_cost(total_cost),
                "rows": rows,
            }
        )

    return tables


@app.get("/api/endpoints")
def api_endpoints():
    model = (request.args.get("model") or "").strip()
    if not model:
        return jsonify({"error": "Missing model slug."}), 400
    try:
        endpoints = fetch_endpoints(model)
    except Exception as exc:  # noqa: BLE001 - expose local lookup failures to the UI.
        return jsonify({"error": str(exc)}), 400
    if not endpoints:
        return jsonify({"error": f"No endpoints returned for {model}."}), 404
    return jsonify({"model": model, "endpoints": endpoints})


def load_run_results(run_id: str) -> tuple[list[dict[str, Any]], str, list[str]]:
    if not run_id.isdigit():
        return [], "", ["Enter a numbered run to load."]

    try:
        records = load_benchmark_run(RUNS_ROOT / run_id)
        summaries = summarize_records(records)
        if not summaries:
            return [], "", [f"No benchmark records found for run {run_id}."]
        return summaries, run_heading(run_id, records), []
    except Exception as exc:  # noqa: BLE001 - render local load failures in the UI.
        return [], "", [str(exc)]


@app.route("/", methods=["GET", "POST"])
def index() -> str | Response:
    errors: list[str] = []
    discovered: dict[str, list[dict[str, Any]]] = {}
    summaries: list[dict[str, Any]] = []

    models_raw = DEFAULT_MODELS_RAW
    results_heading = ""
    samples = 10
    concurrency = 80
    max_retries = 3
    selected_benchmarks = list(DEFAULT_BENCHMARKS)

    load_run_id = (request.args.get("run") or "").strip()
    if request.method == "GET" and load_run_id:
        summaries, results_heading, load_errors = load_run_results(load_run_id)
        errors.extend(load_errors)

    if request.method == "POST":
        action = request.form.get("action")
        models_raw = request.form.get("models", DEFAULT_MODELS_RAW)
        load_run_id = request.form.get("load_run_id", "").strip()
        samples = as_int(request.form.get("samples"), samples) or 1
        concurrency = as_int(request.form.get("concurrency"), concurrency) or 1
        max_retries = as_int(request.form.get("max_retries"), max_retries)
        selected_benchmarks = normalize_benchmarks(request.form.getlist("benchmarks"))

        models = parse_model_slugs(models_raw)
        if action == "run" and not models:
            errors.append("Enter at least one model slug.")

        if action == "load":
            if load_run_id.isdigit():
                return redirect(url_for("index", run=load_run_id))
            errors.append("Enter a numbered run to load.")

        if models and action == "run":
            endpoints_by_model = selected_endpoints()
            endpoint_table_was_submitted = request.form.get("endpoints_present") == "1"
            if not endpoints_by_model and not endpoint_table_was_submitted:
                discovered, discover_errors = discover_models(models)
                errors.extend(discover_errors)
                endpoints_by_model = {
                    model: [endpoint["tag"] for endpoint in endpoints]
                    for model, endpoints in discovered.items()
                }
            elif endpoints_by_model:
                discovered = {
                    model: [{"tag": tag} for tag in provider_tags]
                    for model, provider_tags in endpoints_by_model.items()
                }

            run_root = None
            run_records: list[dict[str, Any]] = []
            for model in models:
                provider_tags = endpoints_by_model.get(model, [])
                if not provider_tags:
                    errors.append(f"No endpoints selected for {model}.")
                    continue
                if run_root is None:
                    run_root = next_run_root()
                try:
                    result = run_benchmarks(
                        BenchmarkConfig(
                            model=model,
                            provider_tags=provider_tags,
                            benchmarks=selected_benchmarks,
                            samples=samples,
                            concurrency=concurrency,
                            max_retries=max_retries,
                            run_root=run_root,
                        )
                    )
                    summaries.extend(result["summary"])
                    run_records.extend(result["results"])
                except Exception as exc:  # noqa: BLE001 - render local tool failures in the UI.
                    errors.append(str(exc))
            if run_root is not None:
                return redirect(url_for("index", run=run_root.name))

    return render_template(
        "index.html",
        available_runs=[{"id": path.name} for path in list_run_roots()],
        benchmark_defs=BENCHMARK_DEFINITIONS,
        concurrency=concurrency,
        discovered=discovered,
        errors=errors,
        initial_state={
            "models": parse_model_slugs(models_raw),
            "endpoints": discovered,
        },
        max_retries=max_retries,
        models=models_raw,
        result_tables=build_result_tables(summaries),
        results_heading=results_heading,
        samples=samples,
        selected_benchmarks=set(selected_benchmarks),
    )


if __name__ == "__main__":
    app.run(debug=True)
