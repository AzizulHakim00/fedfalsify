"""Partial nested-model structural tests from additive sufficient statistics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from scipy.stats import f as f_distribution

from .linear_algebra import RankPolicy, fit_from_sufficient_stats
from .sufficient_stats import SufficientStatsPacket, aggregate_packets


@dataclass(frozen=True)
class NestedFResult:
    admissible: bool
    reason: str
    reduced_terms: tuple[str, ...]
    full_terms: tuple[str, ...]
    n: int
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


def aggregate_scope(
    packets: Sequence[SufficientStatsPacket],
    indices: Sequence[int],
) -> SufficientStatsPacket:
    packets = tuple(packets)
    selected_indices = tuple(int(index) for index in indices)
    if not selected_indices:
        raise ValueError("scope must contain at least one client")
    if len(set(selected_indices)) != len(selected_indices):
        raise ValueError("scope client indices must be unique")
    if any(index < 0 or index >= len(packets) for index in selected_indices):
        raise IndexError("scope client index out of range")
    return aggregate_packets(tuple(packets[index] for index in selected_indices))


def _sign(value: float) -> int:
    if value > 1e-12:
        return 1
    if value < -1e-12:
        return -1
    return 0


def partial_nested_f(
    packet: SufficientStatsPacket,
    reduced_terms: tuple[str, ...],
    full_terms: tuple[str, ...],
    *,
    candidate_term: str,
    policy: RankPolicy = RankPolicy(),
) -> NestedFResult:
    reduced_terms = tuple(reduced_terms)
    full_terms = tuple(full_terms)

    if not reduced_terms or not full_terms:
        raise ValueError("nested structural tests require non-empty term sets")
    if len(set(reduced_terms)) != len(reduced_terms):
        raise ValueError("REDUCED terms must be unique")
    if len(set(full_terms)) != len(full_terms):
        raise ValueError("FULL terms must be unique")
    if candidate_term in reduced_terms:
        raise ValueError("candidate term must not be in REDUCED")
    if len(full_terms) != len(reduced_terms) + 1:
        raise ValueError("FULL must add exactly one term")
    if set(full_terms) != set(reduced_terms) | {candidate_term}:
        raise ValueError("FULL must equal REDUCED plus exactly the candidate term")

    reduced_fit = fit_from_sufficient_stats(packet, reduced_terms, policy)
    full_fit = fit_from_sufficient_stats(packet, full_terms, policy)
    raw_gain = float(max(reduced_fit.sse - full_fit.sse, 0.0))

    if full_fit.rank != reduced_fit.rank + 1:
        return NestedFResult(
            admissible=False,
            reason="STRUCTURAL-RANK-AMBIGUOUS",
            reduced_terms=reduced_terms,
            full_terms=full_terms,
            n=int(packet.support),
            reduced_rank=int(reduced_fit.rank),
            full_rank=int(full_fit.rank),
            residual_df=int(full_fit.residual_df),
            reduced_sse=float(reduced_fit.sse),
            full_sse=float(full_fit.sse),
            raw_gain=raw_gain,
            f_statistic=None,
            p_value=None,
            candidate_coefficient=None,
            candidate_sign=0,
        )

    if full_fit.residual_df <= 0:
        return NestedFResult(
            admissible=False,
            reason="INSUFFICIENT-RESIDUAL-DF",
            reduced_terms=reduced_terms,
            full_terms=full_terms,
            n=int(packet.support),
            reduced_rank=int(reduced_fit.rank),
            full_rank=int(full_fit.rank),
            residual_df=int(full_fit.residual_df),
            reduced_sse=float(reduced_fit.sse),
            full_sse=float(full_fit.sse),
            raw_gain=raw_gain,
            f_statistic=None,
            p_value=None,
            candidate_coefficient=None,
            candidate_sign=0,
        )

    coefficient_by_term = dict(zip(full_fit.terms, full_fit.coefficients))
    candidate_coefficient = float(coefficient_by_term[candidate_term])

    if full_fit.sse <= 1e-15:
        if raw_gain > 1e-15:
            f_statistic = float("inf")
            p_value = 0.0
        else:
            f_statistic = 0.0
            p_value = 1.0
    else:
        f_statistic = float(raw_gain / (full_fit.sse / full_fit.residual_df))
        p_value = float(f_distribution.sf(f_statistic, 1, full_fit.residual_df))

    return NestedFResult(
        admissible=True,
        reason="OK",
        reduced_terms=reduced_terms,
        full_terms=full_terms,
        n=int(packet.support),
        reduced_rank=int(reduced_fit.rank),
        full_rank=int(full_fit.rank),
        residual_df=int(full_fit.residual_df),
        reduced_sse=float(reduced_fit.sse),
        full_sse=float(full_fit.sse),
        raw_gain=raw_gain,
        f_statistic=f_statistic,
        p_value=p_value,
        candidate_coefficient=candidate_coefficient,
        candidate_sign=_sign(candidate_coefficient),
    )
