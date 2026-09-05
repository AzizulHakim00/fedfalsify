"""Independent shared-core re-certification for Phase-3B.

Discovery nominates a frozen ordinary family from the predecessor selector and
high-recall bank. Selector sufficient statistics then certify each term through
one-degree partial nested tests with Holm family-wise error control.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .basis import TermCatalog
from .multiple_testing import MultiplicityResult, holm_adjust
from .nested_tests import partial_nested_f
from .sufficient_stats import SufficientStatsPacket, aggregate_packets

SHARED_ALPHA = 0.05
MAX_NONINTERCEPT_SHARED = 5


@dataclass(frozen=True)
class SharedCandidateDiagnostic:
    term: str
    admissible: bool
    reason: str
    reduced_rank: int
    full_rank: int
    residual_df: int
    reduced_sse: float
    full_sse: float
    raw_p_value: float
    holm_adjusted_p_value: float
    holm_rejected: bool


@dataclass(frozen=True)
class SharedRecertificationResult:
    candidate_family: tuple[str, ...]
    accepted_shared_terms: tuple[str, ...]
    diagnostics: tuple[SharedCandidateDiagnostic, ...]
    holm: MultiplicityResult
    rank_abstentions: tuple[str, ...]
    capacity_truncated: bool
    removed_by_capacity: tuple[str, ...]


def _anchor_terms(anchor) -> tuple[tuple[str, ...], tuple[str, ...]]:
    selector = tuple(getattr(anchor, "selector_structure"))
    bank = getattr(anchor, "bank", None)
    bank_terms = tuple(getattr(bank, "candidate_terms", ()))
    return selector, bank_terms


def nominate_shared_family(anchor, catalog: TermCatalog) -> tuple[str, ...]:
    """Freeze intercept + ordinary predecessor selector/bank terms in catalog order."""
    selector, bank_terms = _anchor_terms(anchor)
    nominated = {"1"}
    for term in selector + bank_terms:
        metadata = catalog.get(term)
        if metadata.kind != "exception":
            nominated.add(term)

    ordered = tuple(term for term in catalog.names() if term in nominated)
    if not ordered or ordered[0] != "1":
        raise RuntimeError("shared family must retain the intercept as canonical first term")
    return ordered


def certify_shared_core(
    anchor,
    selector_packets: Sequence[SufficientStatsPacket],
    catalog: TermCatalog,
) -> SharedRecertificationResult:
    """Certify a Discovery-frozen ordinary family using Selector only."""
    selector_packets = tuple(selector_packets)
    if not selector_packets:
        raise ValueError("SCR requires at least one Selector packet")

    family = nominate_shared_family(anchor, catalog)
    nonintercept = tuple(term for term in family if term != "1")
    if not nonintercept:
        empty = holm_adjust((), (), alpha=SHARED_ALPHA)
        return SharedRecertificationResult(
            candidate_family=family,
            accepted_shared_terms=("1",),
            diagnostics=(),
            holm=empty,
            rank_abstentions=(),
            capacity_truncated=False,
            removed_by_capacity=(),
        )

    pooled = aggregate_packets(selector_packets)
    raw_p_values: list[float] = []
    partials = []
    rank_abstentions: list[str] = []
    for term in nonintercept:
        reduced = tuple(item for item in family if item != term)
        result = partial_nested_f(
            pooled,
            reduced,
            family,
            candidate_term=term,
        )
        partials.append(result)
        if result.admissible:
            raw_p_values.append(float(result.p_value))
        else:
            raw_p_values.append(1.0)
            if result.reason == "STRUCTURAL-RANK-AMBIGUOUS":
                rank_abstentions.append(term)

    holm = holm_adjust(nonintercept, raw_p_values, alpha=SHARED_ALPHA)
    adjusted = dict(zip(holm.names, holm.adjusted_values))
    rejected = set(holm.rejected)
    diagnostics = tuple(
        SharedCandidateDiagnostic(
            term=term,
            admissible=bool(result.admissible),
            reason=result.reason,
            reduced_rank=int(result.reduced_rank),
            full_rank=int(result.full_rank),
            residual_df=int(result.residual_df),
            reduced_sse=float(result.reduced_sse),
            full_sse=float(result.full_sse),
            raw_p_value=float(raw_p),
            holm_adjusted_p_value=float(adjusted[term]),
            holm_rejected=bool(term in rejected),
        )
        for term, raw_p, result in zip(nonintercept, raw_p_values, partials)
    )

    canonical_index = {term: index for index, term in enumerate(catalog.names())}
    supported = [term for term in nonintercept if term in rejected]
    removed: list[str] = []
    if len(supported) > MAX_NONINTERCEPT_SHARED:
        ranked = sorted(
            supported,
            key=lambda term: (float(adjusted[term]), canonical_index[term]),
        )
        keep = set(ranked[:MAX_NONINTERCEPT_SHARED])
        removed = [term for term in supported if term not in keep]
        supported = [term for term in nonintercept if term in keep]

    accepted = ("1",) + tuple(supported)
    return SharedRecertificationResult(
        candidate_family=family,
        accepted_shared_terms=accepted,
        diagnostics=diagnostics,
        holm=holm,
        rank_abstentions=tuple(rank_abstentions),
        capacity_truncated=bool(removed),
        removed_by_capacity=tuple(removed),
    )
