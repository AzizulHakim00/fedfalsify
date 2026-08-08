"""Transactions-scale component ablations on fresh, non-confirmatory seeds."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
from time import perf_counter
from typing import Iterable

import numpy as np

from .baselines import (
    centralized_forward,
    fedfalsify_method,
    fit_federated,
    local_forward,
    score_only_federated,
)
from .benchmarks import (
    BENCHMARKS,
    BenchmarkTermCatalog,
    benchmark_catalog,
    generate_benchmark,
    generate_global_test_data,
)
from .client import FederatedFalsifierClient
from .confirmatory import ConfirmatoryRow, summarize, write_csv
from .confirmatory_report import add_holm_correction
from .replacement import FederatedCoreReplacement


FROZEN_CONFIRMATORY_SEEDS = frozenset(range(9001, 9021))
DEFAULT_DEVELOPMENT_SEEDS = tuple(range(10001, 10006))
DEFAULT_VARIANTS = (
    "fedfalsify-full",
    "fedfalsify-no-heterogeneity",
    "fedfalsify-no-replacement",
    "fedfalsify-no-nondegradation",
    "score-only-federated",
    "centralized-catalog",
    "local-consensus",
    "fedfalsify-no-exception-module",
)


def _term_metrics(
    predicted: Iterable[str], target: Iterable[str]
) -> tuple[float, float, float]:
    predicted_set = set(predicted)
    target_set = set(target)
    intersection = predicted_set & target_set
    precision = len(intersection) / len(predicted_set) if predicted_set else float(
        not target_set
    )
    recall = len(intersection) / len(target_set) if target_set else 1.0
    return float(predicted_set == target_set), precision, recall


def _prediction_nmse(prediction: np.ndarray, target: np.ndarray) -> float:
    return float(
        np.mean((target - prediction) ** 2) / max(float(np.var(target)), 1e-12)
    )


def _evaluate_candidate(
    generated,
    *,
    candidate,
    catalog,
    method: str,
    seed: int,
    runtime_seconds: float,
    communication_bytes: int,
    search_evaluations: int,
    stop_reason: str,
) -> ConfirmatoryRow:
    predicted = {
        term
        for term, coefficient in zip(candidate.active_terms, candidate.coefficients)
        if term != "1" and abs(float(coefficient)) >= 1e-3
    }
    exact, precision, recall = _term_metrics(predicted, generated.target_terms)
    x_test, y_test = generate_global_test_data(generated, seed=seed + 100_000)
    prediction = candidate.predict(x_test, catalog)
    pooled_x = np.concatenate([dataset.x for dataset in generated.clients], axis=0)
    pooled_y = np.concatenate([dataset.y for dataset in generated.clients], axis=0)
    train_mse = float(
        np.mean((pooled_y - candidate.predict(pooled_x, catalog)) ** 2)
    )
    spurious = float(bool({"x4", "x4^2"} & predicted))
    exception_term = "I(x3>1)*x3^2"
    exception_recovered = float(
        exception_term in predicted
        if generated.scenario == "exception"
        else exception_term not in predicted
    )
    return ConfirmatoryRow(
        benchmark=generated.spec.name,
        scenario=generated.scenario,
        noise_ratio=generated.noise_std
        / max(float(np.std(y_test)), 1e-12),
        samples_per_client=len(generated.clients[0].y),
        num_clients=len(generated.clients),
        seed=seed,
        method=method,
        exact_recovery=exact,
        term_precision=precision,
        term_recall=recall,
        test_nmse=_prediction_nmse(prediction, y_test),
        train_mse=train_mse,
        spurious_accepted=spurious,
        exception_recovered=exception_recovered,
        runtime_seconds=runtime_seconds,
        communication_bytes=communication_bytes,
        search_evaluations=search_evaluations,
        discovered_terms=";".join(sorted(predicted)),
        expression=candidate.expression(catalog),
        stop_reason=stop_reason,
    )


def _clients(generated, catalog) -> list[FederatedFalsifierClient]:
    return [
        FederatedFalsifierClient(dataset, catalog)
        for dataset in generated.clients
    ]


def _run_fedfalsify_variant(
    generated,
    *,
    method: str,
    max_terms: int,
    seed: int,
) -> ConfirmatoryRow:
    include_exception_terms = not (
        method == "fedfalsify-no-exception-module"
        and generated.scenario == "exception"
    )
    catalog = (
        benchmark_catalog(scenario=generated.scenario)
        if include_exception_terms
        else BenchmarkTermCatalog(include_exception_terms=False)
    )
    clients = _clients(generated, catalog)
    use_heterogeneity = method != "fedfalsify-no-heterogeneity"
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    start = perf_counter()
    base = fedfalsify_method(
        clients,
        catalog,
        max_terms=max_terms,
        target_mse=target_mse,
        min_repair_score=0.05,
        use_coefficient_heterogeneity=use_heterogeneity,
    )
    candidate = base.candidate
    communication = base.communication_bytes
    evaluations = base.rounds
    stop_reason = base.stop_reason

    if method != "fedfalsify-no-replacement":
        replacement_kwargs = {}
        if method == "fedfalsify-no-nondegradation":
            replacement_kwargs = {
                "min_nonworsening_client_fraction": 0.0,
                "client_worsening_tolerance": 10.0,
            }
        refined = FederatedCoreReplacement(
            clients,
            catalog,
            max_rounds=3,
            max_removed_terms=2,
            **replacement_kwargs,
        ).refine(candidate)
        candidate = refined.candidate
        communication += refined.communication_bytes
        evaluations += len(refined.replacements)
        stop_reason = f"{stop_reason}; {refined.stop_reason}"

    return _evaluate_candidate(
        generated,
        candidate=candidate,
        catalog=catalog,
        method=method,
        seed=seed,
        runtime_seconds=perf_counter() - start,
        communication_bytes=communication,
        search_evaluations=evaluations,
        stop_reason=stop_reason,
    )


def _local_consensus(
    generated,
    *,
    max_terms: int,
) -> tuple[object, object, float, int, int, str]:
    catalog = benchmark_catalog(scenario=generated.scenario)
    clients = _clients(generated, catalog)
    start = perf_counter()
    local = local_forward(generated.clients, catalog, max_terms=max_terms)
    counts: Counter[str] = Counter()
    payload_bytes = 0
    for candidate in local.candidates:
        active = [
            term
            for term, coefficient in zip(
                candidate.active_terms, candidate.coefficients
            )
            if term != "1" and abs(float(coefficient)) >= 1e-3
        ]
        counts.update(active)
        payload_bytes += len(
            json.dumps(
                {
                    "client": candidate.candidate_id,
                    "terms": list(candidate.active_terms),
                    "coefficients": list(candidate.coefficients),
                },
                separators=(",", ":"),
            ).encode("utf-8")
        )
    majority = math.ceil(len(generated.clients) / 2)
    selected = [
        term
        for term, count in sorted(
            counts.items(),
            key=lambda item: (
                -item[1],
                catalog.get(item[0]).complexity,
                item[0],
            ),
        )
        if count >= majority
    ][: max(max_terms - 1, 0)]
    active_terms = ("1", *selected)
    candidate, fit_bytes = fit_federated(clients, active_terms)
    return (
        candidate,
        catalog,
        perf_counter() - start,
        payload_bytes + fit_bytes,
        local.rounds,
        f"majority support >= {majority}/{len(generated.clients)} clients",
    )


def _run_baseline_variant(
    generated,
    *,
    method: str,
    max_terms: int,
    seed: int,
) -> ConfirmatoryRow:
    catalog = benchmark_catalog(scenario=generated.scenario)
    clients = _clients(generated, catalog)
    if method == "centralized-catalog":
        output = centralized_forward(
            generated.clients,
            catalog,
            max_terms=max_terms,
        )
        candidate = output.candidate
        runtime = output.runtime_seconds
        communication = output.communication_bytes
        evaluations = output.rounds
        stop_reason = output.stop_reason
    elif method == "score-only-federated":
        output = score_only_federated(
            clients,
            catalog,
            max_terms=max_terms,
        )
        candidate = output.candidate
        runtime = output.runtime_seconds
        communication = output.communication_bytes
        evaluations = output.rounds
        stop_reason = output.stop_reason
    elif method == "local-consensus":
        (
            candidate,
            catalog,
            runtime,
            communication,
            evaluations,
            stop_reason,
        ) = _local_consensus(generated, max_terms=max_terms)
    else:
        raise KeyError(f"unknown baseline ablation: {method}")

    return _evaluate_candidate(
        generated,
        candidate=candidate,
        catalog=catalog,
        method=method,
        seed=seed,
        runtime_seconds=runtime,
        communication_bytes=communication,
        search_evaluations=evaluations,
        stop_reason=stop_reason,
    )


def validate_development_seeds(seeds: Iterable[int]) -> tuple[int, ...]:
    values = tuple(int(seed) for seed in seeds)
    overlap = sorted(FROZEN_CONFIRMATORY_SEEDS & set(values))
    if overlap:
        raise ValueError(
            "Transactions ablations must not reuse frozen confirmatory seeds: "
            f"{overlap}"
        )
    if len(values) != len(set(values)):
        raise ValueError("ablation seeds must be unique")
    return values


def run_ablation_study(
    *,
    benchmarks: tuple[str, ...] = tuple(BENCHMARKS),
    scenarios: tuple[str, ...] = ("complementary", "spurious", "exception"),
    noise_ratios: tuple[float, ...] = (0.03, 0.10),
    samples_per_client: tuple[int, ...] = (300,),
    client_counts: tuple[int, ...] = (4,),
    seeds: tuple[int, ...] = DEFAULT_DEVELOPMENT_SEEDS,
    variants: tuple[str, ...] = DEFAULT_VARIANTS,
    max_terms: int = 6,
) -> list[ConfirmatoryRow]:
    seeds = validate_development_seeds(seeds)
    unknown = sorted(set(variants) - set(DEFAULT_VARIANTS))
    if unknown:
        raise KeyError(f"unknown Transactions ablation variants: {unknown}")
    rows: list[ConfirmatoryRow] = []
    fedfalsify_variants = {
        "fedfalsify-full",
        "fedfalsify-no-heterogeneity",
        "fedfalsify-no-replacement",
        "fedfalsify-no-nondegradation",
        "fedfalsify-no-exception-module",
    }
    for benchmark in benchmarks:
        for scenario in scenarios:
            for noise_ratio in noise_ratios:
                for sample_count in samples_per_client:
                    for client_count in client_counts:
                        for seed in seeds:
                            generated = generate_benchmark(
                                benchmark,
                                scenario=scenario,
                                samples_per_client=sample_count,
                                noise_ratio=noise_ratio,
                                seed=seed,
                                num_clients=client_count,
                            )
                            for variant in variants:
                                if variant in fedfalsify_variants:
                                    row = _run_fedfalsify_variant(
                                        generated,
                                        method=variant,
                                        max_terms=max_terms,
                                        seed=seed,
                                    )
                                else:
                                    row = _run_baseline_variant(
                                        generated,
                                        method=variant,
                                        max_terms=max_terms,
                                        seed=seed,
                                    )
                                rows.append(
                                    ConfirmatoryRow(
                                        **{
                                            **row.to_dict(),
                                            "noise_ratio": noise_ratio,
                                        }
                                    )
                                )
    return rows


def _parse_strings(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_floats(value: str) -> tuple[float, ...]:
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


def _parse_ints(value: str) -> tuple[int, ...]:
    values: list[int] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start, end = int(start_text), int(end_text)
            if end < start:
                raise ValueError(f"invalid integer range: {item}")
            values.extend(range(start, end + 1))
        else:
            values.append(int(item))
    return tuple(values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run Transactions-scale FedFalsify component ablations on fresh "
            "development seeds. Frozen seeds 9001--9020 are rejected."
        )
    )
    parser.add_argument("--benchmarks", default=",".join(BENCHMARKS))
    parser.add_argument(
        "--scenarios", default="complementary,spurious,exception"
    )
    parser.add_argument("--noise", default="0.03,0.10")
    parser.add_argument("--samples", default="300")
    parser.add_argument("--clients", default="4")
    parser.add_argument(
        "--seeds",
        default=",".join(map(str, DEFAULT_DEVELOPMENT_SEEDS)),
    )
    parser.add_argument("--variants", default=",".join(DEFAULT_VARIANTS))
    parser.add_argument("--max-terms", type=int, default=6)
    parser.add_argument("--bootstrap-resamples", type=int, default=4000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/transactions_ablation.csv"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/transactions_ablation_raw.json"),
    )
    parser.add_argument(
        "--holm-summary",
        type=Path,
        default=Path("results/transactions_ablation_holm.json"),
    )
    parser.add_argument("--smoke", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.smoke:
        settings = {
            "benchmarks": ("base",),
            "scenarios": ("complementary", "exception"),
            "noise_ratios": (0.03,),
            "samples_per_client": (60,),
            "client_counts": (4,),
            "seeds": (10001,),
            "variants": (
                "fedfalsify-full",
                "fedfalsify-no-heterogeneity",
                "fedfalsify-no-replacement",
                "score-only-federated",
                "centralized-catalog",
                "local-consensus",
                "fedfalsify-no-exception-module",
            ),
        }
    else:
        settings = {
            "benchmarks": _parse_strings(args.benchmarks),
            "scenarios": _parse_strings(args.scenarios),
            "noise_ratios": _parse_floats(args.noise),
            "samples_per_client": _parse_ints(args.samples),
            "client_counts": _parse_ints(args.clients),
            "seeds": _parse_ints(args.seeds),
            "variants": _parse_strings(args.variants),
        }
    rows = run_ablation_study(
        **settings,
        max_terms=args.max_terms,
    )
    write_csv(rows, args.output)
    raw = summarize(
        rows,
        reference="fedfalsify-full",
        bootstrap_resamples=args.bootstrap_resamples,
    )
    raw["protocol"] = {
        "seed_policy": "fresh development seeds; frozen seeds 9001--9020 rejected",
        "variants": list(settings["variants"]),
        "max_terms": args.max_terms,
    }
    corrected = add_holm_correction(raw)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    args.holm_summary.parent.mkdir(parents=True, exist_ok=True)
    args.holm_summary.write_text(
        json.dumps(corrected, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} ablation rows to {args.output}")
    print(f"Wrote raw summary to {args.summary}")
    print(f"Wrote Holm summary to {args.holm_summary}")


if __name__ == "__main__":
    main()
