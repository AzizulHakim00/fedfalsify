"""Frozen development-study harness for FedFalsify SCSV-AQCC v10."""

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
from .scsv_v10 import SCSVAQCCV10Output, scsv_aqcc_v10_method
from .scsv_v10_benchmarks import (
    SINGLE_FAMILIES_V10,
    V10_DEVIATIONS,
    V10GeneratedBenchmark,
    generate_v10_benchmark,
    generate_v10_global_test_data,
    v10_catalog,
)
from .scsv_v9 import SCSVRCEFV9Output, scsv_rcef_v9_method

SMOKE_SEED = 28001
DEVELOPMENT_SEEDS = (28101, 28102, 28103, 28104, 28105)
METHODS = (
    "scsv-aqcc-v10-full",
    "scsv-aqcc-v10-no-quarantine",
    "scsv-aqcc-v10-split-veto",
    "scsv-rcef-v9-style",
    "scsv-v6-anchor",
    "centralized-forward",
)
NULL_FAMILIES = {"null_role_v10", "anchor_contamination_null_v10"}


@dataclass(frozen=True)
class V10StudyRow:
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
    ordinary_anchor_structure: str
    quarantined_anchor_exceptions: str
    recertified_anchor_exceptions: str
    removed_anchor_exceptions: str
    final_structure: str
    bank_terms: str
    candidate_deviations: str
    role_proposed_candidates: str
    ordinary_anchor_violation_count: int
    quarantine_integrity_violation_count: int
    role_integrity_violation_count: int
    source_qualification_violation_count: int
    pair_invariant_violation_count: int
    client_consensus_violation_count: int
    diagnostics_json: str
    source_diagnostics_json: str
    expression: str
    stop_reason: str


def _validate_seeds(seeds: Sequence[int], *, smoke: bool) -> None:
    allowed = {SMOKE_SEED} if smoke else set(DEVELOPMENT_SEEDS)
    if set(seeds) != allowed:
        if smoke:
            raise ValueError("v10 engineering smoke must use seed 28001 only")
        raise ValueError("v10 development evidence must use exactly seeds 28101--28105")


def _candidate_terms(candidate: CandidateEquation) -> set[str]:
    return {
        term
        for term, coefficient in zip(candidate.active_terms, candidate.coefficients)
        if term != "1" and abs(float(coefficient)) >= 1e-3
    }


def _term_metrics(predicted: Iterable[str], target: Iterable[str]) -> tuple[float, float, float]:
    p = set(predicted)
    t = set(target)
    both = p & t
    precision = len(both) / len(p) if p else float(not t)
    recall = len(both) / len(t) if t else 1.0
    return float(p == t), float(precision), float(recall)


def _prediction_nmse(prediction: np.ndarray, target: np.ndarray) -> float:
    mse = float(np.mean((np.asarray(target) - np.asarray(prediction)) ** 2))
    return float(mse / max(float(np.var(target)), 1e-12))


def _v10_integrity_counts(output: SCSVAQCCV10Output | None) -> tuple[int, int, int, int, int, int]:
    if output is None:
        return 0, 0, 0, 0, 0, 0
    final = set(output.final_structure)
    accepted = set(output.accepted_deviations)
    ordinary_violation = int(not set(output.ordinary_anchor_structure).issubset(final))
    quarantine_violation = 0
    role_violation = 0
    source_violation = 0
    pair_violation = 0
    consensus_violation = 0

    diag_by_term = {item.term: item for item in output.diagnostics}
    for term in output.quarantined_anchor_exceptions:
        if term in final:
            item = diag_by_term.get(term)
            if item is None or term not in accepted or not item.positive_pre_ambiguity:
                quarantine_violation += 1

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
        ):
            role_violation += 1
        if not (item.pair_invariant and item.selector_outside_safe and item.probe_outside_safe):
            pair_violation += 1
        if output.method == "scsv-aqcc-v10-full" and not (
            item.pooled_delta is not None
            and item.pooled_delta < 0.0
            and item.client_median_gain is not None
            and item.client_median_gain > 0.0
        ):
            consensus_violation += 1

    for source in output.added_sources:
        matches = [item for item in output.source_diagnostics if item.source_term == source]
        if len(matches) != 1:
            source_violation += 1
            continue
        item = matches[0]
        if not (
            not item.source_in_core_anchor
            and item.source_in_bank
            and item.qualified
            and item.invariant
        ):
            source_violation += 1
        if output.method == "scsv-aqcc-v10-full" and not (
            item.pooled_delta is not None
            and item.pooled_delta < 0.0
            and item.client_median_gain is not None
            and item.client_median_gain > 0.0
        ):
            consensus_violation += 1

    return (
        ordinary_violation,
        quarantine_violation,
        role_violation,
        source_violation,
        pair_violation,
        consensus_violation,
    )


def _evaluate_candidate(
    generated: V10GeneratedBenchmark,
    candidate: CandidateEquation,
    *,
    method: str,
    seed: int,
    requested_noise: float,
    runtime_seconds: float,
    communication_bytes: int,
    stop_reason: str,
    v10_output: SCSVAQCCV10Output | None = None,
    v9_output: SCSVRCEFV9Output | None = None,
) -> V10StudyRow:
    catalog = v10_catalog()
    predicted = _candidate_terms(candidate)
    target = set(generated.target_terms)
    exact, precision, recall = _term_metrics(predicted, target)
    x_test, y_test = generate_v10_global_test_data(generated, seed=seed + 100_000)
    test_prediction = candidate.predict(x_test, catalog)
    pooled_x = np.concatenate([item.x for item in generated.clients], axis=0)
    pooled_y = np.concatenate([item.y for item in generated.clients], axis=0)
    train_prediction = candidate.predict(pooled_x, catalog)
    train_mse = float(np.mean((pooled_y - train_prediction) ** 2))

    predicted_deviations = predicted & set(V10_DEVIATIONS)
    true_deviations = set(generated.true_deviations)
    tp = len(predicted_deviations & true_deviations)
    fp = len(predicted_deviations - true_deviations)
    fn = len(true_deviations - predicted_deviations)
    dev_precision = tp / (tp + fp) if tp + fp else float(not true_deviations)
    dev_recall = tp / (tp + fn) if tp + fn else 1.0

    if v10_output is not None:
        accepted = v10_output.accepted_deviations
        anchor_structure = v10_output.anchor_structure
        ordinary = v10_output.ordinary_anchor_structure
        quarantined = v10_output.quarantined_anchor_exceptions
        recertified = v10_output.recertified_anchor_exceptions
        removed = v10_output.removed_anchor_exceptions
        final_structure = v10_output.final_structure
        bank_terms = v10_output.bank_terms
        candidate_deviations = v10_output.candidate_deviations
        role_proposed = v10_output.role_proposed_candidates
        integrity = _v10_integrity_counts(v10_output)
        diagnostics_json = json.dumps(
            [asdict(item) for item in v10_output.diagnostics], sort_keys=True, separators=(",", ":")
        )
        source_diagnostics_json = json.dumps(
            [asdict(item) for item in v10_output.source_diagnostics], sort_keys=True, separators=(",", ":")
        )
    elif v9_output is not None:
        accepted = v9_output.accepted_deviations
        anchor_structure = v9_output.anchor_structure
        ordinary = tuple(
            term for term in v9_output.anchor_structure
            if term == "1" or catalog.get(term).kind != "exception"
        )
        quarantined = recertified = removed = ()
        final_structure = v9_output.final_structure
        bank_terms = v9_output.bank_terms
        candidate_deviations = v9_output.candidate_deviations
        role_proposed = v9_output.role_proposed_candidates
        integrity = (0, 0, 0, 0, 0, 0)
        diagnostics_json = json.dumps(
            [asdict(item) for item in v9_output.diagnostics], sort_keys=True, separators=(",", ":")
        )
        source_diagnostics_json = json.dumps(
            [asdict(item) for item in v9_output.source_diagnostics], sort_keys=True, separators=(",", ":")
        )
    else:
        accepted = anchor_structure = ordinary = quarantined = recertified = removed = ()
        final_structure = candidate.active_terms
        bank_terms = candidate_deviations = role_proposed = ()
        integrity = (0, 0, 0, 0, 0, 0)
        diagnostics_json = source_diagnostics_json = "[]"

    return V10StudyRow(
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
        anchor_structure=";".join(anchor_structure),
        ordinary_anchor_structure=";".join(ordinary),
        quarantined_anchor_exceptions=";".join(quarantined),
        recertified_anchor_exceptions=";".join(recertified),
        removed_anchor_exceptions=";".join(removed),
        final_structure=";".join(final_structure),
        bank_terms=";".join(bank_terms),
        candidate_deviations=";".join(candidate_deviations),
        role_proposed_candidates=";".join(role_proposed),
        ordinary_anchor_violation_count=int(integrity[0]),
        quarantine_integrity_violation_count=int(integrity[1]),
        role_integrity_violation_count=int(integrity[2]),
        source_qualification_violation_count=int(integrity[3]),
        pair_invariant_violation_count=int(integrity[4]),
        client_consensus_violation_count=int(integrity[5]),
        diagnostics_json=diagnostics_json,
        source_diagnostics_json=source_diagnostics_json,
        expression=candidate.expression(catalog),
        stop_reason=stop_reason,
    )


def _evaluate_condition(
    generated: V10GeneratedBenchmark,
    *,
    requested_noise: float,
    seed: int,
    methods: Sequence[str],
) -> list[V10StudyRow]:
    unknown = set(methods) - set(METHODS)
    if unknown:
        raise ValueError(f"unknown v10 methods: {sorted(unknown)}")
    rows: list[V10StudyRow] = []
    catalog = v10_catalog()
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)

    full_output: SCSVAQCCV10Output | None = None
    if "scsv-aqcc-v10-full" in methods or "scsv-v6-anchor" in methods:
        full_output = scsv_aqcc_v10_method(
            generated.clients,
            catalog,
            seed=seed,
            target_mse=target_mse,
            min_repair_score=0.05,
            quarantine_anchor=True,
            split_veto=False,
        )
        if "scsv-aqcc-v10-full" in methods:
            rows.append(_evaluate_candidate(
                generated, full_output.candidate, method="scsv-aqcc-v10-full", seed=seed,
                requested_noise=requested_noise, runtime_seconds=full_output.runtime_seconds,
                communication_bytes=full_output.communication_bytes, stop_reason=full_output.stop_reason,
                v10_output=full_output,
            ))
        if "scsv-v6-anchor" in methods:
            rows.append(_evaluate_candidate(
                generated, full_output.anchor.candidate, method="scsv-v6-anchor", seed=seed,
                requested_noise=requested_noise, runtime_seconds=full_output.anchor.runtime_seconds,
                communication_bytes=full_output.anchor.communication_bytes,
                stop_reason=full_output.anchor.stop_reason,
            ))

    if "scsv-aqcc-v10-no-quarantine" in methods:
        output = scsv_aqcc_v10_method(
            generated.clients, catalog, seed=seed, target_mse=target_mse,
            min_repair_score=0.05, quarantine_anchor=False, split_veto=False,
        )
        rows.append(_evaluate_candidate(
            generated, output.candidate, method="scsv-aqcc-v10-no-quarantine", seed=seed,
            requested_noise=requested_noise, runtime_seconds=output.runtime_seconds,
            communication_bytes=output.communication_bytes, stop_reason=output.stop_reason,
            v10_output=output,
        ))

    if "scsv-aqcc-v10-split-veto" in methods:
        output = scsv_aqcc_v10_method(
            generated.clients, catalog, seed=seed, target_mse=target_mse,
            min_repair_score=0.05, quarantine_anchor=True, split_veto=True,
        )
        rows.append(_evaluate_candidate(
            generated, output.candidate, method="scsv-aqcc-v10-split-veto", seed=seed,
            requested_noise=requested_noise, runtime_seconds=output.runtime_seconds,
            communication_bytes=output.communication_bytes, stop_reason=output.stop_reason,
            v10_output=output,
        ))

    if "scsv-rcef-v9-style" in methods:
        output9 = scsv_rcef_v9_method(
            generated.clients, catalog, seed=seed, target_mse=target_mse,
            min_repair_score=0.05, use_role_proposer=True, evidence_fusion=True,
        )
        rows.append(_evaluate_candidate(
            generated, output9.candidate, method="scsv-rcef-v9-style", seed=seed,
            requested_noise=requested_noise, runtime_seconds=output9.runtime_seconds,
            communication_bytes=output9.communication_bytes, stop_reason=output9.stop_reason,
            v9_output=output9,
        ))

    if "centralized-forward" in methods:
        output = centralized_forward(generated.clients, catalog, max_terms=10)
        rows.append(_evaluate_candidate(
            generated, output.candidate, method="centralized-forward", seed=seed,
            requested_noise=requested_noise, runtime_seconds=output.runtime_seconds,
            communication_bytes=0, stop_reason=output.stop_reason,
        ))
    return rows


def _scientific_conditions(seeds: Sequence[int]):
    for family in SINGLE_FAMILIES_V10:
        for num_clients in (4, 8, 16):
            role_profiles = ("single",) if num_clients == 4 else ("single", "quarter")
            for balance in ("balanced", "imbalanced"):
                for role_profile in role_profiles:
                    for noise in (0.10, 0.30):
                        for seed in seeds:
                            yield family, num_clients, balance, role_profile, noise, seed
    for family in ("null_role_v10", "anchor_contamination_null_v10"):
        for num_clients in (4, 8, 16):
            for balance in ("balanced", "imbalanced"):
                for noise in (0.10, 0.30):
                    for seed in seeds:
                        yield family, num_clients, balance, "none", noise, seed
    for family in ("weak_source_role_v10", "dual_role_v10"):
        for num_clients in (8, 16):
            for balance in ("balanced", "imbalanced"):
                for noise in (0.10, 0.30):
                    for seed in seeds:
                        yield family, num_clients, balance, "quarter", noise, seed


def _smoke_conditions():
    return (
        ("quadratic_role_v10", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("linear_role_v10", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("trig_role_v10", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("interaction_role_v10", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("null_role_v10", 8, "balanced", "none", 0.10, SMOKE_SEED),
        ("anchor_contamination_null_v10", 8, "balanced", "none", 0.30, SMOKE_SEED),
        ("weak_source_role_v10", 8, "balanced", "quarter", 0.10, SMOKE_SEED),
        ("dual_role_v10", 8, "balanced", "quarter", 0.10, SMOKE_SEED),
    )


def run_study(*, seeds: Sequence[int], smoke: bool, methods: Sequence[str] = METHODS) -> list[V10StudyRow]:
    _validate_seeds(seeds, smoke=smoke)
    conditions = _smoke_conditions() if smoke else tuple(_scientific_conditions(seeds))
    if not smoke and len(conditions) != 600:
        raise RuntimeError(f"v10 condition firewall expected 600, got {len(conditions)}")
    rows: list[V10StudyRow] = []
    for family, num_clients, balance, role_profile, noise, seed in conditions:
        generated = generate_v10_benchmark(
            family,
            nominal_samples_per_client=100,
            noise_ratio=noise,
            seed=seed,
            num_clients=num_clients,
            balance_profile=balance,
            role_profile=role_profile,
        )
        rows.extend(_evaluate_condition(generated, requested_noise=noise, seed=seed, methods=methods))
    return rows


def _method_rows(rows: Sequence[V10StudyRow], method: str) -> list[V10StudyRow]:
    return [item for item in rows if item.method == method]


def _pooled_precision(rows: Sequence[V10StudyRow]) -> float:
    tp = sum(item.deviation_tp for item in rows)
    fp = sum(item.deviation_fp for item in rows)
    return float(tp / (tp + fp)) if tp + fp else 1.0


def _pooled_recall(rows: Sequence[V10StudyRow]) -> float:
    tp = sum(item.deviation_tp for item in rows)
    fn = sum(item.deviation_fn for item in rows)
    return float(tp / (tp + fn)) if tp + fn else 1.0


def summarize(rows: Sequence[V10StudyRow], *, evaluate_gate: bool) -> dict:
    methods: dict[str, dict] = {}
    for method in METHODS:
        subset = _method_rows(rows, method)
        if subset:
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
        "status": "scsv-aqcc-v10-development" if evaluate_gate else "scsv-aqcc-v10-engineering-smoke",
        "rows": len(rows),
        "conditions": len(rows) // max(len({item.method for item in rows}), 1),
        "seeds": sorted({item.seed for item in rows}),
        "methods": methods,
    }
    if not evaluate_gate:
        return result

    full = _method_rows(rows, "scsv-aqcc-v10-full")
    no_q = _method_rows(rows, "scsv-aqcc-v10-no-quarantine")
    split = _method_rows(rows, "scsv-aqcc-v10-split-veto")
    v9 = _method_rows(rows, "scsv-rcef-v9-style")
    condition_key = lambda r: (r.family, r.noise_ratio, r.samples_per_client, r.num_clients, r.balance_profile, r.role_profile, r.seed)
    condition_keys = {condition_key(r) for r in full}
    v9_map = {condition_key(r): r for r in v9}
    exact_harms = sum(1 for r in full if v9_map[condition_key(r)].exact_recovery == 1.0 and r.exact_recovery == 0.0)

    deviation_rows = [r for r in full if r.family not in NULL_FAMILIES]
    v9_deviation = [r for r in v9 if r.family not in NULL_FAMILIES]
    main = [r for r in full if r.family in set(SINGLE_FAMILIES_V10)]
    family_recovery = {family: mean(r.all_true_deviations_recovered for r in main if r.family == family) for family in SINGLE_FAMILIES_V10}
    client_recovery = {str(n): mean(r.all_true_deviations_recovered for r in main if r.num_clients == n) for n in (4, 8, 16)}
    balanced = mean(r.all_true_deviations_recovered for r in main if r.balance_profile == "balanced")
    imbalanced = mean(r.all_true_deviations_recovered for r in main if r.balance_profile == "imbalanced")
    high_noise = mean(r.all_true_deviations_recovered for r in main if r.noise_ratio == 0.30)
    weak = [r for r in full if r.family == "weak_source_role_v10"]
    dual = [r for r in full if r.family == "dual_role_v10"]
    dual_both = mean(r.all_true_deviations_recovered for r in dual)
    dual_spurious_when_exact = sum(int(r.spurious_deviation_accepted) for r in dual if r.all_true_deviations_recovered == 1.0)
    nulls = [r for r in full if r.family in NULL_FAMILIES]
    contam_full = [r for r in full if r.family == "anchor_contamination_null_v10"]
    contam_noq = [r for r in no_q if r.family == "anchor_contamination_null_v10"]
    high_noise_dev_full = [r for r in deviation_rows if r.noise_ratio == 0.30]
    high_noise_dev_split = [r for r in split if r.family not in NULL_FAMILIES and r.noise_ratio == 0.30]

    contamination_full = mean(r.spurious_deviation_accepted for r in contam_full)
    contamination_noq = mean(r.spurious_deviation_accepted for r in contam_noq)
    quarantine_superior = bool(
        (contamination_noq <= 0.02 and contamination_full <= contamination_noq + 1e-12)
        or (contamination_full <= 0.02 and contamination_full <= contamination_noq - 0.20)
    )
    consensus_full = mean(r.exact_recovery for r in high_noise_dev_full)
    consensus_split = mean(r.exact_recovery for r in high_noise_dev_split)
    consensus_superior = bool(
        consensus_full >= consensus_split + 0.02
        or (consensus_split >= 0.95 and consensus_full >= consensus_split - 0.005)
    )

    gate_values = {
        "v10_exact": mean(r.exact_recovery for r in full),
        "v9_style_exact": mean(r.exact_recovery for r in v9),
        "deviation_subset_v10_exact": mean(r.exact_recovery for r in deviation_rows),
        "deviation_subset_v9_exact": mean(r.exact_recovery for r in v9_deviation),
        "deviation_precision": _pooled_precision(full),
        "deviation_recall": _pooled_recall(full),
        "family_recovery": family_recovery,
        "weak_source_recovery": mean(r.all_true_deviations_recovered for r in weak),
        "client_recovery": client_recovery,
        "balanced_recovery": balanced,
        "imbalanced_recovery": imbalanced,
        "high_noise_recovery": high_noise,
        "dual_both_recovery": dual_both,
        "dual_exact_spurious_count": dual_spurious_when_exact,
        "null_spurious_deviation_acceptance": mean(r.spurious_deviation_accepted for r in nulls),
        "anchor_contamination_full_spurious": contamination_full,
        "anchor_contamination_no_quarantine_spurious": contamination_noq,
        "high_noise_true_deviation_full_exact": consensus_full,
        "high_noise_true_deviation_split_veto_exact": consensus_split,
        "exact_harms": exact_harms,
        "ordinary_anchor_violations": sum(r.ordinary_anchor_violation_count for r in full),
        "quarantine_integrity_violations": sum(r.quarantine_integrity_violation_count for r in full),
        "role_integrity_violations": sum(r.role_integrity_violation_count for r in full),
        "source_qualification_violations": sum(r.source_qualification_violation_count for r in full),
        "pair_invariant_violations": sum(r.pair_invariant_violation_count for r in full),
        "client_consensus_violations": sum(r.client_consensus_violation_count for r in full),
        "v10_communication_median": median(r.communication_bytes for r in full),
        "v9_communication_median": median(r.communication_bytes for r in v9),
        "v10_runtime_median": median(r.runtime_seconds for r in full),
        "v9_runtime_median": median(r.runtime_seconds for r in v9),
    }

    criteria = {
        "A_integrity_600_fresh_conditions": bool(len(condition_keys) == 600 and len(rows) == 3600 and sorted({r.seed for r in rows}) == list(DEVELOPMENT_SEEDS) and SMOKE_SEED not in {r.seed for r in rows}),
        "B_ordinary_anchor_preservation": gate_values["ordinary_anchor_violations"] == 0,
        "C_quarantine_integrity": gate_values["quarantine_integrity_violations"] == 0,
        "D_null_spurious_deviation_le_002": gate_values["null_spurious_deviation_acceptance"] <= 0.02,
        "E_zero_exact_harms": exact_harms == 0,
        "F_overall_exact_gain_ge_002": gate_values["v10_exact"] >= gate_values["v9_style_exact"] + 0.02,
        "G_deviation_subset_exact_gain_ge_004": gate_values["deviation_subset_v10_exact"] >= gate_values["deviation_subset_v9_exact"] + 0.04,
        "H_deviation_precision_ge_099": gate_values["deviation_precision"] >= 0.99,
        "I_deviation_recall_ge_095": gate_values["deviation_recall"] >= 0.95,
        "J_each_main_family_recovery_ge_092": min(family_recovery.values()) >= 0.92,
        "K_weak_source_recovery_ge_085": gate_values["weak_source_recovery"] >= 0.85,
        "L_four_client_recovery_ge_090": client_recovery["4"] >= 0.90,
        "M_eight_client_recovery_ge_093": client_recovery["8"] >= 0.93,
        "N_sixteen_client_recovery_ge_095": client_recovery["16"] >= 0.95,
        "O_high_noise_recovery_ge_090": high_noise >= 0.90,
        "P_imbalance_gap_le_005": imbalanced >= balanced - 0.05,
        "Q_dual_both_ge_090_and_no_spurious": dual_both >= 0.90 and dual_spurious_when_exact == 0,
        "R_quarantine_mechanism_superiority": quarantine_superior,
        "S_client_consensus_mechanism_superiority": consensus_superior,
        "T_role_integrity": gate_values["role_integrity_violations"] == 0,
        "U_source_qualification_integrity": gate_values["source_qualification_violations"] == 0,
        "V_pair_invariant": gate_values["pair_invariant_violations"] == 0,
        "W_client_consensus_integrity": gate_values["client_consensus_violations"] == 0,
        "X_communication_le_185pct_v9": gate_values["v10_communication_median"] <= 1.85 * gate_values["v9_communication_median"],
        "Y_runtime_le_250pct_v9": gate_values["v10_runtime_median"] <= 2.50 * gate_values["v9_runtime_median"],
    }
    passed = all(criteria.values())
    result["gate_values"] = gate_values
    result["development_gate"] = {
        "evaluated": True,
        "criteria": criteria,
        "passed": passed,
        "status": "DEVELOPMENT-GO" if passed else "DEVELOPMENT-NO-GO",
        "scientific_boundary": (
            "A GO authorizes only a separately frozen v10 independent-validation protocol with a new untouched seed namespace. "
            "A NO-GO permanently spends 28101--28105 and forbids retuning v10 on them."
        ),
    }
    return result


def write_outputs(rows: Sequence[V10StudyRow], out_dir: Path, *, evaluate_gate: bool) -> None:
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
