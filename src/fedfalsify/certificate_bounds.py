"""Finite-sample bounds for a sample-split Gaussian FedFalsify certificate.

The functions implement Theorem 1 and Theorem 2 from
``research/TRANSACTIONS_FINITE_SAMPLE_THEORY.md``. They do not apply to
adaptive reuse of the same observations without a selective-inference or
sample-splitting argument.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def invariant_retention_lower_bound(
    *,
    observable_clients: int,
    standardized_effect: float,
    z_threshold: float,
    support_fraction: float,
) -> float:
    """Lower bound for retaining a positive same-sign invariant term."""

    m = int(observable_clients)
    if m < 1:
        raise ValueError("observable_clients must be positive")
    if standardized_effect <= 0:
        raise ValueError("standardized_effect must be positive")
    if z_threshold <= 0:
        raise ValueError("z_threshold must be positive")
    if not 0 < support_fraction < 1:
        raise ValueError("support_fraction must lie in (0, 1)")

    p_plus = normal_cdf(standardized_effect - z_threshold)
    p_minus = normal_cdf(-z_threshold - standardized_effect)
    if p_plus <= support_fraction:
        return 0.0
    failure = math.exp(
        -2.0 * m * (p_plus - support_fraction) ** 2
    ) + m * p_minus
    return float(max(0.0, min(1.0, 1.0 - failure)))


def shortcut_acceptance_upper_bound(
    *,
    observable_clients: int,
    active_client_fraction: float,
    z_threshold: float,
    support_fraction: float,
) -> float:
    """Upper bound for accepting a term arbitrary on only part of clients."""

    m = int(observable_clients)
    if m < 1:
        raise ValueError("observable_clients must be positive")
    if not 0 <= active_client_fraction <= 1:
        raise ValueError("active_client_fraction must lie in [0, 1]")
    if z_threshold <= 0:
        raise ValueError("z_threshold must be positive")
    if not 0 < support_fraction < 1:
        raise ValueError("support_fraction must lie in (0, 1)")

    null_support = 2.0 * (1.0 - normal_cdf(z_threshold))
    mean_support = active_client_fraction + (
        1.0 - active_client_fraction
    ) * null_support
    if mean_support >= support_fraction:
        return 1.0
    return float(
        math.exp(-2.0 * m * (support_fraction - mean_support) ** 2)
    )


def null_family_acceptance_upper_bound(
    *,
    observable_clients: int,
    candidate_count: int,
    z_threshold: float,
    support_fraction: float,
) -> float:
    """Union-bound family-wise acceptance for globally null candidates."""

    if candidate_count < 1:
        raise ValueError("candidate_count must be positive")
    per_candidate = shortcut_acceptance_upper_bound(
        observable_clients=observable_clients,
        active_client_fraction=0.0,
        z_threshold=z_threshold,
        support_fraction=support_fraction,
    )
    return float(min(1.0, candidate_count * per_candidate))


def standardized_effect_lower_bound(
    *,
    coefficient: float,
    minimum_samples: int,
    minimum_residualized_variance: float,
    maximum_noise_standard_deviation: float,
) -> float:
    """Corollary-1 standardized-effect lower bound."""

    if coefficient == 0:
        return 0.0
    if minimum_samples < 1:
        raise ValueError("minimum_samples must be positive")
    if minimum_residualized_variance <= 0:
        raise ValueError("minimum_residualized_variance must be positive")
    if maximum_noise_standard_deviation <= 0:
        raise ValueError("maximum_noise_standard_deviation must be positive")
    return float(
        abs(coefficient)
        * math.sqrt(minimum_samples * minimum_residualized_variance)
        / maximum_noise_standard_deviation
    )


@dataclass(frozen=True)
class TheorySimulationRow:
    observable_clients: int
    standardized_effect: float
    active_client_fraction: float
    z_threshold: float
    support_fraction: float
    trials: int
    empirical_invariant_retention: float
    invariant_retention_lower_bound: float
    empirical_shortcut_acceptance: float
    shortcut_acceptance_upper_bound: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def simulate_certificate_cell(
    *,
    observable_clients: int,
    standardized_effect: float,
    active_client_fraction: float,
    z_threshold: float,
    support_fraction: float,
    trials: int,
    seed: int,
) -> TheorySimulationRow:
    """Monte Carlo validation under the theorem's independent-normal model."""

    if trials < 100:
        raise ValueError("use at least 100 simulation trials")
    m = int(observable_clients)
    required = int(math.ceil(support_fraction * m))
    rng = np.random.default_rng(seed)

    invariant_statistics = rng.normal(
        loc=standardized_effect,
        scale=1.0,
        size=(trials, m),
    )
    positive_support = np.sum(invariant_statistics >= z_threshold, axis=1)
    wrong_sign = np.any(invariant_statistics <= -z_threshold, axis=1)
    invariant_retained = (positive_support >= required) & (~wrong_sign)

    active_clients = int(math.floor(active_client_fraction * m + 1e-12))
    shortcut_means = np.zeros(m, dtype=float)
    # The theorem treats active clients adversarially as always supporting.
    # In simulation, a very large positive mean approximates this worst case.
    if active_clients:
        shortcut_means[:active_clients] = z_threshold + 8.0
    shortcut_statistics = rng.normal(
        loc=shortcut_means,
        scale=1.0,
        size=(trials, m),
    )
    shortcut_support = np.sum(
        np.abs(shortcut_statistics) >= z_threshold,
        axis=1,
    )
    shortcut_accepted = shortcut_support >= required

    return TheorySimulationRow(
        observable_clients=m,
        standardized_effect=standardized_effect,
        active_client_fraction=active_client_fraction,
        z_threshold=z_threshold,
        support_fraction=support_fraction,
        trials=trials,
        empirical_invariant_retention=float(np.mean(invariant_retained)),
        invariant_retention_lower_bound=invariant_retention_lower_bound(
            observable_clients=m,
            standardized_effect=standardized_effect,
            z_threshold=z_threshold,
            support_fraction=support_fraction,
        ),
        empirical_shortcut_acceptance=float(np.mean(shortcut_accepted)),
        shortcut_acceptance_upper_bound=shortcut_acceptance_upper_bound(
            observable_clients=m,
            active_client_fraction=active_client_fraction,
            z_threshold=z_threshold,
            support_fraction=support_fraction,
        ),
    )


def run_grid(
    *,
    client_counts: Iterable[int],
    standardized_effects: Iterable[float],
    active_client_fractions: Iterable[float],
    z_threshold: float,
    support_fraction: float,
    trials: int,
    seed: int,
) -> list[TheorySimulationRow]:
    rows: list[TheorySimulationRow] = []
    offset = 0
    for m in client_counts:
        for effect in standardized_effects:
            for active_fraction in active_client_fractions:
                rows.append(
                    simulate_certificate_cell(
                        observable_clients=int(m),
                        standardized_effect=float(effect),
                        active_client_fraction=float(active_fraction),
                        z_threshold=z_threshold,
                        support_fraction=support_fraction,
                        trials=trials,
                        seed=seed + offset,
                    )
                )
                offset += 1
    return rows


def write_outputs(
    rows: list[TheorySimulationRow],
    *,
    output: Path,
    summary_path: Path,
) -> None:
    if not rows:
        raise ValueError("cannot write an empty theory grid")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].to_dict()))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)

    tolerance = max(
        0.01,
        4.0 / math.sqrt(min(row.trials for row in rows)),
    )
    lower_bound_violations = [
        row
        for row in rows
        if row.empirical_invariant_retention + tolerance
        < row.invariant_retention_lower_bound
    ]
    upper_bound_violations = [
        row
        for row in rows
        if row.empirical_shortcut_acceptance - tolerance
        > row.shortcut_acceptance_upper_bound
    ]
    summary = {
        "schema_version": 1,
        "status": "validated"
        if not lower_bound_violations and not upper_bound_violations
        else "bound-check-failed",
        "cells": len(rows),
        "minimum_trials_per_cell": min(row.trials for row in rows),
        "monte_carlo_tolerance": tolerance,
        "invariant_lower_bound_violations": len(lower_bound_violations),
        "shortcut_upper_bound_violations": len(upper_bound_violations),
        "mean_empirical_invariant_retention": float(
            np.mean([row.empirical_invariant_retention for row in rows])
        ),
        "mean_invariant_retention_lower_bound": float(
            np.mean([row.invariant_retention_lower_bound for row in rows])
        ),
        "mean_empirical_shortcut_acceptance": float(
            np.mean([row.empirical_shortcut_acceptance for row in rows])
        ),
        "mean_shortcut_acceptance_upper_bound": float(
            np.mean([row.shortcut_acceptance_upper_bound for row in rows])
        ),
        "scientific_boundary": [
            "Fixed-design independent Gaussian validation model.",
            "Active shortcut clients are simulated near the adversarial always-support limit.",
            "Bounds do not cover adaptive reuse without sample splitting.",
            "Monte Carlo agreement does not replace the analytic proof."
        ],
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _parse_ints(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def _parse_floats(value: str) -> tuple[float, ...]:
    return tuple(float(item.strip()) for item in value.split(",") if item.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate finite-sample FedFalsify certificate bounds."
    )
    parser.add_argument("--clients", default="3,4,8,16,32")
    parser.add_argument("--effects", default="1.5,2.0,2.5,3.0,4.0")
    parser.add_argument("--active-fractions", default="0.0,0.2,0.4,0.55")
    parser.add_argument("--z-threshold", type=float, default=1.96)
    parser.add_argument("--support-fraction", type=float, default=0.60)
    parser.add_argument("--trials", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=13001)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/certificate_theory/grid.csv"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/certificate_theory/summary.json"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = run_grid(
        client_counts=_parse_ints(args.clients),
        standardized_effects=_parse_floats(args.effects),
        active_client_fractions=_parse_floats(args.active_fractions),
        z_threshold=args.z_threshold,
        support_fraction=args.support_fraction,
        trials=args.trials,
        seed=args.seed,
    )
    write_outputs(rows, output=args.output, summary_path=args.summary)
    print(f"Wrote {len(rows)} theorem-validation cells to {args.output}")
    print(f"Wrote summary to {args.summary}")


if __name__ == "__main__":
    main()
