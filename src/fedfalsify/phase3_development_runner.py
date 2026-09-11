"""Governed Phase-3C fresh-development orchestration.

This module is intentionally separate from the sealed Phase-3B scientific
implementation. It owns only the prospective development matrix, seed and
checkpoint firewalls, paired analysis, persistence and reporting. It must not
change SCR, NCEE, v11, the V10 benchmark generator, or their scientific rules.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
from itertools import product
import json
import os
from pathlib import Path
import platform
import shutil
import sys
from time import perf_counter
from typing import Callable, Mapping, Sequence
import zipfile

import joblib
import numpy as np
import pandas as pd
from scipy.stats import binomtest

from .phase3_engineering_runner import (
    _ablation_summary,
    _atomic_joblib,
    _atomic_pickle,
    _atomic_write_json,
    _atomic_write_text,
    _diagnostic_frames,
    _evaluate_output as _engineering_evaluate_output,
    _jsonable,
    _method_summary,
    _sha256_file,
    atomic_write_csv,
)
from .scsv_v10_benchmarks import (
    INTERACTION_DEV_V10,
    LINEAR_DEV_V10,
    QUADRATIC_DEV_V10,
    SINGLE_FAMILIES_V10,
    TRIG_DEV_V10,
    V10_DEVIATIONS,
    WEAK_SOURCE_DEV_V10,
    generate_v10_benchmark,
    v10_catalog,
)
from .scsv_v12 import PHASE3_METHODS, SCSVV12Output, run_scsv_v12_branches

DEVELOPMENT_SEEDS = tuple(range(29301, 29311))
AUTHORIZATION_TOKEN = "AUTHORIZE_PHASE3C_FRESH_DEVELOPMENT"
ANALYSIS_RNG_SEED = 930301
FROZEN_SCIENTIFIC_SOURCE = "b67a07371bcf244728536028593373ca7d1990b1"
FROZEN_PROTOCOL_SHA256 = "__UNFROZEN__"
PROTOCOL_NAME = "FROZEN_PHASE3C_DEVELOPMENT_PROTOCOL.md"
CHECKPOINT_NAME = "phase3_development_checkpoint.csv"
STATE_PKL_NAME = "phase3_development_state.pkl"
STATE_JOBLIB_NAME = "phase3_development_state.joblib"
MANIFEST_NAME = "phase3_development_sha256.txt"
ZIP_NAME = "FedFalsify_PHASE3C_FRESH_DEVELOPMENT_RESULTS.zip"

ConditionKey = tuple[str, int, str, str, float, int]
NULL_FAMILIES = {"null_role_v10", "anchor_contamination_null_v10"}
SPECIAL_QUARTER_FAMILIES = {"weak_source_role_v10", "dual_role_v10"}

REQUIRED_ARTIFACTS = (
    PROTOCOL_NAME,
    CHECKPOINT_NAME,
    "phase3_development_rows.csv",
    "phase3_development_method_summary.csv",
    "phase3_development_ablation_summary.csv",
    "phase3_development_shared_diagnostics.csv",
    "phase3_development_localized_diagnostics.csv",
    "phase3_development_failure_taxonomy.csv",
    "phase3_development_paired_analysis.json",
    "phase3_development_seed_level_gain.csv",
    "phase3_development_gate_metrics.json",
    "phase3_development_gate_checks.json",
    "phase3_development_integrity.json",
    "phase3_development_environment.json",
    "phase3_development_decision.json",
    STATE_PKL_NAME,
    STATE_JOBLIB_NAME,
    "phase3_development_report.txt",
    MANIFEST_NAME,
    ZIP_NAME,
)


def _emit(live: bool, message: str) -> None:
    if live:
        print(message, flush=True)


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


def _validate_groups_for_conditions(
    rows: Sequence[dict], conditions: Sequence[ConditionKey]
) -> tuple[list[dict], set[ConditionKey]]:
    authorized_conditions = tuple(conditions)
    authorized = set(authorized_conditions)
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
    for condition in authorized_conditions:
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


def validate_checkpoint_groups(rows: Sequence[dict]) -> tuple[list[dict], set[ConditionKey]]:
    return _validate_groups_for_conditions(rows, scientific_conditions())


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


def _client_ids(indices: Sequence[int]) -> tuple[str, ...]:
    return tuple(f"client-{int(index) + 1}" for index in indices)


def _true_role_map(condition: ConditionKey) -> dict[str, tuple[str, ...]]:
    family, num_clients, _balance, role, _noise, _seed = condition
    if family in NULL_FAMILIES:
        return {}

    family_term = {
        "quadratic_role_v10": QUADRATIC_DEV_V10,
        "linear_role_v10": LINEAR_DEV_V10,
        "trig_role_v10": TRIG_DEV_V10,
        "interaction_role_v10": INTERACTION_DEV_V10,
    }
    if family in family_term:
        count = 1 if role == "single" else max(1, int(num_clients) // 4)
        indices = tuple(range(int(num_clients) - count, int(num_clients)))
        return {family_term[family]: _client_ids(indices)}

    quarter = max(1, int(num_clients) // 4)
    last = tuple(range(int(num_clients) - quarter, int(num_clients)))
    if family == "weak_source_role_v10":
        return {WEAK_SOURCE_DEV_V10: _client_ids(last)}
    if family == "dual_role_v10":
        prior = tuple(range(int(num_clients) - 2 * quarter, int(num_clients) - quarter))
        return {
            QUADRATIC_DEV_V10: _client_ids(last),
            LINEAR_DEV_V10: _client_ids(prior),
        }
    raise KeyError(f"unknown Phase-3C family: {family}")


def _predicted_role_map(output: object) -> dict[str, tuple[str, ...]]:
    accepted = set(getattr(output, "accepted_deviations", ()))
    if not accepted:
        return {}

    result: dict[str, tuple[str, ...]] = {}
    if not isinstance(output, SCSVV12Output):
        for diagnostic in getattr(output, "diagnostics", ()):
            term = str(getattr(diagnostic, "term", ""))
            if term in accepted:
                result[term] = tuple(map(str, getattr(diagnostic, "role_client_ids", ())))
        return result

    if output.localized_mode == "v11-adapter":
        diagnostics = output.ledger.discovery_localized_diagnostics
        for diagnostic in diagnostics:
            term = str(getattr(diagnostic, "term", ""))
            if term in accepted:
                result[term] = tuple(map(str, getattr(diagnostic, "role_client_ids", ())))
        return result

    for diagnostic in output.ledger.probe_diagnostics:
        term = str(getattr(diagnostic, "term", ""))
        if term not in accepted or not bool(getattr(diagnostic, "final_accepted", False)):
            continue
        identity = tuple(getattr(diagnostic, "identity", ()))
        if len(identity) < 5:
            continue
        result[term] = tuple(map(str, identity[4]))
    return result


def _evaluate_condition(condition: ConditionKey) -> list[dict]:
    """Execute the four frozen scientific branches for one authorized condition."""
    family, num_clients, balance, role, noise, seed = condition
    if int(seed) not in set(DEVELOPMENT_SEEDS):
        raise ValueError("Phase-3C evaluator received an unauthorized benchmark seed")
    generated = generate_v10_benchmark(
        family,
        nominal_samples_per_client=100,
        noise_ratio=float(noise),
        seed=int(seed),
        num_clients=int(num_clients),
        balance_profile=balance,
        role_profile=role,
    )
    target_mse = max(float(generated.noise_std) ** 2 * 2.5, 1e-8)
    outputs = run_scsv_v12_branches(
        generated.clients,
        v10_catalog(),
        seed=int(seed),
        target_mse=target_mse,
        min_repair_score=0.05,
    )
    if tuple(output.method for output in outputs) != PHASE3_METHODS:
        raise RuntimeError("Phase-3C evaluator method order drifted")

    true_roles = _true_role_map(condition)
    rows: list[dict] = []
    for output in outputs:
        row = _engineering_evaluate_output(generated, output, condition)
        predicted_roles = _predicted_role_map(output)
        scope_exact = scope_exact_recovery(true_roles, predicted_roles)
        row.update(
            {
                "true_roles_json": json.dumps(_jsonable(true_roles), sort_keys=True, separators=(",", ":")),
                "predicted_roles_json": json.dumps(_jsonable(predicted_roles), sort_keys=True, separators=(",", ":")),
                "scope_exact_recovery": float(scope_exact),
                "mechanism_exact_recovery": float(float(row["exact_recovery"]) == 1.0 and scope_exact == 1.0),
            }
        )
        rows.append(row)
    return rows


def _validate_new_group(condition: ConditionKey, rows: Sequence[dict]) -> list[dict]:
    if len(rows) != len(PHASE3_METHODS):
        raise RuntimeError("development condition did not return exactly four rows")
    methods = tuple(str(row.get("method", "")) for row in rows)
    if methods != PHASE3_METHODS or len(set(methods)) != len(PHASE3_METHODS):
        raise RuntimeError("development condition returned an invalid method group")
    normalized = []
    for row in rows:
        item = dict(row)
        if condition_key_from_row(item) != condition:
            raise RuntimeError("development evaluator changed condition identity")
        item["condition_key"] = condition_key_string(condition)
        normalized.append(item)
    return normalized


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


def _pooled_precision(frame: pd.DataFrame, prefix: str) -> float:
    tp = float(pd.to_numeric(frame[f"{prefix}_tp"], errors="coerce").sum())
    fp = float(pd.to_numeric(frame[f"{prefix}_fp"], errors="coerce").sum())
    return float(tp / (tp + fp)) if tp + fp else 1.0


def _pooled_recall(frame: pd.DataFrame, prefix: str) -> float:
    tp = float(pd.to_numeric(frame[f"{prefix}_tp"], errors="coerce").sum())
    fn = float(pd.to_numeric(frame[f"{prefix}_fn"], errors="coerce").sum())
    return float(tp / (tp + fn)) if tp + fn else 1.0


def _subset_exact_gain(full: pd.DataFrame, v11: pd.DataFrame, mask: pd.Series) -> float:
    selected_full = full.loc[mask]
    keys = set(selected_full["condition_key"])
    selected_v11 = v11[v11["condition_key"].isin(keys)]
    full_map = selected_full.set_index("condition_key")["exact_recovery"].astype(float)
    v11_map = selected_v11.set_index("condition_key")["exact_recovery"].astype(float)
    common = sorted(set(full_map.index) & set(v11_map.index))
    if not common:
        return float("nan")
    return float(np.mean([float(full_map[key]) - float(v11_map[key]) for key in common]))


def development_gate_metrics(rows: Sequence[dict]) -> dict:
    frame = pd.DataFrame(list(rows))
    if frame.empty:
        raise ValueError("development gate requires rows")
    full = frame[frame["method"] == PHASE3_METHODS[-1]].copy()
    v11 = frame[frame["method"] == PHASE3_METHODS[0]].copy()
    paired = paired_analysis(rows)

    full["all_true_deviations_recovered"] = pd.to_numeric(
        full["deviation_fn"], errors="coerce"
    ).eq(0)
    main_mask = full["family"].isin(set(SINGLE_FAMILIES_V10))
    nonnull_mask = ~full["family"].isin(NULL_FAMILIES)
    null_mask = full["family"].isin(NULL_FAMILIES)

    family_recovery = {
        family: float(full.loc[full["family"] == family, "all_true_deviations_recovered"].mean())
        for family in SINGLE_FAMILIES_V10
    }
    client_recovery = {
        str(k): float(
            full.loc[nonnull_mask & full["num_clients"].astype(int).eq(k), "all_true_deviations_recovered"].mean()
        )
        for k in (4, 8, 16)
    }
    high_main = main_mask & pd.to_numeric(full["noise_ratio"], errors="coerce").eq(0.30)
    weak = full["family"].eq("weak_source_role_v10")
    dual = full["family"].eq("dual_role_v10")

    cleaned, completed = validate_checkpoint_groups(rows)
    return {
        "overall_exact_gain": float(paired["exact_gain"]),
        "bootstrap_ci_low": float(paired["bootstrap_ci_low"]),
        "bootstrap_ci_high": float(paired["bootstrap_ci_high"]),
        "mcnemar_exact_p": float(paired["mcnemar_exact_p"]),
        "seed_sign_flip_p_one_sided": float(paired["seed_sign_flip_p_one_sided"]),
        "deviation_precision_pooled": _pooled_precision(full, "deviation"),
        "deviation_recall_pooled": _pooled_recall(full, "deviation"),
        "shared_precision_pooled": _pooled_precision(full, "shared"),
        "shared_recall_pooled": _pooled_recall(full, "shared"),
        "null_localized_fp_rate": float(pd.to_numeric(full.loc[null_mask, "deviation_fp"], errors="coerce").gt(0).mean()),
        "null_shared_fp_rate": float(pd.to_numeric(full.loc[null_mask, "shared_fp"], errors="coerce").gt(0).mean()),
        "exact_harm_rate": float(paired["exact_harm_rate"]),
        "family_recovery": family_recovery,
        "client_recovery": client_recovery,
        "high_noise_main_deviation_recovery": float(full.loc[high_main, "all_true_deviations_recovered"].mean()),
        "high_noise_main_exact_gain": _subset_exact_gain(full, v11, high_main),
        "weak_source_recovery": float(full.loc[weak, "all_true_deviations_recovered"].mean()),
        "dual_role_recovery": float(full.loc[dual, "all_true_deviations_recovered"].mean()),
        "communication_ratio_vs_v11": float(
            pd.to_numeric(full["communication_bytes"], errors="coerce").median()
            / max(float(pd.to_numeric(v11["communication_bytes"], errors="coerce").median()), 1.0)
        ),
        "runtime_ratio_vs_v11": float(
            pd.to_numeric(full["runtime_seconds"], errors="coerce").median()
            / max(float(pd.to_numeric(v11["runtime_seconds"], errors="coerce").median()), 1e-15)
        ),
        "scope_exact_recovery": float(pd.to_numeric(full["scope_exact_recovery"], errors="coerce").mean()),
        "mechanism_exact_recovery": float(pd.to_numeric(full["mechanism_exact_recovery"], errors="coerce").mean()),
        "integrity_violations": int(
            sum(int(float(row.get("integrity_violations", 0))) for row in cleaned)
        ),
        "complete_conditions": int(len(completed)),
        "primary_rows": int(len(rows)),
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


def development_decision(rows: Sequence[dict]) -> dict:
    metrics = development_gate_metrics(rows)
    checks = gate_checks(metrics)
    return {
        "decision": "PHASE3-DEVELOPMENT-GO" if all(checks.values()) else "PHASE3-DEVELOPMENT-NO-GO",
        "basis": "prospectively frozen conjunctive Phase-3C development gate",
        "metrics": metrics,
        "checks": checks,
    }


def load_checkpoint(path: Path | str) -> list[dict]:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return []
    return [dict(row) for row in pd.read_csv(path).to_dict(orient="records")]


def _state_payload(rows: Sequence[dict]) -> dict:
    cleaned, completed = validate_checkpoint_groups(rows)
    ordered_conditions = scientific_conditions()
    return {
        "schema_version": 1,
        "development_seeds": DEVELOPMENT_SEEDS,
        "methods": PHASE3_METHODS,
        "completed_condition_keys": [
            condition_key_string(condition)
            for condition in ordered_conditions
            if condition in completed
        ],
        "rows": list(cleaned),
    }


def _save_checkpoint_state(rows: Sequence[dict], output_dir: Path) -> None:
    cleaned, _ = validate_checkpoint_groups(rows)
    atomic_write_csv(pd.DataFrame(cleaned), output_dir / CHECKPOINT_NAME)
    state = _state_payload(cleaned)
    _atomic_pickle(state, output_dir / STATE_PKL_NAME)
    _atomic_joblib(state, output_dir / STATE_JOBLIB_NAME)


def _run_condition_groups(
    output_dir: Path,
    conditions: Sequence[ConditionKey],
    *,
    evaluator: Callable[[ConditionKey], list[dict]] = _evaluate_condition,
    live: bool,
) -> tuple[list[dict], set[ConditionKey]]:
    checkpoint_path = output_dir / CHECKPOINT_NAME
    loaded = load_checkpoint(checkpoint_path)
    rows, completed = _validate_groups_for_conditions(loaded, conditions)
    if len(rows) != len(loaded):
        atomic_write_csv(pd.DataFrame(rows), checkpoint_path)
        _emit(live, "[RESUME] discarded partial, duplicate, or unauthorized checkpoint rows")

    total = len(conditions)
    _emit(live, f"[RESUME] valid complete groups={len(completed)}/{total}")
    for index, condition in enumerate(conditions, start=1):
        if condition in completed:
            _emit(live, f"[CONDITION {index}/{total}] resume-skip {condition_key_string(condition)}")
            continue
        started = perf_counter()
        _emit(live, f"[CONDITION {index}/{total}] start {condition_key_string(condition)}")
        group = _validate_new_group(condition, evaluator(condition))
        rows.extend(group)
        rows, completed = _validate_groups_for_conditions(rows, conditions)
        atomic_write_csv(pd.DataFrame(rows), checkpoint_path)
        if tuple(conditions) == scientific_conditions():
            state = _state_payload(rows)
            _atomic_pickle(state, output_dir / STATE_PKL_NAME)
            _atomic_joblib(state, output_dir / STATE_JOBLIB_NAME)
        _emit(live, f"[CHECKPOINT] {index}/{total} saved; elapsed={perf_counter() - started:.2f}s")
    return rows, completed


def _repo_protocol_path() -> Path:
    return Path(__file__).resolve().parents[2] / "research" / PROTOCOL_NAME


def _verify_and_copy_protocol(output_dir: Path) -> Path:
    if FROZEN_PROTOCOL_SHA256 == "__UNFROZEN__":
        raise RuntimeError("Phase-3C protocol is not frozen; fresh-development execution is blocked")
    source = _repo_protocol_path()
    if not source.exists():
        raise FileNotFoundError(f"frozen development protocol missing: {source}")
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != FROZEN_PROTOCOL_SHA256:
        raise RuntimeError(f"Phase-3C protocol SHA mismatch: expected {FROZEN_PROTOCOL_SHA256}, got {actual}")
    destination = output_dir / PROTOCOL_NAME
    tmp = destination.with_name(destination.name + ".tmp")
    shutil.copyfile(source, tmp)
    os.replace(tmp, destination)
    return destination


def _method_summary_with_scope(rows: Sequence[dict]) -> pd.DataFrame:
    summary = _method_summary(rows)
    frame = pd.DataFrame(list(rows))
    scope = (
        frame.groupby("method", sort=False)[["scope_exact_recovery", "mechanism_exact_recovery"]]
        .mean()
        .reset_index()
    )
    return summary.merge(scope, on="method", how="left")


def _failure_taxonomy(rows: Sequence[dict]) -> pd.DataFrame:
    records = []
    for row in rows:
        shared_error = int(row.get("shared_fp", 0)) > 0 or int(row.get("shared_fn", 0)) > 0
        local_error = int(row.get("deviation_fp", 0)) > 0 or int(row.get("deviation_fn", 0)) > 0
        if int(row.get("integrity_violations", 0)) > 0:
            category = "INTEGRITY"
        elif not shared_error and not local_error and float(row.get("exact_recovery", 0.0)) == 1.0:
            category = "EXACT"
        elif shared_error and local_error:
            category = "BOTH"
        elif shared_error:
            category = "SHARED-ONLY"
        elif local_error:
            category = "LOCALIZED-ONLY"
        else:
            category = "OTHER"
        records.append(
            {
                "condition_key": row.get("condition_key"),
                "seed": row.get("seed"),
                "family": row.get("family"),
                "method": row.get("method"),
                "failure_category": category,
                "scope_exact_recovery": row.get("scope_exact_recovery"),
                "mechanism_exact_recovery": row.get("mechanism_exact_recovery"),
            }
        )
    return pd.DataFrame(records)


def _environment_payload(protocol_path: Path) -> dict:
    def version(name: str) -> str:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return "unavailable"

    return {
        "schema_version": 1,
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": version("scipy"),
        "joblib": joblib.__version__,
        "fedfalsify": version("fedfalsify"),
        "frozen_scientific_source": FROZEN_SCIENTIFIC_SOURCE,
        "development_harness_commit": os.environ.get("FEDFALSIFY_PHASE3C_HARNESS_COMMIT", "unknown"),
        "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        "development_seeds": list(DEVELOPMENT_SEEDS),
        "blocked_engineering_seed": 29300,
        "blocked_final_seed_range": "11001-11999",
        "analysis_rng_seed": ANALYSIS_RNG_SEED,
    }


def _integrity_payload(rows: Sequence[dict], *, artifacts_ok: bool, zip_verified: bool) -> dict:
    cleaned, completed = validate_checkpoint_groups(rows)
    return {
        "schema_version": 1,
        "expected_conditions": 1200,
        "complete_conditions": len(completed),
        "expected_primary_rows": 4800,
        "primary_rows": len(rows),
        "valid_primary_rows": len(cleaned),
        "duplicate_or_partial_rows": int(len(rows) - len(cleaned)),
        "integrity_violations": int(
            sum(int(float(row.get("integrity_violations", 0))) for row in cleaned)
        ),
        "method_set": list(PHASE3_METHODS),
        "seed_set": sorted({int(condition[-1]) for condition in completed}),
        "base_artifacts_ok": bool(artifacts_ok),
        "zip_verified": bool(zip_verified),
    }


def _write_manifest(output_dir: Path) -> Path:
    lines = []
    for name in sorted(REQUIRED_ARTIFACTS):
        if name in {MANIFEST_NAME, ZIP_NAME}:
            continue
        path = output_dir / name
        if not path.exists():
            raise FileNotFoundError(f"required development artifact missing before manifest: {name}")
        lines.append(f"{_sha256_file(path)}  {name}")
    manifest = output_dir / MANIFEST_NAME
    _atomic_write_text("\n".join(lines) + "\n", manifest)
    return manifest


def _write_zip(output_dir: Path) -> tuple[Path, bool]:
    archive = output_dir / ZIP_NAME
    tmp = archive.with_name(archive.name + ".tmp")
    members = [name for name in REQUIRED_ARTIFACTS if name != ZIP_NAME]
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for name in sorted(members):
            handle.write(output_dir / name, arcname=name)
    os.replace(tmp, archive)
    with zipfile.ZipFile(archive, "r") as handle:
        ok = handle.testzip() is None
    return archive, bool(ok)


def _base_artifacts_ok(output_dir: Path) -> bool:
    excluded = {MANIFEST_NAME, ZIP_NAME, "phase3_development_integrity.json"}
    for name in REQUIRED_ARTIFACTS:
        if name in excluded:
            continue
        path = output_dir / name
        if not path.exists() or not path.is_file():
            return False
        _sha256_file(path)
    return True


def save_development_artifacts(rows: Sequence[dict], output_dir: Path | str) -> dict:
    output_dir = Path(output_dir)
    cleaned, completed = validate_checkpoint_groups(rows)
    if len(completed) != 1200 or len(cleaned) != 4800 or len(rows) != 4800:
        raise RuntimeError("Phase-3C final artifacts require exactly 1200 complete four-method groups")

    protocol_path = _verify_and_copy_protocol(output_dir)
    atomic_write_csv(pd.DataFrame(cleaned), output_dir / "phase3_development_rows.csv")
    atomic_write_csv(pd.DataFrame(cleaned), output_dir / CHECKPOINT_NAME)

    shared, localized = _diagnostic_frames(cleaned)
    atomic_write_csv(shared, output_dir / "phase3_development_shared_diagnostics.csv")
    atomic_write_csv(localized, output_dir / "phase3_development_localized_diagnostics.csv")
    atomic_write_csv(_failure_taxonomy(cleaned), output_dir / "phase3_development_failure_taxonomy.csv")

    method_summary = _method_summary_with_scope(cleaned)
    ablation = _ablation_summary(method_summary)
    atomic_write_csv(method_summary, output_dir / "phase3_development_method_summary.csv")
    atomic_write_csv(ablation, output_dir / "phase3_development_ablation_summary.csv")

    paired = paired_analysis(cleaned)
    _atomic_write_json(paired, output_dir / "phase3_development_paired_analysis.json")
    seed_frame = pd.DataFrame(
        [
            {"seed": int(seed), "exact_gain_full_minus_v11": float(gain)}
            for seed, gain in paired["seed_level_gain"].items()
        ]
    )
    atomic_write_csv(seed_frame, output_dir / "phase3_development_seed_level_gain.csv")

    decision_payload = development_decision(cleaned)
    metrics = decision_payload["metrics"]
    checks = decision_payload["checks"]
    _atomic_write_json(metrics, output_dir / "phase3_development_gate_metrics.json")
    _atomic_write_json(checks, output_dir / "phase3_development_gate_checks.json")
    _atomic_write_json(
        {"decision": decision_payload["decision"], "basis": decision_payload["basis"]},
        output_dir / "phase3_development_decision.json",
    )
    _atomic_write_json(_environment_payload(protocol_path), output_dir / "phase3_development_environment.json")

    state = _state_payload(cleaned)
    _atomic_pickle(state, output_dir / STATE_PKL_NAME)
    _atomic_joblib(state, output_dir / STATE_JOBLIB_NAME)

    report = (
        "FedFalsify Phase-3C Fresh-Development Report\n"
        "============================================\n"
        f"Development seeds: {DEVELOPMENT_SEEDS[0]}-{DEVELOPMENT_SEEDS[-1]}\n"
        f"Complete conditions: {len(completed)}\n"
        f"Primary method rows: {len(cleaned)}\n"
        f"Decision: {decision_payload['decision']}\n\n"
        "METHOD SUMMARY\n"
        + method_summary.to_string(index=False)
        + "\n\nABLATION SUMMARY\n"
        + ablation.to_string(index=False)
        + "\n\nPAIRED ANALYSIS\n"
        + json.dumps(_jsonable(paired), indent=2, sort_keys=True)
        + "\n\nGATE CHECKS\n"
        + json.dumps(_jsonable(checks), indent=2, sort_keys=True)
        + "\n"
    )
    _atomic_write_text(report, output_dir / "phase3_development_report.txt")

    artifacts_ok = _base_artifacts_ok(output_dir)
    _atomic_write_json(
        _integrity_payload(cleaned, artifacts_ok=artifacts_ok, zip_verified=False),
        output_dir / "phase3_development_integrity.json",
    )
    _write_manifest(output_dir)
    archive, first_zip_ok = _write_zip(output_dir)

    _atomic_write_json(
        _integrity_payload(cleaned, artifacts_ok=artifacts_ok, zip_verified=first_zip_ok),
        output_dir / "phase3_development_integrity.json",
    )
    _write_manifest(output_dir)
    archive, final_zip_ok = _write_zip(output_dir)
    if not final_zip_ok:
        raise RuntimeError("Phase-3C final ZIP integrity check failed")

    return {
        "decision": decision_payload["decision"],
        "method_summary": method_summary,
        "ablation_summary": ablation,
        "paired_analysis": paired,
        "gate_metrics": metrics,
        "gate_checks": checks,
        "zip_path": str(archive),
        "zip_sha256": _sha256_file(archive),
    }


def run_development(
    output_dir: Path | str,
    *,
    authorization_token: str,
    live: bool = True,
) -> dict:
    """Run or resume the exact 1200-condition Phase-3C fresh-development block."""
    require_development_authorization(authorization_token)
    validate_development_seed_block(DEVELOPMENT_SEEDS)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    protocol_path = _verify_and_copy_protocol(output_dir)
    _emit(live, "[PHASE3C] fresh-development authorization accepted")
    _emit(live, f"[PROTOCOL] {protocol_path.name} sha256={FROZEN_PROTOCOL_SHA256}")
    _emit(live, f"[SOURCE] frozen scientific source={FROZEN_SCIENTIFIC_SOURCE}")
    _emit(live, "[FIREWALL] engineering=29300 BLOCKED; development=29301-29310; final=11001-11999 BLOCKED")
    _emit(live, f"[PERSISTENCE] {output_dir}")

    conditions = scientific_conditions()
    rows, completed = _run_condition_groups(
        output_dir,
        conditions,
        evaluator=_evaluate_condition,
        live=live,
    )
    rows, completed = validate_checkpoint_groups(rows)
    if len(completed) != 1200 or len(rows) != 4800:
        raise RuntimeError("Phase-3C execution ended without 1200 complete four-method groups")

    _emit(live, "[ANALYSIS] complete block reached; comparative analysis is now permitted")
    artifacts = save_development_artifacts(rows, output_dir)
    _emit(live, f"[DECISION] {artifacts['decision']}")
    _emit(live, f"[ZIP] {artifacts['zip_path']}")
    _emit(live, f"[ZIP SHA256] {artifacts['zip_sha256']}")
    return {
        "decision": artifacts["decision"],
        "conditions_complete": len(completed),
        "primary_rows": len(rows),
        "output_dir": str(output_dir),
        "zip_path": artifacts["zip_path"],
        "zip_sha256": artifacts["zip_sha256"],
        "method_summary": artifacts["method_summary"],
        "ablation_summary": artifacts["ablation_summary"],
        "paired_analysis": artifacts["paired_analysis"],
        "gate_metrics": artifacts["gate_metrics"],
        "gate_checks": artifacts["gate_checks"],
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run frozen FedFalsify Phase-3C fresh development")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--authorization-token", required=True)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    result = run_development(
        args.output_dir,
        authorization_token=args.authorization_token,
        live=not args.quiet,
    )
    print(
        json.dumps(
            {
                key: _jsonable(value)
                for key, value in result.items()
                if key not in {"method_summary", "ablation_summary"}
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
