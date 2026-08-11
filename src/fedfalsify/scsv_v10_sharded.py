"""Infrastructure-only sharding for the frozen v10 development study."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, fields
import json
from pathlib import Path

from .scsv_v10_benchmarks import generate_v10_benchmark
from .scsv_v10_study import (
    DEVELOPMENT_SEEDS,
    METHODS,
    SMOKE_SEED,
    V10StudyRow,
    _evaluate_condition,
    _scientific_conditions,
    summarize,
)

SPENT_SEEDS = {
    19101, 19102, 19103, 19104, 19105,
    20101, 20102, 20103, 20104, 20105,
    24101, 24102, 24103, 24104, 24105,
    25101, 25102, 25103, 25104, 25105,
    26101, 26102, 26103, 26104, 26105,
    27101, 27102, 27103, 27104, 27105,
}


def _row_from_csv(data: dict[str, str]) -> V10StudyRow:
    int_fields = {
        "samples_per_client", "num_clients", "seed", "deviation_tp", "deviation_fp", "deviation_fn",
        "communication_bytes", "ordinary_anchor_violation_count", "quarantine_integrity_violation_count",
        "role_integrity_violation_count", "source_qualification_violation_count",
        "pair_invariant_violation_count", "client_consensus_violation_count",
    }
    float_fields = {
        "noise_ratio", "exact_recovery", "term_precision", "term_recall", "test_nmse", "train_mse",
        "deviation_precision", "deviation_recall", "all_true_deviations_recovered",
        "spurious_deviation_accepted", "runtime_seconds",
    }
    values = {}
    for field in fields(V10StudyRow):
        value = data[field.name]
        if field.name in int_fields:
            values[field.name] = int(value)
        elif field.name in float_fields:
            values[field.name] = float(value)
        else:
            values[field.name] = value
    return V10StudyRow(**values)


def run_shard(seed: int, out_dir: Path) -> None:
    if seed not in DEVELOPMENT_SEEDS:
        raise ValueError(f"v10 shard seed must be one of {DEVELOPMENT_SEEDS}")
    if seed in SPENT_SEEDS or seed == SMOKE_SEED:
        raise ValueError("spent/smoke seed cannot be used for v10 fresh shard")
    conditions = tuple(_scientific_conditions((seed,)))
    if len(conditions) != 120 or len(set(conditions)) != 120:
        raise RuntimeError(f"v10 shard geometry expected 120 unique conditions, got {len(set(conditions))}")
    rows: list[V10StudyRow] = []
    for family, num_clients, balance, role_profile, noise, condition_seed in conditions:
        generated = generate_v10_benchmark(
            family,
            nominal_samples_per_client=100,
            noise_ratio=noise,
            seed=condition_seed,
            num_clients=num_clients,
            balance_profile=balance,
            role_profile=role_profile,
        )
        rows.extend(_evaluate_condition(generated, requested_noise=noise, seed=condition_seed, methods=METHODS))
    if len(rows) != 720:
        raise RuntimeError(f"v10 shard expected 720 rows, got {len(rows)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"rows-{seed}.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    manifest = {
        "schema_version": 1,
        "run_mode": "fresh-scsv-aqcc-v10-development-shard",
        "seed": seed,
        "conditions": 120,
        "rows": 720,
        "methods": list(METHODS),
    }
    (out_dir / f"manifest-{seed}.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def combine(input_root: Path, out_dir: Path) -> None:
    row_files = sorted(input_root.glob("rows-281*.csv"))
    if len(row_files) != 5:
        raise RuntimeError(f"v10 combine requires five shard row files, found {len(row_files)}")
    rows: list[V10StudyRow] = []
    for path in row_files:
        with path.open(encoding="utf-8") as handle:
            shard = [_row_from_csv(item) for item in csv.DictReader(handle)]
        if len(shard) != 720:
            raise RuntimeError(f"bad v10 shard row count for {path}: {len(shard)}")
        rows.extend(shard)
    if len(rows) != 3600:
        raise RuntimeError(f"v10 combine expected 3600 rows, got {len(rows)}")
    seeds = {row.seed for row in rows}
    if seeds != set(DEVELOPMENT_SEEDS):
        raise RuntimeError(f"v10 combine seed mismatch: {sorted(seeds)}")
    unique = {
        (r.family, r.noise_ratio, r.samples_per_client, r.num_clients, r.balance_profile, r.role_profile, r.seed, r.method)
        for r in rows
    }
    if len(unique) != 3600:
        raise RuntimeError(f"v10 combine duplicate rows: {3600 - len(unique)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    summary = summarize(rows, evaluate_gate=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
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
    sub = parser.add_subparsers(dest="command", required=True)
    shard = sub.add_parser("shard")
    shard.add_argument("--seed", type=int, required=True)
    shard.add_argument("--out", type=Path, required=True)
    agg = sub.add_parser("combine")
    agg.add_argument("--input-root", type=Path, required=True)
    agg.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "shard":
        run_shard(args.seed, args.out)
    else:
        combine(args.input_root, args.out)


if __name__ == "__main__":
    main()
