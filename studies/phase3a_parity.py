"""Engineering-only Phase-3A parity audit.

This runner checks numerical equivalence only. It does not compute scientific
performance, benchmark recovery, or GO/NO-GO metrics.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path

import numpy as np

from fedfalsify.benchmarks import BenchmarkClientDataset
from fedfalsify.crossfit_redesign import partition_clients
from fedfalsify.crossfit_surrogate import split_selector_probe
from fedfalsify.linear_algebra import RankPolicy, fit_from_sufficient_stats
from fedfalsify.phase3_cache import build_phase3_packet_cache
from fedfalsify.scsv_diagnostic import _build_packets as predecessor_build_packets
from fedfalsify.scsv_v10_benchmarks import generate_v10_benchmark, v10_catalog
from fedfalsify.scsv_v11_study import SMOKE_SEED, _smoke_conditions
from fedfalsify.sufficient_stats import aggregate_packets, packet_from_dataset


@dataclass(frozen=True)
class Phase3AParityRecord:
    family: str
    noise_ratio: float
    num_clients: int
    balance_profile: str
    role_profile: str
    seed: int
    packet_equivalent: bool
    aggregate_equivalent: bool
    least_squares_equivalent: bool
    max_abs_gram_error: float
    max_abs_target_error: float
    max_abs_sse_error: float


@dataclass(frozen=True)
class Phase3AParityReport:
    schema_version: int
    seed: int
    conditions: int
    passed: bool
    records: tuple[Phase3AParityRecord, ...]


def _max_abs(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(a, dtype=float) - np.asarray(b, dtype=float))))


def _packet_group_errors(old_group, new_group) -> tuple[bool, float, float]:
    if len(old_group) != len(new_group):
        return False, float("inf"), float("inf")
    ok = True
    max_gram = 0.0
    max_target = 0.0
    for old, new in zip(old_group, new_group):
        gram_error = _max_abs(old.gram, new.gram)
        target_error = _max_abs(old.target, new.target)
        max_gram = max(max_gram, gram_error)
        max_target = max(max_target, target_error)
        ok = bool(
            ok
            and old.client_id == new.client_id
            and old.support == new.support
            and old.terms == new.terms
            and old.observed_support == new.observed_support
            and abs(float(old.target_energy) - float(new.target_energy)) <= 1e-12
            and np.allclose(old.gram, new.gram, rtol=0.0, atol=1e-12)
            and np.allclose(old.target, new.target, rtol=0.0, atol=1e-12)
        )
    return ok, max_gram, max_target


def _audit_condition(condition) -> Phase3AParityRecord:
    family, num_clients, balance, role, noise, seed = condition
    if int(seed) != 29001:
        raise ValueError("Phase-3A parity audit permits seed 29001 only")

    generated = generate_v10_benchmark(
        family,
        nominal_samples_per_client=100,
        noise_ratio=noise,
        seed=seed,
        num_clients=num_clients,
        balance_profile=balance,
        role_profile=role,
    )
    catalog = v10_catalog()
    all_terms = tuple(catalog.names())

    partitions = partition_clients(generated.clients, seed=seed, validation_fraction=0.30)
    selectors, probes = split_selector_probe(partitions, seed=seed)
    old_discovery, old_selector, old_probe, _ = predecessor_build_packets(
        partitions, selectors, probes, catalog, all_terms
    )
    cache = build_phase3_packet_cache(generated.clients, catalog, all_terms, seed=seed)

    packet_ok = True
    max_gram = 0.0
    max_target = 0.0
    for old_group, new_group in (
        (old_discovery, cache.discovery),
        (old_selector, cache.selector),
        (old_probe, cache.probe),
    ):
        group_ok, gram_error, target_error = _packet_group_errors(old_group, new_group)
        packet_ok = bool(packet_ok and group_ok)
        max_gram = max(max_gram, gram_error)
        max_target = max(max_target, target_error)

    aggregate = aggregate_packets(cache.discovery)
    pooled_discovery = BenchmarkClientDataset(
        "pooled-discovery",
        np.concatenate([item.discovery.x for item in partitions], axis=0),
        np.concatenate([item.discovery.y for item in partitions], axis=0),
    )
    direct = packet_from_dataset(pooled_discovery, catalog, all_terms)
    aggregate_ok = bool(
        aggregate.support == direct.support
        and aggregate.terms == direct.terms
        and aggregate.observed_support == direct.observed_support
        and np.allclose(aggregate.gram, direct.gram, rtol=1e-12, atol=1e-10)
        and np.allclose(aggregate.target, direct.target, rtol=1e-12, atol=1e-10)
        and abs(aggregate.target_energy - direct.target_energy) <= 1e-10
    )
    max_gram = max(max_gram, _max_abs(aggregate.gram, direct.gram))
    max_target = max(max_target, _max_abs(aggregate.target, direct.target))

    selected_terms = ("1", "x1", "x3^2")
    fit = fit_from_sufficient_stats(aggregate, selected_terms, RankPolicy())
    design = catalog.matrix(pooled_discovery.x, selected_terms)
    response = np.asarray(pooled_discovery.y, dtype=float)
    beta_central, *_ = np.linalg.lstsq(design, response, rcond=None)
    residual = response - design @ beta_central
    sse_central = float(residual @ residual)
    rank_central = int(np.linalg.matrix_rank(design))
    max_sse = abs(float(fit.sse) - sse_central)
    ls_ok = bool(
        np.allclose(np.asarray(fit.coefficients), beta_central, rtol=1e-10, atol=1e-10)
        and max_sse <= 1e-8
        and fit.rank == rank_central
    )

    return Phase3AParityRecord(
        family=str(family),
        noise_ratio=float(noise),
        num_clients=int(num_clients),
        balance_profile=str(balance),
        role_profile=str(role),
        seed=int(seed),
        packet_equivalent=packet_ok,
        aggregate_equivalent=aggregate_ok,
        least_squares_equivalent=ls_ok,
        max_abs_gram_error=float(max_gram),
        max_abs_target_error=float(max_target),
        max_abs_sse_error=float(max_sse),
    )


def run_parity() -> Phase3AParityReport:
    conditions = tuple(_smoke_conditions())
    if SMOKE_SEED != 29001:
        raise RuntimeError("frozen v11 engineering seed changed unexpectedly")
    if len(conditions) != 6 or any(int(condition[-1]) != 29001 for condition in conditions):
        raise RuntimeError("Phase-3A requires exactly six frozen seed-29001 smoke conditions")

    records = tuple(_audit_condition(condition) for condition in conditions)
    passed = bool(
        all(
            record.packet_equivalent
            and record.aggregate_equivalent
            and record.least_squares_equivalent
            for record in records
        )
    )
    return Phase3AParityReport(
        schema_version=1,
        seed=29001,
        conditions=len(records),
        passed=passed,
        records=records,
    )


def _validate_output_path(path: Path) -> None:
    text = str(path.parent).lower().replace("\\", "/")
    blocked = ("results/scsv_v11", "phase1", "phase2", "29300", "29301", "11001")
    if any(token in text for token in blocked):
        raise ValueError("Phase-3A output path overlaps a protected scientific namespace")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run engineering-only Phase-3A parity checks")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    _validate_output_path(args.output)

    report = run_parity()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"seed": report.seed, "conditions": report.conditions, "passed": report.passed}, sort_keys=True))
    if not report.passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
