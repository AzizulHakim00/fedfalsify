"""Scope-contrast structural tests for FedFalsify v13 / SCSV-SCC.

The key difference from v12 is identifiability geometry.  A localized source
shift may be exactly collinear with its source inside a role client.  v13
therefore tests a client-scope regressor on the aggregate role+outside design:
zero outside the frozen scope and equal to the shared source basis inside it.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Sequence

import numpy as np

from .multiple_testing import bh_adjust
from .nested_tests import NestedFResult, partial_nested_f
from .sufficient_stats import SufficientStatsPacket, aggregate_packets

ROLE_Q = 0.10
MAX_ROLE_FRACTION = 0.50


@dataclass(frozen=True)
class ScopeContrastResult:
    admissible: bool
    reason: str
    source_term: str
    role_indices: tuple[int, ...]
    role_client_ids: tuple[str, ...]
    outside_client_ids: tuple[str, ...]
    candidate_term: str
    reduced_rank: int
    full_rank: int
    residual_df: int
    reduced_sse: float
    full_sse: float
    raw_gain: float
    f_statistic: float | None
    p_value: float | None
    candidate_coefficient: float | None
    candidate_sign: int


@dataclass(frozen=True)
class FrozenScopeHypothesis:
    localized_term: str
    source_term: str
    role_indices: tuple[int, ...]
    outside_indices: tuple[int, ...]
    role_client_ids: tuple[str, ...]
    outside_client_ids: tuple[str, ...]
    discovery_sign: int
    discovery_result: ScopeContrastResult
    tested_scope_count: int
    bh_adjusted_value: float

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            self.localized_term,
            self.source_term,
            self.role_client_ids,
            self.outside_client_ids,
            self.discovery_sign,
        )


@dataclass(frozen=True)
class ScopeContrastRejection:
    localized_term: str
    source_term: str
    reason: str
    tested_scope_count: int


def _scope_name(source_term: str, role_ids: tuple[str, ...]) -> str:
    return f"SCOPE[{source_term}|{','.join(role_ids)}]"


def _packet_with_scope_column(
    dataset,
    catalog,
    shared_terms: tuple[str, ...],
    *,
    source_term: str,
    candidate_term: str,
    in_role: bool,
) -> SufficientStatsPacket:
    shared_design = np.asarray(catalog.matrix(dataset.x, shared_terms), dtype=float)
    source = np.asarray(catalog.get(source_term).evaluate(dataset.x), dtype=float)
    scope = source if in_role else np.zeros_like(source)
    design = np.column_stack([shared_design, scope])
    response = np.asarray(dataset.y, dtype=float)
    terms = tuple(shared_terms) + (candidate_term,)
    observed_support = tuple(
        int(np.count_nonzero(np.abs(design[:, index]) > 1e-12))
        for index in range(design.shape[1])
    )
    return SufficientStatsPacket(
        client_id=str(dataset.client_id),
        support=int(len(response)),
        terms=terms,
        gram=np.asarray(design.T @ design, dtype=float),
        target=np.asarray(design.T @ response, dtype=float),
        target_energy=float(response @ response),
        observed_support=observed_support,
    )


def scope_contrast_test(
    clients: Sequence[object],
    catalog,
    *,
    shared_terms: tuple[str, ...],
    source_term: str,
    role_indices: Sequence[int],
) -> ScopeContrastResult:
    """Test one frozen client scope by pooled role-vs-outside rank expansion."""
    clients = tuple(clients)
    shared_terms = tuple(shared_terms)
    role_indices = tuple(sorted(int(index) for index in role_indices))
    if not clients:
        raise ValueError("scope contrast requires at least one client")
    if "1" not in shared_terms or len(set(shared_terms)) != len(shared_terms):
        raise ValueError("shared terms must be unique and include intercept")
    if source_term not in shared_terms:
        raise ValueError("source term must be retained in the shared structure")
    if not role_indices or len(role_indices) >= len(clients):
        raise ValueError("scope must contain at least one role and one outside client")
    if len(set(role_indices)) != len(role_indices):
        raise ValueError("scope indices must be unique")
    if any(index < 0 or index >= len(clients) for index in role_indices):
        raise IndexError("scope index out of range")

    role_set = set(role_indices)
    role_ids = tuple(str(clients[index].client_id) for index in role_indices)
    outside_ids = tuple(
        str(client.client_id) for index, client in enumerate(clients) if index not in role_set
    )
    candidate_term = _scope_name(source_term, role_ids)
    packets = tuple(
        _packet_with_scope_column(
            client,
            catalog,
            shared_terms,
            source_term=source_term,
            candidate_term=candidate_term,
            in_role=index in role_set,
        )
        for index, client in enumerate(clients)
    )
    pooled = aggregate_packets(packets)
    nested: NestedFResult = partial_nested_f(
        pooled,
        shared_terms,
        shared_terms + (candidate_term,),
        candidate_term=candidate_term,
    )
    return ScopeContrastResult(
        admissible=bool(nested.admissible),
        reason=str(nested.reason),
        source_term=source_term,
        role_indices=role_indices,
        role_client_ids=role_ids,
        outside_client_ids=outside_ids,
        candidate_term=candidate_term,
        reduced_rank=int(nested.reduced_rank),
        full_rank=int(nested.full_rank),
        residual_df=int(nested.residual_df),
        reduced_sse=float(nested.reduced_sse),
        full_sse=float(nested.full_sse),
        raw_gain=float(nested.raw_gain),
        f_statistic=None if nested.f_statistic is None else float(nested.f_statistic),
        p_value=None if nested.p_value is None else float(nested.p_value),
        candidate_coefficient=(
            None if nested.candidate_coefficient is None else float(nested.candidate_coefficient)
        ),
        candidate_sign=int(nested.candidate_sign),
    )


def _candidate_scopes(num_clients: int) -> tuple[tuple[int, ...], ...]:
    max_size = max(1, int(np.floor(MAX_ROLE_FRACTION * num_clients)))
    return tuple(
        scope
        for size in range(1, max_size + 1)
        for scope in combinations(range(num_clients), size)
        if size < num_clients
    )


def discover_scope_contrast(
    fixture,
    discovery_clients: Sequence[object],
    catalog,
    *,
    shared_terms: tuple[str, ...],
    localized_term: str,
    source_term: str,
) -> FrozenScopeHypothesis | ScopeContrastRejection:
    """Discover one localized client scope using Discovery evidence only."""
    clients = tuple(discovery_clients)
    metadata = catalog.get(localized_term)
    if metadata.kind != "exception":
        return ScopeContrastRejection(localized_term, source_term, "LOCALIZED-CANDIDATE-NOT-EXCEPTION", 0)
    if metadata.source_term != source_term:
        return ScopeContrastRejection(localized_term, source_term, "SOURCE-PROVENANCE-MISMATCH", 0)
    if source_term not in set(shared_terms):
        return ScopeContrastRejection(localized_term, source_term, "SOURCE-NOT-PROTECTED", 0)

    scopes = _candidate_scopes(len(clients))
    results: list[ScopeContrastResult] = []
    for scope in scopes:
        result = scope_contrast_test(
            clients,
            catalog,
            shared_terms=tuple(shared_terms),
            source_term=source_term,
            role_indices=scope,
        )
        if result.admissible and result.p_value is not None:
            results.append(result)

    if not results:
        return ScopeContrastRejection(localized_term, source_term, "NO-ESTIMABLE-SCOPE", len(scopes))

    names = tuple(result.candidate_term for result in results)
    p_values = tuple(float(result.p_value) for result in results)
    bh = bh_adjust(names, p_values, q=ROLE_Q)
    adjusted = dict(zip(bh.names, bh.adjusted_values))
    rejected = set(bh.rejected)
    supported = [result for result in results if result.candidate_term in rejected and result.candidate_sign != 0]
    if not supported:
        return ScopeContrastRejection(localized_term, source_term, "EFFECT-SCOPE-NOT-LOCALIZED", len(scopes))

    # Full SSE is the primary structural criterion.  The exact true scope is the
    # unique scope that can reproduce a deterministic/noiseless source shift.
    # Adjusted p-value and scope size are deterministic secondary tie-breakers.
    chosen = min(
        supported,
        key=lambda result: (
            float(result.full_sse),
            float(adjusted[result.candidate_term]),
            len(result.role_indices),
            result.role_client_ids,
        ),
    )
    role_set = set(chosen.role_indices)
    outside_indices = tuple(index for index in range(len(clients)) if index not in role_set)
    return FrozenScopeHypothesis(
        localized_term=localized_term,
        source_term=source_term,
        role_indices=chosen.role_indices,
        outside_indices=outside_indices,
        role_client_ids=chosen.role_client_ids,
        outside_client_ids=chosen.outside_client_ids,
        discovery_sign=int(chosen.candidate_sign),
        discovery_result=chosen,
        tested_scope_count=len(scopes),
        bh_adjusted_value=float(adjusted[chosen.candidate_term]),
    )
