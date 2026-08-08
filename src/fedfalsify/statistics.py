"""Small dependency-free statistical utilities for matched SR experiments."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Iterable, Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class McNemarResult:
    reference_only_success: int
    comparator_only_success: int
    discordant_pairs: int
    exact_p_value: float


@dataclass(frozen=True)
class BootstrapInterval:
    estimate: float
    lower: float
    upper: float
    confidence: float
    resamples: int


def wilson_interval(
    successes: int,
    total: int,
    *,
    confidence: float = 0.95,
) -> tuple[float, float]:
    if total <= 0:
        raise ValueError("total must be positive")
    if not 0 <= successes <= total:
        raise ValueError("successes must lie in [0, total]")
    if abs(confidence - 0.95) > 1e-12:
        raise ValueError("the dependency-free implementation currently supports 95% only")
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z * z / (4.0 * total * total)
        )
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def _binomial_cdf(k: int, n: int) -> float:
    return sum(math.comb(n, index) for index in range(k + 1)) / (2.0**n)


def mcnemar_exact(
    reference: Sequence[bool | int | float],
    comparator: Sequence[bool | int | float],
) -> McNemarResult:
    """Two-sided exact McNemar test for paired binary recovery outcomes."""

    if len(reference) != len(comparator):
        raise ValueError("paired outcomes must have equal length")
    reference_only = 0
    comparator_only = 0
    for left, right in zip(reference, comparator):
        left_value = bool(left)
        right_value = bool(right)
        if left_value and not right_value:
            reference_only += 1
        elif right_value and not left_value:
            comparator_only += 1
    discordant = reference_only + comparator_only
    if discordant == 0:
        p_value = 1.0
    else:
        p_value = min(
            1.0,
            2.0 * _binomial_cdf(min(reference_only, comparator_only), discordant),
        )
    return McNemarResult(reference_only, comparator_only, discordant, p_value)


def holm_adjust(p_values: Mapping[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values keyed by comparison label.

    The implementation preserves monotonic adjusted values after ordering and
    returns values in the caller's original key space.
    """

    if not p_values:
        return {}
    for label, value in p_values.items():
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"p-value for {label!r} must lie in [0, 1]")
    ordered = sorted(
        ((label, float(value)) for label, value in p_values.items()),
        key=lambda item: item[1],
    )
    total = len(ordered)
    adjusted_ordered: list[tuple[str, float]] = []
    running = 0.0
    for index, (label, value) in enumerate(ordered):
        candidate = min(1.0, (total - index) * value)
        running = max(running, candidate)
        adjusted_ordered.append((label, running))
    return {label: value for label, value in adjusted_ordered}


def paired_bootstrap_difference(
    reference: Iterable[float],
    comparator: Iterable[float],
    *,
    confidence: float = 0.95,
    resamples: int = 4000,
    seed: int = 2026,
) -> BootstrapInterval:
    """Percentile bootstrap interval for mean(comparator-reference)."""

    left = np.asarray(tuple(reference), dtype=float)
    right = np.asarray(tuple(comparator), dtype=float)
    if left.shape != right.shape or left.ndim != 1 or left.size == 0:
        raise ValueError("paired numeric samples must be non-empty and equally sized")
    if not 0 < confidence < 1:
        raise ValueError("confidence must lie in (0, 1)")
    if resamples < 200:
        raise ValueError("use at least 200 resamples")
    rng = random.Random(seed)
    differences = right - left
    estimates = np.empty(resamples, dtype=float)
    for index in range(resamples):
        draw = [rng.randrange(differences.size) for _ in range(differences.size)]
        estimates[index] = float(np.mean(differences[draw]))
    alpha = (1.0 - confidence) / 2.0
    return BootstrapInterval(
        estimate=float(np.mean(differences)),
        lower=float(np.quantile(estimates, alpha)),
        upper=float(np.quantile(estimates, 1.0 - alpha)),
        confidence=confidence,
        resamples=resamples,
    )
