"""Matched Transactions-development study for adaptive expression-tree methods.

The study compares certificate-guided federated expression-tree search against
centralized, aggregate-federated, and residual-counterexample tree searches
under the same expression library and evolutionary budget. Frozen confirmatory
seeds are rejected by construction.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from statistics import mean
from typing import Iterable

import numpy as np

from .benchmarks import (
    BENCHMARKS,
    benchmark_catalog,
    evaluate_terms,
    generate_benchmark,
    generate_global_test_data,
)
from .certificate_tree import CertificateTreeOutput, run_certificate_tree_search
from .expression_baselines import TreeSearchOutput, run_tree_search
from .statistics import mcnemar_exact, paired_bootstrap_difference, wilson_interval
from .transactions_analysis import _extrapolation_data, normalized_mse


FROZEN_CONFIRMATORY_SEEDS = frozenset(range(9001, 9021))
DEFAULT_DEVELOPMENT_SEEDS = tuple(range(10011, 10016))
METHODS = (
    "certificate-guided-federated-tree",
    "centralized-tree-gp",
    "federated-tree-gp-style",
    "centralized-residual-counterexample-gp",
)


@dataclass(frozen=True)
class AdaptiveTreeRow:
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
    interpolation_nmse: float
    client_support_nmse: float
    mild_extrapolation_nmse: float
    strong_extrapolation_nmse: float
    semantic_all_1e4: float
    semantic_all_1e3: float
    semantic_all_1e2: float
    spurious_accepted: float
    exception_recovered: float
    expression_complexity: int
    runtime_seconds: float
    communication_bytes: int
    search_evaluations: int
    certificate_penalty: float
    violating_certificates: int
    mean_certificate_support: float
    mean_certificate_sign_agreement: float
    discovered_terms: str
    expression: str
    stop_reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_fresh_seeds(seeds: Iterable[int]) -> tuple[int, ...]:
    values = tuple(int(seed) for seed in seeds)
    overlap = sorted(FROZEN_CONFIRMATORY_SEEDS & set(values))
    if overlap:
        raise ValueError(
            "adaptive Transactions study must not reuse frozen seeds: "
            f"{overlap}"
        )
    if len(values) != len(set(values)):
        raise ValueError("adaptive-study seeds must be unique")
    return values


def _term_metrics(
    predicted: Iterable[str], target: Iterable[str]
) -> tuple[float, float, float]:
    predicted_set = set(predicted)
    target_set = set(target)
    overlap = predicted_set & target_set
    precision = len(overlap) / len(predicted_set) if predicted_set else float(
        not target_set
    )
    recall = len(overlap) / len(target_set) if target_set else 1.0
    return float(predicted_set == target_set), precision, recall


def _semantic_success(values: tuple[float, ...], threshold: float) -> float:
    return float(
        all(np.isfinite(value) for value in values)
        and max(values) <= threshold
    )


def _evaluate_model(
    generated,
    *,
    model,
    method: str,
    seed: int,
    runtime_seconds: float,
    communication_bytes: int,
    evaluations: int,
    stop_reason: str,
    certificate_penalty: float = float("nan"),
    violating_certificates: int = -1,
    mean_certificate_support: float = float("nan"),
    mean_certificate_sign_agreement: float = float("nan"),
) -> AdaptiveTreeRow:
    predicted = set(model.active_terms())
    exact, precision, recall = _term_metrics(predicted, generated.target_terms)
    x_interpolation, y_interpolation = generate_global_test_data(
        generated,
        samples=4000,
        seed=seed + 100_000,
    )
    interpolation_prediction = model.predict(x_interpolation)
    client_x = np.concatenate([dataset.x for dataset in generated.clients], axis=0)
    client_y = evaluate_terms(
        client_x,
        generated.target_coefficients,
        benchmark_catalog(scenario=generated.scenario),
    )
    client_prediction = model.predict(client_x)
    x_mild, y_mild = _extrapolation_data(
        generated,
        scale=1.25,
        samples=4000,
        seed=seed + 200_000,
    )
    x_strong, y_strong = _extrapolation_data(
        generated,
        scale=1.50,
        samples=4000,
        seed=seed + 300_000,
    )
    semantic_values = (
        normalized_mse(interpolation_prediction, y_interpolation),
        normalized_mse(client_prediction, client_y),
        normalized_mse(model.predict(x_mild), y_mild),
        normalized_mse(model.predict(x_strong), y_strong),
    )
    exception = "I(x3>1)*x3^2"
    return AdaptiveTreeRow(
        benchmark=generated.spec.name,
        scenario=generated.scenario,
        noise_ratio=generated.noise_std
        / max(float(np.std(y_interpolation)), 1e-12),
        samples_per_client=len(generated.clients[0].y),
        num_clients=len(generated.clients),
        seed=seed,
        method=method,
        exact_recovery=exact,
        term_precision=precision,
        term_recall=recall,
        interpolation_nmse=semantic_values[0],
        client_support_nmse=semantic_values[1],
        mild_extrapolation_nmse=semantic_values[2],
        strong_extrapolation_nmse=semantic_values[3],
        semantic_all_1e4=_semantic_success(semantic_values, 1e-4),
        semantic_all_1e3=_semantic_success(semantic_values, 1e-3),
        semantic_all_1e2=_semantic_success(semantic_values, 1e-2),
        spurious_accepted=float(any("x4" in term for term in predicted)),
        exception_recovered=float(
            exception in predicted
            if generated.scenario == "exception"
            else exception not in predicted
        ),
        expression_complexity=model.complexity(),
        runtime_seconds=runtime_seconds,
        communication_bytes=communication_bytes,
        search_evaluations=evaluations,
        certificate_penalty=certificate_penalty,
        violating_certificates=violating_certificates,
        mean_certificate_support=mean_certificate_support,
        mean_certificate_sign_agreement=mean_certificate_sign_agreement,
        discovered_terms=";".join(sorted(predicted)),
        expression=model.expression(),
        stop_reason=stop_reason,
    )


def _run_certificate_method(
    generated,
    *,
    seed: int,
    population_size: int,
    generations: int,
    max_genes: int,
    max_complexity: int,
) -> AdaptiveTreeRow:
    output: CertificateTreeOutput = run_certificate_tree_search(
        generated.clients,
        seed=seed,
        population_size=population_size,
        generations=generations,
        max_genes=max_genes,
        max_complexity=max_complexity,
    )
    penalties = [certificate.penalty for certificate in output.certificates]
    supports = [certificate.support_fraction for certificate in output.certificates]
    agreements = [
        certificate.sign_agreement for certificate in output.certificates
    ]
    return _evaluate_model(
        generated,
        model=output.model,
        method=output.method,
        seed=seed,
        runtime_seconds=output.runtime_seconds,
        communication_bytes=output.communication_bytes,
        evaluations=output.evaluations,
        stop_reason=output.stop_reason,
        certificate_penalty=float(sum(penalties)),
        violating_certificates=sum(value > 0 for value in penalties),
        mean_certificate_support=float(mean(supports)) if supports else 1.0,
        mean_certificate_sign_agreement=float(mean(agreements))
        if agreements
        else 1.0,
    )


def _run_controlled_method(
    generated,
    *,
    method: str,
    seed: int,
    population_size: int,
    generations: int,
    max_genes: int,
    max_complexity: int,
) -> AdaptiveTreeRow:
    mode = {
        "centralized-tree-gp": "centralized",
        "federated-tree-gp-style": "federated",
        "centralized-residual-counterexample-gp": "counterexample",
    }[method]
    output: TreeSearchOutput = run_tree_search(
        generated.clients,
        mode=mode,
        seed=seed,
        population_size=population_size,
        generations=generations,
        max_genes=max_genes,
        max_complexity=max_complexity,
    )
    return _evaluate_model(
        generated,
        model=output.model,
        method=output.method,
        seed=seed,
        runtime_seconds=output.runtime_seconds,
        communication_bytes=output.communication_bytes,
        evaluations=output.evaluations,
        stop_reason=output.stop_reason,
    )


def run_study(
    *,
    benchmarks: tuple[str, ...] = tuple(BENCHMARKS),
    scenarios: tuple[str, ...] = ("complementary", "spurious", "exception"),
    noise_ratios: tuple[float, ...] = (0.03, 0.10),
    samples_per_client: tuple[int, ...] = (300,),
    client_counts: tuple[int, ...] = (4,),
    seeds: tuple[int, ...] = DEFAULT_DEVELOPMENT_SEEDS,
    methods: tuple[str, ...] = METHODS,
    population_size: int = 48,
    generations: int = 12,
    max_genes: int = 4,
    max_complexity: int = 7,
) -> list[AdaptiveTreeRow]:
    seeds = validate_fresh_seeds(seeds)
    unknown_methods = sorted(set(methods) - set(METHODS))
    if unknown_methods:
        raise KeyError(f"unknown adaptive-study methods: {unknown_methods}")
    rows: list[AdaptiveTreeRow] = []
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
                            for method in methods:
                                if method == "certificate-guided-federated-tree":
                                    row = _run_certificate_method(
                                        generated,
                                        seed=seed,
                                        population_size=population_size,
                                        generations=generations,
                                        max_genes=max_genes,
                                        max_complexity=max_complexity,
                                    )
                                else:
                                    row = _run_controlled_method(
                                        generated,
                                        method=method,
                                        seed=seed,
                                        population_size=population_size,
                                        generations=generations,
                                        max_genes=max_genes,
                                        max_complexity=max_complexity,
                                    )
                                rows.append(
                                    AdaptiveTreeRow(
                                        **{
                                            **row.to_dict(),
                                            "noise_ratio": noise_ratio,
                                        }
                                    )
                                )
    return rows


def _method_summary(rows: list[AdaptiveTreeRow]) -> dict[str, object]:
    return {
        "runs": len(rows),
        "exact_recovery": mean(row.exact_recovery for row in rows),
        "exact_wilson_95": wilson_interval(
            int(sum(row.exact_recovery for row in rows)), len(rows)
        ),
        "term_precision": mean(row.term_precision for row in rows),
        "term_recall": mean(row.term_recall for row in rows),
        "semantic_all_1e3": mean(row.semantic_all_1e3 for row in rows),
        "semantic_all_1e2": mean(row.semantic_all_1e2 for row in rows),
        "interpolation_nmse": mean(row.interpolation_nmse for row in rows),
        "strong_extrapolation_nmse": mean(
            row.strong_extrapolation_nmse for row in rows
        ),
        "spurious_accepted": mean(row.spurious_accepted for row in rows),
        "exception_recovered": mean(row.exception_recovered for row in rows),
        "expression_complexity": mean(row.expression_complexity for row in rows),
        "runtime_seconds": mean(row.runtime_seconds for row in rows),
        "communication_bytes": mean(row.communication_bytes for row in rows),
        "search_evaluations": mean(row.search_evaluations for row in rows),
    }


def summarize(
    rows: list[AdaptiveTreeRow],
    *,
    reference: str = "certificate-guided-federated-tree",
    bootstrap_resamples: int = 4000,
) -> dict[str, object]:
    by_method = {
        method: [row for row in rows if row.method == method]
        for method in sorted({row.method for row in rows})
    }
    identities = lambda row: (
        row.benchmark,
        row.scenario,
        row.noise_ratio,
        row.samples_per_client,
        row.num_clients,
        row.seed,
    )
    reference_rows = {identities(row): row for row in by_method[reference]}
    paired: dict[str, object] = {}
    for method, selected in by_method.items():
        if method == reference:
            continue
        comparison_rows = {identities(row): row for row in selected}
        common = sorted(set(reference_rows) & set(comparison_rows))
        reference_success = [
            int(reference_rows[key].exact_recovery) for key in common
        ]
        comparison_success = [
            int(comparison_rows[key].exact_recovery) for key in common
        ]
        paired[method] = {
            "pairs": len(common),
            "mcnemar": mcnemar_exact(reference_success, comparison_success),
            "strong_extrapolation_comparator_minus_reference": paired_bootstrap_difference(
                [reference_rows[key].strong_extrapolation_nmse for key in common],
                [comparison_rows[key].strong_extrapolation_nmse for key in common],
                resamples=bootstrap_resamples,
                seed=41,
            ),
            "runtime_comparator_minus_reference": paired_bootstrap_difference(
                [reference_rows[key].runtime_seconds for key in common],
                [comparison_rows[key].runtime_seconds for key in common],
                resamples=bootstrap_resamples,
                seed=43,
            ),
        }
    return {
        "schema_version": 1,
        "status": "development",
        "reference": reference,
        "methods": {
            method: _method_summary(selected)
            for method, selected in by_method.items()
        },
        "paired": paired,
        "scientific_boundary": [
            "Fresh-seed development evidence only.",
            "All methods share one expression-tree grammar and search budget.",
            "The certificate-guided objective is not yet theoretically calibrated.",
            "Final validation and confirmation seeds remain untouched."
        ],
    }


def write_csv(rows: list[AdaptiveTreeRow], output: Path) -> None:
    if not rows:
        raise ValueError("cannot write an empty adaptive-tree study")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].to_dict()))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)


def _parse_strings(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _parse_floats(value: str) -> tuple[float, ...]:
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


def _parse_ints(value: str) -> tuple[int, ...]:
    result: list[int] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if "-" in item:
            start_text, end_text = item.split("-", 1)
            start, end = int(start_text), int(end_text)
            if end < start:
                raise ValueError(f"invalid integer range: {item}")
            result.extend(range(start, end + 1))
        else:
            result.append(int(item))
    return tuple(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare certificate-guided and controlled expression-tree search "
            "under a matched adaptive grammar and fresh seeds."
        )
    )
    parser.add_argument("--benchmarks", default=",".join(BENCHMARKS))
    parser.add_argument("--scenarios", default="complementary,spurious,exception")
    parser.add_argument("--noise", default="0.03,0.10")
    parser.add_argument("--samples", default="300")
    parser.add_argument("--clients", default="4")
    parser.add_argument(
        "--seeds", default=",".join(map(str, DEFAULT_DEVELOPMENT_SEEDS))
    )
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--population-size", type=int, default=48)
    parser.add_argument("--generations", type=int, default=12)
    parser.add_argument("--max-genes", type=int, default=4)
    parser.add_argument("--max-complexity", type=int, default=7)
    parser.add_argument("--bootstrap-resamples", type=int, default=4000)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/transactions_adaptive_tree/rows.csv"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/transactions_adaptive_tree/summary.json"),
    )
    parser.add_argument("--smoke", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.smoke:
        settings = {
            "benchmarks": ("base",),
            "scenarios": ("spurious",),
            "noise_ratios": (0.03,),
            "samples_per_client": (60,),
            "client_counts": (4,),
            "seeds": (10011,),
            "methods": METHODS,
            "population_size": 8,
            "generations": 1,
            "max_genes": 2,
            "max_complexity": 5,
        }
    else:
        settings = {
            "benchmarks": _parse_strings(args.benchmarks),
            "scenarios": _parse_strings(args.scenarios),
            "noise_ratios": _parse_floats(args.noise),
            "samples_per_client": _parse_ints(args.samples),
            "client_counts": _parse_ints(args.clients),
            "seeds": _parse_ints(args.seeds),
            "methods": _parse_strings(args.methods),
            "population_size": args.population_size,
            "generations": args.generations,
            "max_genes": args.max_genes,
            "max_complexity": args.max_complexity,
        }
    rows = run_study(**settings)
    write_csv(rows, args.output)
    summary = summarize(
        rows,
        bootstrap_resamples=args.bootstrap_resamples,
    )
    summary["protocol"] = {
        "benchmarks": list(settings["benchmarks"]),
        "scenarios": list(settings["scenarios"]),
        "noise_ratios": list(settings["noise_ratios"]),
        "samples_per_client": list(settings["samples_per_client"]),
        "client_counts": list(settings["client_counts"]),
        "seeds": list(settings["seeds"]),
        "methods": list(settings["methods"]),
        "population_size": settings["population_size"],
        "generations": settings["generations"],
        "max_genes": settings["max_genes"],
        "max_complexity": settings["max_complexity"],
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} adaptive-tree rows to {args.output}")
    print(f"Wrote summary to {args.summary}")


if __name__ == "__main__":
    main()
