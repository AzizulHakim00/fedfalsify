"""Frozen development study harness for FedFalsify SCSV-SPCC v8."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from statistics import mean, median
from typing import Iterable, Sequence

import numpy as np

from .baselines import centralized_forward
from .basis import CandidateEquation
from .scsv_v7 import SCSVRCDV7Output, scsv_rcd_v7_method
from .scsv_v8 import SCSVSPCCV8Output, scsv_spcc_v8_method
from .scsv_v8_benchmarks import (
    SINGLE_FAMILIES_V8,
    V8_DEVIATIONS,
    V8GeneratedBenchmark,
    generate_v8_benchmark,
    generate_v8_global_test_data,
    v8_catalog,
)

SMOKE_SEED = 25001
DEVELOPMENT_SEEDS = (25101, 25102, 25103, 25104, 25105)
METHODS = (
    "scsv-spcc-v8-full",
    "scsv-spcc-v8-strict-probe",
    "scsv-rcd-v7-style",
    "scsv-v6-anchor",
    "centralized-forward",
)


@dataclass(frozen=True)
class V8StudyRow:
    family: str
    noise_ratio: float
    samples_per_client: int
    num_clients: int
    balance_profile: str
    role_profile: str
    seed: int
    method: str
    exact_recovery: float
    term_precision: float
    term_recall: float
    test_nmse: float
    train_mse: float
    deviation_tp: int
    deviation_fp: int
    deviation_fn: int
    deviation_precision: float
    deviation_recall: float
    all_true_deviations_recovered: float
    spurious_deviation_accepted: float
    runtime_seconds: float
    communication_bytes: int
    discovered_terms: str
    accepted_deviations: str
    anchor_structure: str
    final_structure: str
    bank_terms: str
    source_linked_candidates: str
    role_hypothesis_positive: float
    min_accepted_role_gap: float | None
    min_accepted_role_mean: float | None
    max_accepted_outside_mean: float | None
    certificate_violation_count: int
    source_ambiguity: float
    global_ambiguity: float
    diagnostics_json: str
    expression: str
    stop_reason: str


def _validate_seeds(seeds: Sequence[int], *, smoke: bool) -> None:
    allowed = {SMOKE_SEED} if smoke else set(DEVELOPMENT_SEEDS)
    if set(seeds) != allowed:
        if smoke:
            raise ValueError("v8 engineering smoke must use seed 25001 only")
        raise ValueError("v8 development evidence must use exactly seeds 25101--25105")


def _candidate_terms(candidate: CandidateEquation) -> set[str]:
    return {
        term
        for term, coefficient in zip(candidate.active_terms, candidate.coefficients)
        if term != "1" and abs(float(coefficient)) >= 1e-3
    }


def _term_metrics(predicted: Iterable[str], target: Iterable[str]) -> tuple[float, float, float]:
    predicted_set = set(predicted)
    target_set = set(target)
    intersection = predicted_set & target_set
    precision = len(intersection) / len(predicted_set) if predicted_set else float(not target_set)
    recall = len(intersection) / len(target_set) if target_set else 1.0
    return float(predicted_set == target_set), float(precision), float(recall)


def _prediction_nmse(prediction: np.ndarray, target: np.ndarray) -> float:
    mse = float(np.mean((np.asarray(target) - np.asarray(prediction)) ** 2))
    return float(mse / max(float(np.var(target)), 1e-12))


def _v8_certificate_violations(output: SCSVSPCCV8Output | None) -> int:
    if output is None:
        return 0
    accepted = set(output.accepted_deviations)
    violations = 0
    for item in output.diagnostics:
        if item.term not in accepted:
            continue
        if not (
            item.role_admissible
            and item.role_client_ids
            and item.outside_client_ids
            and item.occupancy_gap >= 0.50
            and item.role_mean_occupancy >= 0.75
            and item.outside_mean_occupancy <= 0.25
            and item.selector_supported
            and item.selector_outside_safe
            and item.probe_state != "CONTRADICTED"
            and item.probe_outside_safe
            and item.pair_invariant
        ):
            violations += 1
    return int(violations)


def _v8_diagnostics(output: SCSVSPCCV8Output | None):
    if output is None:
        return (), (), (), False
    accepted = set(output.accepted_deviations)
    accepted_items = tuple(item for item in output.diagnostics if item.term in accepted)
    gaps = tuple(item.occupancy_gap for item in accepted_items)
    role_means = tuple(item.role_mean_occupancy for item in accepted_items)
    outside_means = tuple(item.outside_mean_occupancy for item in accepted_items)
    any_role = any(item.role_admissible for item in output.diagnostics)
    return gaps, role_means, outside_means, any_role


def _evaluate_candidate(
    generated: V8GeneratedBenchmark,
    candidate: CandidateEquation,
    *,
    method: str,
    seed: int,
    runtime_seconds: float,
    communication_bytes: int,
    stop_reason: str,
    v8_output: SCSVSPCCV8Output | None = None,
    v7_output: SCSVRCDV7Output | None = None,
) -> V8StudyRow:
    catalog = v8_catalog()
    predicted = _candidate_terms(candidate)
    target = set(generated.target_terms)
    exact, precision, recall = _term_metrics(predicted, target)
    x_test, y_test = generate_v8_global_test_data(generated, seed=seed + 100_000)
    test_prediction = candidate.predict(x_test, catalog)
    pooled_x = np.concatenate([item.x for item in generated.clients], axis=0)
    pooled_y = np.concatenate([item.y for item in generated.clients], axis=0)
    train_prediction = candidate.predict(pooled_x, catalog)
    train_mse = float(np.mean((pooled_y - train_prediction) ** 2))

    predicted_deviations = predicted & set(V8_DEVIATIONS)
    true_deviations = set(generated.true_deviations)
    tp = len(predicted_deviations & true_deviations)
    fp = len(predicted_deviations - true_deviations)
    fn = len(true_deviations - predicted_deviations)
    dev_precision = tp / (tp + fp) if tp + fp else float(not true_deviations)
    dev_recall = tp / (tp + fn) if tp + fn else 1.0

    if v8_output is not None:
        accepted = v8_output.accepted_deviations
        anchor_structure = v8_output.anchor_structure
        final_structure = v8_output.final_structure
        bank_terms = v8_output.bank_terms
        source_linked = v8_output.source_linked_candidates
        gaps, role_means, outside_means, any_role = _v8_diagnostics(v8_output)
        source_ambiguity = float(v8_output.source_ambiguity)
        global_ambiguity = float(v8_output.global_ambiguity)
        diagnostics_json = json.dumps(
            [asdict(item) for item in v8_output.diagnostics],
            sort_keys=True,
            separators=(",", ":"),
        )
        violations = _v8_certificate_violations(v8_output)
    elif v7_output is not None:
        accepted = v7_output.accepted_deviations
        anchor_structure = v7_output.anchor_structure
        final_structure = v7_output.final_structure
        bank_terms = v7_output.bank_terms
        source_linked = v7_output.source_linked_candidates
        gaps = role_means = outside_means = ()
        any_role = False
        source_ambiguity = 0.0
        global_ambiguity = float(v7_output.ambiguity_guard)
        diagnostics_json = json.dumps(
            [asdict(item) for item in v7_output.diagnostics],
            sort_keys=True,
            separators=(",", ":"),
        )
        violations = 0
    else:
        accepted = ()
        anchor_structure = ()
        final_structure = candidate.active_terms
        bank_terms = ()
        source_linked = ()
        gaps = role_means = outside_means = ()
        any_role = False
        source_ambiguity = 0.0
        global_ambiguity = 0.0
        diagnostics_json = "[]"
        violations = 0

    return V8StudyRow(
        family=generated.family,
        noise_ratio=float(generated.noise_std / max(float(np.std(y_test)), 1e-12)),
        samples_per_client=generated.nominal_samples_per_client,
        num_clients=generated.num_clients,
        balance_profile=generated.balance_profile,
        role_profile=generated.role_profile,
        seed=int(seed),
        method=method,
        exact_recovery=exact,
        term_precision=precision,
        term_recall=recall,
        test_nmse=_prediction_nmse(test_prediction, y_test),
        train_mse=train_mse,
        deviation_tp=int(tp),
        deviation_fp=int(fp),
        deviation_fn=int(fn),
        deviation_precision=float(dev_precision),
        deviation_recall=float(dev_recall),
        all_true_deviations_recovered=float(true_deviations.issubset(predicted_deviations)),
        spurious_deviation_accepted=float(bool(predicted_deviations - true_deviations)),
        runtime_seconds=float(runtime_seconds),
        communication_bytes=int(communication_bytes),
        discovered_terms=";".join(sorted(predicted)),
        accepted_deviations=";".join(accepted),
        anchor_structure=";".join(anchor_structure),
        final_structure=";".join(final_structure),
        bank_terms=";".join(bank_terms),
        source_linked_candidates=";".join(source_linked),
        role_hypothesis_positive=float(any_role),
        min_accepted_role_gap=min(gaps) if gaps else None,
        min_accepted_role_mean=min(role_means) if role_means else None,
        max_accepted_outside_mean=max(outside_means) if outside_means else None,
        certificate_violation_count=int(violations),
        source_ambiguity=source_ambiguity,
        global_ambiguity=global_ambiguity,
        diagnostics_json=diagnostics_json,
        expression=candidate.expression(catalog),
        stop_reason=stop_reason,
    )


def _evaluate_condition(
    generated: V8GeneratedBenchmark,
    *,
    requested_noise: float,
    seed: int,
    methods: Sequence[str],
) -> list[V8StudyRow]:
    unknown = set(methods) - set(METHODS)
    if unknown:
        raise ValueError(f"unknown v8 methods: {sorted(unknown)}")
    rows: list[V8StudyRow] = []
    catalog = v8_catalog()
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)

    full_output: SCSVSPCCV8Output | None = None
    if "scsv-spcc-v8-full" in methods or "scsv-v6-anchor" in methods:
        full_output = scsv_spcc_v8_method(
            generated.clients,
            catalog,
            seed=seed,
            target_mse=target_mse,
            min_repair_score=0.05,
            strict_probe=False,
        )
        if "scsv-spcc-v8-full" in methods:
            rows.append(
                _evaluate_candidate(
                    generated,
                    full_output.candidate,
                    method="scsv-spcc-v8-full",
                    seed=seed,
                    runtime_seconds=full_output.runtime_seconds,
                    communication_bytes=full_output.communication_bytes,
                    stop_reason=full_output.stop_reason,
                    v8_output=full_output,
                )
            )
        if "scsv-v6-anchor" in methods:
            rows.append(
                _evaluate_candidate(
                    generated,
                    full_output.anchor.candidate,
                    method="scsv-v6-anchor",
                    seed=seed,
                    runtime_seconds=full_output.anchor.runtime_seconds,
                    communication_bytes=full_output.anchor.communication_bytes,
                    stop_reason=full_output.anchor.stop_reason,
                )
            )

    if "scsv-spcc-v8-strict-probe" in methods:
        strict_output = scsv_spcc_v8_method(
            generated.clients,
            catalog,
            seed=seed,
            target_mse=target_mse,
            min_repair_score=0.05,
            strict_probe=True,
        )
        rows.append(
            _evaluate_candidate(
                generated,
                strict_output.candidate,
                method="scsv-spcc-v8-strict-probe",
                seed=seed,
                runtime_seconds=strict_output.runtime_seconds,
                communication_bytes=strict_output.communication_bytes,
                stop_reason=strict_output.stop_reason,
                v8_output=strict_output,
            )
        )

    if "scsv-rcd-v7-style" in methods:
        v7_output = scsv_rcd_v7_method(
            generated.clients,
            catalog,
            seed=seed,
            target_mse=target_mse,
            min_repair_score=0.05,
            require_probe=True,
        )
        rows.append(
            _evaluate_candidate(
                generated,
                v7_output.candidate,
                method="scsv-rcd-v7-style",
                seed=seed,
                runtime_seconds=v7_output.runtime_seconds,
                communication_bytes=v7_output.communication_bytes,
                stop_reason=v7_output.stop_reason,
                v7_output=v7_output,
            )
        )

    if "centralized-forward" in methods:
        centralized = centralized_forward(generated.clients, catalog, max_terms=8)
        rows.append(
            _evaluate_candidate(
                generated,
                centralized.candidate,
                method="centralized-forward",
                seed=seed,
                runtime_seconds=centralized.runtime_seconds,
                communication_bytes=0,
                stop_reason=centralized.stop_reason,
            )
        )

    return [V8StudyRow(**{**asdict(row), "noise_ratio": float(requested_noise)}) for row in rows]


def _scientific_conditions(seeds: Sequence[int]):
    for family in SINGLE_FAMILIES_V8:
        for num_clients in (4, 8, 16):
            role_profiles = ("single",) if num_clients == 4 else ("single", "quarter")
            for balance in ("balanced", "imbalanced"):
                for role_profile in role_profiles:
                    for noise in (0.10, 0.30):
                        for seed in seeds:
                            yield family, num_clients, balance, role_profile, noise, seed
    for num_clients in (4, 8, 16):
        for balance in ("balanced", "imbalanced"):
            for noise in (0.10, 0.30):
                for seed in seeds:
                    yield "null_role_v8", num_clients, balance, "none", noise, seed
    for num_clients in (4, 8):
        for balance in ("balanced", "imbalanced"):
            for noise in (0.10, 0.30):
                for seed in seeds:
                    yield "diffuse_null_v8", num_clients, balance, "none", noise, seed
    for num_clients in (8, 16):
        for balance in ("balanced", "imbalanced"):
            for noise in (0.10, 0.30):
                for seed in seeds:
                    yield "dual_role_v8", num_clients, balance, "quarter", noise, seed


def _smoke_conditions():
    return (
        ("quadratic_role_v8", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("linear_role_v8", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("trig_role_v8", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("interaction_role_v8", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("null_role_v8", 8, "balanced", "none", 0.10, SMOKE_SEED),
        ("diffuse_null_v8", 8, "balanced", "none", 0.10, SMOKE_SEED),
        ("dual_role_v8", 8, "balanced", "quarter", 0.10, SMOKE_SEED),
    )


def run_study(
    *,
    seeds: Sequence[int] = DEVELOPMENT_SEEDS,
    methods: Sequence[str] = METHODS,
    smoke: bool = False,
) -> list[V8StudyRow]:
    _validate_seeds(seeds, smoke=smoke)
    rows: list[V8StudyRow] = []
    conditions = _smoke_conditions() if smoke else _scientific_conditions(seeds)
    for family, num_clients, balance, role_profile, noise, seed in conditions:
        generated = generate_v8_benchmark(
            family,
            nominal_samples_per_client=100,
            noise_ratio=noise,
            seed=seed,
            num_clients=num_clients,
            balance_profile=balance,
            role_profile=role_profile,
        )
        rows.extend(
            _evaluate_condition(
                generated,
                requested_noise=noise,
                seed=seed,
                methods=methods,
            )
        )
    return rows


def _mean(rows: Sequence[V8StudyRow], field: str) -> float:
    return float(mean(float(getattr(row, field)) for row in rows))


def _median(rows: Sequence[V8StudyRow], field: str) -> float:
    return float(median(float(getattr(row, field)) for row in rows))


def _key(row: V8StudyRow) -> tuple[object, ...]:
    return (
        row.family,
        row.noise_ratio,
        row.samples_per_client,
        row.num_clients,
        row.balance_profile,
        row.role_profile,
        row.seed,
    )


def _pooled_deviation(rows: Sequence[V8StudyRow]) -> tuple[float, float]:
    tp = sum(row.deviation_tp for row in rows)
    fp = sum(row.deviation_fp for row in rows)
    fn = sum(row.deviation_fn for row in rows)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return float(precision), float(recall)


def summarize(rows: Sequence[V8StudyRow], *, evaluate_gate: bool = True) -> dict[str, object]:
    by_method: dict[str, list[V8StudyRow]] = {}
    for row in rows:
        by_method.setdefault(row.method, []).append(row)

    result: dict[str, object] = {
        "schema_version": 1,
        "status": "scsv-spcc-v8-development" if evaluate_gate else "scsv-spcc-v8-engineering-smoke",
        "rows": len(rows),
        "conditions": len({_key(row) for row in rows}),
        "seeds": sorted({row.seed for row in rows}),
        "methods": {},
    }
    for method, selected in sorted(by_method.items()):
        precision, recall = _pooled_deviation(selected)
        result["methods"][method] = {
            "runs": len(selected),
            "exact_recovery": _mean(selected, "exact_recovery"),
            "term_precision": _mean(selected, "term_precision"),
            "term_recall": _mean(selected, "term_recall"),
            "test_nmse": _mean(selected, "test_nmse"),
            "deviation_precision_pooled": precision,
            "deviation_recall_pooled": recall,
            "spurious_deviation_acceptance": _mean(selected, "spurious_deviation_accepted"),
            "runtime_seconds_median": _median(selected, "runtime_seconds"),
            "communication_bytes_median": _median(selected, "communication_bytes"),
        }

    if not evaluate_gate:
        result["development_gate"] = {
            "evaluated": False,
            "passed": None,
            "scientific_boundary": "Engineering smoke cannot evaluate v8 scientific gates.",
        }
        return result

    missing = set(METHODS) - set(by_method)
    if missing:
        raise ValueError(f"missing v8 methods: {sorted(missing)}")
    full = by_method["scsv-spcc-v8-full"]
    strict = by_method["scsv-spcc-v8-strict-probe"]
    v7style = by_method["scsv-rcd-v7-style"]
    v6 = by_method["scsv-v6-anchor"]
    if any(len(group) != 540 for group in (full, strict, v7style, v6)):
        raise ValueError("expected 540 matched rows for every federated method")

    maps = {name: {_key(row): row for row in group} for name, group in (
        ("full", full), ("strict", strict), ("v7", v7style), ("v6", v6)
    )}
    keys = set(maps["full"])
    if len(keys) != 540 or any(set(mapping) != keys for mapping in maps.values()):
        raise ValueError("v8 matched condition keys are incomplete")

    deviation_rows = [row for row in full if row.family not in {"null_role_v8", "diffuse_null_v8"}]
    v6_deviation_rows = [row for row in v6 if row.family not in {"null_role_v8", "diffuse_null_v8"}]
    v7_deviation_rows = [row for row in v7style if row.family not in {"null_role_v8", "diffuse_null_v8"}]
    singles = [row for row in full if row.family in SINGLE_FAMILIES_V8]
    nulls = [row for row in full if row.family in {"null_role_v8", "diffuse_null_v8"}]
    dual = [row for row in full if row.family == "dual_role_v8"]
    precision, recall = _pooled_deviation(full)

    exact_harms = sum(
        maps["v6"][key].exact_recovery == 1.0 and row.exact_recovery == 0.0
        for key, row in maps["full"].items()
    )
    v7_harms = sum(
        maps["v6"][key].exact_recovery == 1.0 and maps["v7"][key].exact_recovery == 0.0
        for key in keys
    )
    family_recovery = {
        family: _mean([row for row in singles if row.family == family], "all_true_deviations_recovered")
        for family in SINGLE_FAMILIES_V8
    }
    client_recovery = {
        clients: _mean([row for row in singles if row.num_clients == clients], "all_true_deviations_recovered")
        for clients in (4, 8, 16)
    }
    balanced = _mean([row for row in singles if row.balance_profile == "balanced"], "all_true_deviations_recovered")
    imbalanced = _mean([row for row in singles if row.balance_profile == "imbalanced"], "all_true_deviations_recovered")
    high_noise = _mean([row for row in singles if row.noise_ratio == 0.30], "all_true_deviations_recovered")
    dual_both = _mean(dual, "all_true_deviations_recovered")
    dual_exact_spurious = sum(
        row.spurious_deviation_accepted > 0 for row in dual if row.all_true_deviations_recovered == 1.0
    )
    role_false_rate = _mean(nulls, "role_hypothesis_positive")
    cert_violations = sum(row.certificate_violation_count for row in full)
    anchor_preserved = all(
        set(filter(None, row.anchor_structure.split(";"))).issubset(
            set(filter(None, row.final_structure.split(";")))
        )
        for row in full
    )
    accepted_role_values_ok = all(
        (row.min_accepted_role_gap is None or row.min_accepted_role_gap >= 0.50)
        and (row.min_accepted_role_mean is None or row.min_accepted_role_mean >= 0.75)
        and (row.max_accepted_outside_mean is None or row.max_accepted_outside_mean <= 0.25)
        for row in full
    )

    criteria = {
        "A_integrity_540_fresh_conditions": (
            len(full) == 540
            and {row.seed for row in full} == set(DEVELOPMENT_SEEDS)
            and SMOKE_SEED not in {row.seed for row in full}
            and len(keys) == 540
            and all(np.isfinite(row.test_nmse) and np.isfinite(row.runtime_seconds) for row in full)
        ),
        "B_anchor_monotonicity": anchor_preserved,
        "C_null_spurious_deviation_le_002": _mean(nulls, "spurious_deviation_accepted") <= 0.02,
        "D_zero_exact_harms": exact_harms == 0,
        "E_overall_exact_noninferior_001": _mean(full, "exact_recovery") >= _mean(v6, "exact_recovery") - 0.01,
        "F_deviation_subset_exact_gain_ge_005": _mean(deviation_rows, "exact_recovery") >= _mean(v6_deviation_rows, "exact_recovery") + 0.05,
        "G_deviation_precision_ge_099": precision >= 0.99,
        "H_deviation_recall_ge_093": recall >= 0.93,
        "I_each_family_recovery_ge_090": all(value >= 0.90 for value in family_recovery.values()),
        "J_four_client_recovery_ge_088": client_recovery[4] >= 0.88,
        "K_eight_client_recovery_ge_092": client_recovery[8] >= 0.92,
        "L_sixteen_client_recovery_ge_092": client_recovery[16] >= 0.92,
        "M_high_noise_recovery_ge_088": high_noise >= 0.88,
        "N_imbalance_gap_le_006": imbalanced >= balanced - 0.06,
        "O_dual_both_ge_090_and_no_spurious_in_exact": dual_both >= 0.90 and dual_exact_spurious == 0,
        "P_role_contrast_integrity": accepted_role_values_ok and role_false_rate <= 0.02,
        "Q_certificate_integrity": cert_violations == 0,
        "R_mechanism_superiority_vs_v7style": (
            _mean(deviation_rows, "exact_recovery") >= _mean(v7_deviation_rows, "exact_recovery") + 0.03
            and exact_harms <= v7_harms
        ),
        "S_communication_le_150pct_v6": _median(full, "communication_bytes") <= 1.50 * _median(v6, "communication_bytes"),
        "T_runtime_le_200pct_v6": _median(full, "runtime_seconds") <= 2.00 * _median(v6, "runtime_seconds"),
    }

    strict_precision, strict_recall = _pooled_deviation(strict)
    result["gate_values"] = {
        "v8_exact": _mean(full, "exact_recovery"),
        "v6_exact": _mean(v6, "exact_recovery"),
        "deviation_subset_v8_exact": _mean(deviation_rows, "exact_recovery"),
        "deviation_subset_v6_exact": _mean(v6_deviation_rows, "exact_recovery"),
        "deviation_subset_v7style_exact": _mean(v7_deviation_rows, "exact_recovery"),
        "deviation_precision": precision,
        "deviation_recall": recall,
        "strict_probe_deviation_precision": strict_precision,
        "strict_probe_deviation_recall": strict_recall,
        "family_recovery": family_recovery,
        "client_recovery": client_recovery,
        "balanced_recovery": balanced,
        "imbalanced_recovery": imbalanced,
        "high_noise_recovery": high_noise,
        "dual_both_recovery": dual_both,
        "dual_exact_spurious_count": dual_exact_spurious,
        "null_spurious_deviation_acceptance": _mean(nulls, "spurious_deviation_accepted"),
        "null_false_role_hypothesis_rate": role_false_rate,
        "exact_harms": exact_harms,
        "v7style_exact_harms": v7_harms,
        "certificate_violations": cert_violations,
        "v8_communication_median": _median(full, "communication_bytes"),
        "v6_communication_median": _median(v6, "communication_bytes"),
        "v8_runtime_median": _median(full, "runtime_seconds"),
        "v6_runtime_median": _median(v6, "runtime_seconds"),
    }
    result["development_gate"] = {
        "evaluated": True,
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
        "status": "DEVELOPMENT-GO" if all(criteria.values()) else "DEVELOPMENT-NO-GO",
        "scientific_boundary": (
            "A GO authorizes only a separately frozen v8 independent-validation protocol with a new seed namespace. "
            "A NO-GO permanently spends 25101--25105 and forbids retuning v8 on them."
        ),
    }
    return result


def write_csv(rows: Sequence[V8StudyRow], path: Path) -> None:
    if not rows:
        raise ValueError("cannot write empty v8 study")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--output", type=Path, default=Path("results/scsv_v8/rows.csv"))
    parser.add_argument("--summary", type=Path, default=Path("results/scsv_v8/summary.json"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    methods = tuple(item.strip() for item in args.methods.split(",") if item.strip())
    seeds = (SMOKE_SEED,) if args.smoke else DEVELOPMENT_SEEDS
    rows = run_study(seeds=seeds, methods=methods, smoke=args.smoke)
    summary = summarize(rows, evaluate_gate=not args.smoke)
    write_csv(rows, args.output)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
