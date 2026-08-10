"""Frozen development study harness for FedFalsify SCSV-RCEF v9."""

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
from .scsv_v8 import SCSVSPCCV8Output, scsv_spcc_v8_method
from .scsv_v9 import SCSVRCEFV9Output, scsv_rcef_v9_method
from .scsv_v9_benchmarks import (
    SINGLE_FAMILIES_V9,
    V9_DEVIATIONS,
    V9GeneratedBenchmark,
    generate_v9_benchmark,
    generate_v9_global_test_data,
    v9_catalog,
)

SMOKE_SEED = 26001
DEVELOPMENT_SEEDS = (26101, 26102, 26103, 26104, 26105)
METHODS = (
    "scsv-rcef-v9-full",
    "scsv-rcef-v9-no-role-proposer",
    "scsv-rcef-v9-selector-only",
    "scsv-spcc-v8-style",
    "scsv-v6-anchor",
    "centralized-forward",
)


@dataclass(frozen=True)
class V9StudyRow:
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
    added_sources: str
    anchor_structure: str
    final_structure: str
    bank_terms: str
    candidate_deviations: str
    role_proposed_candidates: str
    role_hypothesis_positive: float
    role_integrity_violation_count: int
    source_qualification_violation_count: int
    pair_invariant_violation_count: int
    evidence_fusion_violation_count: int
    source_ambiguity: float
    global_ambiguity: float
    diagnostics_json: str
    source_diagnostics_json: str
    expression: str
    stop_reason: str


def _validate_seeds(seeds: Sequence[int], *, smoke: bool) -> None:
    allowed = {SMOKE_SEED} if smoke else set(DEVELOPMENT_SEEDS)
    if set(seeds) != allowed:
        if smoke:
            raise ValueError("v9 engineering smoke must use seed 26001 only")
        raise ValueError("v9 development evidence must use exactly seeds 26101--26105")


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


def _v9_integrity_counts(output: SCSVRCEFV9Output | None) -> tuple[int, int, int, int, bool]:
    if output is None:
        return 0, 0, 0, 0, False
    accepted = set(output.accepted_deviations)
    added_sources = set(output.added_sources)
    role_violations = 0
    pair_violations = 0
    fusion_violations = 0
    any_role = False
    for item in output.diagnostics:
        any_role = any_role or item.role_admissible
        if item.term not in accepted:
            continue
        if not (
            item.role_admissible
            and item.role_client_ids
            and item.outside_client_ids
            and item.occupancy_gap >= 0.50
            and item.role_mean_occupancy >= 0.75
            and item.outside_mean_occupancy <= 0.25
        ):
            role_violations += 1
        if not (
            item.pair_invariant
            and item.selector_outside_safe
            and item.probe_outside_safe
        ):
            pair_violations += 1
        if output.method == "scsv-rcef-v9-full" and not (
            item.selector_state != "CONTRADICTED"
            and item.probe_state != "CONTRADICTED"
            and item.pooled_delta is not None
            and item.pooled_delta < 0.0
        ):
            fusion_violations += 1

    source_violations = 0
    for source in added_sources:
        matches = [item for item in output.source_diagnostics if item.source_term == source]
        if len(matches) != 1:
            source_violations += 1
            continue
        item = matches[0]
        if not (
            not item.source_in_anchor
            and item.source_in_bank
            and item.qualified
            and item.invariant
            and item.selector_state != "CONTRADICTED"
            and item.probe_state != "CONTRADICTED"
            and item.pooled_delta is not None
            and item.pooled_delta < 0.0
        ):
            source_violations += 1
    return role_violations, source_violations, pair_violations, fusion_violations, any_role


def _evaluate_candidate(
    generated: V9GeneratedBenchmark,
    candidate: CandidateEquation,
    *,
    method: str,
    seed: int,
    requested_noise: float,
    runtime_seconds: float,
    communication_bytes: int,
    stop_reason: str,
    v9_output: SCSVRCEFV9Output | None = None,
    v8_output: SCSVSPCCV8Output | None = None,
) -> V9StudyRow:
    catalog = v9_catalog()
    predicted = _candidate_terms(candidate)
    target = set(generated.target_terms)
    exact, precision, recall = _term_metrics(predicted, target)
    x_test, y_test = generate_v9_global_test_data(generated, seed=seed + 100_000)
    test_prediction = candidate.predict(x_test, catalog)
    pooled_x = np.concatenate([item.x for item in generated.clients], axis=0)
    pooled_y = np.concatenate([item.y for item in generated.clients], axis=0)
    train_prediction = candidate.predict(pooled_x, catalog)
    train_mse = float(np.mean((pooled_y - train_prediction) ** 2))

    predicted_deviations = predicted & set(V9_DEVIATIONS)
    true_deviations = set(generated.true_deviations)
    tp = len(predicted_deviations & true_deviations)
    fp = len(predicted_deviations - true_deviations)
    fn = len(true_deviations - predicted_deviations)
    dev_precision = tp / (tp + fp) if tp + fp else float(not true_deviations)
    dev_recall = tp / (tp + fn) if tp + fn else 1.0

    if v9_output is not None:
        accepted = v9_output.accepted_deviations
        added_sources = v9_output.added_sources
        anchor_structure = v9_output.anchor_structure
        final_structure = v9_output.final_structure
        bank_terms = v9_output.bank_terms
        candidate_deviations = v9_output.candidate_deviations
        role_proposed = v9_output.role_proposed_candidates
        role_v, source_v, pair_v, fusion_v, any_role = _v9_integrity_counts(v9_output)
        source_ambiguity = float(v9_output.source_ambiguity)
        global_ambiguity = float(v9_output.global_ambiguity)
        diagnostics_json = json.dumps(
            [asdict(item) for item in v9_output.diagnostics], sort_keys=True, separators=(",", ":")
        )
        source_diagnostics_json = json.dumps(
            [asdict(item) for item in v9_output.source_diagnostics], sort_keys=True, separators=(",", ":")
        )
    elif v8_output is not None:
        accepted = v8_output.accepted_deviations
        added_sources = ()
        anchor_structure = v8_output.anchor_structure
        final_structure = v8_output.final_structure
        bank_terms = v8_output.bank_terms
        candidate_deviations = v8_output.source_linked_candidates
        role_proposed = ()
        role_v = source_v = pair_v = fusion_v = 0
        any_role = any(item.role_admissible for item in v8_output.diagnostics)
        source_ambiguity = float(v8_output.source_ambiguity)
        global_ambiguity = float(v8_output.global_ambiguity)
        diagnostics_json = json.dumps(
            [asdict(item) for item in v8_output.diagnostics], sort_keys=True, separators=(",", ":")
        )
        source_diagnostics_json = "[]"
    else:
        accepted = ()
        added_sources = ()
        anchor_structure = ()
        final_structure = candidate.active_terms
        bank_terms = ()
        candidate_deviations = ()
        role_proposed = ()
        role_v = source_v = pair_v = fusion_v = 0
        any_role = False
        source_ambiguity = global_ambiguity = 0.0
        diagnostics_json = source_diagnostics_json = "[]"

    return V9StudyRow(
        family=generated.family,
        noise_ratio=float(requested_noise),
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
        added_sources=";".join(added_sources),
        anchor_structure=";".join(anchor_structure),
        final_structure=";".join(final_structure),
        bank_terms=";".join(bank_terms),
        candidate_deviations=";".join(candidate_deviations),
        role_proposed_candidates=";".join(role_proposed),
        role_hypothesis_positive=float(any_role),
        role_integrity_violation_count=int(role_v),
        source_qualification_violation_count=int(source_v),
        pair_invariant_violation_count=int(pair_v),
        evidence_fusion_violation_count=int(fusion_v),
        source_ambiguity=source_ambiguity,
        global_ambiguity=global_ambiguity,
        diagnostics_json=diagnostics_json,
        source_diagnostics_json=source_diagnostics_json,
        expression=candidate.expression(catalog),
        stop_reason=stop_reason,
    )


def _evaluate_condition(
    generated: V9GeneratedBenchmark,
    *,
    requested_noise: float,
    seed: int,
    methods: Sequence[str],
) -> list[V9StudyRow]:
    unknown = set(methods) - set(METHODS)
    if unknown:
        raise ValueError(f"unknown v9 methods: {sorted(unknown)}")
    rows: list[V9StudyRow] = []
    catalog = v9_catalog()
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)

    full_output: SCSVRCEFV9Output | None = None
    if "scsv-rcef-v9-full" in methods or "scsv-v6-anchor" in methods:
        full_output = scsv_rcef_v9_method(
            generated.clients,
            catalog,
            seed=seed,
            target_mse=target_mse,
            min_repair_score=0.05,
            use_role_proposer=True,
            evidence_fusion=True,
        )
        if "scsv-rcef-v9-full" in methods:
            rows.append(
                _evaluate_candidate(
                    generated,
                    full_output.candidate,
                    method="scsv-rcef-v9-full",
                    seed=seed,
                    requested_noise=requested_noise,
                    runtime_seconds=full_output.runtime_seconds,
                    communication_bytes=full_output.communication_bytes,
                    stop_reason=full_output.stop_reason,
                    v9_output=full_output,
                )
            )
        if "scsv-v6-anchor" in methods:
            rows.append(
                _evaluate_candidate(
                    generated,
                    full_output.anchor.candidate,
                    method="scsv-v6-anchor",
                    seed=seed,
                    requested_noise=requested_noise,
                    runtime_seconds=full_output.anchor.runtime_seconds,
                    communication_bytes=full_output.anchor.communication_bytes,
                    stop_reason=full_output.anchor.stop_reason,
                )
            )

    if "scsv-rcef-v9-no-role-proposer" in methods:
        output = scsv_rcef_v9_method(
            generated.clients,
            catalog,
            seed=seed,
            target_mse=target_mse,
            min_repair_score=0.05,
            use_role_proposer=False,
            evidence_fusion=True,
        )
        rows.append(
            _evaluate_candidate(
                generated,
                output.candidate,
                method="scsv-rcef-v9-no-role-proposer",
                seed=seed,
                requested_noise=requested_noise,
                runtime_seconds=output.runtime_seconds,
                communication_bytes=output.communication_bytes,
                stop_reason=output.stop_reason,
                v9_output=output,
            )
        )

    if "scsv-rcef-v9-selector-only" in methods:
        output = scsv_rcef_v9_method(
            generated.clients,
            catalog,
            seed=seed,
            target_mse=target_mse,
            min_repair_score=0.05,
            use_role_proposer=True,
            evidence_fusion=False,
        )
        rows.append(
            _evaluate_candidate(
                generated,
                output.candidate,
                method="scsv-rcef-v9-selector-only",
                seed=seed,
                requested_noise=requested_noise,
                runtime_seconds=output.runtime_seconds,
                communication_bytes=output.communication_bytes,
                stop_reason=output.stop_reason,
                v9_output=output,
            )
        )

    if "scsv-spcc-v8-style" in methods:
        output8 = scsv_spcc_v8_method(
            generated.clients,
            catalog,
            seed=seed,
            target_mse=target_mse,
            min_repair_score=0.05,
            strict_probe=False,
        )
        rows.append(
            _evaluate_candidate(
                generated,
                output8.candidate,
                method="scsv-spcc-v8-style",
                seed=seed,
                requested_noise=requested_noise,
                runtime_seconds=output8.runtime_seconds,
                communication_bytes=output8.communication_bytes,
                stop_reason=output8.stop_reason,
                v8_output=output8,
            )
        )

    if "centralized-forward" in methods:
        output = centralized_forward(generated.clients, catalog, max_terms=10)
        rows.append(
            _evaluate_candidate(
                generated,
                output.candidate,
                method="centralized-forward",
                seed=seed,
                requested_noise=requested_noise,
                runtime_seconds=output.runtime_seconds,
                communication_bytes=0,
                stop_reason=output.stop_reason,
            )
        )
    return rows


def _scientific_conditions(seeds: Sequence[int]):
    for family in SINGLE_FAMILIES_V9:
        for num_clients in (4, 8, 16):
            role_profiles = ("single",) if num_clients == 4 else ("single", "quarter")
            for balance in ("balanced", "imbalanced"):
                for role_profile in role_profiles:
                    for noise in (0.10, 0.30):
                        for seed in seeds:
                            yield family, num_clients, balance, role_profile, noise, seed
    for family in ("null_role_v9", "diffuse_null_v9"):
        for num_clients in (4, 8, 16):
            for balance in ("balanced", "imbalanced"):
                for noise in (0.10, 0.30):
                    for seed in seeds:
                        yield family, num_clients, balance, "none", noise, seed
    for family in ("weak_source_role_v9", "dual_role_v9"):
        for num_clients in (8, 16):
            for balance in ("balanced", "imbalanced"):
                for noise in (0.10, 0.30):
                    for seed in seeds:
                        yield family, num_clients, balance, "quarter", noise, seed


def _smoke_conditions():
    return (
        ("quadratic_role_v9", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("linear_role_v9", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("trig_role_v9", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("interaction_role_v9", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("null_role_v9", 8, "balanced", "none", 0.10, SMOKE_SEED),
        ("diffuse_null_v9", 8, "balanced", "none", 0.10, SMOKE_SEED),
        ("weak_source_role_v9", 8, "balanced", "quarter", 0.10, SMOKE_SEED),
        ("dual_role_v9", 8, "balanced", "quarter", 0.10, SMOKE_SEED),
    )


def run_study(*, seeds: Sequence[int], smoke: bool, methods: Sequence[str] = METHODS) -> list[V9StudyRow]:
    _validate_seeds(seeds, smoke=smoke)
    conditions = _smoke_conditions() if smoke else tuple(_scientific_conditions(seeds))
    if not smoke and len(conditions) != 600:
        raise RuntimeError(f"v9 condition firewall expected 600, got {len(conditions)}")
    rows: list[V9StudyRow] = []
    for family, num_clients, balance, role_profile, noise, seed in conditions:
        generated = generate_v9_benchmark(
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


def _pooled_precision(rows: Sequence[V9StudyRow]) -> float:
    tp = sum(item.deviation_tp for item in rows)
    fp = sum(item.deviation_fp for item in rows)
    return float(tp / (tp + fp)) if tp + fp else 1.0


def _pooled_recall(rows: Sequence[V9StudyRow]) -> float:
    tp = sum(item.deviation_tp for item in rows)
    fn = sum(item.deviation_fn for item in rows)
    return float(tp / (tp + fn)) if tp + fn else 1.0


def _method_rows(rows: Sequence[V9StudyRow], method: str) -> list[V9StudyRow]:
    return [item for item in rows if item.method == method]


def summarize(rows: Sequence[V9StudyRow], *, evaluate_gate: bool) -> dict:
    methods: dict[str, dict] = {}
    for method in METHODS:
        subset = _method_rows(rows, method)
        if not subset:
            continue
        methods[method] = {
            "runs": len(subset),
            "exact_recovery": mean(item.exact_recovery for item in subset),
            "term_precision": mean(item.term_precision for item in subset),
            "term_recall": mean(item.term_recall for item in subset),
            "test_nmse": mean(item.test_nmse for item in subset),
            "deviation_precision_pooled": _pooled_precision(subset),
            "deviation_recall_pooled": _pooled_recall(subset),
            "spurious_deviation_acceptance": mean(item.spurious_deviation_accepted for item in subset),
            "runtime_seconds_median": median(item.runtime_seconds for item in subset),
            "communication_bytes_median": median(item.communication_bytes for item in subset),
        }

    result = {
        "schema_version": 1,
        "status": "scsv-rcef-v9-development" if evaluate_gate else "scsv-rcef-v9-engineering-smoke",
        "rows": len(rows),
        "conditions": len(rows) // max(len({item.method for item in rows}), 1),
        "seeds": sorted({item.seed for item in rows}),
        "methods": methods,
    }
    if not evaluate_gate:
        return result

    full = _method_rows(rows, "scsv-rcef-v9-full")
    selector_only = _method_rows(rows, "scsv-rcef-v9-selector-only")
    v8 = _method_rows(rows, "scsv-spcc-v8-style")
    condition_keys = {
        (r.family, r.noise_ratio, r.samples_per_client, r.num_clients, r.balance_profile, r.role_profile, r.seed)
        for r in full
    }
    nulls = [r for r in full if r.family in {"null_role_v9", "diffuse_null_v9"}]
    deviation_rows = [r for r in full if r.family not in {"null_role_v9", "diffuse_null_v9"}]
    v8_deviation = [r for r in v8 if r.family not in {"null_role_v9", "diffuse_null_v9"}]
    selector_deviation = [r for r in selector_only if r.family not in {"null_role_v9", "diffuse_null_v9"}]
    main = [r for r in full if r.family in set(SINGLE_FAMILIES_V9)]

    v8_map = {
        (r.family, r.noise_ratio, r.samples_per_client, r.num_clients, r.balance_profile, r.role_profile, r.seed): r
        for r in v8
    }
    exact_harms = sum(
        1
        for r in full
        if v8_map[(r.family, r.noise_ratio, r.samples_per_client, r.num_clients, r.balance_profile, r.role_profile, r.seed)].exact_recovery == 1.0
        and r.exact_recovery == 0.0
    )

    family_recovery = {
        family: mean(r.all_true_deviations_recovered for r in main if r.family == family)
        for family in SINGLE_FAMILIES_V9
    }
    client_recovery = {
        str(n): mean(r.all_true_deviations_recovered for r in main if r.num_clients == n)
        for n in (4, 8, 16)
    }
    balanced = mean(r.all_true_deviations_recovered for r in main if r.balance_profile == "balanced")
    imbalanced = mean(r.all_true_deviations_recovered for r in main if r.balance_profile == "imbalanced")
    high_noise = mean(r.all_true_deviations_recovered for r in main if r.noise_ratio == 0.30)
    weak = [r for r in full if r.family == "weak_source_role_v9"]
    dual = [r for r in full if r.family == "dual_role_v9"]
    dual_both = mean(r.all_true_deviations_recovered for r in dual)
    dual_spurious_when_exact = sum(
        int(r.spurious_deviation_accepted)
        for r in dual
        if r.all_true_deviations_recovered == 1.0
    )

    fusion_full = mean(r.exact_recovery for r in deviation_rows)
    fusion_selector = mean(r.exact_recovery for r in selector_deviation)
    fusion_superior = bool(
        fusion_full >= fusion_selector + 0.01
        or (fusion_selector >= 0.95 and fusion_full >= fusion_selector - 0.005)
    )

    gate_values = {
        "v9_exact": mean(r.exact_recovery for r in full),
        "v8_style_exact": mean(r.exact_recovery for r in v8),
        "deviation_subset_v9_exact": fusion_full,
        "deviation_subset_v8_exact": mean(r.exact_recovery for r in v8_deviation),
        "deviation_subset_selector_only_exact": fusion_selector,
        "deviation_precision": _pooled_precision(full),
        "deviation_recall": _pooled_recall(full),
        "family_recovery": family_recovery,
        "weak_source_recovery": mean(r.all_true_deviations_recovered for r in weak),
        "client_recovery": client_recovery,
        "high_noise_recovery": high_noise,
        "balanced_recovery": balanced,
        "imbalanced_recovery": imbalanced,
        "dual_both_recovery": dual_both,
        "dual_exact_spurious_count": dual_spurious_when_exact,
        "null_spurious_deviation_acceptance": mean(r.spurious_deviation_accepted for r in nulls),
        "exact_harms": exact_harms,
        "role_integrity_violations": sum(r.role_integrity_violation_count for r in full),
        "source_qualification_violations": sum(r.source_qualification_violation_count for r in full),
        "pair_invariant_violations": sum(r.pair_invariant_violation_count for r in full),
        "evidence_fusion_violations": sum(r.evidence_fusion_violation_count for r in full),
        "v9_communication_median": median(r.communication_bytes for r in full),
        "v8_communication_median": median(r.communication_bytes for r in v8),
        "v9_runtime_median": median(r.runtime_seconds for r in full),
        "v8_runtime_median": median(r.runtime_seconds for r in v8),
    }

    criteria = {
        "A_integrity_600_fresh_conditions": bool(
            len(condition_keys) == 600
            and len(rows) == 3600
            and sorted({r.seed for r in rows}) == list(DEVELOPMENT_SEEDS)
            and SMOKE_SEED not in {r.seed for r in rows}
        ),
        "B_anchor_monotonicity": all(
            set(filter(None, r.anchor_structure.split(";"))).issubset(set(filter(None, r.final_structure.split(";"))))
            for r in full
        ),
        "C_null_spurious_deviation_le_002": gate_values["null_spurious_deviation_acceptance"] <= 0.02,
        "D_zero_exact_harms": exact_harms == 0,
        "E_overall_exact_noninferior_001": gate_values["v9_exact"] >= gate_values["v8_style_exact"] - 0.01,
        "F_deviation_subset_exact_gain_ge_004": gate_values["deviation_subset_v9_exact"] >= gate_values["deviation_subset_v8_exact"] + 0.04,
        "G_deviation_precision_ge_099": gate_values["deviation_precision"] >= 0.99,
        "H_deviation_recall_ge_093": gate_values["deviation_recall"] >= 0.93,
        "I_each_main_family_recovery_ge_090": min(family_recovery.values()) >= 0.90,
        "J_weak_source_recovery_ge_080": gate_values["weak_source_recovery"] >= 0.80,
        "K_four_client_recovery_ge_088": client_recovery["4"] >= 0.88,
        "L_eight_client_recovery_ge_090": client_recovery["8"] >= 0.90,
        "M_sixteen_client_recovery_ge_094": client_recovery["16"] >= 0.94,
        "N_high_noise_recovery_ge_088": high_noise >= 0.88,
        "O_imbalance_gap_le_006": imbalanced >= balanced - 0.06,
        "P_dual_both_ge_090_and_no_spurious": dual_both >= 0.90 and dual_spurious_when_exact == 0,
        "Q_role_contrast_integrity": gate_values["role_integrity_violations"] == 0,
        "R_source_qualification_integrity": gate_values["source_qualification_violations"] == 0,
        "S_pair_invariant": gate_values["pair_invariant_violations"] == 0,
        "T_evidence_fusion_integrity": gate_values["evidence_fusion_violations"] == 0,
        "U_mechanism_superiority": fusion_superior,
        "V_communication_le_175pct_v8": gate_values["v9_communication_median"] <= 1.75 * gate_values["v8_communication_median"],
        "W_runtime_le_225pct_v8": gate_values["v9_runtime_median"] <= 2.25 * gate_values["v8_runtime_median"],
    }
    passed = all(criteria.values())
    result["gate_values"] = gate_values
    result["development_gate"] = {
        "evaluated": True,
        "criteria": criteria,
        "passed": passed,
        "status": "DEVELOPMENT-GO" if passed else "DEVELOPMENT-NO-GO",
        "scientific_boundary": (
            "A GO authorizes only a separately frozen v9 independent-validation protocol with a new untouched seed namespace. "
            "A NO-GO permanently spends 26101--26105 and forbids retuning v9 on them."
        ),
    }
    return result


def write_outputs(rows: Sequence[V9StudyRow], out_dir: Path, *, evaluate_gate: bool) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out_dir / "rows.csv"
    with rows_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    summary = summarize(rows, evaluate_gate=evaluate_gate)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if evaluate_gate:
        decision = {
            "schema_version": 1,
            "criteria": summary["development_gate"]["criteria"],
            "passed": summary["development_gate"]["passed"],
            "status": summary["development_gate"]["status"],
            "scientific_boundary": summary["development_gate"]["scientific_boundary"],
        }
        (out_dir / "decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("smoke", "development"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    smoke = args.mode == "smoke"
    seeds = (SMOKE_SEED,) if smoke else DEVELOPMENT_SEEDS
    rows = run_study(seeds=seeds, smoke=smoke, methods=METHODS)
    write_outputs(rows, args.out, evaluate_gate=not smoke)
    print(json.dumps(summarize(rows, evaluate_gate=not smoke), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
