"""Frozen fresh-development study harness for FedFalsify SCSV-RCD v7."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from statistics import mean, median
from typing import Iterable, Sequence

import numpy as np

from .baselines import centralized_forward, fedfalsify_method
from .basis import CandidateEquation
from .client import FederatedFalsifierClient
from .scsv_v7 import SCSVRCDV7Output, scsv_rcd_v7_method
from .scsv_v7_benchmarks import (
    V7_DEVIATIONS,
    V7GeneratedBenchmark,
    generate_v7_benchmark,
    generate_v7_global_test_data,
    v7_catalog,
)

SMOKE_SEED = 24001
DEVELOPMENT_SEEDS = (24101, 24102, 24103, 24104, 24105)
SINGLE_FAMILIES = ("quadratic_role", "linear_role", "trig_role", "interaction_role")
METHODS = (
    "scsv-rcd-v7-full",
    "scsv-v6-full",
    "legacy-certificate",
    "centralized-forward",
    "scsv-rcd-v7-no-probe",
)


@dataclass(frozen=True)
class V7StudyRow:
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
    final_structure: str
    accepted_deviations: str
    anchor_structure: str
    bank_terms: str
    source_linked_candidates: str
    ambiguity_guard: float
    certificate_violation_count: int
    diagnostics_json: str
    expression: str
    stop_reason: str


def _validate_seeds(seeds: Sequence[int], *, smoke: bool) -> None:
    allowed = {SMOKE_SEED} if smoke else set(DEVELOPMENT_SEEDS)
    if set(seeds) != allowed:
        if smoke:
            raise ValueError("v7 engineering smoke must use seed 24001 only")
        raise ValueError("v7 development evidence must use exactly seeds 24101--24105")


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


def _diagnostic_json(output: SCSVRCDV7Output | None) -> str:
    if output is None:
        return "[]"
    return json.dumps(
        [asdict(item) for item in output.diagnostics],
        sort_keys=True,
        separators=(",", ":"),
    )


def _certificate_violations(output: SCSVRCDV7Output | None) -> int:
    if output is None:
        return 0
    accepted = set(output.accepted_deviations)
    violations = 0
    for item in output.diagnostics:
        if item.term not in accepted:
            continue
        if not (
            item.selector_passed
            and item.probe_passed
            and item.selector_outside_safe
            and item.probe_outside_safe
        ):
            violations += 1
    return violations


def _evaluate_candidate(
    generated: V7GeneratedBenchmark,
    candidate: CandidateEquation,
    *,
    method: str,
    seed: int,
    runtime_seconds: float,
    communication_bytes: int,
    stop_reason: str,
    output: SCSVRCDV7Output | None = None,
) -> V7StudyRow:
    catalog = v7_catalog()
    predicted = _candidate_terms(candidate)
    target = set(generated.target_terms)
    exact, precision, recall = _term_metrics(predicted, target)
    x_test, y_test = generate_v7_global_test_data(generated, seed=seed + 100_000)
    test_prediction = candidate.predict(x_test, catalog)
    pooled_x = np.concatenate([item.x for item in generated.clients], axis=0)
    pooled_y = np.concatenate([item.y for item in generated.clients], axis=0)
    train_prediction = candidate.predict(pooled_x, catalog)
    train_mse = float(np.mean((pooled_y - train_prediction) ** 2))

    predicted_deviations = predicted & set(V7_DEVIATIONS)
    true_deviations = set(generated.true_deviations)
    tp = len(predicted_deviations & true_deviations)
    fp = len(predicted_deviations - true_deviations)
    fn = len(true_deviations - predicted_deviations)
    dev_precision = tp / (tp + fp) if tp + fp else float(not true_deviations)
    dev_recall = tp / (tp + fn) if tp + fn else 1.0
    operational_structure = (
        tuple(output.final_structure) if output is not None else tuple(candidate.active_terms)
    )

    return V7StudyRow(
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
        final_structure=";".join(operational_structure),
        accepted_deviations=";".join(output.accepted_deviations) if output else "",
        anchor_structure=";".join(output.anchor_structure) if output else "",
        bank_terms=";".join(output.bank_terms) if output else "",
        source_linked_candidates=";".join(output.source_linked_candidates) if output else "",
        ambiguity_guard=float(output.ambiguity_guard) if output else 0.0,
        certificate_violation_count=_certificate_violations(output),
        diagnostics_json=_diagnostic_json(output),
        expression=candidate.expression(catalog),
        stop_reason=stop_reason,
    )


def _evaluate_condition(
    generated: V7GeneratedBenchmark,
    *,
    requested_noise: float,
    seed: int,
    methods: Sequence[str],
) -> list[V7StudyRow]:
    unknown = set(methods) - set(METHODS)
    if unknown:
        raise ValueError(f"unknown v7 methods: {sorted(unknown)}")
    rows: list[V7StudyRow] = []
    catalog = v7_catalog()
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)

    full_output: SCSVRCDV7Output | None = None
    if "scsv-rcd-v7-full" in methods or "scsv-v6-full" in methods:
        full_output = scsv_rcd_v7_method(
            generated.clients,
            catalog,
            seed=seed,
            target_mse=target_mse,
            min_repair_score=0.05,
            require_probe=True,
        )
        if "scsv-rcd-v7-full" in methods:
            rows.append(
                _evaluate_candidate(
                    generated,
                    full_output.candidate,
                    method="scsv-rcd-v7-full",
                    seed=seed,
                    runtime_seconds=full_output.runtime_seconds,
                    communication_bytes=full_output.communication_bytes,
                    stop_reason=full_output.stop_reason,
                    output=full_output,
                )
            )
        if "scsv-v6-full" in methods:
            rows.append(
                _evaluate_candidate(
                    generated,
                    full_output.anchor.candidate,
                    method="scsv-v6-full",
                    seed=seed,
                    runtime_seconds=full_output.anchor.runtime_seconds,
                    communication_bytes=full_output.anchor.communication_bytes,
                    stop_reason=full_output.anchor.stop_reason,
                    output=None,
                )
            )

    if "scsv-rcd-v7-no-probe" in methods:
        no_probe = scsv_rcd_v7_method(
            generated.clients,
            catalog,
            seed=seed,
            target_mse=target_mse,
            min_repair_score=0.05,
            require_probe=False,
        )
        rows.append(
            _evaluate_candidate(
                generated,
                no_probe.candidate,
                method="scsv-rcd-v7-no-probe",
                seed=seed,
                runtime_seconds=no_probe.runtime_seconds,
                communication_bytes=no_probe.communication_bytes,
                stop_reason=no_probe.stop_reason,
                output=no_probe,
            )
        )

    if "legacy-certificate" in methods:
        clients = [FederatedFalsifierClient(item, catalog) for item in generated.clients]
        legacy = fedfalsify_method(
            clients,
            catalog,
            max_terms=6,
            target_mse=target_mse,
            min_repair_score=0.05,
        )
        rows.append(
            _evaluate_candidate(
                generated,
                legacy.candidate,
                method="legacy-certificate",
                seed=seed,
                runtime_seconds=legacy.runtime_seconds,
                communication_bytes=legacy.communication_bytes,
                stop_reason=legacy.stop_reason,
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

    return [V7StudyRow(**{**asdict(row), "noise_ratio": float(requested_noise)}) for row in rows]


def _scientific_conditions(seeds: Sequence[int]):
    for family in SINGLE_FAMILIES:
        for num_clients in (4, 8, 16):
            for balance in ("balanced", "imbalanced"):
                for role_profile in ("single", "quarter"):
                    for noise in (0.10, 0.30):
                        for seed in seeds:
                            yield family, num_clients, balance, role_profile, noise, seed
    for num_clients in (4, 8, 16):
        for balance in ("balanced", "imbalanced"):
            for noise in (0.10, 0.30):
                for seed in seeds:
                    yield "null_role", num_clients, balance, "none", noise, seed
    for num_clients in (8, 16):
        for balance in ("balanced", "imbalanced"):
            for noise in (0.10, 0.30):
                for seed in seeds:
                    yield "dual_role", num_clients, balance, "quarter", noise, seed


def _smoke_conditions():
    return (
        ("quadratic_role", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("linear_role", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("trig_role", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("interaction_role", 4, "balanced", "single", 0.10, SMOKE_SEED),
        ("null_role", 4, "balanced", "none", 0.10, SMOKE_SEED),
        ("dual_role", 8, "balanced", "quarter", 0.10, SMOKE_SEED),
    )


def run_study(
    *,
    seeds: Sequence[int] = DEVELOPMENT_SEEDS,
    methods: Sequence[str] = METHODS,
    smoke: bool = False,
) -> list[V7StudyRow]:
    _validate_seeds(seeds, smoke=smoke)
    rows: list[V7StudyRow] = []
    conditions = _smoke_conditions() if smoke else _scientific_conditions(seeds)
    for family, num_clients, balance, role_profile, noise, seed in conditions:
        generated = generate_v7_benchmark(
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


def _mean(rows: Sequence[V7StudyRow], field: str) -> float:
    return float(mean(float(getattr(row, field)) for row in rows))


def _median(rows: Sequence[V7StudyRow], field: str) -> float:
    return float(median(float(getattr(row, field)) for row in rows))


def _key(row: V7StudyRow) -> tuple[object, ...]:
    return (
        row.family,
        row.noise_ratio,
        row.samples_per_client,
        row.num_clients,
        row.balance_profile,
        row.role_profile,
        row.seed,
    )


def summarize(rows: Sequence[V7StudyRow], *, evaluate_gate: bool = True) -> dict[str, object]:
    by_method: dict[str, list[V7StudyRow]] = {}
    for row in rows:
        by_method.setdefault(row.method, []).append(row)

    result: dict[str, object] = {
        "schema_version": 1,
        "status": "scsv-rcd-v7-development" if evaluate_gate else "scsv-rcd-v7-engineering-smoke",
        "rows": len(rows),
        "conditions": len({_key(row) for row in rows}),
        "seeds": sorted({row.seed for row in rows}),
        "methods": {},
    }
    for method, selected in sorted(by_method.items()):
        tp = sum(row.deviation_tp for row in selected)
        fp = sum(row.deviation_fp for row in selected)
        fn = sum(row.deviation_fn for row in selected)
        result["methods"][method] = {
            "runs": len(selected),
            "exact_recovery": _mean(selected, "exact_recovery"),
            "term_precision": _mean(selected, "term_precision"),
            "term_recall": _mean(selected, "term_recall"),
            "test_nmse": _mean(selected, "test_nmse"),
            "deviation_precision_pooled": tp / (tp + fp) if tp + fp else 1.0,
            "deviation_recall_pooled": tp / (tp + fn) if tp + fn else 1.0,
            "spurious_deviation_acceptance": _mean(selected, "spurious_deviation_accepted"),
            "runtime_seconds_median": _median(selected, "runtime_seconds"),
            "communication_bytes_median": _median(selected, "communication_bytes"),
        }

    if not evaluate_gate:
        result["development_gate"] = {
            "evaluated": False,
            "passed": None,
            "scientific_boundary": "Engineering smoke cannot evaluate v7 scientific gates.",
        }
        return result

    required = set(METHODS)
    missing = required - set(by_method)
    if missing:
        raise ValueError(f"missing v7 methods: {sorted(missing)}")
    full = by_method["scsv-rcd-v7-full"]
    v6 = by_method["scsv-v6-full"]
    if len(full) != 580 or len(v6) != 580:
        raise ValueError(f"expected 580 matched full/v6 conditions, got {len(full)}/{len(v6)}")
    full_map = {_key(row): row for row in full}
    v6_map = {_key(row): row for row in v6}
    if set(full_map) != set(v6_map):
        raise ValueError("v7/v6 condition keys do not match")

    null_rows = [row for row in full if row.family == "null_role"]
    deviation_rows = [row for row in full if row.family != "null_role"]
    single_rows = [row for row in full if row.family in SINGLE_FAMILIES]
    dual_rows = [row for row in full if row.family == "dual_role"]
    tp = sum(row.deviation_tp for row in full)
    fp = sum(row.deviation_fp for row in full)
    fn = sum(row.deviation_fn for row in full)
    pooled_precision = tp / (tp + fp) if tp + fp else 1.0
    pooled_recall = tp / (tp + fn) if tp + fn else 1.0
    exact_harms = sum(
        v6_map[key].exact_recovery == 1.0 and row.exact_recovery == 0.0
        for key, row in full_map.items()
    )

    family_recovery = {
        family: _mean([row for row in single_rows if row.family == family], "all_true_deviations_recovered")
        for family in SINGLE_FAMILIES
    }
    by_clients = {
        clients: _mean([row for row in single_rows if row.num_clients == clients], "all_true_deviations_recovered")
        for clients in (4, 8, 16)
    }
    balanced = _mean(
        [row for row in single_rows if row.balance_profile == "balanced"],
        "all_true_deviations_recovered",
    )
    imbalanced = _mean(
        [row for row in single_rows if row.balance_profile == "imbalanced"],
        "all_true_deviations_recovered",
    )
    high_noise = _mean(
        [row for row in single_rows if row.noise_ratio == 0.30],
        "all_true_deviations_recovered",
    )
    dual_both = _mean(dual_rows, "all_true_deviations_recovered")
    dual_exact_rows = [row for row in dual_rows if row.all_true_deviations_recovered == 1.0]
    dual_exact_spurious = sum(row.spurious_deviation_accepted > 0 for row in dual_exact_rows)
    cert_violations = sum(row.certificate_violation_count for row in full)
    anchor_preserved = all(
        set(filter(None, row.anchor_structure.split(";"))).issubset(
            set(filter(None, row.final_structure.split(";")))
        )
        for row in full
    )

    criteria = {
        "A_integrity_580_fresh_conditions": (
            len(full) == 580
            and {row.seed for row in full} == set(DEVELOPMENT_SEEDS)
            and SMOKE_SEED not in {row.seed for row in full}
            and len(full_map) == 580
            and all(np.isfinite(row.test_nmse) and np.isfinite(row.runtime_seconds) for row in full)
        ),
        "B_shared_anchor_preserved": anchor_preserved,
        "C_null_spurious_deviation_le_005": _mean(null_rows, "spurious_deviation_accepted") <= 0.05,
        "D_zero_exact_harms": exact_harms == 0,
        "E_overall_exact_noninferior_001": _mean(full, "exact_recovery") >= _mean(v6, "exact_recovery") - 0.01,
        "F_deviation_subset_exact_gain_ge_003": (
            _mean(deviation_rows, "exact_recovery")
            >= _mean([row for row in v6 if row.family != "null_role"], "exact_recovery") + 0.03
        ),
        "G_deviation_precision_ge_095": pooled_precision >= 0.95,
        "H_deviation_recall_ge_090": pooled_recall >= 0.90,
        "I_each_family_recovery_ge_085": all(value >= 0.85 for value in family_recovery.values()),
        "J_four_client_recovery_ge_085": by_clients[4] >= 0.85,
        "K_eight_client_recovery_ge_090": by_clients[8] >= 0.90,
        "L_sixteen_client_recovery_ge_090": by_clients[16] >= 0.90,
        "M_imbalance_gap_le_008": imbalanced >= balanced - 0.08,
        "N_high_noise_recovery_ge_085": high_noise >= 0.85,
        "O_dual_both_ge_075_and_no_spurious_in_exact": dual_both >= 0.75 and dual_exact_spurious == 0,
        "P_certificate_integrity": cert_violations == 0,
        "Q_communication_le_150pct_v6": _median(full, "communication_bytes") <= 1.50 * _median(v6, "communication_bytes"),
        "R_runtime_le_200pct_v6": _median(full, "runtime_seconds") <= 2.00 * _median(v6, "runtime_seconds"),
    }
    result["gate_values"] = {
        "v7_exact": _mean(full, "exact_recovery"),
        "v6_exact": _mean(v6, "exact_recovery"),
        "deviation_subset_v7_exact": _mean(deviation_rows, "exact_recovery"),
        "deviation_subset_v6_exact": _mean(
            [row for row in v6 if row.family != "null_role"], "exact_recovery"
        ),
        "deviation_precision": pooled_precision,
        "deviation_recall": pooled_recall,
        "family_recovery": family_recovery,
        "client_recovery": by_clients,
        "balanced_recovery": balanced,
        "imbalanced_recovery": imbalanced,
        "high_noise_recovery": high_noise,
        "dual_both_recovery": dual_both,
        "dual_exact_spurious_count": dual_exact_spurious,
        "exact_harms": exact_harms,
        "certificate_violations": cert_violations,
        "null_spurious_deviation_acceptance": _mean(null_rows, "spurious_deviation_accepted"),
        "v7_communication_median": _median(full, "communication_bytes"),
        "v6_communication_median": _median(v6, "communication_bytes"),
        "v7_runtime_median": _median(full, "runtime_seconds"),
        "v6_runtime_median": _median(v6, "runtime_seconds"),
    }
    result["development_gate"] = {
        "evaluated": True,
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
        "status": "DEVELOPMENT-GO" if all(criteria.values()) else "DEVELOPMENT-NO-GO",
        "scientific_boundary": (
            "A GO authorizes only a separately frozen independent v7 validation with a new seed namespace. "
            "A NO-GO permanently spends 24101--24105 and forbids retuning v7 on them."
        ),
    }
    return result


def write_csv(rows: Sequence[V7StudyRow], path: Path) -> None:
    if not rows:
        raise ValueError("cannot write empty v7 study")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--output", type=Path, default=Path("results/scsv_v7/rows.csv"))
    parser.add_argument("--summary", type=Path, default=Path("results/scsv_v7/summary.json"))
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
