"""Frozen development study for the cross-fitted certificate redesign."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from statistics import mean
from typing import Iterable, Sequence

import numpy as np

from .baselines import centralized_forward, fedfalsify_method, score_only_federated
from .benchmarks import (
    BENCHMARKS,
    benchmark_catalog,
    generate_benchmark,
    generate_global_test_data,
)
from .client import FederatedFalsifierClient
from .crossfit_redesign import RedesignOutput, crossfit_fedfalsify_method

DEVELOPMENT_SEEDS = tuple(range(13001, 13006))
DEFAULT_BENCHMARKS = tuple(BENCHMARKS)
DEFAULT_SCENARIOS = ("complementary", "spurious", "exception")
DEFAULT_NOISE = (0.03, 0.10, 0.20)
DEFAULT_SAMPLES = (120, 300)
METHODS = (
    "legacy-certificate",
    "crossfit-intersection",
    "crossfit-governed",
    "score-only-federated",
    "centralized-forward",
)


@dataclass(frozen=True)
class RedesignRow:
    benchmark: str
    scenario: str
    noise_ratio: float
    samples_per_client: int
    num_clients: int
    seed: int
    method: str
    exact_recovery: float
    term_precision: float
    term_recall: float
    test_nmse: float
    train_mse: float
    spurious_accepted: float
    exception_recovered: float
    fallback_selected: float
    selected_source: str
    validation_mse: float | None
    worst_validation_mse: float | None
    runtime_seconds: float
    communication_bytes: int
    discovered_terms: str
    expression: str
    stop_reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _validate_development_seeds(seeds: Sequence[int]) -> None:
    forbidden = set(range(9001, 9021)) | set(range(10501, 10506))
    if any(seed in forbidden or seed >= 11001 and seed < 13001 for seed in seeds):
        raise ValueError("confirmatory, PySR-validation, and final seeds are prohibited")
    if any(seed < 13001 or seed > 13999 for seed in seeds):
        raise ValueError("redesign development seeds must be in 13001--13999")


def _term_metrics(
    predicted: Iterable[str], target: Iterable[str]
) -> tuple[float, float, float]:
    predicted_set = set(predicted)
    target_set = set(target)
    intersection = predicted_set & target_set
    precision = len(intersection) / len(predicted_set) if predicted_set else float(not target_set)
    recall = len(intersection) / len(target_set) if target_set else 1.0
    return float(predicted_set == target_set), float(precision), float(recall)


def _prediction_nmse(prediction: np.ndarray, target: np.ndarray) -> float:
    mse = float(np.mean((np.asarray(target) - np.asarray(prediction)) ** 2))
    return float(mse / max(float(np.var(target)), 1e-12))


def _candidate_terms(candidate) -> set[str]:
    return {
        term
        for term, coefficient in zip(candidate.active_terms, candidate.coefficients)
        if term != "1" and abs(float(coefficient)) >= 1e-3
    }


def _evaluate_candidate(
    generated,
    candidate,
    *,
    method: str,
    seed: int,
    runtime_seconds: float,
    communication_bytes: int,
    stop_reason: str,
    fallback_selected: bool = False,
    selected_source: str = "",
    validation_mse: float | None = None,
    worst_validation_mse: float | None = None,
) -> RedesignRow:
    catalog = benchmark_catalog(scenario=generated.scenario)
    predicted = _candidate_terms(candidate)
    exact, precision, recall = _term_metrics(predicted, generated.target_terms)
    x_test, y_test = generate_global_test_data(generated, seed=seed + 100_000)
    test_prediction = candidate.predict(x_test, catalog)
    pooled_x = np.concatenate([dataset.x for dataset in generated.clients], axis=0)
    pooled_y = np.concatenate([dataset.y for dataset in generated.clients], axis=0)
    train_prediction = candidate.predict(pooled_x, catalog)
    train_mse = float(np.mean((pooled_y - train_prediction) ** 2))
    spurious = float(bool({"x4", "x4^2"} & predicted))
    exception_term = "I(x3>1)*x3^2"
    exception_recovered = float(
        exception_term in predicted
        if generated.scenario == "exception"
        else exception_term not in predicted
    )
    return RedesignRow(
        benchmark=generated.spec.name,
        scenario=generated.scenario,
        noise_ratio=float(generated.noise_std / max(np.std(y_test), 1e-12)),
        samples_per_client=len(generated.clients[0].y),
        num_clients=len(generated.clients),
        seed=seed,
        method=method,
        exact_recovery=exact,
        term_precision=precision,
        term_recall=recall,
        test_nmse=_prediction_nmse(test_prediction, y_test),
        train_mse=train_mse,
        spurious_accepted=spurious,
        exception_recovered=exception_recovered,
        fallback_selected=float(fallback_selected),
        selected_source=selected_source,
        validation_mse=validation_mse,
        worst_validation_mse=worst_validation_mse,
        runtime_seconds=float(runtime_seconds),
        communication_bytes=int(communication_bytes),
        discovered_terms=";".join(sorted(predicted)),
        expression=candidate.expression(catalog),
        stop_reason=stop_reason,
    )


def _evaluate_method(generated, method: str, *, seed: int, max_terms: int) -> RedesignRow:
    catalog = benchmark_catalog(scenario=generated.scenario)
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    if method == "legacy-certificate":
        clients = [FederatedFalsifierClient(dataset, catalog) for dataset in generated.clients]
        output = fedfalsify_method(
            clients,
            catalog,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=0.05,
        )
        return _evaluate_candidate(
            generated,
            output.candidate,
            method=method,
            seed=seed,
            runtime_seconds=output.runtime_seconds,
            communication_bytes=output.communication_bytes,
            stop_reason=output.stop_reason,
            selected_source="legacy-certificate",
        )
    if method in {"crossfit-intersection", "crossfit-governed"}:
        redesigned: RedesignOutput = crossfit_fedfalsify_method(
            generated.clients,
            catalog,
            seed=seed,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=0.05,
            allow_fallback=method == "crossfit-governed",
        )
        return _evaluate_candidate(
            generated,
            redesigned.candidate,
            method=method,
            seed=seed,
            runtime_seconds=redesigned.runtime_seconds,
            communication_bytes=redesigned.communication_bytes,
            stop_reason=redesigned.stop_reason,
            fallback_selected=redesigned.fallback_selected,
            selected_source=redesigned.selected_source,
            validation_mse=redesigned.validation_profile.weighted_mse,
            worst_validation_mse=redesigned.validation_profile.worst_client_mse,
        )
    if method == "score-only-federated":
        clients = [FederatedFalsifierClient(dataset, catalog) for dataset in generated.clients]
        output = score_only_federated(clients, catalog, max_terms=max_terms)
        return _evaluate_candidate(
            generated,
            output.candidate,
            method=method,
            seed=seed,
            runtime_seconds=output.runtime_seconds,
            communication_bytes=output.communication_bytes,
            stop_reason=output.stop_reason,
            selected_source="score-only",
        )
    if method == "centralized-forward":
        output = centralized_forward(generated.clients, catalog, max_terms=max_terms)
        return _evaluate_candidate(
            generated,
            output.candidate,
            method=method,
            seed=seed,
            runtime_seconds=output.runtime_seconds,
            communication_bytes=0,
            stop_reason=output.stop_reason,
            selected_source="centralized",
        )
    raise KeyError(f"unknown redesign method: {method}")


def run_study(
    *,
    benchmarks: Sequence[str] = DEFAULT_BENCHMARKS,
    scenarios: Sequence[str] = DEFAULT_SCENARIOS,
    noise_ratios: Sequence[float] = DEFAULT_NOISE,
    samples_per_client: Sequence[int] = DEFAULT_SAMPLES,
    seeds: Sequence[int] = DEVELOPMENT_SEEDS,
    methods: Sequence[str] = METHODS,
    max_terms: int = 6,
) -> list[RedesignRow]:
    _validate_development_seeds(seeds)
    rows: list[RedesignRow] = []
    for benchmark in benchmarks:
        for scenario in scenarios:
            for requested_noise in noise_ratios:
                for sample_count in samples_per_client:
                    for seed in seeds:
                        generated = generate_benchmark(
                            benchmark,
                            scenario=scenario,
                            samples_per_client=sample_count,
                            noise_ratio=requested_noise,
                            seed=seed,
                            num_clients=4,
                        )
                        for method in methods:
                            row = _evaluate_method(
                                generated, method, seed=seed, max_terms=max_terms
                            )
                            rows.append(
                                RedesignRow(
                                    **{
                                        **row.to_dict(),
                                        "noise_ratio": float(requested_noise),
                                    }
                                )
                            )
    return rows


def _mean(rows: Sequence[RedesignRow], field: str) -> float:
    return float(mean(float(getattr(row, field)) for row in rows))


def summarize(rows: Sequence[RedesignRow]) -> dict[str, object]:
    by_method: dict[str, list[RedesignRow]] = {}
    for row in rows:
        by_method.setdefault(row.method, []).append(row)
    methods: dict[str, object] = {}
    for method, selected in sorted(by_method.items()):
        validation_pairs = [
            (row.validation_mse, row.test_nmse)
            for row in selected
            if row.validation_mse is not None
        ]
        if len(validation_pairs) >= 2:
            validation_values = np.asarray([pair[0] for pair in validation_pairs], dtype=float)
            test_values = np.asarray([pair[1] for pair in validation_pairs], dtype=float)
            validation_test_correlation = float(
                np.corrcoef(validation_values, test_values)[0, 1]
            )
        else:
            validation_test_correlation = float("nan")
        methods[method] = {
            "runs": len(selected),
            "exact_recovery": _mean(selected, "exact_recovery"),
            "term_precision": _mean(selected, "term_precision"),
            "term_recall": _mean(selected, "term_recall"),
            "test_nmse": _mean(selected, "test_nmse"),
            "spurious_accepted": _mean(selected, "spurious_accepted"),
            "exception_recovered": _mean(selected, "exception_recovered"),
            "fallback_selected": _mean(selected, "fallback_selected"),
            "runtime_seconds": _mean(selected, "runtime_seconds"),
            "communication_bytes": _mean(selected, "communication_bytes"),
            "validation_test_correlation": validation_test_correlation,
        }

    legacy = by_method["legacy-certificate"]
    proposed = by_method["crossfit-governed"]
    high_noise_legacy = [
        row
        for row in legacy
        if row.noise_ratio == 0.20 and row.benchmark in {"poly3", "interaction"}
    ]
    high_noise_proposed = [
        row
        for row in proposed
        if row.noise_ratio == 0.20 and row.benchmark in {"poly3", "interaction"}
    ]
    proposed_spurious = [row for row in proposed if row.scenario == "spurious"]
    proposed_complementary = [
        row for row in proposed if row.scenario == "complementary"
    ]

    criteria = {
        "overall_exact_noninferiority": _mean(proposed, "exact_recovery")
        >= _mean(legacy, "exact_recovery") - 0.02,
        "mean_test_nmse_improves": _mean(proposed, "test_nmse")
        < _mean(legacy, "test_nmse"),
        "spurious_acceptance_controlled": _mean(proposed, "spurious_accepted")
        <= _mean(legacy, "spurious_accepted") + 0.01,
        "high_noise_poly_interaction_exact_gain": _mean(
            high_noise_proposed, "exact_recovery"
        )
        >= _mean(high_noise_legacy, "exact_recovery") + 0.05,
        "fallback_not_disproportionate_on_spurious": _mean(
            proposed_spurious, "fallback_selected"
        )
        <= _mean(proposed_complementary, "fallback_selected") + 0.10,
    }
    return {
        "schema_version": 1,
        "status": "development-redesign",
        "rows": len(rows),
        "conditions": len(rows) // len(METHODS),
        "methods": methods,
        "development_gate": {
            "criteria": criteria,
            "passed": bool(all(criteria.values())),
            "high_noise_definition": "noise_ratio == 0.20 and benchmark in {poly3, interaction}",
            "scientific_boundary": "Passing permits later independent confirmation only; it is not confirmatory evidence.",
        },
    }


def write_csv(rows: Sequence[RedesignRow], output: Path) -> None:
    if not rows:
        raise ValueError("no redesign rows to write")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].to_dict()))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)


def _parse_strings(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_ints(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def _parse_floats(value: str) -> tuple[float, ...]:
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen cross-fit redesign study")
    parser.add_argument("--benchmarks", default=",".join(DEFAULT_BENCHMARKS))
    parser.add_argument("--scenarios", default=",".join(DEFAULT_SCENARIOS))
    parser.add_argument("--noise", default=",".join(map(str, DEFAULT_NOISE)))
    parser.add_argument("--samples", default=",".join(map(str, DEFAULT_SAMPLES)))
    parser.add_argument("--seeds", default=",".join(map(str, DEVELOPMENT_SEEDS)))
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--max-terms", type=int, default=6)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--output", type=Path, default=Path("results/crossfit_redesign_v1/rows.csv")
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/crossfit_redesign_v1/summary.json"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.smoke:
        settings = {
            "benchmarks": ("base", "interaction"),
            "scenarios": ("complementary", "spurious"),
            "noise_ratios": (0.10,),
            "samples_per_client": (80,),
            "seeds": (13001,),
            "methods": METHODS,
            "max_terms": min(args.max_terms, 5),
        }
    else:
        settings = {
            "benchmarks": _parse_strings(args.benchmarks),
            "scenarios": _parse_strings(args.scenarios),
            "noise_ratios": _parse_floats(args.noise),
            "samples_per_client": _parse_ints(args.samples),
            "seeds": _parse_ints(args.seeds),
            "methods": _parse_strings(args.methods),
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
        f"Wrote {len(rows)} redesign rows; "
        f"development_gate={summary['development_gate']['passed']}"
    )


if __name__ == "__main__":
    main()
