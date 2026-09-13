"""Deterministic/noiseless Phase-3D fixtures for v13 architectural proof.

These fixtures deliberately use no RNG and accept no seed parameter.  Their
purpose is structural admissibility: can a method retain a shared source term
while also representing a client-scope coefficient shift of that same source?
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .benchmarks import BenchmarkClientDataset, evaluate_terms
from .scsv_v10_benchmarks import (
    INTERACTION_DEV_V10,
    LINEAR_DEV_V10,
    QUADRATIC_DEV_V10,
    TRIG_DEV_V10,
    WEAK_SOURCE_DEV_V10,
    v10_catalog,
)

PHASE3D_FIXTURE_NAMES = (
    "quadratic_scope_shift",
    "linear_scope_shift",
    "trig_scope_shift",
    "interaction_scope_shift",
    "weak_source_scope_shift",
    "dual_scope_shift",
    "null_no_localized",
    "anchor_contamination_null",
)

PHASE3D_ROWS_PER_CLIENT = 120
PHASE3D_NUM_CLIENTS = 8

# Broad deterministic ordinary family.  It intentionally contains distractors;
# v13 must not need an oracle ordinary structure for its joint recertification.
PHASE3D_SHARED_CANDIDATE_FAMILY = (
    "1",
    "x1",
    "x2",
    "x3",
    "x4",
    "x1^2",
    "x2^2",
    "x3^2",
    "x4^2",
    "sin(x1)",
    "sin(x2)",
    "sin(x3)",
    "cos(x1)",
    "cos(x2)",
    "cos(x3)",
    "x1*x2",
)

PHASE3D_LOCALIZED_CANDIDATES = (
    QUADRATIC_DEV_V10,
    LINEAR_DEV_V10,
    TRIG_DEV_V10,
    INTERACTION_DEV_V10,
    WEAK_SOURCE_DEV_V10,
)


@dataclass(frozen=True)
class Phase3DFixture:
    name: str
    clients: tuple[BenchmarkClientDataset, ...]
    shared_coefficients: tuple[tuple[str, float], ...]
    localized_coefficients: tuple[tuple[str, float], ...]
    truth_scopes: tuple[tuple[str, tuple[str, ...]], ...]
    candidate_shared_terms: tuple[str, ...] = PHASE3D_SHARED_CANDIDATE_FAMILY
    localized_candidates: tuple[str, ...] = PHASE3D_LOCALIZED_CANDIDATES

    @property
    def true_shared_terms(self) -> tuple[str, ...]:
        return ("1",) + tuple(term for term, _ in self.shared_coefficients)

    @property
    def true_localized_terms(self) -> tuple[str, ...]:
        return tuple(term for term, _ in self.localized_coefficients)


@dataclass(frozen=True)
class _FixtureDefinition:
    name: str
    shared: tuple[tuple[str, float], ...]
    localized: tuple[tuple[str, float], ...]
    scopes: tuple[tuple[str, tuple[int, ...]], ...]
    support_only: tuple[tuple[str, tuple[int, ...]], ...] = ()


def _client_ids(indices: tuple[int, ...]) -> tuple[str, ...]:
    return tuple(f"client-{index + 1}" for index in indices)


_DEFINITIONS = (
    _FixtureDefinition(
        "quadratic_scope_shift",
        (("x3^2", 0.86), ("sin(x2)", 0.72), ("x1", 0.56)),
        ((QUADRATIC_DEV_V10, 0.70),),
        ((QUADRATIC_DEV_V10, (6, 7)),),
    ),
    _FixtureDefinition(
        "linear_scope_shift",
        (("x1", 0.90), ("cos(x2)", 0.70), ("x4^2", 0.62)),
        ((LINEAR_DEV_V10, 0.68),),
        ((LINEAR_DEV_V10, (6, 7)),),
    ),
    _FixtureDefinition(
        "trig_scope_shift",
        (("cos(x2)", 0.86), ("x3^2", 0.64), ("x1", 0.58)),
        ((TRIG_DEV_V10, 0.70),),
        ((TRIG_DEV_V10, (6, 7)),),
    ),
    _FixtureDefinition(
        "interaction_scope_shift",
        (("x1*x2", 0.90), ("x3^2", 0.60), ("sin(x1)", 0.54)),
        ((INTERACTION_DEV_V10, 0.62),),
        ((INTERACTION_DEV_V10, (6, 7)),),
    ),
    _FixtureDefinition(
        "weak_source_scope_shift",
        (("x4^2", 0.25), ("sin(x2)", 0.65), ("x1", 0.55)),
        ((WEAK_SOURCE_DEV_V10, 0.75),),
        ((WEAK_SOURCE_DEV_V10, (6, 7)),),
    ),
    _FixtureDefinition(
        "dual_scope_shift",
        (("x3^2", 0.70), ("x1", 0.66), ("cos(x2)", 0.55)),
        ((QUADRATIC_DEV_V10, 0.62), (LINEAR_DEV_V10, 0.60)),
        ((QUADRATIC_DEV_V10, (6, 7)), (LINEAR_DEV_V10, (4, 5))),
    ),
    _FixtureDefinition(
        "null_no_localized",
        (("x3^2", 0.62), ("x1", 0.58), ("cos(x2)", 0.54), ("x1*x2", 0.50), ("x4^2", 0.22)),
        (),
        (),
    ),
    _FixtureDefinition(
        "anchor_contamination_null",
        (("x3^2", 0.62), ("x1", 0.58), ("cos(x2)", 0.54), ("x1*x2", 0.50), ("x4^2", 0.22)),
        (),
        (),
        ((WEAK_SOURCE_DEV_V10, (6, 7)),),
    ),
)


def _scaled_permutation(
    size: int,
    multiplier: int,
    offset: int,
    low: float,
    high: float,
) -> np.ndarray:
    index = (np.arange(size, dtype=int) * multiplier + offset) % size
    unit = index.astype(float) / float(size - 1)
    return low + (high - low) * unit


def _base_client_x(client_index: int, size: int) -> np.ndarray:
    # All default ranges remain outside every exception gate.  This makes a
    # scope-support manipulation explicit rather than accidental.
    x1 = _scaled_permutation(size, 37, 11 * client_index + 3, -0.60, 2.60)
    x2 = _scaled_permutation(size, 53, 7 * client_index + 5, -3.00, 0.65)
    x3 = _scaled_permutation(size, 29, 13 * client_index + 1, -0.60, 2.50)
    x4 = _scaled_permutation(size, 31, 17 * client_index + 9, -0.60, 2.45)
    return np.column_stack([x1, x2, x3, x4])


def _activate_support(x: np.ndarray, term: str, client_index: int) -> np.ndarray:
    x = np.asarray(x, dtype=float).copy()
    size = x.shape[0]
    if term == QUADRATIC_DEV_V10:
        x[:, 2] = _scaled_permutation(size, 29, 5 * client_index + 2, -2.60, -1.00)
    elif term == LINEAR_DEV_V10:
        x[:, 0] = _scaled_permutation(size, 37, 3 * client_index + 4, -2.80, -1.00)
    elif term in {TRIG_DEV_V10, INTERACTION_DEV_V10}:
        x[:, 1] = _scaled_permutation(size, 53, 9 * client_index + 6, 1.00, 3.05)
    elif term == WEAK_SOURCE_DEV_V10:
        x[:, 3] = _scaled_permutation(size, 31, 15 * client_index + 7, -2.60, -1.00)
    else:
        raise KeyError(f"unsupported Phase-3D support term: {term}")
    return x


def _build_fixture(definition: _FixtureDefinition) -> Phase3DFixture:
    catalog = v10_catalog()
    scope_map = {term: set(indices) for term, indices in definition.scopes}
    support_map = {term: set(indices) for term, indices in definition.support_only}
    clients: list[BenchmarkClientDataset] = []

    for client_index in range(PHASE3D_NUM_CLIENTS):
        x = _base_client_x(client_index, PHASE3D_ROWS_PER_CLIENT)
        for term, indices in scope_map.items():
            if client_index in indices:
                x = _activate_support(x, term, client_index)
        for term, indices in support_map.items():
            if client_index in indices:
                x = _activate_support(x, term, client_index)

        y = evaluate_terms(x, definition.shared, catalog)
        for term, coefficient in definition.localized:
            if client_index in scope_map.get(term, set()):
                # Role clients are constructed inside the term's active gate,
                # therefore the v10 exception term equals its source basis.
                y = y + float(coefficient) * catalog.get(term).evaluate(x)

        clients.append(BenchmarkClientDataset(f"client-{client_index + 1}", x, y))

    return Phase3DFixture(
        name=definition.name,
        clients=tuple(clients),
        shared_coefficients=definition.shared,
        localized_coefficients=definition.localized,
        truth_scopes=tuple((term, _client_ids(indices)) for term, indices in definition.scopes),
    )


def build_phase3d_fixtures() -> tuple[Phase3DFixture, ...]:
    """Return all eight deterministic/noiseless Phase-3D fixtures."""
    return tuple(_build_fixture(definition) for definition in _DEFINITIONS)


def split_fixture_clients(
    fixture: Phase3DFixture,
    *,
    outer_fold: int = 0,
) -> tuple[
    tuple[BenchmarkClientDataset, ...],
    tuple[BenchmarkClientDataset, ...],
    tuple[BenchmarkClientDataset, ...],
]:
    """Deterministically split every client into Discovery/Selector/Probe thirds.

    Additional outer-fold IDs rotate the modulo assignment; no RNG is used and
    persistence semantics therefore remain unchanged if future fixture studies
    add folds.
    """
    fold = int(outer_fold)
    groups: list[list[BenchmarkClientDataset]] = [[], [], []]
    for client in fixture.clients:
        row_index = np.arange(len(client.y), dtype=int)
        bucket = (row_index + fold) % 3
        for target_bucket in range(3):
            mask = bucket == target_bucket
            groups[target_bucket].append(
                BenchmarkClientDataset(
                    client.client_id,
                    np.asarray(client.x[mask], dtype=float),
                    np.asarray(client.y[mask], dtype=float),
                )
            )
    return tuple(groups[0]), tuple(groups[1]), tuple(groups[2])
