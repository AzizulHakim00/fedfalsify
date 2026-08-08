"""Frozen GO/NO-GO summary for HR-VFS v5."""

from __future__ import annotations

from statistics import mean, median
from typing import Sequence


def _rate(rows, attr):
    return mean(float(getattr(row, attr)) for row in rows) if rows else 0.0


def _method(rows, name):
    return [row for row in rows if row.method == name]


def summarize(rows: Sequence[object]) -> dict[str, object]:
    full = _method(rows, "hr-v5-full")
    legacy = _method(rows, "legacy-certificate")
    if len(full) != 450 or len(legacy) != 450:
        raise ValueError("v5 gate requires exactly 450 full and 450 legacy rows")

    def subset(items, *, benchmark=None, noise=None, scenario=None):
        out = list(items)
        if benchmark is not None:
            out = [r for r in out if r.benchmark == benchmark]
        if noise is not None:
            out = [r for r in out if abs(float(r.noise_ratio) - noise) < 1e-12]
        if scenario is not None:
            out = [r for r in out if r.scenario == scenario]
        return out

    high_poly_full = subset(full, benchmark="poly3", noise=0.20)
    high_poly_legacy = subset(legacy, benchmark="poly3", noise=0.20)
    high_int_full = subset(full, benchmark="interaction", noise=0.20)
    high_int_legacy = subset(legacy, benchmark="interaction", noise=0.20)
    base_full = subset(full, benchmark="base")
    base_legacy = subset(legacy, benchmark="base")
    exception_full = subset(full, scenario="exception")

    gates = {
        "A_overall_exact_noninferiority": _rate(full, "exact_recovery") >= _rate(legacy, "exact_recovery") - 0.01,
        "B_high_noise_poly3_gain": _rate(high_poly_full, "exact_recovery") >= _rate(high_poly_legacy, "exact_recovery") + 0.05,
        "C_high_noise_interaction_gain": _rate(high_int_full, "exact_recovery") >= _rate(high_int_legacy, "exact_recovery") + 0.05,
        "D_base_noninferiority": _rate(base_full, "exact_recovery") >= _rate(base_legacy, "exact_recovery") - 0.01,
        "E_poly3_bank_target_recall": _rate(high_poly_full, "candidate_pool_target_recall") >= 0.95,
        "F_poly3_complete_bank_coverage": _rate(high_poly_full, "candidate_bank_contains_all_truth") >= 0.90,
        "G_exception_bank_recall": _rate(exception_full, "exception_candidate_recalled") >= 0.95,
        "H_exception_final_recovery": _rate(exception_full, "exception_recovered") >= 0.97,
        "I_spurious_control": _rate(full, "spurious_accepted") <= max(0.05, _rate(legacy, "spurious_accepted") + 0.01),
        "J_zero_single_forward_exact_harms": sum(int(r.single_exact_harms or 0) for r in full) == 0,
        "K_zero_pair_exact_harms": sum(int(r.pair_exact_harms or 0) for r in full) == 0,
        "L_nmse_noninferiority": _rate(full, "test_nmse") <= 1.10 * _rate(legacy, "test_nmse"),
        "M_bank_size": median(float(r.candidate_pool_size or 0) for r in full) <= 10,
        "N_runtime": median(float(r.runtime_seconds) for r in full) < 15 * median(float(r.runtime_seconds) for r in legacy),
        "O_communication": median(float(r.communication_bytes) for r in full) < 30 * median(float(r.communication_bytes) for r in legacy),
    }
    metrics = {
        "full_exact_recovery": _rate(full, "exact_recovery"),
        "legacy_exact_recovery": _rate(legacy, "exact_recovery"),
        "high_noise_poly3_full_exact": _rate(high_poly_full, "exact_recovery"),
        "high_noise_poly3_legacy_exact": _rate(high_poly_legacy, "exact_recovery"),
        "high_noise_interaction_full_exact": _rate(high_int_full, "exact_recovery"),
        "high_noise_interaction_legacy_exact": _rate(high_int_legacy, "exact_recovery"),
        "high_noise_poly3_bank_target_recall": _rate(high_poly_full, "candidate_pool_target_recall"),
        "high_noise_poly3_complete_bank_coverage": _rate(high_poly_full, "candidate_bank_contains_all_truth"),
        "exception_bank_recall": _rate(exception_full, "exception_candidate_recalled"),
        "exception_final_recovery": _rate(exception_full, "exception_recovered"),
        "full_spurious_acceptance": _rate(full, "spurious_accepted"),
        "full_mean_test_nmse": _rate(full, "test_nmse"),
        "legacy_mean_test_nmse": _rate(legacy, "test_nmse"),
        "single_exact_harms": sum(int(r.single_exact_harms or 0) for r in full),
        "pair_exact_harms": sum(int(r.pair_exact_harms or 0) for r in full),
        "median_bank_size": median(float(r.candidate_pool_size or 0) for r in full),
    }
    return {
        "protocol": "HR-VFS-v5-frozen",
        "rows": len(rows),
        "conditions_per_method": 450,
        "gates": gates,
        "metrics": metrics,
        "decision": "GO" if all(gates.values()) else "NO-GO",
    }
