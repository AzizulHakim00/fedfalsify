"""Infrastructure-only sharded recovery harness for frozen FedFalsify v9.

This module does not change the v9 scientific mechanism, benchmark grammar,
methods, or A--W thresholds. It only partitions the unchanged 600-condition
study by a new untouched seed namespace after the monolithic v9 workflow was
cancelled before sealing evidence.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import json
import math
from pathlib import Path
from typing import Iterable, Sequence

from . import scsv_v9_study as v9s

RECOVERY_SMOKE_SEED = 27001
RECOVERY_SEEDS = (27101, 27102, 27103, 27104, 27105)
SPENT_V9_SEEDS = (26101, 26102, 26103, 26104, 26105)
METHODS = v9s.METHODS

FROZEN_GATE_KEYS = (
    "A_integrity_600_fresh_conditions",
    "B_anchor_monotonicity",
    "C_null_spurious_deviation_le_002",
    "D_zero_exact_harms",
    "E_overall_exact_noninferior_001",
    "F_deviation_subset_exact_gain_ge_004",
    "G_deviation_precision_ge_099",
    "H_deviation_recall_ge_093",
    "I_each_main_family_recovery_ge_090",
    "J_weak_source_recovery_ge_080",
    "K_four_client_recovery_ge_088",
    "L_eight_client_recovery_ge_090",
    "M_sixteen_client_recovery_ge_094",
    "N_high_noise_recovery_ge_088",
    "O_imbalance_gap_le_006",
    "P_dual_both_ge_090_and_no_spurious",
    "Q_role_contrast_integrity",
    "R_source_qualification_integrity",
    "S_pair_invariant",
    "T_evidence_fusion_integrity",
    "U_mechanism_superiority",
    "V_communication_le_175pct_v8",
    "W_runtime_le_225pct_v8",
)

_INT_FIELDS = {
    "samples_per_client",
    "num_clients",
    "seed",
    "deviation_tp",
    "deviation_fp",
    "deviation_fn",
    "communication_bytes",
    "role_integrity_violation_count",
    "source_qualification_violation_count",
    "pair_invariant_violation_count",
    "evidence_fusion_violation_count",
}
_FLOAT_FIELDS = {
    "noise_ratio",
    "exact_recovery",
    "term_precision",
    "term_recall",
    "test_nmse",
    "train_mse",
    "deviation_precision",
    "deviation_recall",
    "all_true_deviations_recovered",
    "spurious_deviation_accepted",
    "runtime_seconds",
    "role_hypothesis_positive",
    "source_ambiguity",
    "global_ambiguity",
}


def _condition_key(row: v9s.V9StudyRow) -> tuple[object, ...]:
    return (
        row.family,
        float(row.noise_ratio),
        int(row.samples_per_client),
        int(row.num_clients),
        row.balance_profile,
        row.role_profile,
        int(row.seed),
    )


def _expected_condition_keys(seeds: Sequence[int]) -> set[tuple[object, ...]]:
    return {
        (family, float(noise), 100, int(num_clients), balance, role_profile, int(seed))
        for family, num_clients, balance, role_profile, noise, seed in v9s._scientific_conditions(seeds)
    }


def _run_conditions(
    conditions: Iterable[tuple[str, int, str, str, float, int]],
    *,
    methods: Sequence[str],
) -> list[v9s.V9StudyRow]:
    rows: list[v9s.V9StudyRow] = []
    for family, num_clients, balance, role_profile, noise, seed in conditions:
        generated = v9s.generate_v9_benchmark(
            family,
            nominal_samples_per_client=100,
            noise_ratio=noise,
            seed=seed,
            num_clients=num_clients,
            balance_profile=balance,
            role_profile=role_profile,
        )
        rows.extend(
            v9s._evaluate_condition(
                generated,
                requested_noise=noise,
                seed=seed,
                methods=methods,
            )
        )
    return rows


def run_recovery_shard(seed: int) -> list[v9s.V9StudyRow]:
    if seed not in RECOVERY_SEEDS:
        raise ValueError(f"recovery shard seed must be one of {RECOVERY_SEEDS}")
    conditions = tuple(v9s._scientific_conditions((seed,)))
    if len(conditions) != 120:
        raise RuntimeError(f"recovery shard expected 120 conditions, got {len(conditions)}")
    rows = _run_conditions(conditions, methods=METHODS)
    audit_rows(rows, expected_seeds=(seed,), expected_conditions=120, expected_rows=720)
    return rows


def run_recovery_smoke() -> list[v9s.V9StudyRow]:
    seed = RECOVERY_SMOKE_SEED
    conditions = (
        ("quadratic_role_v9", 4, "balanced", "single", 0.10, seed),
        ("linear_role_v9", 4, "balanced", "single", 0.10, seed),
        ("trig_role_v9", 4, "balanced", "single", 0.10, seed),
        ("interaction_role_v9", 4, "balanced", "single", 0.10, seed),
        ("null_role_v9", 8, "balanced", "none", 0.10, seed),
        ("diffuse_null_v9", 8, "balanced", "none", 0.10, seed),
        ("weak_source_role_v9", 8, "balanced", "quarter", 0.10, seed),
        ("dual_role_v9", 8, "balanced", "quarter", 0.10, seed),
    )
    rows = _run_conditions(conditions, methods=("scsv-rcef-v9-full",))
    if len(rows) != 8 or {row.seed for row in rows} != {RECOVERY_SMOKE_SEED}:
        raise RuntimeError("recovery engineering smoke isolation failed")
    return rows


def _write_rows(rows: Sequence[v9s.V9StudyRow], path: Path) -> None:
    if not rows:
        raise ValueError("cannot write empty recovery rows")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _parse_row(raw: dict[str, str]) -> v9s.V9StudyRow:
    converted: dict[str, object] = {}
    for key, value in raw.items():
        if key in _INT_FIELDS:
            converted[key] = int(value)
        elif key in _FLOAT_FIELDS:
            number = float(value)
            if not math.isfinite(number):
                raise ValueError(f"non-finite numeric field {key}: {value}")
            converted[key] = number
        else:
            converted[key] = value
    return v9s.V9StudyRow(**converted)


def read_rows(path: Path) -> list[v9s.V9StudyRow]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [_parse_row(item) for item in csv.DictReader(handle)]


def audit_rows(
    rows: Sequence[v9s.V9StudyRow],
    *,
    expected_seeds: Sequence[int],
    expected_conditions: int,
    expected_rows: int,
) -> None:
    if len(rows) != expected_rows:
        raise ValueError(f"expected {expected_rows} rows, got {len(rows)}")
    seed_set = {int(row.seed) for row in rows}
    if seed_set != set(expected_seeds):
        raise ValueError(f"seed mismatch: {sorted(seed_set)}")
    if RECOVERY_SMOKE_SEED in seed_set or set(SPENT_V9_SEEDS) & seed_set:
        raise ValueError("engineering or spent v9 seed found in recovery evidence")

    condition_keys = {_condition_key(row) for row in rows}
    expected_keys = _expected_condition_keys(tuple(expected_seeds))
    if len(condition_keys) != expected_conditions or condition_keys != expected_keys:
        raise ValueError(
            f"condition firewall failed: observed={len(condition_keys)} expected={len(expected_keys)}"
        )

    row_keys = {(_condition_key(row), row.method) for row in rows}
    if len(row_keys) != len(rows):
        raise ValueError("duplicate condition-method rows detected")
    for key in condition_keys:
        methods = {row.method for row in rows if _condition_key(row) == key}
        if methods != set(METHODS):
            raise ValueError(f"method coverage mismatch for {key}: {sorted(methods)}")


def summarize_recovery(rows: Sequence[v9s.V9StudyRow]) -> dict:
    audit_rows(
        rows,
        expected_seeds=RECOVERY_SEEDS,
        expected_conditions=600,
        expected_rows=3600,
    )

    old_development = v9s.DEVELOPMENT_SEEDS
    old_smoke = v9s.SMOKE_SEED
    try:
        # Infrastructure-only substitution: execute the already-frozen A--W
        # implementation verbatim with the replacement fresh seed namespace.
        v9s.DEVELOPMENT_SEEDS = RECOVERY_SEEDS
        v9s.SMOKE_SEED = RECOVERY_SMOKE_SEED
        result = v9s.summarize(rows, evaluate_gate=True)
    finally:
        v9s.DEVELOPMENT_SEEDS = old_development
        v9s.SMOKE_SEED = old_smoke

    criteria = result["development_gate"]["criteria"]
    if tuple(criteria.keys()) != FROZEN_GATE_KEYS:
        raise RuntimeError("recovery A--W gate-key parity failure")
    boundary = (
        "A GO authorizes only a separately frozen v9 independent-validation protocol with a new untouched seed namespace. "
        "A NO-GO permanently spends 27101--27105 and forbids retuning v9 on them."
    )
    result["status"] = "scsv-rcef-v9-infrastructure-recovery"
    result["development_gate"]["scientific_boundary"] = boundary
    return result


def write_shard(seed: int, out_dir: Path) -> None:
    rows = run_recovery_shard(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out_dir / f"rows-{seed}.csv"
    _write_rows(rows, rows_path)
    manifest = {
        "schema_version": 1,
        "status": "scsv-rcef-v9-recovery-shard",
        "seed": seed,
        "conditions": 120,
        "rows": 720,
        "methods": list(METHODS),
        "scientific_interpretation": "NONE-PARTIAL-SHARD",
    }
    (out_dir / f"manifest-{seed}.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )


def write_smoke(out_dir: Path) -> None:
    rows = run_recovery_smoke()
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_rows(rows, out_dir / "rows-smoke.csv")
    summary = {
        "schema_version": 1,
        "status": "scsv-rcef-v9-recovery-engineering-smoke",
        "seed": RECOVERY_SMOKE_SEED,
        "conditions": 8,
        "rows": 8,
        "methods": ["scsv-rcef-v9-full"],
        "development_gate": {"evaluated": False, "passed": None},
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )


def combine_shards(input_root: Path, out_dir: Path) -> None:
    files = sorted(input_root.rglob("rows-27*.csv"))
    if len(files) != 5:
        raise ValueError(f"expected five recovery shard row files, found {len(files)}")
    rows: list[v9s.V9StudyRow] = []
    for path in files:
        rows.extend(read_rows(path))
    summary = summarize_recovery(rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    ordered = sorted(
        rows,
        key=lambda row: (
            row.seed,
            row.family,
            row.num_clients,
            row.balance_profile,
            row.role_profile,
            row.noise_ratio,
            row.method,
        ),
    )
    _write_rows(ordered, out_dir / "rows.csv")
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    decision = {
        "schema_version": 1,
        "criteria": summary["development_gate"]["criteria"],
        "passed": summary["development_gate"]["passed"],
        "status": summary["development_gate"]["status"],
        "scientific_boundary": summary["development_gate"]["scientific_boundary"],
    }
    (out_dir / "decision.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    shard = subparsers.add_parser("shard")
    shard.add_argument("--seed", type=int, required=True)
    shard.add_argument("--out", type=Path, required=True)

    smoke = subparsers.add_parser("smoke")
    smoke.add_argument("--out", type=Path, required=True)

    combine = subparsers.add_parser("combine")
    combine.add_argument("--input-root", type=Path, required=True)
    combine.add_argument("--out", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "shard":
        write_shard(args.seed, args.out)
    elif args.command == "smoke":
        write_smoke(args.out)
    elif args.command == "combine":
        combine_shards(args.input_root, args.out)
    else:  # pragma: no cover
        raise RuntimeError(args.command)


if __name__ == "__main__":
    main()
