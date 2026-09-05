"""Deterministic family-wise and false-discovery multiplicity procedures."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


@dataclass(frozen=True)
class MultiplicityResult:
    names: tuple[str, ...]
    raw_values: tuple[float, ...]
    adjusted_values: tuple[float, ...]
    rejected: tuple[str, ...]


def _validate_inputs(
    names: Sequence[str],
    values: Sequence[float],
    threshold: float,
    *,
    threshold_name: str,
) -> tuple[tuple[str, ...], tuple[float, ...]]:
    names = tuple(str(name) for name in names)
    values = tuple(float(value) for value in values)
    if len(names) != len(values):
        raise ValueError("hypothesis names and p-values must have equal length")
    if len(set(names)) != len(names):
        raise ValueError("hypothesis names must be unique")
    if not 0.0 < float(threshold) < 1.0:
        raise ValueError(f"{threshold_name} must be strictly between 0 and 1")
    if any((not math.isfinite(value)) or value < 0.0 or value > 1.0 for value in values):
        raise ValueError("p-values must be finite and lie in [0, 1]")
    return names, values


def holm_adjust(
    names: Sequence[str],
    p_values: Sequence[float],
    *,
    alpha: float = 0.05,
) -> MultiplicityResult:
    names, raw_values = _validate_inputs(names, p_values, alpha, threshold_name="alpha")
    count = len(names)
    if count == 0:
        return MultiplicityResult((), (), (), ())

    order = sorted(range(count), key=lambda index: (raw_values[index], index))
    adjusted_sorted: list[float] = []
    running = 0.0
    for rank, index in enumerate(order):
        scaled = min(1.0, float((count - rank) * raw_values[index]))
        running = max(running, scaled)
        adjusted_sorted.append(min(1.0, running))

    adjusted = [0.0] * count
    for sorted_position, original_index in enumerate(order):
        adjusted[original_index] = adjusted_sorted[sorted_position]
    adjusted_values = tuple(float(value) for value in adjusted)
    rejected = tuple(
        name for name, adjusted_value in zip(names, adjusted_values) if adjusted_value <= alpha
    )
    return MultiplicityResult(names, raw_values, adjusted_values, rejected)


def bh_adjust(
    names: Sequence[str],
    p_values: Sequence[float],
    *,
    q: float = 0.10,
) -> MultiplicityResult:
    names, raw_values = _validate_inputs(names, p_values, q, threshold_name="q")
    count = len(names)
    if count == 0:
        return MultiplicityResult((), (), (), ())

    order = sorted(range(count), key=lambda index: (raw_values[index], index))
    scaled = [
        min(1.0, float(raw_values[index] * count / (rank + 1)))
        for rank, index in enumerate(order)
    ]
    adjusted_sorted = [0.0] * count
    running = 1.0
    for position in range(count - 1, -1, -1):
        running = min(running, scaled[position])
        adjusted_sorted[position] = min(1.0, running)

    adjusted = [0.0] * count
    for sorted_position, original_index in enumerate(order):
        adjusted[original_index] = adjusted_sorted[sorted_position]
    adjusted_values = tuple(float(value) for value in adjusted)
    rejected = tuple(
        name for name, adjusted_value in zip(names, adjusted_values) if adjusted_value <= q
    )
    return MultiplicityResult(names, raw_values, adjusted_values, rejected)
