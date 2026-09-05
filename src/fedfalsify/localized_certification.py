"""Selector screening and untouched-Probe localized certification.

The hypothesis identity (candidate, provenance, role, outside set, Discovery
sign) is immutable after Discovery. Selector may only remove hypotheses. Probe
then tests the complete surviving family and applies Holm before deterministic
safety filters.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from statistics import median
from typing import Sequence

import numpy as np

from .basis import TermCatalog
from .linear_algebra import fit_from_sufficient_stats
from .multiple_testing import MultiplicityResult, holm_adjust
from .nested_tests import NestedFResult, aggregate_scope, partial_nested_f
from .role_localization_v12 import FrozenLocalizedHypothesis
from .sufficient_stats import SufficientStatsPacket, subset_packet

DEV_ALPHA = 0.05
OUTSIDE_TOLERANCE = 1e-10
MAX_LOCALIZED_TERMS = 2


@dataclass(frozen=True)
class SelectorLocalizedDiagnostic:
    term: str
    source_term: str
    identity: tuple[object, ...]
    survived: bool
    reason: str
    role_raw_p_value: float | None
    role_candidate_sign: int
    role_median_gain: float | None
    outside_reduced_sse: float | None
    outside_full_sse: float | None
    outside_delta_sse: float | None
    outside_safe: bool


@dataclass(frozen=True)
class SelectorScreeningResult:
    input_hypotheses: tuple[FrozenLocalizedHypothesis, ...]
    surviving_hypotheses: tuple[FrozenLocalizedHypothesis, ...]
    diagnostics: tuple[SelectorLocalizedDiagnostic, ...]


@dataclass(frozen=True)
class ProbeLocalizedDiagnostic:
    term: str
    source_term: str
    identity: tuple[object, ...]
    reason: str
    raw_p_value: float
    holm_adjusted_p_value: float
    holm_rejected: bool
    role_candidate_sign: int
    role_median_gain: float | None
    outside_reduced_sse: float | None
    outside_full_sse: float | None
    outside_delta_sse: float | None
    outside_safe: bool
    final_accepted: bool


@dataclass(frozen=True)
class LocalizedCertificationResult:
    frozen_hypotheses: tuple[FrozenLocalizedHypothesis, ...]
    family_identities: tuple[tuple[object, ...], ...]
    holm: MultiplicityResult
    diagnostics: tuple[ProbeLocalizedDiagnostic, ...]
    accepted_hypotheses: tuple[FrozenLocalizedHypothesis, ...]
    accepted_terms: tuple[str, ...]
    source_ambiguity: bool
    capacity_ambiguous: bool


@dataclass(frozen=True)
class _FixedScopeEvidence:
    admissible: bool
    reason: str
    role_result: NestedFResult | None
    role_median_gain: float | None
    outside_reduced_sse: float | None
    outside_full_sse: float | None
    outside_safe: bool


def outside_safe(*, reduced_sse: float, full_sse: float) -> bool:
    return bool(float(full_sse) <= float(reduced_sse) + OUTSIDE_TOLERANCE)


def _client_index_map(packets: Sequence[SufficientStatsPacket]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, packet in enumerate(packets):
        client_id = str(packet.client_id)
        if client_id in mapping:
            raise ValueError("Selector/Probe client IDs must be unique")
        mapping[client_id] = index
    return mapping


def _resolve_frozen_scope(
    hypothesis: FrozenLocalizedHypothesis,
    packets: Sequence[SufficientStatsPacket],
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    mapping = _client_index_map(packets)
    role_ids = tuple(hypothesis.role_client_ids)
    outside_ids = tuple(hypothesis.outside_client_ids)
    if not role_ids or not outside_ids:
        raise ValueError("frozen localized scope must be non-vacuous")
    if set(role_ids) & set(outside_ids):
        raise ValueError("frozen role and outside IDs must be disjoint")
    if set(role_ids) | set(outside_ids) != set(mapping):
        raise ValueError("frozen role/outside IDs must partition current clients exactly")
    return (
        tuple(mapping[client_id] for client_id in role_ids),
        tuple(mapping[client_id] for client_id in outside_ids),
    )


def _transported_outside_sse(
    packet: SufficientStatsPacket,
    shared_terms: tuple[str, ...],
    candidate_term: str,
    candidate_coefficient: float,
) -> tuple[float, float]:
    """Compare outside fit with a role-estimated candidate effect held fixed.

    Shared nuisance coefficients are re-estimated on the outside scope in both
    models. In the transported FULL model only the candidate coefficient is
    fixed to the role-scope estimate, making non-degradation a real safety test
    rather than the tautology obtained by freely refitting the extra term.
    """
    full_terms = tuple(shared_terms) + (candidate_term,)
    selected = subset_packet(packet, full_terms)
    reduced_fit = fit_from_sufficient_stats(selected, tuple(shared_terms))
    if not reduced_fit.full_rank:
        raise ValueError("STRUCTURAL-RANK-AMBIGUOUS")

    candidate_index = selected.terms.index(candidate_term)
    shared_indices = tuple(selected.terms.index(term) for term in shared_terms)
    gram = np.asarray(selected.gram, dtype=float)
    target = np.asarray(selected.target, dtype=float)
    delta = float(candidate_coefficient)

    shared_gram = gram[np.ix_(shared_indices, shared_indices)]
    cross = gram[np.asarray(shared_indices, dtype=int), candidate_index]
    adjusted_target = target[np.asarray(shared_indices, dtype=int)] - delta * cross
    adjusted_energy = (
        float(selected.target_energy)
        - 2.0 * delta * float(target[candidate_index])
        + delta * delta * float(gram[candidate_index, candidate_index])
    )
    numerical_limit = 1e-10 * max(1.0, abs(float(selected.target_energy)))
    if adjusted_energy < -numerical_limit:
        raise FloatingPointError("transported outside target energy became negative")
    adjusted_energy = max(0.0, float(adjusted_energy))

    adjusted_packet = SufficientStatsPacket(
        client_id=selected.client_id,
        support=selected.support,
        terms=tuple(shared_terms),
        gram=np.asarray(shared_gram, dtype=float),
        target=np.asarray(adjusted_target, dtype=float),
        target_energy=adjusted_energy,
        observed_support=tuple(selected.observed_support[index] for index in shared_indices),
    )
    transported_fit = fit_from_sufficient_stats(adjusted_packet, tuple(shared_terms))
    if not transported_fit.full_rank:
        raise ValueError("STRUCTURAL-RANK-AMBIGUOUS")
    return float(reduced_fit.sse), float(transported_fit.sse)


def _evaluate_fixed_scope(
    hypothesis: FrozenLocalizedHypothesis,
    shared_terms: tuple[str, ...],
    packets: Sequence[SufficientStatsPacket],
    catalog: TermCatalog,
) -> _FixedScopeEvidence:
    packets = tuple(packets)
    try:
        catalog.get(hypothesis.term)
        role_indices, outside_indices = _resolve_frozen_scope(hypothesis, packets)
        if hypothesis.term in shared_terms:
            raise ValueError("candidate already belongs to shared structure")
        full_terms = tuple(shared_terms) + (hypothesis.term,)
        role_packet = aggregate_scope(packets, role_indices)
        role_result = partial_nested_f(
            role_packet,
            tuple(shared_terms),
            full_terms,
            candidate_term=hypothesis.term,
        )
    except (KeyError, ValueError):
        return _FixedScopeEvidence(False, "STRUCTURAL-NESTING-FAIL", None, None, None, None, False)

    if not role_result.admissible:
        return _FixedScopeEvidence(
            False, role_result.reason, role_result, None, None, None, False
        )

    gains: list[float] = []
    for index in role_indices:
        try:
            client_result = partial_nested_f(
                packets[index],
                tuple(shared_terms),
                full_terms,
                candidate_term=hypothesis.term,
            )
        except (KeyError, ValueError):
            return _FixedScopeEvidence(
                False, "STRUCTURAL-NESTING-FAIL", role_result, None, None, None, False
            )
        if not client_result.admissible:
            return _FixedScopeEvidence(
                False, client_result.reason, role_result, None, None, None, False
            )
        gains.append(float(client_result.raw_gain))
    role_median_gain = float(median(gains)) if gains else None

    try:
        outside_packet = aggregate_scope(packets, outside_indices)
        reduced_sse, full_sse = _transported_outside_sse(
            outside_packet,
            tuple(shared_terms),
            hypothesis.term,
            float(role_result.candidate_coefficient),
        )
    except (KeyError, ValueError):
        return _FixedScopeEvidence(
            False, "STRUCTURAL-RANK-AMBIGUOUS", role_result, role_median_gain,
            None, None, False,
        )

    return _FixedScopeEvidence(
        admissible=True,
        reason="OK",
        role_result=role_result,
        role_median_gain=role_median_gain,
        outside_reduced_sse=float(reduced_sse),
        outside_full_sse=float(full_sse),
        outside_safe=outside_safe(reduced_sse=reduced_sse, full_sse=full_sse),
    )


def screen_on_selector(
    hypotheses: Sequence[FrozenLocalizedHypothesis],
    shared_terms: tuple[str, ...],
    selector_packets: Sequence[SufficientStatsPacket],
    catalog: TermCatalog,
) -> SelectorScreeningResult:
    hypotheses = tuple(hypotheses)
    packets = tuple(selector_packets)
    survivors: list[FrozenLocalizedHypothesis] = []
    diagnostics: list[SelectorLocalizedDiagnostic] = []

    for hypothesis in hypotheses:
        evidence = _evaluate_fixed_scope(hypothesis, tuple(shared_terms), packets, catalog)
        role_result = evidence.role_result
        role_p = (
            float(role_result.p_value)
            if role_result is not None and role_result.admissible
            else None
        )
        role_sign = int(role_result.candidate_sign) if role_result is not None else 0
        reason = evidence.reason
        survived = False
        if evidence.admissible:
            if evidence.role_median_gain is None or evidence.role_median_gain <= 0.0:
                reason = "NONPOSITIVE-ROLE-GAIN"
            elif role_sign != int(hypothesis.discovery_sign):
                reason = "SCOPE-SIGN-MISMATCH"
            elif not evidence.outside_safe:
                reason = "OUTSIDE-NONDEGRADATION-FAIL"
            else:
                reason = "SELECTOR-SURVIVED"
                survived = True
                survivors.append(hypothesis)

        diagnostics.append(
            SelectorLocalizedDiagnostic(
                term=hypothesis.term,
                source_term=hypothesis.source_term,
                identity=hypothesis.identity,
                survived=survived,
                reason=reason,
                role_raw_p_value=role_p,
                role_candidate_sign=role_sign,
                role_median_gain=evidence.role_median_gain,
                outside_reduced_sse=evidence.outside_reduced_sse,
                outside_full_sse=evidence.outside_full_sse,
                outside_delta_sse=(
                    None
                    if evidence.outside_reduced_sse is None or evidence.outside_full_sse is None
                    else float(evidence.outside_full_sse - evidence.outside_reduced_sse)
                ),
                outside_safe=bool(evidence.outside_safe),
            )
        )

    return SelectorScreeningResult(hypotheses, tuple(survivors), tuple(diagnostics))


def certify_on_probe(
    hypotheses: Sequence[FrozenLocalizedHypothesis],
    shared_terms: tuple[str, ...],
    probe_packets: Sequence[SufficientStatsPacket],
    catalog: TermCatalog,
) -> LocalizedCertificationResult:
    hypotheses = tuple(hypotheses)
    packets = tuple(probe_packets)
    if len({item.term for item in hypotheses}) != len(hypotheses):
        raise ValueError("Probe localized hypothesis terms must be unique")

    evidence_by_term: dict[str, _FixedScopeEvidence] = {}
    raw_p_values: list[float] = []
    for hypothesis in hypotheses:
        evidence = _evaluate_fixed_scope(hypothesis, tuple(shared_terms), packets, catalog)
        evidence_by_term[hypothesis.term] = evidence
        if evidence.admissible and evidence.role_result is not None:
            raw_p_values.append(float(evidence.role_result.p_value))
        else:
            raw_p_values.append(1.0)

    names = tuple(item.term for item in hypotheses)
    holm = holm_adjust(names, raw_p_values, alpha=DEV_ALPHA)
    adjusted = dict(zip(holm.names, holm.adjusted_values))
    rejected = set(holm.rejected)

    diagnostics: list[ProbeLocalizedDiagnostic] = []
    accepted_terms: list[str] = []
    for hypothesis, raw_p in zip(hypotheses, raw_p_values):
        evidence = evidence_by_term[hypothesis.term]
        role_result = evidence.role_result
        role_sign = int(role_result.candidate_sign) if role_result is not None else 0
        reason = evidence.reason
        accepted = False
        if evidence.admissible:
            if hypothesis.term not in rejected:
                reason = "HOLM-NOT-REJECTED"
            elif evidence.role_median_gain is None or evidence.role_median_gain <= 0.0:
                reason = "NONPOSITIVE-ROLE-GAIN"
            elif role_sign != int(hypothesis.discovery_sign):
                reason = "SCOPE-SIGN-MISMATCH"
            elif not evidence.outside_safe:
                reason = "OUTSIDE-NONDEGRADATION-FAIL"
            else:
                reason = "ACCEPTED-PRE-AMBIGUITY"
                accepted = True
                accepted_terms.append(hypothesis.term)

        diagnostics.append(
            ProbeLocalizedDiagnostic(
                term=hypothesis.term,
                source_term=hypothesis.source_term,
                identity=hypothesis.identity,
                reason=reason,
                raw_p_value=float(raw_p),
                holm_adjusted_p_value=float(adjusted[hypothesis.term]),
                holm_rejected=bool(hypothesis.term in rejected),
                role_candidate_sign=role_sign,
                role_median_gain=evidence.role_median_gain,
                outside_reduced_sse=evidence.outside_reduced_sse,
                outside_full_sse=evidence.outside_full_sse,
                outside_delta_sse=(
                    None
                    if evidence.outside_reduced_sse is None or evidence.outside_full_sse is None
                    else float(evidence.outside_full_sse - evidence.outside_reduced_sse)
                ),
                outside_safe=bool(evidence.outside_safe),
                final_accepted=accepted,
            )
        )

    source_groups: dict[str, list[str]] = {}
    for hypothesis in hypotheses:
        if hypothesis.term in accepted_terms:
            source_groups.setdefault(hypothesis.source_term, []).append(hypothesis.term)
    ambiguous_terms = {
        term
        for terms in source_groups.values()
        if len(terms) > 1
        for term in terms
    }
    source_ambiguity = bool(ambiguous_terms)
    if ambiguous_terms:
        accepted_terms = [term for term in accepted_terms if term not in ambiguous_terms]
        diagnostics = [
            replace(
                item,
                reason=("SOURCE-SCOPE-AMBIGUOUS" if item.term in ambiguous_terms else item.reason),
                final_accepted=(item.term in accepted_terms),
            )
            for item in diagnostics
        ]

    capacity_ambiguous = bool(len(accepted_terms) > MAX_LOCALIZED_TERMS)
    if capacity_ambiguous:
        capacity_terms = set(accepted_terms)
        accepted_terms = []
        diagnostics = [
            replace(
                item,
                reason=("LOCALIZED-CAPACITY-AMBIGUOUS" if item.term in capacity_terms else item.reason),
                final_accepted=False if item.term in capacity_terms else item.final_accepted,
            )
            for item in diagnostics
        ]

    accepted_set = set(accepted_terms)
    accepted_hypotheses = tuple(item for item in hypotheses if item.term in accepted_set)
    return LocalizedCertificationResult(
        frozen_hypotheses=hypotheses,
        family_identities=tuple(item.identity for item in hypotheses),
        holm=holm,
        diagnostics=tuple(diagnostics),
        accepted_hypotheses=accepted_hypotheses,
        accepted_terms=tuple(item.term for item in accepted_hypotheses),
        source_ambiguity=source_ambiguity,
        capacity_ambiguous=capacity_ambiguous,
    )
