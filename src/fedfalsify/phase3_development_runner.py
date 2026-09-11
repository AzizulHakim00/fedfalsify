"""Governed Phase-3C fresh-development orchestration.

This module is intentionally separate from the sealed Phase-3B scientific
implementation. It owns only the prospective development matrix, seed and
checkpoint firewalls, paired analysis, persistence and reporting. It must not
change SCR, NCEE, v11, the V10 benchmark generator, or their scientific rules.
"""

from __future__ import annotations

from itertools import product
import os
from typing import Mapping, Sequence

import numpy as np
from scipy.stats import binomtest

from .scsv_v10_benchmarks import SINGLE_FAMILIES_V10
from .scsv_v12 import PHASE3_METHODS

DEVELOPMENT_SEEDS = tuple(range(29301, 29311))
AUTHORIZATION_TOKEN = "AUTHORIZE_PHASE3C_FRESH_DEVELOPMENT"
ANALYSIS_RNG_SEED = 930301
ConditionKey = tuple[str, int, str, str, float, int]
NULL_FAMILIES = {"null_role_v10", "anchor_contamination_null_v10"}
SPECIAL_QUARTER_FAMILIES = {"weak_source_role_v10", "dual_role_v10"}


def validate_development_seed_block(seeds: Sequence[int]) -> None:
    normalized = tuple(int(seed) for seed in seeds)
    if normalized != DEVELOPMENT_SEEDS:
        raise ValueError("Phase-3C development requires exactly seeds 29301--29310 in order")
    if 29300 in normalized:
        raise ValueError("engineering seed 29300 is not a development seed")
    if any(11001 <= seed <= 11999 for seed in normalized):
        raise ValueError("final-confirmation seeds 11001--11999 are blocked")


def require_development_authorization(token: str) -> None:
    """Fail closed unless tests passed and the exact development token is supplied."""
    if os.environ.get("FEDFALSIFY_PHASE3_TEST_GATE") != "PASS":
        raise RuntimeError("Phase-3 scientific test gate must pass before development execution")
    if str(token) != AUTHORIZATION_TOKEN:
        raise RuntimeError("explicit Phase-3C fresh-development authorization token is required")


def scientific_conditions(seeds: Sequence[int] = DEVELOPMENT_SEEDS) -> tuple[ConditionKey, ...]:
    validate_development_seed_block(seeds)
    conditions: list[ConditionKey] = []

    for family in SINGLE_FAMILIES_V10:
        for num_clients in (4, 8, 16):
            roles = ("single",) if num_clients == 4 else ("single", "quarter")
            for balance in ("balanced", "imbalanced"):
                for role in roles:
                    for noise in (0.10, 0.30):
                        for seed in seeds:
                            conditions.append(
                                (family, num_clients, balance, role, float(noise), int(seed))
                            )

    for family in ("null_role_v10", "anchor_contamination_null_v10"):
        for num_clients in (4, 8, 16):
            for balance in ("balanced", "imbalanced"):
                for noise in (0.10, 0.30):
                    for seed in seeds:
                        conditions.append(
                            (family, num_clients, balance, "none", float(noise), int(seed))
                        )

    for family in ("weak_source_role_v10", "dual_role_v10"):
        for num_clients in (8, 16):
            for balance in ("balanced", "imbalanced"):
                for noise in (0.10, 0.30):
                    for seed in seeds:
                        conditions.append(
                            (family, num_clients, balance, "quarter", float(noise), int(seed))
                        )

    result = tuple(conditions)
    if len(result) != 1200 or len(set(result)) != 1200:
        raise RuntimeError(f"Phase-3C condition firewall expected 1200 unique conditions, got {len(result)}")
    return result


def condition_key_string(condition: ConditionKey) -> str:
    family, clients, balance, role, noise, seed = condition
    return f"{family}|{int(clients)}|{balance}|{role}|{float(noise):.2f}|{int(seed)}"


def condition_key_from_row(row: Mapping[str, object]) -> ConditionKey:
    return (
        str(row["family"]),
        int(row["num_clients"]),
        str(row["balance_profile"]),
        str(row["role_profile"]),
        float(row["noise_ratio"]),
        int(row["seed"]),
    )


def validate_checkpoint_groups(rows: Sequence[dict]) -> tuple[list[dict], set[ConditionKey]]:
    authorized = set(scientific_conditions())
    grouped: dict[ConditionKey, list[dict]] = {}
    for raw in rows:
        try:
            key = condition_key_from_row(raw)
        except (KeyError, TypeError, ValueError):
            continue
        if key not in authorized:
            continue
        grouped.setdefault(key, []).append(dict(raw))

    cleaned: list[dict] = []
    completed: set[ConditionKey] = set()
    required_methods = set(PHASE3_METHODS)
    for condition in scientific_conditions():
        group = grouped.get(condition, [])
        methods = [str(row.get("method", "")) for row in group]
        if (
            len(group) == len(PHASE3_METHODS)
            and set(methods) == required_methods
            and len(methods) == len(set(methods))
        ):
            by_method = {str(row["method"]): dict(row) for row in group}
            for method in PHASE3_METHODS:
                item = by_method[method]
                item["condition_key"] = condition_key_string(condition)
                cleaned.append(item)
            completed.add(condition)
    return cleaned, completed


def scope_exact_recovery(
    true_roles: Mapping[str, Sequence[str]],
    predicted_roles: Mapping[str, Sequence[str]],
) -> float:
    """Return 1 only when localized term identities and client scopes both match."""
    true_keys = set(true_roles)
    predicted_keys = set(predicted_roles)
    if true_keys != predicted_keys:
        return 0.0
    for term in true_keys:
        if set(map(str, true_roles[term])) != set(map(str, predicted_roles[term])):
            return 0.0
    return 1.0


def _paired_maps(rows: Sequence[Mapping[str, object]]) -> tuple[dict[str, Mapping[str, object]], dict[str, Mapping[str, object]]]:
    baseline: dict[str, Mapping[str, object]] = {}
    full: dict[str, Mapping[str, object]] = {}
    for row in rows:
        method = str(row.get("method", ""))
        if method not in {PHASE3_METHODS[0], PHASE3_METHODS[-1]}:
            continue
        key = str(row["condition_key"])
        target = baseline if method == PHASE3_METHODS[0] else full
        if key in target:
            raise ValueError(f"duplicate paired-analysis row for {method}: {key}")
        target[key] = row
    if set(baseline) != set(full) or not baseline:
        raise ValueError("paired analysis requires exactly matched v11/full condition keys")
    return baseline, full


def paired_analysis(rows: Sequence[Mapping[str, object]], *, bootstrap_reps: int = 20_000) -> dict:
    """Paired v11/full exact-recovery analysis clustered by development seed."""
    if int(bootstrap_reps) <= 0:
        raise ValueError("bootstrap_reps must be positive")
    baseline, full = _paired_maps(rows)
    keys = sorted(baseline)

    differences: list[float] = []
    repairs = 0
    harms = 0
    seed_values: dict[int, list[float]] = {}
    for key in keys:
        v11_exact = float(baseline[key]["exact_recovery"])
        full_exact = float(full[key]["exact_recovery"])
        delta = full_exact - v11_exact
        differences.append(delta)
        if v11_exact == 0.0 and full_exact == 1.0:
            repairs += 1
        if v11_exact == 1.0 and full_exact == 0.0:
            harms += 1
        seed = int(full[key]["seed"])
        seed_values.setdefault(seed, []).append(delta)

    exact_gain = float(np.mean(differences))
    discordant = repairs + harms
    mcnemar_p = (
        float(binomtest(min(repairs, harms), n=discordant, p=0.5, alternative="two-sided").pvalue)
        if discordant
        else 1.0
    )

    seed_level = {
        int(seed): float(np.mean(values))
        for seed, values in sorted(seed_values.items())
    }
    seed_array = np.asarray(list(seed_level.values()), dtype=float)
    rng = np.random.default_rng(ANALYSIS_RNG_SEED)
    indices = rng.integers(0, len(seed_array), size=(int(bootstrap_reps), len(seed_array)))
    bootstrap = seed_array[indices].mean(axis=1)
    ci_low, ci_high = np.quantile(bootstrap, [0.025, 0.975])

    sign_statistics = []
    for signs in product((-1.0, 1.0), repeat=len(seed_array)):
        sign_statistics.append(float(np.mean(seed_array * np.asarray(signs, dtype=float))))
    sign_flip_p = float(
        np.mean(np.asarray(sign_statistics, dtype=float) >= exact_gain - 1e-15)
    )

    return {
        "matched_conditions": int(len(keys)),
        "repairs": int(repairs),
        "harms": int(harms),
        "exact_gain": exact_gain,
        "exact_harm_rate": float(harms / len(keys)),
        "mcnemar_exact_p": mcnemar_p,
        "bootstrap_reps": int(bootstrap_reps),
        "bootstrap_analysis_seed": ANALYSIS_RNG_SEED,
        "bootstrap_ci_low": float(ci_low),
        "bootstrap_ci_high": float(ci_high),
        "seed_sign_flip_p_one_sided": sign_flip_p,
        "seed_level_gain": seed_level,
    }


def gate_checks(metrics: Mapping[str, object]) -> dict[str, bool]:
    """Evaluate the frozen conjunctive Phase-3C development gate."""
    family = dict(metrics["family_recovery"])
    clients = dict(metrics["client_recovery"])
    checks = {
        "overall_exact_gain": float(metrics["overall_exact_gain"]) >= 0.03,
        "bootstrap_ci_positive": float(metrics["bootstrap_ci_low"]) > 0.0,
        "deviation_precision": float(metrics["deviation_precision_pooled"]) >= 0.99,
        "deviation_recall": float(metrics["deviation_recall_pooled"]) >= 0.94,
        "shared_precision": float(metrics["shared_precision_pooled"]) >= 0.975,
        "shared_recall": float(metrics["shared_recall_pooled"]) >= 0.98,
        "null_localized_fp": float(metrics["null_localized_fp_rate"]) <= 0.02,
        "null_shared_fp": float(metrics["null_shared_fp_rate"]) <= 0.02,
        "exact_harm_rate": float(metrics["exact_harm_rate"]) <= 0.01,
        "family_quadratic": float(family["quadratic_role_v10"]) >= 0.92,
        "family_linear": float(family["linear_role_v10"]) >= 0.92,
        "family_trig": float(family["trig_role_v10"]) >= 0.92,
        "family_interaction": float(family["interaction_role_v10"]) >= 0.92,
        "clients_k4": float(clients["4"]) >= 0.90,
        "clients_k8": float(clients["8"]) >= 0.93,
        "clients_k16": float(clients["16"]) >= 0.95,
        "high_noise_main_deviation": float(metrics["high_noise_main_deviation_recovery"]) >= 0.90,
        "high_noise_main_exact_gain": float(metrics["high_noise_main_exact_gain"]) >= 0.05,
        "weak_source": float(metrics["weak_source_recovery"]) >= 0.90,
        "dual_role": float(metrics["dual_role_recovery"]) >= 0.90,
        "communication_ratio": float(metrics["communication_ratio_vs_v11"]) <= 1.25,
        "runtime_ratio": float(metrics["runtime_ratio_vs_v11"]) <= 1.50,
        "integrity_zero": int(metrics["integrity_violations"]) == 0,
        "complete_conditions": int(metrics["complete_conditions"]) == 1200,
        "primary_rows": int(metrics["primary_rows"]) == 4800,
    }
    return {name: bool(value) for name, value in checks.items()}
