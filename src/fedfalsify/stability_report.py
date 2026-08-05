"""Frozen go/no-go summary for the v3 development matrix."""

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
    by_method: dict[str, list[object]] = {}
    for row in rows:
        by_method.setdefault(row.method, []).append(row)
    required = {
        "legacy-certificate",
        "crossfit-v1-governed",
        "crossfit-v2-structural",
        "stability-superset-v3",
        "score-only-federated",
        "centralized-forward",
        "stability-v3-intersection",
    }
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
            "exception_recovered": _mean(
                selected, "exception_recovered"
            ),
            "continuation_selected": _mean(
                selected, "fallback_selected"
            ),
            "runtime_seconds": _mean(selected, "runtime_seconds"),
            "communication_bytes": _mean(
                selected, "communication_bytes"
            ),
        }

    conditions = {_key(row) for row in rows}
    full = (
        {row.benchmark for row in rows} == set(BENCHMARKS)
        and len(conditions) == 450
        and len(rows) == 3150
    )
    legacy = by_method["legacy-certificate"]
    v2 = by_method["crossfit-v2-structural"]
    proposed = by_method["stability-superset-v3"]
    intersections = {
        _key(row): row for row in by_method["stability-v3-intersection"]
    }
    activated = [row for row in proposed if row.fallback_selected == 1.0]
    exact_gains = sum(
        row.exact_recovery > intersections[_key(row)].exact_recovery
        for row in activated
    )
    exact_harms = sum(
        row.exact_recovery < intersections[_key(row)].exact_recovery
        for row in activated
    )
    nmse_gains = sum(
        row.test_nmse < intersections[_key(row)].test_nmse
        for row in activated
    )
    nmse_harms = sum(
        row.test_nmse > intersections[_key(row)].test_nmse
        for row in activated
    )

    def high(selected):
        return [
            row
            for row in selected
            if row.noise_ratio == 0.20
            and row.benchmark in {"poly3", "interaction"}
        ]

    high_poly3 = [
        row
        for row in proposed
        if row.noise_ratio == 0.20 and row.benchmark == "poly3"
    ]
    critical_recall = (
        float(mean(float(row.critical_term_recalled) for row in high_poly3))
        if high_poly3
        else None
    )
    sizes = [int(row.stable_superset_size) for row in proposed]
    nuisance = [
        int(row.stable_superset_nuisance_count) for row in proposed
    ]
    target_recall = [
        float(row.superset_target_recall) for row in proposed
    ]
    median_size = float(median(sizes))
    runtime_ratio = _mean(proposed, "runtime_seconds") / max(
        _mean(legacy, "runtime_seconds"), 1e-12
    )
    communication_ratio = _mean(
        proposed, "communication_bytes"
    ) / max(_mean(legacy, "communication_bytes"), 1.0)

    names = (
        "overall_exact_noninferiority",
        "high_noise_gain_over_legacy",
        "high_noise_gain_over_v2",
        "high_noise_poly3_candidate_recall",
        "spurious_acceptance_controlled",
        "exception_recovery",
        "zero_observed_exact_harms_on_activation",
        "median_superset_size",
        "runtime_below_15x",
        "communication_below_30x",
    )
    if full:
        criteria = {
            "overall_exact_noninferiority": _mean(
                proposed, "exact_recovery"
            )
            >= _mean(legacy, "exact_recovery") - 0.01,
            "high_noise_gain_over_legacy": _mean(
                high(proposed), "exact_recovery"
            )
            >= _mean(high(legacy), "exact_recovery") + 0.05,
            "high_noise_gain_over_v2": _mean(
                high(proposed), "exact_recovery"
            )
            >= _mean(high(v2), "exact_recovery") + 0.05,
            "high_noise_poly3_candidate_recall": (
                critical_recall is not None and critical_recall >= 0.85
            ),
            "spurious_acceptance_controlled": _mean(
                proposed, "spurious_accepted"
            )
            <= _mean(legacy, "spurious_accepted") + 0.01,
            "exception_recovery": _mean(
                proposed, "exception_recovered"
            )
            >= 0.97,
            "zero_observed_exact_harms_on_activation": exact_harms == 0,
            "median_superset_size": median_size <= 5.0,
            "runtime_below_15x": runtime_ratio < 15.0,
            "communication_below_30x": communication_ratio < 30.0,
        }
        passed = bool(all(criteria.values()))
    else:
        criteria = {name: None for name in names}
        passed = None

    return {
        "schema_version": 1,
        "status": "development-stability-superset-v3",
        "rows": len(rows),
        "conditions": len(conditions),
        "benchmarks": sorted({row.benchmark for row in rows}),
        "methods": methods,
        "candidate_generation": {
            "mean_target_recall": float(mean(target_recall)),
            "high_noise_poly3_critical_term_recall": critical_recall,
            "median_superset_size": median_size,
            "mean_nuisance_terms": float(mean(nuisance)),
        },
        "continuation_audit": {
            "activations": len(activated),
            "exact_gains": int(exact_gains),
            "exact_harms": int(exact_harms),
            "nmse_improvements": int(nmse_gains),
            "nmse_harms": int(nmse_harms),
        },
        "runtime_ratio_vs_legacy": runtime_ratio,
        "communication_ratio_vs_legacy": communication_ratio,
        "development_gate": {
            "evaluated": full,
            "criteria": criteria,
            "passed": passed,
            "scientific_boundary": (
                "Passing permits an independent external redesign study only."
            ),
        },
    }
