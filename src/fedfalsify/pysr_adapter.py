"""Optional adapter for the official PySR package.

PySR is intentionally optional because installation launches a Julia-backed
runtime and is too heavy for the repository's default CI. Confirmatory users
should install the `sr` extra and archive PySR's hall-of-fame outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class PySROutput:
    method: str
    equation: str
    predictions: np.ndarray
    runtime_seconds: float
    available: bool
    note: str


def pysr_available() -> bool:
    try:
        import pysr  # noqa: F401
    except ImportError:
        return False
    return True


def run_pysr(
    datasets: Sequence[object],
    x_test: np.ndarray,
    *,
    seed: int,
    niterations: int = 40,
    populations: int = 6,
    population_size: int = 40,
    maxsize: int = 18,
) -> PySROutput:
    """Run stable PySR 1.5.x on pooled observations.

    The adapter uses only operators shared with the controlled tree baselines.
    Restricted x3-gated exceptions are not represented by this generic search
    space and should be reported as an unsupported condition rather than forced
    into an unfair custom operator.
    """

    if not pysr_available():
        return PySROutput(
            method="official-pysr",
            equation="",
            predictions=np.full(x_test.shape[0], np.nan),
            runtime_seconds=0.0,
            available=False,
            note='Install with: python -m pip install -e ".[sr]"',
        )

    from pysr import PySRRegressor

    x = np.concatenate([np.asarray(item.x, dtype=float) for item in datasets], axis=0)
    y = np.concatenate([np.asarray(item.y, dtype=float) for item in datasets], axis=0)
    start = perf_counter()
    model = PySRRegressor(
        niterations=niterations,
        populations=populations,
        population_size=population_size,
        maxsize=maxsize,
        binary_operators=["+", "*"],
        unary_operators=["sin", "cos", "square"],
        model_selection="best",
        random_state=seed,
        deterministic=True,
        parallelism="serial",
        progress=False,
        verbosity=0,
    )
    model.fit(x, y, variable_names=[f"x{index + 1}" for index in range(x.shape[1])])
    predictions = np.asarray(model.predict(x_test), dtype=float)
    try:
        equation = str(model.sympy())
    except Exception:  # pragma: no cover - PySR version-specific export fallback.
        equation = str(model)
    return PySROutput(
        method="official-pysr",
        equation=equation,
        predictions=predictions,
        runtime_seconds=perf_counter() - start,
        available=True,
        note="Official PySR pooled-data baseline; archive the run directory.",
    )
