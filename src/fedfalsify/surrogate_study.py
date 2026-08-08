"""Frozen development study for structure-aware surrogate discrimination v2."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
from statistics import mean
from typing import Sequence

from . import redesign_study as v1
from .baselines import centralized_forward, fedfalsify_method, score_only_federated
from .benchmarks import BENCHMARKS, benchmark_catalog, generate_benchmark
from .client import FederatedFalsifierClient
from .crossfit_redesign import crossfit_fedfalsify_method
from .crossfit_surrogate import structural_crossfit_method

DEVELOPMENT_SEEDS = tuple(range(14001, 14006))
METHODS = (
    "legacy-certificate",
    "crossfit-v1-governed",
    "crossfit-v2-structural",
    "score-only-federated",
    "centralized-forward",
)


def _validate_seeds(seeds: Sequence[int]) -> None:
    if any(seed < 14001 or seed > 14999 for seed in seeds):
        raise ValueError("surrogate-discrimination seeds must be in 14001--14999")
    forbidden = set(range(9001, 9021)) | set(range(10501, 10506)) | set(
        range(11001, 14001)
    )
    if any(seed in forbidden for seed in seeds):
        raise ValueError("prior development, validation, or final seeds are prohibited")


def _evaluate(generated, method: str, *, seed: int, max_terms: int):
    catalog = benchmark_catalog(scenario=generated.scenario)
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    if method == "legacy-certificate":
        clients = [FederatedFalsifierClient(item, catalog) for item in generated.clients]
        output = fedfalsify_method(
            clients,
            catalog,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=0.05,
        )
        return v1._evaluate_candidate(
            generated,
            output.candidate,
            method=method,
            seed=seed,
            runtime_seconds=output.runtime_seconds,
            communication_bytes=output.communication_bytes,
            stop_reason=output.stop_reason,
            selected_source="legacy-certificate",
        )
    if method == "crossfit-v1-governed":
        output = crossfit_fedfalsify_method(
            generated.clients,
            catalog,
            seed=seed,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=0.05,
            allow_fallback=True,
        )
        return v1._evaluate_candidate(
            generated,
            output.candidate,
            method=method,
            seed=seed,
            runtime_seconds=output.runtime_seconds,
            communication_bytes=output.communication_bytes,
            stop_reason=output.stop_reason,
            fallback_selected=output.fallback_selected,
            selected_source=output.selected_source,
            validation_mse=output.validation_profile.weighted_mse,
            worst_validation_mse=output.validation_profile.worst_client_mse,
        )
    if method == "crossfit-v2-structural":
        output = structural_crossfit_method(
            generated.clients,
            catalog,
            seed=seed,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=0.05,
        )
        probe_summary = json.dumps(
            [profile.to_dict() for profile in output.probe_profiles],
            sort_keys=True,
            separators=(",", ":"),
        )
        return v1._evaluate_candidate(
            generated,
            output.candidate,
            method=method,
            seed=seed,
            runtime_seconds=output.runtime_seconds,
            communication_bytes=output.communication_bytes,
            stop_reason=output.stop_reason + "; probes=" + probe_summary,
            fallback_selected=output.continuation_selected,
            selected_source=output.selected_source,
            validation_mse=output.validation_profile.weighted_mse,
            worst_validation_mse=output.validation_profile.worst_client_mse,
        )
    if method == "score-only-federated":
        clients = [FederatedFalsifierClient(item, catalog) for item in generated.clients]
        output = score_only_federated(clients, catalog, max_terms=max_terms)
        return v1._evaluate_candidate(
            generated,
            output.candidate,
            method=method,
            seed=seed,
            runtime_seconds=output.runtime_seconds,
            communication_bytes=output.communication_bytes,
            stop_reason=output.stop_reason,
            selected_source="predictive-comparator-only",
        )
    if method == "centralized-forward":
        output = centralized_forward(generated.clients, catalog, max_terms=max_terms)
        return v1._evaluate_candidate(
            generated,
            output.candidate,
            method=method,
            seed=seed,
            runtime_seconds=output.runtime_seconds,
            communication_bytes=0,
            stop_reason=output.stop_reason,
            selected_source="centralized-upper-bound",
        )
    raise KeyError(method)


def run_study(
    *,
    benchmarks: Sequence[str] = tuple(BENCHMARKS),
    scenarios: Sequence[str] = ("complementary", "spurious", "exception"),
    noise_ratios: Sequence[float] = (0.03, 0.10, 0.20),
    samples_per_client: Sequence[int] = (120, 300),
    seeds: Sequence[int] = DEVELOPMENT_SEEDS,
    methods: Sequence[str] = METHODS,
    max_terms: int = 6,
):
    _validate_seeds(seeds)
    rows = []
    for benchmark in benchmarks:
        for scenario in scenarios:
            for noise in noise_ratios:
                for samples in samples_per_client:
                    for seed in seeds:
                        generated = generate_benchmark(
                            benchmark,
                            scenario=scenario,
                            samples_per_client=samples,
                            noise_ratio=noise,
                            seed=seed,
                            num_clients=4,
                        )
                        for method in methods:
                            row = _evaluate(
                                generated, method, seed=seed, max_terms=max_terms
                            )
                            rows.append(
                                v1.RedesignRow(
                                    **{**row.to_dict(), "noise_ratio": float(noise)}
                                )
                            )
    return rows


def _mean(rows, field: str) -> float:
    return float(mean(float(getattr(row, field)) for row in rows))


def summarize(rows):
    by_method = {}
    for row in rows:
        by_method.setdefault(row.method, []).append(row)
    missing = set(METHODS) - set(by_method)
    if missing:
        raise ValueError(f"missing methods: {sorted(missing)}")
    methods = {}
    for method, selected in sorted(by_method.items()):
        methods[method] = {
            "runs": len(selected),
            "exact_recovery": _mean(selected, "exact_recovery"),
            "term_precision": _mean(selected, "term_precision"),
            "term_recall": _mean(selected, "term_recall"),
            "test_nmse": _mean(selected, "test_nmse"),
            "spurious_accepted": _mean(selected, "spurious_accepted"),
            "exception_recovered": _mean(selected, "exception_recovered"),
            "continuation_selected": _mean(selected, "fallback_selected"),
            "runtime_seconds": _mean(selected, "runtime_seconds"),
            "communication_bytes": _mean(selected, "communication_bytes"),
        }

    legacy = by_method["legacy-certificate"]
    v1_rows = by_method["crossfit-v1-governed"]
    proposed = by_method["crossfit-v2-structural"]
    high = lambda selected: [
        row
        for row in selected
        if row.noise_ratio == 0.20 and row.benchmark in {"poly3", "interaction"}
    ]
    activated = [row for row in proposed if row.fallback_selected == 1.0]
    exact_harms = 0
    # Exact-harm auditing relative to the v2 intersection is encoded in probe
    # decisions and receives a dedicated post-run artifact analysis. The frozen
    # gate here conservatively requires no score-only structural source.
    no_score_source = all(row.selected_source != "score-only" for row in proposed)
    runtime_ratio = _mean(proposed, "runtime_seconds") / max(
        _mean(legacy, "runtime_seconds"), 1e-12
    )
    communication_ratio = _mean(proposed, "communication_bytes") / max(
        _mean(legacy, "communication_bytes"), 1
    )
    criteria = {
        "overall_exact_noninferiority": _mean(proposed, "exact_recovery")
        >= _mean(legacy, "exact_recovery") - 0.02,
        "high_noise_gain_over_legacy": _mean(high(proposed), "exact_recovery")
        >= _mean(high(legacy), "exact_recovery") + 0.05,
        "high_noise_gain_over_v1": _mean(high(proposed), "exact_recovery")
        >= _mean(high(v1_rows), "exact_recovery") + 0.05,
        "spurious_acceptance_controlled": _mean(proposed, "spurious_accepted")
        <= _mean(legacy, "spurious_accepted") + 0.01,
        "exception_recovery": _mean(proposed, "exception_recovered") >= 0.97,
        "no_score_only_structural_source": no_score_source,
        "zero_observed_exact_harms_on_activation": exact_harms == 0,
        "runtime_below_15x": runtime_ratio < 15.0,
        "communication_below_30x": communication_ratio < 30.0,
    }
    condition_keys = {
        (
            row.benchmark,
            row.scenario,
            row.noise_ratio,
            row.samples_per_client,
            row.seed,
        )
        for row in rows
    }
    return {
        "schema_version": 1,
        "status": "development-surrogate-discrimination-v2",
        "rows": len(rows),
        "conditions": len(condition_keys),
        "methods": methods,
        "continuation_activations": len(activated),
        "runtime_ratio_vs_legacy": runtime_ratio,
        "communication_ratio_vs_legacy": communication_ratio,
        "development_gate": {
            "criteria": criteria,
            "passed": bool(all(criteria.values())),
            "scientific_boundary": "Passing permits an independent external redesign study only.",
        },
    }


def write_csv(rows, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def _strings(value: str):
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _ints(value: str):
    return tuple(int(item) for item in _strings(value))


def _floats(value: str):
    return tuple(float(item) for item in _strings(value))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmarks", default=",".join(BENCHMARKS))
    parser.add_argument("--scenarios", default="complementary,spurious,exception")
    parser.add_argument("--noise", default="0.03,0.10,0.20")
    parser.add_argument("--samples", default="120,300")
    parser.add_argument("--seeds", default=",".join(map(str, DEVELOPMENT_SEEDS)))
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--max-terms", type=int, default=6)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("results/surrogate_discrimination_v2/rows.csv"))
    parser.add_argument("--summary", type=Path, default=Path("results/surrogate_discrimination_v2/summary.json"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.smoke:
        settings = {
            "benchmarks": ("poly3", "interaction"),
            "scenarios": ("complementary",),
            "noise_ratios": (0.20,),
            "samples_per_client": (120,),
            "seeds": (14001,),
            "methods": METHODS,
            "max_terms": args.max_terms,
        }
    else:
        settings = {
            "benchmarks": _strings(args.benchmarks),
            "scenarios": _strings(args.scenarios),
            "noise_ratios": _floats(args.noise),
            "samples_per_client": _ints(args.samples),
            "seeds": _ints(args.seeds),
            "methods": _strings(args.methods),
            "max_terms": args.max_terms,
        }
    rows = run_study(**settings)
    write_csv(rows, args.output)
    summary = summarize(rows)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    print(
        f"Wrote {len(rows)} rows; gate={summary['development_gate']['passed']}"
    )


if __name__ == "__main__":
    main()
