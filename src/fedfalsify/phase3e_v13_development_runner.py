"""Governed Phase-3E fresh-noisy evaluation for frozen FedFalsify v13.

This module is additive orchestration only. It does not modify the frozen v11,
v12, v13, scope-contrast, or V10 benchmark science.
"""

from __future__ import annotations

import argparse
import hashlib
from itertools import product
import json
import os
from pathlib import Path
import shutil
from typing import Mapping, Sequence
import zipfile

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from .phase3_engineering_runner import (
    _atomic_write_json,
    _atomic_write_text,
    _branch_integrity,
    _jsonable,
    atomic_write_csv,
)
from .phase3d_fixtures import Phase3DFixture
from .scsv_v10_benchmarks import (
    INTERACTION_DEV_V10,
    LINEAR_DEV_V10,
    QUADRATIC_DEV_V10,
    SINGLE_FAMILIES_V10,
    TRUE_DEVIATIONS_V10,
    TRIG_DEV_V10,
    V10_DEVIATIONS,
    WEAK_SOURCE_DEV_V10,
    generate_v10_benchmark,
    v10_catalog,
)
from .scsv_v12 import SCSVV12Output, run_scsv_v12_branches
from .scsv_v13 import Phase3DModelResult, run_phase3d_model

DEVELOPMENT_SEEDS = tuple(range(29401, 29411))
PHASE3E_METHODS = (
    "scsv-elrc-v11-full",
    "scsv-ncsc",
    "scope-contrast-only",
    "v13-full",
)
AUTHORIZATION_TOKEN = "AUTHORIZE_PHASE3E_V13_FRESH_NOISY_DEVELOPMENT"
FROZEN_BASE_HEAD = "435a8c1af7436fac3d3b1a625e356cf6de180bb0"
FROZEN_PROTOCOL_SHA256 = "2eebcf892e3acd90c9a133f7945850f60cb8a89fd577f2c3ac6011f5f8fbeac7"
PROTOCOL_NAME = "FROZEN_PHASE3E_V13_DEVELOPMENT_PROTOCOL.md"
ANALYSIS_RNG_SEED = 930401
HELDOUT_SEED_OFFSET = 500_000

CHECKPOINT_NAME = "phase3e_v13_checkpoint.csv"
ROWS_NAME = "phase3e_v13_rows.csv"
METHOD_SUMMARY_NAME = "phase3e_v13_method_summary.csv"
SEED_GAIN_NAME = "phase3e_v13_seed_level_gain.csv"
PAIRED_NAME = "phase3e_v13_paired_analysis.json"
GATE_METRICS_NAME = "phase3e_v13_gate_metrics.json"
GATE_CHECKS_NAME = "phase3e_v13_gate_checks.json"
DECISION_NAME = "phase3e_v13_decision.json"
FAILURE_NAME = "phase3e_v13_failure_taxonomy.csv"
REPORT_NAME = "phase3e_v13_report.txt"
MANIFEST_NAME = "phase3e_v13_sha256.txt"
ZIP_NAME = "FedFalsify_PHASE3E_V13_FRESH_NOISY_RESULTS.zip"

ConditionKey = tuple[str, int, str, str, float, int]
NULL_FAMILIES = {"null_role_v10", "anchor_contamination_null_v10"}


def _emit(live: bool, message: str) -> None:
    if live:
        print(message, flush=True)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_development_seed_block(seeds: Sequence[int]) -> None:
    normalized = tuple(int(seed) for seed in seeds)
    if normalized != DEVELOPMENT_SEEDS:
        raise ValueError("Phase-3E development requires exactly seeds 29401--29410 in order")
    if 29300 in normalized or any(29301 <= seed <= 29310 for seed in normalized):
        raise ValueError("spent Phase-3C/engineering seeds are blocked")
    if any(11001 <= seed <= 11999 for seed in normalized):
        raise ValueError("final-confirmation seeds 11001--11999 are blocked")


def require_development_authorization(token: str) -> None:
    if os.environ.get("FEDFALSIFY_PHASE3E_TEST_GATE") != "PASS":
        raise RuntimeError("Phase-3E test gate must PASS before scientific execution")
    if str(token) != AUTHORIZATION_TOKEN:
        raise RuntimeError("exact Phase-3E fresh-noisy authorization token is required")


def scientific_conditions(seeds: Sequence[int] = DEVELOPMENT_SEEDS) -> tuple[ConditionKey, ...]:
    """Return the unchanged Phase-3C benchmark geometry on the new seed block."""
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
        raise RuntimeError(
            f"Phase-3E condition firewall expected 1200 unique conditions, got {len(result)}"
        )
    return result


def condition_key_string(condition: ConditionKey) -> str:
    family, clients, balance, role, noise, seed = condition
    return f"{family}|{int(clients)}|{balance}|{role}|{float(noise):.2f}|{int(seed)}"


def condition_key_from_row(row: Mapping[str, object]) -> ConditionKey:
    return (
        str(row["family"]),
        int(float(row["num_clients"])),
        str(row["balance_profile"]),
        str(row["role_profile"]),
        float(row["noise_ratio"]),
        int(float(row["seed"])),
    )


def validate_checkpoint_groups(
    rows: Sequence[dict], conditions: Sequence[ConditionKey] | None = None
) -> tuple[list[dict], set[ConditionKey]]:
    authorized_conditions = tuple(scientific_conditions() if conditions is None else conditions)
    authorized = set(authorized_conditions)
    grouped: dict[ConditionKey, list[dict]] = {}
    for raw in rows:
        try:
            key = condition_key_from_row(raw)
        except (KeyError, TypeError, ValueError):
            continue
        if key in authorized:
            grouped.setdefault(key, []).append(dict(raw))

    cleaned: list[dict] = []
    completed: set[ConditionKey] = set()
    required = set(PHASE3E_METHODS)
    for condition in authorized_conditions:
        group = grouped.get(condition, [])
        methods = [str(row.get("method", "")) for row in group]
        if (
            len(group) == len(PHASE3E_METHODS)
            and set(methods) == required
            and len(set(methods)) == len(PHASE3E_METHODS)
        ):
            by_method = {str(row["method"]): dict(row) for row in group}
            for method in PHASE3E_METHODS:
                item = by_method[method]
                item["condition_key"] = condition_key_string(condition)
                cleaned.append(item)
            completed.add(condition)
    return cleaned, completed


def _client_ids(indices: Sequence[int]) -> tuple[str, ...]:
    return tuple(f"client-{int(index) + 1}" for index in indices)


def true_role_map(condition: ConditionKey) -> dict[str, tuple[str, ...]]:
    """Benchmark truth for evaluation only; never used by v13-full decisions."""
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
    raise KeyError(f"unknown Phase-3E family: {family}")


def benchmark_to_v13_fixture(generated, condition: ConditionKey) -> Phase3DFixture:
    """Adapt one stochastic V10 benchmark to the already-frozen v13 API."""
    roles = true_role_map(condition)
    localized = tuple(TRUE_DEVIATIONS_V10[str(generated.family)])
    scopes = tuple((term, tuple(roles[term])) for term, _coefficient in localized)
    return Phase3DFixture(
        name=(
            f"{condition[0]}__K{condition[1]}__{condition[2]}__{condition[3]}"
            f"__noise{condition[4]:.2f}__seed{condition[5]}"
        ),
        clients=tuple(generated.clients),
        shared_coefficients=tuple(generated.spec.coefficients),
        localized_coefficients=localized,
        truth_scopes=scopes,
    )


def _metric_triplet(
    predicted: set[str], target: set[str]
) -> tuple[float, float, float, int, int, int]:
    tp = len(predicted & target)
    fp = len(predicted - target)
    fn = len(target - predicted)
    precision = tp / (tp + fp) if tp + fp else float(not target)
    recall = tp / (tp + fn) if tp + fn else 1.0
    return float(predicted == target), float(precision), float(recall), tp, fp, fn


def scope_exact_recovery(
    true_roles: Mapping[str, Sequence[str]],
    predicted_roles: Mapping[str, Sequence[str]],
) -> float:
    if set(true_roles) != set(predicted_roles):
        return 0.0
    return float(
        all(set(map(str, true_roles[t])) == set(map(str, predicted_roles[t])) for t in true_roles)
    )


def _predicted_role_map(output: object) -> dict[str, tuple[str, ...]]:
    if isinstance(output, Phase3DModelResult):
        return {str(term): tuple(map(str, ids)) for term, ids in output.localized_scopes}

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
        if len(identity) >= 5:
            result[term] = tuple(map(str, identity[4]))
    return result


def _structures(output: object) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    if isinstance(output, Phase3DModelResult):
        shared = tuple(output.shared_structure)
        localized = tuple(output.accepted_localized)
        return shared, localized, shared + localized
    if isinstance(output, SCSVV12Output):
        return (
            tuple(output.shared_structure),
            tuple(output.accepted_deviations),
            tuple(output.final_structure),
        )
    shared = tuple(getattr(output, "ordinary_anchor_structure", ("1",)))
    localized = tuple(getattr(output, "accepted_deviations", ()))
    final = tuple(getattr(output, "final_structure", shared + localized))
    return shared, localized, final


def _scoped_design(
    clients: Sequence[object],
    shared: Sequence[str],
    localized: Sequence[str],
    roles: Mapping[str, Sequence[str]],
) -> tuple[np.ndarray, np.ndarray] | None:
    catalog = v10_catalog()
    shared = tuple(shared)
    localized = tuple(localized)
    if any(term not in roles for term in localized):
        return None
    blocks: list[np.ndarray] = []
    responses: list[np.ndarray] = []
    for client in clients:
        x = np.asarray(client.x, dtype=float)
        cols = [np.asarray(catalog.get(term).evaluate(x), dtype=float) for term in shared]
        cid = str(client.client_id)
        for term in localized:
            values = np.asarray(catalog.get(term).evaluate(x), dtype=float)
            cols.append(values if cid in set(map(str, roles[term])) else np.zeros_like(values))
        blocks.append(np.column_stack(cols))
        responses.append(np.asarray(client.y, dtype=float))
    return np.vstack(blocks), np.concatenate(responses)


def _heldout_nmse(
    generated,
    condition: ConditionKey,
    shared: Sequence[str],
    localized: Sequence[str],
    roles: Mapping[str, Sequence[str]],
) -> float:
    train = _scoped_design(generated.clients, shared, localized, roles)
    if train is None:
        return float("nan")
    x_train, y_train = train
    coefficients, *_ = np.linalg.lstsq(x_train, y_train, rcond=None)

    family, num_clients, balance, role, noise, seed = condition
    heldout = generate_v10_benchmark(
        family,
        nominal_samples_per_client=100,
        noise_ratio=float(noise),
        seed=HELDOUT_SEED_OFFSET + int(seed),
        num_clients=int(num_clients),
        balance_profile=balance,
        role_profile=role,
    )
    test = _scoped_design(heldout.clients, shared, localized, roles)
    if test is None:
        return float("nan")
    x_test, y_test = test
    prediction = x_test @ coefficients
    mse = float(np.mean((y_test - prediction) ** 2))
    return float(mse / max(float(np.var(y_test)), 1e-12))


def _integrity(output: object, shared: Sequence[str], localized: Sequence[str]) -> int:
    if isinstance(output, Phase3DModelResult):
        violations = 0
        shared = tuple(shared)
        localized = tuple(localized)
        if not shared or shared[0] != "1" or len(set(shared)) != len(shared):
            violations += 1
        if len(shared) - 1 > 5 or len(localized) > 2 or len(shared) + len(localized) > 10:
            violations += 1
        if set(localized) != set(term for term, _ids in output.localized_scopes):
            violations += 1
        if output.execution_error is not None:
            violations += 1
        return violations
    return int(_branch_integrity(output))


def _evaluate_method(generated, condition: ConditionKey, output: object) -> dict:
    shared, localized, final = _structures(output)
    predicted = set(final) - {"1"}
    target = set(generated.target_terms)
    exact, term_p, term_r, term_tp, term_fp, term_fn = _metric_triplet(predicted, target)

    true_deviations = set(generated.true_deviations)
    predicted_deviations = set(localized)
    _, dev_p, dev_r, dev_tp, dev_fp, dev_fn = _metric_triplet(
        predicted_deviations, true_deviations
    )
    true_shared = target - true_deviations
    predicted_shared = set(shared) - {"1"}
    _, shared_p, shared_r, shared_tp, shared_fp, shared_fn = _metric_triplet(
        predicted_shared, true_shared
    )

    truth_roles = true_role_map(condition)
    predicted_roles = _predicted_role_map(output)
    scope_exact = scope_exact_recovery(truth_roles, predicted_roles)

    communication_accounted = not isinstance(output, Phase3DModelResult)
    communication = (
        int(getattr(output, "communication_bytes", 0)) if communication_accounted else None
    )
    if isinstance(output, Phase3DModelResult):
        diagnostics = list(output.diagnostics)
        execution_error = output.execution_error
    elif isinstance(output, SCSVV12Output):
        diagnostics = {
            "shared": _jsonable(output.ledger.shared_diagnostics),
            "discovery": _jsonable(output.ledger.discovery_localized_diagnostics),
            "selector": _jsonable(output.ledger.selector_diagnostics),
            "probe": _jsonable(output.ledger.probe_diagnostics),
        }
        execution_error = None
    else:
        diagnostics = _jsonable(getattr(output, "diagnostics", ()))
        execution_error = None

    return {
        "family": condition[0],
        "num_clients": int(condition[1]),
        "balance_profile": condition[2],
        "role_profile": condition[3],
        "noise_ratio": float(condition[4]),
        "seed": int(condition[5]),
        "condition_key": condition_key_string(condition),
        "method": str(getattr(output, "method")),
        "exact_recovery": exact,
        "term_precision": term_p,
        "term_recall": term_r,
        "term_tp": term_tp,
        "term_fp": term_fp,
        "term_fn": term_fn,
        "shared_precision": shared_p,
        "shared_recall": shared_r,
        "shared_tp": shared_tp,
        "shared_fp": shared_fp,
        "shared_fn": shared_fn,
        "deviation_precision": dev_p,
        "deviation_recall": dev_r,
        "deviation_tp": dev_tp,
        "deviation_fp": dev_fp,
        "deviation_fn": dev_fn,
        "scope_exact_recovery": scope_exact,
        "mechanism_exact_recovery": float(exact == 1.0 and scope_exact == 1.0),
        "client_heldout_nmse": _heldout_nmse(
            generated, condition, shared, localized, predicted_roles
        ),
        "runtime_seconds": float(getattr(output, "runtime_seconds", float("nan"))),
        "communication_bytes": communication,
        "communication_accounted": bool(communication_accounted),
        "shared_structure": ";".join(shared),
        "accepted_deviations": ";".join(localized),
        "final_structure": ";".join(final),
        "true_roles_json": json.dumps(_jsonable(truth_roles), sort_keys=True, separators=(",", ":")),
        "predicted_roles_json": json.dumps(
            _jsonable(predicted_roles), sort_keys=True, separators=(",", ":")
        ),
        "diagnostics_json": json.dumps(_jsonable(diagnostics), sort_keys=True, separators=(",", ":")),
        "stop_reason": str(getattr(output, "stop_reason", "")),
        "execution_error": execution_error,
        "integrity_violations": _integrity(output, shared, localized),
    }


def _evaluate_condition(condition: ConditionKey) -> list[dict]:
    if int(condition[-1]) not in set(DEVELOPMENT_SEEDS):
        raise ValueError("Phase-3E evaluator received an unauthorized benchmark seed")
    family, num_clients, balance, role, noise, seed = condition
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
    predecessor_outputs = run_scsv_v12_branches(
        generated.clients,
        v10_catalog(),
        seed=int(seed),
        target_mse=target_mse,
        min_repair_score=0.05,
    )
    v11 = predecessor_outputs[0]
    v12 = next(item for item in predecessor_outputs if item.method == "scsv-ncsc")

    fixture = benchmark_to_v13_fixture(generated, condition)
    scope_only = run_phase3d_model(fixture, "scope-contrast-only", outer_fold=int(seed))
    v13 = run_phase3d_model(fixture, "v13-full", outer_fold=int(seed))
    outputs = (v11, v12, scope_only, v13)
    if tuple(str(getattr(item, "method")) for item in outputs) != PHASE3E_METHODS:
        raise RuntimeError("Phase-3E method order drifted")
    return [_evaluate_method(generated, condition, output) for output in outputs]


def _validate_new_group(condition: ConditionKey, rows: Sequence[dict]) -> list[dict]:
    if len(rows) != len(PHASE3E_METHODS):
        raise RuntimeError("Phase-3E condition did not return exactly four rows")
    methods = tuple(str(row.get("method", "")) for row in rows)
    if methods != PHASE3E_METHODS or len(set(methods)) != len(PHASE3E_METHODS):
        raise RuntimeError("Phase-3E condition returned an invalid method group")
    normalized: list[dict] = []
    for row in rows:
        item = dict(row)
        if condition_key_from_row(item) != condition:
            raise RuntimeError("Phase-3E evaluator changed condition identity")
        item["condition_key"] = condition_key_string(condition)
        normalized.append(item)
    return normalized


def _paired_maps(rows: Sequence[Mapping[str, object]]):
    baseline: dict[str, Mapping[str, object]] = {}
    full: dict[str, Mapping[str, object]] = {}
    for row in rows:
        method = str(row.get("method", ""))
        if method not in {"scsv-elrc-v11-full", "v13-full"}:
            continue
        key = str(row["condition_key"])
        target = baseline if method == "scsv-elrc-v11-full" else full
        if key in target:
            raise ValueError(f"duplicate paired row: {method} {key}")
        target[key] = row
    if not baseline or set(baseline) != set(full):
        raise ValueError("paired analysis requires matched v11/v13 condition keys")
    return baseline, full


def paired_analysis(
    rows: Sequence[Mapping[str, object]], *, bootstrap_reps: int = 20_000
) -> dict:
    baseline, full = _paired_maps(rows)
    keys = sorted(baseline)
    diffs: list[float] = []
    repairs = harms = 0
    seed_values: dict[int, list[float]] = {}
    for key in keys:
        b = float(baseline[key]["exact_recovery"])
        f = float(full[key]["exact_recovery"])
        delta = f - b
        diffs.append(delta)
        repairs += int(b == 0.0 and f == 1.0)
        harms += int(b == 1.0 and f == 0.0)
        seed_values.setdefault(int(float(full[key]["seed"])), []).append(delta)

    exact_gain = float(np.mean(diffs))
    discordant = repairs + harms
    mcnemar = (
        float(binomtest(min(repairs, harms), n=discordant, p=0.5).pvalue)
        if discordant
        else 1.0
    )
    seed_level = {
        int(seed): float(np.mean(values)) for seed, values in sorted(seed_values.items())
    }
    seed_array = np.asarray(list(seed_level.values()), dtype=float)
    rng = np.random.default_rng(ANALYSIS_RNG_SEED)
    indices = rng.integers(0, len(seed_array), size=(int(bootstrap_reps), len(seed_array)))
    boot = seed_array[indices].mean(axis=1)
    ci_low, ci_high = np.quantile(boot, [0.025, 0.975])
    sign_stats = [
        float(np.mean(seed_array * np.asarray(signs, dtype=float)))
        for signs in product((-1.0, 1.0), repeat=len(seed_array))
    ]
    sign_p = float(np.mean(np.asarray(sign_stats) >= exact_gain - 1e-15))
    return {
        "matched_conditions": len(keys),
        "repairs": repairs,
        "harms": harms,
        "exact_gain": exact_gain,
        "exact_harm_rate": harms / len(keys),
        "mcnemar_exact_p": mcnemar,
        "bootstrap_reps": int(bootstrap_reps),
        "bootstrap_analysis_seed": ANALYSIS_RNG_SEED,
        "bootstrap_ci_low": float(ci_low),
        "bootstrap_ci_high": float(ci_high),
        "seed_sign_flip_p_one_sided": sign_p,
        "seed_level_gain": seed_level,
    }


def _pooled_precision(frame: pd.DataFrame, prefix: str) -> float:
    tp = float(pd.to_numeric(frame[f"{prefix}_tp"], errors="coerce").sum())
    fp = float(pd.to_numeric(frame[f"{prefix}_fp"], errors="coerce").sum())
    return tp / (tp + fp) if tp + fp else 1.0


def _pooled_recall(frame: pd.DataFrame, prefix: str) -> float:
    tp = float(pd.to_numeric(frame[f"{prefix}_tp"], errors="coerce").sum())
    fn = float(pd.to_numeric(frame[f"{prefix}_fn"], errors="coerce").sum())
    return tp / (tp + fn) if tp + fn else 1.0


def _subset_gain(full: pd.DataFrame, baseline: pd.DataFrame, mask: pd.Series) -> float:
    f = full.loc[mask].set_index("condition_key")["exact_recovery"].astype(float)
    b = baseline[baseline["condition_key"].isin(f.index)].set_index("condition_key")[
        "exact_recovery"
    ].astype(float)
    common = sorted(set(f.index) & set(b.index))
    return float(np.mean([f[k] - b[k] for k in common])) if common else float("nan")


def development_gate_metrics(rows: Sequence[dict]) -> dict:
    frame = pd.DataFrame(list(rows))
    full = frame[frame["method"] == "v13-full"].copy()
    v11 = frame[frame["method"] == "scsv-elrc-v11-full"].copy()
    paired = paired_analysis(rows)
    full["all_true_deviations_recovered"] = pd.to_numeric(
        full["deviation_fn"], errors="coerce"
    ).eq(0)
    main = full["family"].isin(set(SINGLE_FAMILIES_V10))
    nonnull = ~full["family"].isin(NULL_FAMILIES)
    null = full["family"].isin(NULL_FAMILIES)
    family_recovery = {
        family: float(
            full.loc[full["family"].eq(family), "all_true_deviations_recovered"].mean()
        )
        for family in SINGLE_FAMILIES_V10
    }
    client_recovery = {
        str(k): float(
            full.loc[
                nonnull & full["num_clients"].astype(int).eq(k),
                "all_true_deviations_recovered",
            ].mean()
        )
        for k in (4, 8, 16)
    }
    high_main = main & pd.to_numeric(full["noise_ratio"], errors="coerce").eq(0.30)
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
        "null_localized_fp_rate": float(
            pd.to_numeric(full.loc[null, "deviation_fp"], errors="coerce").gt(0).mean()
        ),
        "null_shared_fp_rate": float(
            pd.to_numeric(full.loc[null, "shared_fp"], errors="coerce").gt(0).mean()
        ),
        "exact_harm_rate": float(paired["exact_harm_rate"]),
        "scope_exact_nonnull": float(
            pd.to_numeric(full.loc[nonnull, "scope_exact_recovery"], errors="coerce").mean()
        ),
        "family_recovery": family_recovery,
        "client_recovery": client_recovery,
        "high_noise_main_deviation_recovery": float(
            full.loc[high_main, "all_true_deviations_recovered"].mean()
        ),
        "high_noise_main_exact_gain": _subset_gain(full, v11, high_main),
        "weak_source_recovery": float(
            full.loc[
                full["family"].eq("weak_source_role_v10"),
                "all_true_deviations_recovered",
            ].mean()
        ),
        "dual_role_recovery": float(
            full.loc[
                full["family"].eq("dual_role_v10"), "all_true_deviations_recovered"
            ].mean()
        ),
        "integrity_violations": int(
            sum(int(float(row.get("integrity_violations", 0))) for row in cleaned)
        ),
        "complete_conditions": int(len(completed)),
        "primary_rows": int(len(rows)),
    }


def gate_checks(metrics: Mapping[str, object]) -> dict[str, bool]:
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
        "scope_exact_nonnull": float(metrics["scope_exact_nonnull"]) >= 0.94,
        "family_quadratic": float(family["quadratic_role_v10"]) >= 0.92,
        "family_linear": float(family["linear_role_v10"]) >= 0.92,
        "family_trig": float(family["trig_role_v10"]) >= 0.92,
        "family_interaction": float(family["interaction_role_v10"]) >= 0.92,
        "clients_k4": float(clients["4"]) >= 0.90,
        "clients_k8": float(clients["8"]) >= 0.93,
        "clients_k16": float(clients["16"]) >= 0.95,
        "high_noise_main_deviation": float(
            metrics["high_noise_main_deviation_recovery"]
        ) >= 0.90,
        "high_noise_main_exact_gain": float(metrics["high_noise_main_exact_gain"]) >= 0.05,
        "weak_source": float(metrics["weak_source_recovery"]) >= 0.90,
        "dual_role": float(metrics["dual_role_recovery"]) >= 0.90,
        "integrity_zero": int(metrics["integrity_violations"]) == 0,
        "complete_conditions": int(metrics["complete_conditions"]) == 1200,
        "primary_rows": int(metrics["primary_rows"]) == 4800,
    }
    return {name: bool(value) for name, value in checks.items()}


def _repo_protocol_path() -> Path:
    return Path(__file__).resolve().parents[2] / "research" / PROTOCOL_NAME


def _verify_and_copy_protocol(output_dir: Path) -> None:
    source = _repo_protocol_path()
    if not source.exists():
        raise FileNotFoundError(f"frozen Phase-3E protocol missing: {source}")
    actual = _sha256_file(source)
    if actual != FROZEN_PROTOCOL_SHA256:
        raise RuntimeError(
            f"Phase-3E protocol hash mismatch: expected {FROZEN_PROTOCOL_SHA256}, got {actual}"
        )
    destination = output_dir / PROTOCOL_NAME
    if destination.exists() and _sha256_file(destination) != FROZEN_PROTOCOL_SHA256:
        raise RuntimeError("existing Drive protocol conflicts with frozen Phase-3E protocol")
    if not destination.exists():
        tmp = destination.with_name(destination.name + ".tmp")
        shutil.copyfile(source, tmp)
        os.replace(tmp, destination)


def _load_checkpoint(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    return pd.read_csv(path).to_dict(orient="records")


def _save_checkpoint(rows: Sequence[dict], output_dir: Path) -> None:
    atomic_write_csv(pd.DataFrame(list(rows)), output_dir / CHECKPOINT_NAME)


def _method_summary(rows: Sequence[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(list(rows))
    metrics = [
        "exact_recovery",
        "term_precision",
        "term_recall",
        "shared_precision",
        "shared_recall",
        "deviation_precision",
        "deviation_recall",
        "scope_exact_recovery",
        "mechanism_exact_recovery",
        "client_heldout_nmse",
        "runtime_seconds",
    ]
    for name in metrics:
        frame[name] = pd.to_numeric(frame[name], errors="coerce")
    return frame.groupby("method", as_index=False)[metrics].mean()


def _failure_taxonomy(rows: Sequence[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(list(rows))
    full = frame[frame["method"].eq("v13-full")].copy()
    for key in (
        "shared_fp",
        "shared_fn",
        "deviation_fp",
        "deviation_fn",
        "scope_exact_recovery",
        "exact_recovery",
    ):
        full[key] = pd.to_numeric(full[key], errors="coerce")
    full["failure_type"] = np.select(
        [
            full["deviation_fp"].gt(0),
            full["deviation_fn"].gt(0),
            full["shared_fp"].gt(0),
            full["shared_fn"].gt(0),
            full["scope_exact_recovery"].lt(1),
            full["exact_recovery"].lt(1),
        ],
        [
            "localized_false_positive",
            "localized_false_negative",
            "shared_false_positive",
            "shared_false_negative",
            "scope_mismatch",
            "other_structure_error",
        ],
        default="exact",
    )
    return (
        full.groupby(["family", "failure_type"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )


def _write_final_outputs(rows: Sequence[dict], output_dir: Path) -> dict:
    frame = pd.DataFrame(list(rows))
    atomic_write_csv(frame, output_dir / ROWS_NAME)
    atomic_write_csv(_method_summary(rows), output_dir / METHOD_SUMMARY_NAME)
    atomic_write_csv(_failure_taxonomy(rows), output_dir / FAILURE_NAME)

    paired = paired_analysis(rows)
    _atomic_write_json(paired, output_dir / PAIRED_NAME)
    seed_df = pd.DataFrame(
        [{"seed": int(k), "exact_gain": float(v)} for k, v in paired["seed_level_gain"].items()]
    )
    atomic_write_csv(seed_df, output_dir / SEED_GAIN_NAME)

    metrics = development_gate_metrics(rows)
    checks = gate_checks(metrics)
    decision = {
        "decision": "PHASE3E-DEVELOPMENT-GO" if all(checks.values()) else "PHASE3E-DEVELOPMENT-NO-GO",
        "all_checks_passed": bool(all(checks.values())),
        "communication_claim_allowed": False,
        "interpretation": (
            "Development-only result. GO permits freezing v13 for external/final validation; "
            "NO-GO is retained and seeds 29401-29410 remain spent."
        ),
    }
    _atomic_write_json(metrics, output_dir / GATE_METRICS_NAME)
    _atomic_write_json(checks, output_dir / GATE_CHECKS_NAME)
    _atomic_write_json(decision, output_dir / DECISION_NAME)

    report = [
        "FedFalsify Phase-3E / v13 fresh-noisy development",
        f"Decision: {decision['decision']}",
        f"Complete conditions: {metrics['complete_conditions']}/1200",
        f"Primary rows: {metrics['primary_rows']}/4800",
        f"v13 exact-recovery gain vs v11: {metrics['overall_exact_gain']:.6f}",
        f"Bootstrap 95% CI: [{metrics['bootstrap_ci_low']:.6f}, {metrics['bootstrap_ci_high']:.6f}]",
        f"v13 localized precision/recall: {metrics['deviation_precision_pooled']:.6f} / {metrics['deviation_recall_pooled']:.6f}",
        f"v13 shared precision/recall: {metrics['shared_precision_pooled']:.6f} / {metrics['shared_recall_pooled']:.6f}",
        f"v13 non-null exact scope: {metrics['scope_exact_nonnull']:.6f}",
        f"Null localized FP rate: {metrics['null_localized_fp_rate']:.6f}",
        "Communication comparison: NOT CLAIMED (v13 accounting not comparable in Phase-3E).",
    ]
    _atomic_write_text("\n".join(report) + "\n", output_dir / REPORT_NAME)

    artifact_names = [
        PROTOCOL_NAME,
        CHECKPOINT_NAME,
        ROWS_NAME,
        METHOD_SUMMARY_NAME,
        FAILURE_NAME,
        SEED_GAIN_NAME,
        PAIRED_NAME,
        GATE_METRICS_NAME,
        GATE_CHECKS_NAME,
        DECISION_NAME,
        REPORT_NAME,
    ]
    manifest_lines = [
        f"{_sha256_file(output_dir / name)}  {name}"
        for name in artifact_names
        if (output_dir / name).exists()
    ]
    _atomic_write_text("\n".join(manifest_lines) + "\n", output_dir / MANIFEST_NAME)
    with zipfile.ZipFile(output_dir / ZIP_NAME, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in artifact_names + [MANIFEST_NAME]:
            path = output_dir / name
            if path.exists():
                archive.write(path, arcname=name)
    return decision


def run_phase3e_development(
    output_dir: Path | str,
    *,
    authorization_token: str,
    live: bool = True,
) -> dict:
    validate_development_seed_block(DEVELOPMENT_SEEDS)
    require_development_authorization(authorization_token)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _verify_and_copy_protocol(output_dir)

    conditions = scientific_conditions()
    existing = _load_checkpoint(output_dir / CHECKPOINT_NAME)
    rows, completed = validate_checkpoint_groups(existing, conditions)
    _save_checkpoint(rows, output_dir)
    _emit(live, f"[RESUME] {len(completed)}/1200 complete conditions")

    for index, condition in enumerate(conditions, start=1):
        if condition in completed:
            continue
        _emit(live, f"[RUN] {index}/1200 {condition_key_string(condition)}")
        group = _validate_new_group(condition, _evaluate_condition(condition))
        rows.extend(group)
        completed.add(condition)
        _save_checkpoint(rows, output_dir)
        _emit(live, f"[CHECKPOINT] {len(completed)}/1200 complete")

    cleaned, completed = validate_checkpoint_groups(rows, conditions)
    if len(completed) != 1200 or len(cleaned) != 4800:
        raise RuntimeError(
            f"Phase-3E completeness failure: conditions={len(completed)}, rows={len(cleaned)}"
        )
    decision = _write_final_outputs(cleaned, output_dir)
    _emit(live, f"[DECISION] {decision['decision']}")
    return decision


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--authorization-token", required=True)
    args = parser.parse_args(argv)
    run_phase3e_development(
        args.output_dir,
        authorization_token=args.authorization_token,
        live=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
