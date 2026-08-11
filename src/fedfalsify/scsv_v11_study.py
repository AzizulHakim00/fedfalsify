"""Governed smoke/development harness for FedFalsify SCSV-ELRC v11."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from statistics import mean, median
from typing import Sequence

import numpy as np

from .basis import CandidateEquation
from .scsv_v10 import scsv_aqcc_v10_method
from .scsv_v10_benchmarks import (
    SINGLE_FAMILIES_V10,
    V10_DEVIATIONS,
    generate_v10_benchmark,
    generate_v10_global_test_data,
    v10_catalog,
)
from .scsv_v11 import SCSVELRCV11Output, scsv_elrc_v11_method

SMOKE_SEED = 29001
DEVELOPMENT_SEEDS = (29101, 29102, 29103, 29104, 29105)
METHODS = ("scsv-elrc-v11-full", "scsv-aqcc-v10-frozen-comparator")
NULL_FAMILIES = {"null_role_v10", "anchor_contamination_null_v10"}


@dataclass(frozen=True)
class V11StudyRow:
    family: str
    noise_ratio: float
    num_clients: int
    balance_profile: str
    role_profile: str
    seed: int
    method: str
    exact_recovery: float
    term_precision: float
    term_recall: float
    test_nmse: float
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
    final_structure: str
    diagnostics_json: str
    integrity_violations: int
    expression: str
    stop_reason: str


def _validate_seeds(seeds: Sequence[int], *, smoke: bool) -> None:
    expected = {SMOKE_SEED} if smoke else set(DEVELOPMENT_SEEDS)
    if set(seeds) != expected:
        raise ValueError(
            "v11 smoke must use 29001 only"
            if smoke
            else "v11 development must use exactly 29101--29105"
        )
    if 28001 in set(seeds) or set(seeds) & {28101, 28102, 28103, 28104, 28105}:
        raise ValueError("v11 cannot reuse v10 smoke/development seeds")
    if any(11001 <= int(seed) < 12000 for seed in seeds):
        raise ValueError("v11 cannot touch reserved 11001+ final-confirmation namespace")


def _candidate_terms(candidate: CandidateEquation) -> set[str]:
    return {
        term
        for term, coefficient in zip(candidate.active_terms, candidate.coefficients)
        if term != "1" and abs(float(coefficient)) >= 1e-3
    }


def _metrics(predicted: set[str], target: set[str]) -> tuple[float, float, float]:
    common = predicted & target
    precision = len(common) / len(predicted) if predicted else float(not target)
    recall = len(common) / len(target) if target else 1.0
    return float(predicted == target), float(precision), float(recall)


def _v11_integrity(output: SCSVELRCV11Output) -> int:
    violations = 0
    final = set(output.final_structure)
    if not set(output.ordinary_anchor_structure).issubset(final):
        violations += 1
    accepted = set(output.accepted_deviations)
    diag = {item.term: item for item in output.diagnostics}
    for term in accepted:
        item = diag.get(term)
        if item is None:
            violations += 1
            continue
        if not (
            item.weak_heredity_passed
            and item.role_admissible
            and item.role_client_ids
            and item.outside_client_ids
            and item.pair_invariant
            and item.selector_outside_safe
            and item.probe_outside_safe
            and item.pooled_delta is not None
            and item.pooled_delta < 0.0
            and item.client_median_gain is not None
            and item.client_median_gain > 0.0
        ):
            violations += 1
        client_count = len(item.role_client_ids) + len(item.outside_client_ids)
        if len(item.role_client_ids) > max(1, client_count // 2):
            violations += 1
    for term in output.quarantined_anchor_exceptions:
        if term in final and term not in accepted:
            violations += 1
    return int(violations)


def _evaluate(
    generated,
    candidate: CandidateEquation,
    *,
    method: str,
    seed: int,
    requested_noise: float,
    runtime_seconds: float,
    communication_bytes: int,
    stop_reason: str,
    output11: SCSVELRCV11Output | None = None,
    accepted_deviations: Sequence[str] = (),
) -> V11StudyRow:
    catalog = v10_catalog()
    predicted = _candidate_terms(candidate)
    target = set(generated.target_terms)
    exact, precision, recall = _metrics(predicted, target)
    x_test, y_test = generate_v10_global_test_data(generated, seed=seed + 100_000)
    prediction = candidate.predict(x_test, catalog)
    mse = float(np.mean((np.asarray(y_test) - np.asarray(prediction)) ** 2))
    nmse = float(mse / max(float(np.var(y_test)), 1e-12))

    pred_dev = predicted & set(V10_DEVIATIONS)
    true_dev = set(generated.true_deviations)
    tp = len(pred_dev & true_dev)
    fp = len(pred_dev - true_dev)
    fn = len(true_dev - pred_dev)
    dev_precision = tp / (tp + fp) if tp + fp else float(not true_dev)
    dev_recall = tp / (tp + fn) if tp + fn else 1.0

    diagnostics_json = "[]"
    integrity = 0
    if output11 is not None:
        diagnostics_json = json.dumps(
            [asdict(item) for item in output11.diagnostics],
            sort_keys=True,
            separators=(",", ":"),
        )
        integrity = _v11_integrity(output11)

    return V11StudyRow(
        family=generated.family,
        noise_ratio=float(requested_noise),
        num_clients=int(generated.num_clients),
        balance_profile=str(generated.balance_profile),
        role_profile=str(generated.role_profile),
        seed=int(seed),
        method=method,
        exact_recovery=exact,
        term_precision=precision,
        term_recall=recall,
        test_nmse=nmse,
        deviation_tp=int(tp),
        deviation_fp=int(fp),
        deviation_fn=int(fn),
        deviation_precision=float(dev_precision),
        deviation_recall=float(dev_recall),
        all_true_deviations_recovered=float(true_dev.issubset(pred_dev)),
        spurious_deviation_accepted=float(bool(pred_dev - true_dev)),
        runtime_seconds=float(runtime_seconds),
        communication_bytes=int(communication_bytes),
        discovered_terms=";".join(sorted(predicted)),
        accepted_deviations=";".join(accepted_deviations),
        final_structure=";".join(candidate.active_terms),
        diagnostics_json=diagnostics_json,
        integrity_violations=int(integrity),
        expression=candidate.expression(catalog),
        stop_reason=stop_reason,
    )


def _condition_rows(generated, *, seed: int, noise: float) -> list[V11StudyRow]:
    catalog = v10_catalog()
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)

    output11 = scsv_elrc_v11_method(
        generated.clients,
        catalog,
        seed=seed,
        target_mse=target_mse,
        min_repair_score=0.05,
    )
    output10 = scsv_aqcc_v10_method(
        generated.clients,
        catalog,
        seed=seed,
        target_mse=target_mse,
        min_repair_score=0.05,
        quarantine_anchor=True,
        split_veto=False,
    )
    return [
        _evaluate(
            generated,
            output11.candidate,
            method="scsv-elrc-v11-full",
            seed=seed,
            requested_noise=noise,
            runtime_seconds=output11.runtime_seconds,
            communication_bytes=output11.communication_bytes,
            stop_reason=output11.stop_reason,
            output11=output11,
            accepted_deviations=output11.accepted_deviations,
        ),
        _evaluate(
            generated,
            output10.candidate,
            method="scsv-aqcc-v10-frozen-comparator",
            seed=seed,
            requested_noise=noise,
            runtime_seconds=output10.runtime_seconds,
            communication_bytes=output10.communication_bytes,
            stop_reason=output10.stop_reason,
            accepted_deviations=output10.accepted_deviations,
        ),
    ]


def _scientific_conditions(seeds: Sequence[int]):
    for family in SINGLE_FAMILIES_V10:
        for num_clients in (4, 8, 16):
            roles = ("single",) if num_clients == 4 else ("single", "quarter")
            for balance in ("balanced", "imbalanced"):
                for role in roles:
                    for noise in (0.10, 0.30):
                        for seed in seeds:
                            yield family, num_clients, balance, role, noise, seed
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
        ("trig_role_v10", 4, "balanced", "single", 0.30, SMOKE_SEED),
        ("null_role_v10", 8, "balanced", "none", 0.10, SMOKE_SEED),
        ("anchor_contamination_null_v10", 8, "balanced", "none", 0.30, SMOKE_SEED),
        ("weak_source_role_v10", 8, "balanced", "quarter", 0.10, SMOKE_SEED),
        ("dual_role_v10", 8, "imbalanced", "quarter", 0.30, SMOKE_SEED),
    )


def run_study(*, seeds: Sequence[int], smoke: bool) -> list[V11StudyRow]:
    _validate_seeds(seeds, smoke=smoke)
    conditions = _smoke_conditions() if smoke else tuple(_scientific_conditions(seeds))
    if not smoke and len(conditions) != 600:
        raise RuntimeError(f"v11 condition firewall expected 600, got {len(conditions)}")
    rows: list[V11StudyRow] = []
    for family, clients, balance, role, noise, seed in conditions:
        generated = generate_v10_benchmark(
            family,
            nominal_samples_per_client=100,
            noise_ratio=noise,
            seed=seed,
            num_clients=clients,
            balance_profile=balance,
            role_profile=role,
        )
        rows.extend(_condition_rows(generated, seed=seed, noise=noise))
    return rows


def _subset(rows: Sequence[V11StudyRow], method: str) -> list[V11StudyRow]:
    return [row for row in rows if row.method == method]


def _pooled_precision(rows: Sequence[V11StudyRow]) -> float:
    tp = sum(row.deviation_tp for row in rows)
    fp = sum(row.deviation_fp for row in rows)
    return float(tp / (tp + fp)) if tp + fp else 1.0


def _pooled_recall(rows: Sequence[V11StudyRow]) -> float:
    tp = sum(row.deviation_tp for row in rows)
    fn = sum(row.deviation_fn for row in rows)
    return float(tp / (tp + fn)) if tp + fn else 1.0


def summarize(rows: Sequence[V11StudyRow], *, evaluate_gate: bool) -> dict:
    result = {
        "schema_version": 1,
        "status": "scsv-elrc-v11-development" if evaluate_gate else "scsv-elrc-v11-engineering-smoke",
        "rows": len(rows),
        "conditions": len(rows) // 2,
        "seeds": sorted({row.seed for row in rows}),
        "methods": {},
    }
    for method in METHODS:
        subset = _subset(rows, method)
        result["methods"][method] = {
            "runs": len(subset),
            "exact_recovery": mean(row.exact_recovery for row in subset),
            "term_precision": mean(row.term_precision for row in subset),
            "term_recall": mean(row.term_recall for row in subset),
            "test_nmse": mean(row.test_nmse for row in subset),
            "deviation_precision_pooled": _pooled_precision(subset),
            "deviation_recall_pooled": _pooled_recall(subset),
            "spurious_deviation_acceptance": mean(row.spurious_deviation_accepted for row in subset),
            "runtime_seconds_median": median(row.runtime_seconds for row in subset),
            "communication_bytes_median": median(row.communication_bytes for row in subset),
        }
    if not evaluate_gate:
        return result

    v11 = _subset(rows, METHODS[0])
    v10 = _subset(rows, METHODS[1])
    key = lambda r: (
        r.family, r.noise_ratio, r.num_clients, r.balance_profile, r.role_profile, r.seed
    )
    v10_map = {key(row): row for row in v10}
    exact_harms = sum(
        1 for row in v11
        if v10_map[key(row)].exact_recovery == 1.0 and row.exact_recovery == 0.0
    )
    deviation11 = [r for r in v11 if r.family not in NULL_FAMILIES]
    deviation10 = [r for r in v10 if r.family not in NULL_FAMILIES]
    main11 = [r for r in v11 if r.family in set(SINGLE_FAMILIES_V10)]
    main10 = [r for r in v10 if r.family in set(SINGLE_FAMILIES_V10)]
    family_recovery = {
        family: mean(r.all_true_deviations_recovered for r in main11 if r.family == family)
        for family in SINGLE_FAMILIES_V10
    }
    clients_recovery = {
        str(n): mean(r.all_true_deviations_recovered for r in main11 if r.num_clients == n)
        for n in (4, 8, 16)
    }
    high11 = mean(r.all_true_deviations_recovered for r in main11 if r.noise_ratio == 0.30)
    high10 = mean(r.all_true_deviations_recovered for r in main10 if r.noise_ratio == 0.30)
    weak11 = mean(
        r.all_true_deviations_recovered for r in v11 if r.family == "weak_source_role_v10"
    )
    dual11 = mean(
        r.all_true_deviations_recovered for r in v11 if r.family == "dual_role_v10"
    )
    null_spurious = mean(
        r.spurious_deviation_accepted for r in v11 if r.family in NULL_FAMILIES
    )
    overall11 = mean(r.exact_recovery for r in v11)
    overall10 = mean(r.exact_recovery for r in v10)
    dev_exact11 = mean(r.exact_recovery for r in deviation11)
    dev_exact10 = mean(r.exact_recovery for r in deviation10)
    comm_ratio = median(r.communication_bytes for r in v11) / max(
        median(r.communication_bytes for r in v10), 1
    )
    runtime_ratio = median(r.runtime_seconds for r in v11) / max(
        median(r.runtime_seconds for r in v10), 1e-9
    )
    integrity = sum(r.integrity_violations for r in v11)

    values = {
        "v11_exact": overall11,
        "v10_fresh_comparator_exact": overall10,
        "deviation_subset_v11_exact": dev_exact11,
        "deviation_subset_v10_exact": dev_exact10,
        "deviation_precision": _pooled_precision(v11),
        "deviation_recall": _pooled_recall(v11),
        "family_recovery": family_recovery,
        "client_recovery": clients_recovery,
        "high_noise_recovery": high11,
        "high_noise_v10_recovery": high10,
        "weak_source_recovery": weak11,
        "dual_both_recovery": dual11,
        "null_spurious_deviation_acceptance": null_spurious,
        "exact_harms": exact_harms,
        "integrity_violations": integrity,
        "communication_ratio_vs_v10": comm_ratio,
        "runtime_ratio_vs_v10": runtime_ratio,
    }
    criteria = {
        "A_integrity_600_fresh_conditions": len(v11) == 600 and sorted({r.seed for r in v11}) == list(DEVELOPMENT_SEEDS),
        "B_zero_integrity_violations": integrity == 0,
        "C_deviation_precision_ge_099": values["deviation_precision"] >= 0.99,
        "D_deviation_recall_ge_095": values["deviation_recall"] >= 0.95,
        "E_null_spurious_le_002": null_spurious <= 0.02,
        "F_zero_exact_harms": exact_harms == 0,
        "G_overall_exact_gain_ge_002": overall11 >= overall10 + 0.02,
        "H_deviation_subset_exact_gain_ge_004": dev_exact11 >= dev_exact10 + 0.04,
        "I_each_main_family_recovery_ge_092": min(family_recovery.values()) >= 0.92,
        "J_four_client_recovery_ge_090": clients_recovery["4"] >= 0.90,
        "K_eight_client_recovery_ge_093": clients_recovery["8"] >= 0.93,
        "L_sixteen_client_recovery_ge_095": clients_recovery["16"] >= 0.95,
        "M_high_noise_recovery_ge_090_and_gain_ge_003": high11 >= 0.90 and high11 >= high10 + 0.03,
        "N_weak_source_recovery_ge_085": weak11 >= 0.85,
        "O_dual_both_recovery_ge_090": dual11 >= 0.90,
        "P_communication_le_8x_v10": comm_ratio <= 8.0,
        "Q_runtime_le_8x_v10": runtime_ratio <= 8.0,
    }
    result["gate_values"] = values
    result["development_gate"] = {
        "evaluated": True,
        "passed": all(criteria.values()),
        "criteria": criteria,
        "status": "DEVELOPMENT-GO" if all(criteria.values()) else "DEVELOPMENT-NO-GO",
        "scientific_boundary": (
            "GO authorizes only a separately frozen independent-validation protocol "
            "with a new untouched seed namespace. NO-GO permanently spends 29101--29105."
        ),
    }
    return result


def write_outputs(rows: Sequence[V11StudyRow], output_dir: Path, *, evaluate_gate: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)
    (output_dir / "summary.json").write_text(
        json.dumps(summarize(rows, evaluate_gate=evaluate_gate), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    seeds = (SMOKE_SEED,) if args.smoke else DEVELOPMENT_SEEDS
    rows = run_study(seeds=seeds, smoke=args.smoke)
    write_outputs(rows, args.output_dir, evaluate_gate=not args.smoke)


if __name__ == "__main__":
    main()
