"""Frozen summary and go/no-go gate for the role-conditioned v4 matrix."""

from __future__ import annotations

from statistics import mean, median
from typing import Sequence

from .benchmarks import BENCHMARKS


def _key(row):
    return (
        row.benchmark,
        row.scenario,
        row.noise_ratio,
        row.samples_per_client,
        row.seed,
    )


def _mean(rows: Sequence[object], field: str) -> float:
    return float(mean(float(getattr(row, field)) for row in rows))


def summarize(rows: Sequence[object]) -> dict[str, object]:
    required = {
        "legacy-certificate",
        "crossfit-v2-structural",
        "stability-superset-v3",
        "role-v4-full",
        "role-v4-anchor",
        "role-v4-no-role-conditioning",
        "role-v4-no-path-persistence",
        "role-v4-no-backward",
        "centralized-forward",
        "score-only-federated",
    }
    by_method: dict[str, list[object]] = {}
    for row in rows:
        by_method.setdefault(row.method, []).append(row)
    missing = required - set(by_method)
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
            "forward_selected": _mean(selected, "fallback_selected"),
            "runtime_seconds": _mean(selected, "runtime_seconds"),
            "communication_bytes": _mean(selected, "communication_bytes"),
        }

    legacy = by_method["legacy-certificate"]
    proposed = by_method["role-v4-full"]
    anchor = {_key(row): row for row in by_method["role-v4-anchor"]}
    forward = {_key(row): row for row in by_method["role-v4-no-backward"]}

    conditions = {_key(row) for row in rows}
    full = (
        {row.benchmark for row in rows} == set(BENCHMARKS)
        and len(conditions) == 450
        and len(rows) == 4500
        and all(len(selected) == 450 for selected in by_method.values())
    )

    high = [
        row
        for row in proposed
        if row.noise_ratio == 0.20
        and row.benchmark in {"poly3", "interaction"}
    ]
    high_legacy = [
        row
        for row in legacy
        if row.noise_ratio == 0.20
        and row.benchmark in {"poly3", "interaction"}
    ]
    high_poly3 = [
        row
        for row in proposed
        if row.noise_ratio == 0.20 and row.benchmark == "poly3"
    ]
    exception_rows = [row for row in proposed if row.scenario == "exception"]

    pool_sizes = [
        int(row.candidate_pool_size)
        for row in proposed
        if row.candidate_pool_size is not None
    ]
    pool_nuisance = [
        int(row.candidate_pool_nuisance_count)
        for row in proposed
        if row.candidate_pool_nuisance_count is not None
    ]
    pool_recall = [
        float(row.candidate_pool_target_recall)
        for row in proposed
        if row.candidate_pool_target_recall is not None
    ]

    activated_forward = [
        row
        for row in by_method["role-v4-no-backward"]
        if row.fallback_selected == 1.0
    ]
    forward_exact_gains = sum(
        row.exact_recovery > anchor[_key(row)].exact_recovery
        for row in activated_forward
    )
    forward_exact_harms = sum(
        row.exact_recovery < anchor[_key(row)].exact_recovery
        for row in activated_forward
    )
    forward_nmse_gains = sum(
        row.test_nmse < anchor[_key(row)].test_nmse
        for row in activated_forward
    )
    forward_nmse_harms = sum(
        row.test_nmse > anchor[_key(row)].test_nmse
        for row in activated_forward
    )
    backward_exact_gains = sum(
        row.exact_recovery > forward[_key(row)].exact_recovery
        for row in proposed
    )
    backward_exact_harms = sum(
        row.exact_recovery < forward[_key(row)].exact_recovery
        for row in proposed
    )

    runtime_ratio = _mean(proposed, "runtime_seconds") / max(
        _mean(legacy, "runtime_seconds"), 1e-12
    )
    communication_ratio = _mean(
        proposed, "communication_bytes"
    ) / max(_mean(legacy, "communication_bytes"), 1.0)
    nmse_ratio = _mean(proposed, "test_nmse") / max(
        _mean(legacy, "test_nmse"), 1e-15
    )

    if full:
        high_poly3_target_recall = _mean(
            high_poly3, "candidate_pool_target_recall"
        )
        high_poly3_complete = _mean(
            high_poly3, "candidate_pool_contains_all_truth"
        )
        exception_candidate_recall = _mean(
            exception_rows, "exception_candidate_recalled"
        )
        conditional_exception_recovery = _mean(
            exception_rows, "exception_recovered"
        )
        median_pool_size = float(median(pool_sizes))
        criteria = {
            "overall_exact_noninferiority": _mean(
                proposed, "exact_recovery"
            )
            >= _mean(legacy, "exact_recovery") - 0.01,
            "high_noise_gain_over_legacy": _mean(
                high, "exact_recovery"
            )
            >= _mean(high_legacy, "exact_recovery") + 0.05,
            "high_noise_poly3_target_recall": high_poly3_target_recall >= 0.90,
            "high_noise_poly3_complete_coverage": high_poly3_complete >= 0.80,
            "exception_candidate_recall": exception_candidate_recall >= 0.90,
            "conditional_exception_recovery": conditional_exception_recovery >= 0.97,
            "spurious_acceptance_controlled": _mean(
                proposed, "spurious_accepted"
            )
            <= _mean(legacy, "spurious_accepted") + 0.01,
            "zero_forward_exact_harms": forward_exact_harms == 0,
            "zero_backward_exact_harms": backward_exact_harms == 0,
            "predictive_safety": nmse_ratio <= 1.10,
            "median_candidate_pool_size": median_pool_size <= 6.0,
            "runtime_below_15x": runtime_ratio < 15.0,
            "communication_below_30x": communication_ratio < 30.0,
        }
        passed = bool(all(criteria.values()))
    else:
        high_poly3_target_recall = None
        high_poly3_complete = None
        exception_candidate_recall = None
        conditional_exception_recovery = None
        median_pool_size = float(median(pool_sizes)) if pool_sizes else None
        criteria = {
            name: None
            for name in (
                "overall_exact_noninferiority",
                "high_noise_gain_over_legacy",
                "high_noise_poly3_target_recall",
                "high_noise_poly3_complete_coverage",
                "exception_candidate_recall",
                "conditional_exception_recovery",
                "spurious_acceptance_controlled",
                "zero_forward_exact_harms",
                "zero_backward_exact_harms",
                "predictive_safety",
                "median_candidate_pool_size",
                "runtime_below_15x",
                "communication_below_30x",
            )
        }
        passed = None

    return {
        "schema_version": 1,
        "status": "development-role-conditional-v4",
        "rows": len(rows),
        "conditions": len(conditions),
        "benchmarks": sorted({row.benchmark for row in rows}),
        "methods": methods,
        "candidate_generation": {
            "mean_target_recall": float(mean(pool_recall)) if pool_recall else None,
            "high_noise_poly3_target_recall": high_poly3_target_recall,
            "high_noise_poly3_complete_coverage": high_poly3_complete,
            "exception_candidate_recall": exception_candidate_recall,
            "median_candidate_pool_size": median_pool_size,
            "mean_nuisance_terms": (
                float(mean(pool_nuisance)) if pool_nuisance else None
            ),
        },
        "forward_audit": {
            "activations": len(activated_forward),
            "exact_gains": int(forward_exact_gains),
            "exact_harms": int(forward_exact_harms),
            "nmse_improvements": int(forward_nmse_gains),
            "nmse_harms": int(forward_nmse_harms),
        },
        "backward_audit": {
            "exact_gains": int(backward_exact_gains),
            "exact_harms": int(backward_exact_harms),
        },
        "conditional_exception_recovery": conditional_exception_recovery,
        "runtime_ratio_vs_legacy": runtime_ratio,
        "communication_ratio_vs_legacy": communication_ratio,
        "test_nmse_ratio_vs_legacy": nmse_ratio,
        "development_gate": {
            "evaluated": full,
            "criteria": criteria,
            "passed": passed,
            "scientific_boundary": (
                "Passing permits independent external validation and scalability only."
            ),
        },
    }
