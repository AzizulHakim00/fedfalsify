"""Failure-retaining compatibility entry point for the PySR validation study.

The preregistered binary endpoint treats an unavailable, unparsable or
non-finite PySR equation as a failed recovery.  Such rows must remain in the
400-row validation matrix rather than causing the workflow to reject the
entire seed.  Continuous summaries use only finite matched values and report
the number of usable observations explicitly.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import numpy as np

from . import transactions_pysr_validation as _core
from .statistics import holm_adjust, mcnemar_exact, paired_bootstrap_difference, wilson_interval


PySRValidationRow = _core.PySRValidationRow
BUDGETS = _core.BUDGETS
VALIDATION_SEEDS = _core.VALIDATION_SEEDS
FINAL_CONFIRMATION_START = _core.FINAL_CONFIRMATION_START
run_seed = _core.run_seed
read_csv = _core.read_csv
write_csv = _core.write_csv
validate_validation_seeds = _core.validate_validation_seeds
environment_manifest = _core.environment_manifest


def _finite_summary(values: Iterable[float]) -> dict[str, object]:
    array = np.asarray(tuple(values), dtype=float)
    finite = array[np.isfinite(array)]
    return {
        "mean": float(np.mean(finite)) if finite.size else None,
        "finite_rows": int(finite.size),
        "total_rows": int(array.size),
    }


def _finite_complexity(values: Iterable[int]) -> dict[str, object]:
    array = np.asarray(tuple(values), dtype=float)
    finite = array[np.isfinite(array) & (array >= 0)]
    return {
        "mean": float(np.mean(finite)) if finite.size else None,
        "finite_rows": int(finite.size),
        "total_rows": int(array.size),
    }


def _paired_finite_bootstrap(
    reference: Iterable[float],
    comparator: Iterable[float],
    *,
    seed: int,
) -> dict[str, object]:
    left = np.asarray(tuple(reference), dtype=float)
    right = np.asarray(tuple(comparator), dtype=float)
    if left.shape != right.shape:
        raise ValueError("paired continuous values must have equal shapes")
    mask = np.isfinite(left) & np.isfinite(right)
    usable_left = left[mask]
    usable_right = right[mask]
    result: dict[str, object] = {
        "finite_pairs": int(mask.sum()),
        "total_pairs": int(mask.size),
        "estimate": None,
        "lower": None,
        "upper": None,
        "confidence": 0.95,
        "resamples": 0,
    }
    if usable_left.size < 2:
        return result
    interval = paired_bootstrap_difference(
        usable_left,
        usable_right,
        resamples=5000,
        seed=seed,
    )
    result.update(asdict(interval))
    result["finite_pairs"] = int(mask.sum())
    result["total_pairs"] = int(mask.size)
    return result


def summarize(rows: list[PySRValidationRow]) -> dict[str, object]:
    if not rows:
        raise ValueError("no validation rows supplied")

    identities: dict[tuple[object, ...], dict[str, PySRValidationRow]] = {}
    for row in rows:
        identity = (
            row.benchmark,
            row.scenario,
            row.noise_ratio,
            row.samples_per_client,
            row.num_clients,
            row.seed,
            row.regime,
        )
        pair = identities.setdefault(identity, {})
        if row.method in pair:
            raise ValueError(f"duplicate validation method row: {identity}, {row.method}")
        pair[row.method] = row
    if any(set(pair) != {"fedfalsify-v05", "official-pysr"} for pair in identities.values()):
        raise ValueError("every validation condition must contain exactly two methods")

    method_summary: dict[str, dict[str, object]] = {}
    for regime in BUDGETS:
        for method in ("fedfalsify-v05", "official-pysr"):
            subset = [
                row for row in rows if row.regime == regime and row.method == method
            ]
            if not subset:
                raise ValueError(f"missing validation rows for {regime}:{method}")
            successes = int(sum(row.semantic_all_1e3 for row in subset))
            completed = int(sum(row.completed for row in subset))
            method_summary[f"{regime}:{method}"] = {
                "runs": len(subset),
                "completed": completed,
                "failed_or_incomplete": len(subset) - completed,
                "semantic_all_1e4": float(
                    np.mean([row.semantic_all_1e4 for row in subset])
                ),
                "semantic_all_1e3": float(
                    np.mean([row.semantic_all_1e3 for row in subset])
                ),
                "semantic_all_1e2": float(
                    np.mean([row.semantic_all_1e2 for row in subset])
                ),
                "semantic_1e3_wilson_95": wilson_interval(successes, len(subset)),
                "interpolation_nmse": _finite_summary(
                    row.interpolation_nmse for row in subset
                ),
                "client_support_nmse": _finite_summary(
                    row.client_support_nmse for row in subset
                ),
                "mild_extrapolation_nmse": _finite_summary(
                    row.mild_extrapolation_nmse for row in subset
                ),
                "strong_extrapolation_nmse": _finite_summary(
                    row.strong_extrapolation_nmse for row in subset
                ),
                "runtime_seconds": _finite_summary(
                    row.runtime_seconds for row in subset
                ),
                "expression_complexity": _finite_complexity(
                    row.expression_complexity for row in subset
                ),
                "raw_data_pooled": method == "official-pysr",
                "strict_exact_recovery": (
                    float(np.mean([row.strict_exact_recovery for row in subset]))
                    if method == "fedfalsify-v05"
                    else None
                ),
            }

    paired: dict[str, dict[str, object]] = {}
    primary_p: dict[str, float] = {}
    for regime in BUDGETS:
        ordered = sorted(
            (identity, pair)
            for identity, pair in identities.items()
            if identity[-1] == regime
        )
        fed = [pair["fedfalsify-v05"] for _, pair in ordered]
        pysr = [pair["official-pysr"] for _, pair in ordered]
        semantic_test = mcnemar_exact(
            [row.semantic_all_1e3 for row in fed],
            [row.semantic_all_1e3 for row in pysr],
        )
        primary_p[regime] = semantic_test.exact_p_value
        paired[regime] = {
            "pairs": len(fed),
            "pysr_completed_pairs": int(sum(row.completed for row in pysr)),
            "pysr_failed_or_incomplete_pairs": int(
                sum(not row.completed for row in pysr)
            ),
            "semantic_1e3_mcnemar": asdict(semantic_test),
            "semantic_1e2_mcnemar": asdict(
                mcnemar_exact(
                    [row.semantic_all_1e2 for row in fed],
                    [row.semantic_all_1e2 for row in pysr],
                )
            ),
            "strong_extrapolation_pysr_minus_fedfalsify": _paired_finite_bootstrap(
                [row.strong_extrapolation_nmse for row in fed],
                [row.strong_extrapolation_nmse for row in pysr],
                seed=20260804,
            ),
            "runtime_pysr_minus_fedfalsify": _paired_finite_bootstrap(
                [row.runtime_seconds for row in fed],
                [row.runtime_seconds for row in pysr],
                seed=20260805,
            ),
        }
    adjusted = holm_adjust(primary_p)
    for regime, value in adjusted.items():
        paired[regime]["semantic_1e3_holm_adjusted_p"] = value

    by_benchmark: dict[str, dict[str, object]] = {}
    benchmark_names = sorted({row.benchmark for row in rows})
    for benchmark in benchmark_names:
        for regime in BUDGETS:
            for method in ("fedfalsify-v05", "official-pysr"):
                subset = [
                    row
                    for row in rows
                    if row.benchmark == benchmark
                    and row.regime == regime
                    and row.method == method
                ]
                if not subset:
                    continue
                by_benchmark[f"{benchmark}:{regime}:{method}"] = {
                    "runs": len(subset),
                    "completed": int(sum(row.completed for row in subset)),
                    "semantic_all_1e3": float(
                        np.mean([row.semantic_all_1e3 for row in subset])
                    ),
                    "semantic_all_1e2": float(
                        np.mean([row.semantic_all_1e2 for row in subset])
                    ),
                    "strong_extrapolation_nmse": _finite_summary(
                        row.strong_extrapolation_nmse for row in subset
                    ),
                }

    return {
        "schema_version": 2,
        "status": "validation",
        "primary_endpoint": (
            "quality-regime all-domain semantic recovery at NMSE 1e-3"
        ),
        "rows": len(rows),
        "pairs": len(identities),
        "seeds": sorted({row.seed for row in rows}),
        "methods": method_summary,
        "paired": paired,
        "by_benchmark": by_benchmark,
        "protocol": {
            "benchmarks": benchmark_names,
            "scenarios": sorted({row.scenario for row in rows}),
            "noise_ratios": sorted({row.noise_ratio for row in rows}),
            "samples_per_client": sorted({row.samples_per_client for row in rows}),
            "clients": sorted({row.num_clients for row in rows}),
            "validation_seeds": list(VALIDATION_SEEDS),
            "budgets": BUDGETS,
            "semantic_samples_per_domain": 4000,
            "final_confirmation_start": FINAL_CONFIRMATION_START,
        },
        "scientific_boundary": [
            "Official PySR pools raw observations; FedFalsify does not.",
            "Strict structural recovery is reported only for finite-catalog FedFalsify.",
            "Primary matched inference retains incomplete PySR equations as failures.",
            "Continuous comparisons use finite matched pairs and report usable counts.",
            "Exception scenarios are excluded because the shared PySR grammar is unsupported.",
            "Seeds 11001 and above remain untouched for final confirmation.",
        ],
    }


_core.summarize = summarize


def main() -> None:
    _core.main()


if __name__ == "__main__":
    main()
