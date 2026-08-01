"""Interpretable basis functions used by the first FedFalsify prototype.

The prototype intentionally starts with a finite grammar. This makes exact
mechanism recovery measurable and lets the server repair a hypothesis by adding
one falsification-supported term at a time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np

Array = np.ndarray


@dataclass(frozen=True)
class BasisTerm:
    """A named, deterministic basis function."""

    name: str
    function: Callable[[Array], Array]
    complexity: int
    display: str

    def evaluate(self, x: Array) -> Array:
        values = np.asarray(self.function(x), dtype=float)
        if values.ndim != 1 or values.shape[0] != x.shape[0]:
            raise ValueError(f"Term {self.name!r} returned an invalid shape")
        if not np.all(np.isfinite(values)):
            raise ValueError(f"Term {self.name!r} produced non-finite values")
        return values


class TermCatalog:
    """Finite symbolic grammar for the minimum viable invention."""

    def __init__(self) -> None:
        self._terms: dict[str, BasisTerm] = {
            "1": BasisTerm("1", lambda x: np.ones(x.shape[0]), 1, "1"),
            "x1": BasisTerm("x1", lambda x: x[:, 0], 1, "x₁"),
            "x2": BasisTerm("x2", lambda x: x[:, 1], 1, "x₂"),
            "x3": BasisTerm("x3", lambda x: x[:, 2], 1, "x₃"),
            "x1^2": BasisTerm("x1^2", lambda x: x[:, 0] ** 2, 2, "x₁²"),
            "x2^2": BasisTerm("x2^2", lambda x: x[:, 1] ** 2, 2, "x₂²"),
            "x3^2": BasisTerm("x3^2", lambda x: x[:, 2] ** 2, 2, "x₃²"),
            "sin(x1)": BasisTerm("sin(x1)", lambda x: np.sin(x[:, 0]), 2, "sin(x₁)"),
            "sin(x2)": BasisTerm("sin(x2)", lambda x: np.sin(x[:, 1]), 2, "sin(x₂)"),
            "sin(x3)": BasisTerm("sin(x3)", lambda x: np.sin(x[:, 2]), 2, "sin(x₃)"),
            "cos(x1)": BasisTerm("cos(x1)", lambda x: np.cos(x[:, 0]), 2, "cos(x₁)"),
            "cos(x2)": BasisTerm("cos(x2)", lambda x: np.cos(x[:, 1]), 2, "cos(x₂)"),
            "cos(x3)": BasisTerm("cos(x3)", lambda x: np.cos(x[:, 2]), 2, "cos(x₃)"),
        }

    def names(self) -> tuple[str, ...]:
        return tuple(self._terms)

    def get(self, name: str) -> BasisTerm:
        try:
            return self._terms[name]
        except KeyError as exc:
            raise KeyError(f"Unknown basis term: {name}") from exc

    def matrix(self, x: Array, names: Iterable[str]) -> Array:
        selected = tuple(names)
        if not selected:
            raise ValueError("At least one term is required")
        return np.column_stack([self.get(name).evaluate(x) for name in selected])

    def complexity(self, names: Iterable[str]) -> int:
        return sum(self.get(name).complexity for name in names)


@dataclass(frozen=True)
class CandidateEquation:
    """A server-owned symbolic hypothesis with fitted coefficients."""

    active_terms: tuple[str, ...]
    coefficients: tuple[float, ...]
    candidate_id: str = "candidate"

    def __post_init__(self) -> None:
        if len(self.active_terms) != len(self.coefficients):
            raise ValueError("Each active term must have one coefficient")
        if len(set(self.active_terms)) != len(self.active_terms):
            raise ValueError("Duplicate active terms are not allowed")
        if "1" not in self.active_terms:
            raise ValueError("The intercept term '1' must remain active")

    def predict(self, x: Array, catalog: TermCatalog) -> Array:
        design = catalog.matrix(x, self.active_terms)
        return design @ np.asarray(self.coefficients, dtype=float)

    def expression(self, catalog: TermCatalog, precision: int = 4) -> str:
        pieces: list[str] = []
        for coefficient, name in zip(self.coefficients, self.active_terms):
            if abs(coefficient) < 10 ** (-(precision + 1)):
                continue
            display = catalog.get(name).display
            value = f"{abs(coefficient):.{precision}g}"
            body = value if name == "1" else f"{value}·{display}"
            if not pieces:
                pieces.append(f"-{body}" if coefficient < 0 else body)
            else:
                pieces.append((" - " if coefficient < 0 else " + ") + body)
        return "".join(pieces) if pieces else "0"
