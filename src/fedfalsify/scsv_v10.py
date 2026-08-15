"""FedFalsify v10: SCSV with Anchor Quarantine and Client Consensus.

Scientific rules are frozen in research/TRANSACTIONS_SCSV_AQCC_V10_PROTOCOL.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from time import perf_counter
from typing import Sequence

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .crossfit_redesign import _ordered_terms, _refit, partition_clients
from .crossfit_surrogate import split_selector_probe
from .scsv_diagnostic import SufficientPacket, _build_packets, _packet_sse
from .scsv_v6 import SCSVV6Output, scsv_cert_method
from .scsv_v8 import (
    ProbeState,
    V8RoleHypothesis,
    _anchor_discovery_candidate,
    _estimate_pair,
    _outside_safety,
    _pair_invariant,
    _probe_state,
    _residual_cross,
    _role_hypothesis,
)
from .scsv_v9 import _evidence_pass as _v9_evidence_pass
from .scsv_v9 import _pooled_delta


@dataclass(frozen=True)
class V10SourceDiagnostic:
    source_term: str
    source_in_core_anchor: bool
    source_in_bank: bool
    source_coefficient: float | None
    selector_support: int
    selector_full_sse: float | None
    selector_reduced_sse: float | None
    selector_delta: float | None
    selector_state: ProbeState
    probe_support: int
    probe_full_sse: float | None
    probe_reduced_sse: float | None
    probe_delta: float | None
    probe_state: ProbeState
    pooled_delta: float | None
    client_gains: tuple[float, ...]
    client_median_gain: float | None
    client_positive_fraction: float
    qualified: bool
    invariant: bool


@dataclass(frozen=True)
class V10DeviationDiagnostic:
    term: str
    source_term: str
    was_anchor_exception: bool
    quarantined: bool
    in_response_bank: bool
    role_proposed: bool
    role_admissible: bool
    role_client_ids: tuple[str, ...]
    outside_client_ids: tuple[str, ...]
    occupancy_gap: float
    role_mean_occupancy: float
    outside_mean_occupancy: float
    source_in_core_anchor: bool
    source_qualified: bool
    source_coefficient: float | None
    deviation_coefficient: float | None
    selector_support: int
    selector_full_sse: float | None
    selector_reduced_sse: float | None
    selector_delta: float | None
    selector_state: ProbeState
    probe_support: int
    probe_full_sse: float | None
    probe_reduced_sse: float | None
    probe_delta: float | None
    probe_state: ProbeState
    pooled_delta: float | None
    client_gains: tuple[float, ...]
    client_median_gain: float | None
    client_positive_fraction: float
    selector_outside_full_sse: float
    selector_outside_reduced_sse: float
    selector_outside_safe: bool
    probe_outside_full_sse: float
    probe_outside_reduced_sse: float
    probe_outside_safe: bool
    pair_invariant: bool
    positive_pre_ambiguity: bool
    rejection_reason: str


@dataclass(frozen=True)
class SCSVAQCCV10Output:
    method: str
    candidate: CandidateEquation
    anchor: SCSVV6Output
    anchor_structure: tuple[str, ...]
    ordinary_anchor_structure: tuple[str, ...]
    quarantined_anchor_exceptions: tuple[str, ...]
    final_structure: tuple[str, ...]
    bank_terms: tuple[str, ...]
    candidate_deviations: tuple[str, ...]
    role_proposed_candidates: tuple[str, ...]
    diagnostics: tuple[V10DeviationDiagnostic, ...]
    source_diagnostics: tuple[V10SourceDiagnostic, ...]
    accepted_deviations: tuple[str, ...]
    recertified_anchor_exceptions: tuple[str, ...]
    removed_anchor_exceptions: tuple[str, ...]
    added_sources: tuple[str, ...]
    source_ambiguity: bool
    global_ambiguity: bool
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _anchor_exception_terms(anchor: SCSVV6Output, catalog: TermCatalog) -> tuple[str, ...]:
    return tuple(
        term
        for term in anchor.selector_structure
        if term != "1" and catalog.get(term).kind == "exception"
    )


def _ordinary_anchor_terms(anchor: SCSVV6Output, catalog: TermCatalog) -> tuple[str, ...]:
    return tuple(
        term
        for term in anchor.selector_structure
        if term == "1" or catalog.get(term).kind != "exception"
    )


def _filtered_anchor_candidate(
    anchor: SCSVV6Output,
    catalog: TermCatalog,
    *,
    quarantine_anchor: bool,
) -> CandidateEquation:
    discovery = _anchor_discovery_candidate(anchor)
    if not quarantine_anchor:
        return CandidateEquation(
            discovery.active_terms,
            discovery.coefficients,
            "scsv-aqcc-v10-full-anchor-discovery",
        )
    keep = set(_ordinary_anchor_terms(anchor, catalog))
    terms = tuple(term for term in discovery.active_terms if term in keep)
    coefficient_map = dict(zip(discovery.active_terms, discovery.coefficients))
    return CandidateEquation(
        terms,
        tuple(float(coefficient_map[term]) for term in terms),
        "scsv-aqcc-v10-core-anchor-discovery",
    )


def _source_model(
    core_anchor: CandidateEquation,
    source: str,
    fit_packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    outside_indices: tuple[int, ...],
    catalog: TermCatalog,
) -> tuple[CandidateEquation, CandidateEquation, float]:
    if source in core_anchor.active_terms:
        raise ValueError("source qualification is only for a source absent from core anchor")
    if not outside_indices:
        raise ValueError("source qualification requires outside-role clients")

    anchor_map = dict(zip(core_anchor.active_terms, core_anchor.coefficients))
    frozen_terms = tuple(core_anchor.active_terms)
    frozen_coefficients = tuple(float(anchor_map[term]) for term in frozen_terms)
    source_index = all_terms.index(source)
    numerator = 0.0
    denominator = 0.0
    for index in outside_indices:
        packet = fit_packets[index]
        numerator += _residual_cross(
            packet,
            target_term=source,
            frozen_terms=frozen_terms,
            frozen_coefficients=frozen_coefficients,
            all_terms=all_terms,
        )
        denominator += float(packet.gram[source_index, source_index])
    beta = float(numerator / (denominator + 1e-10))

    structure = _ordered_terms(catalog, (set(core_anchor.active_terms) - {"1"}) | {source})
    coefficient_map = {term: float(value) for term, value in anchor_map.items()}
    coefficient_map[source] = beta
    full = CandidateEquation(
        structure,
        tuple(float(coefficient_map[term]) for term in structure),
        f"scsv-aqcc-v10-source-full-{source}",
    )
    reduced = CandidateEquation(
        structure,
        tuple(0.0 if term == source else float(coefficient_map[term]) for term in structure),
        f"scsv-aqcc-v10-source-zero-{source}",
    )
    return full, reduced, beta


def _conditional_summary(
    full: CandidateEquation,
    reduced: CandidateEquation,
    packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    indices: tuple[int, ...],
) -> tuple[int, float | None, float | None, float | None, ProbeState]:
    if not indices:
        return 0, None, None, None, "CONTRADICTED"
    support = int(sum(packets[index].support for index in indices))
    full_sse = float(sum(_packet_sse(packets[index], all_terms, full) for index in indices))
    reduced_sse = float(sum(_packet_sse(packets[index], all_terms, reduced) for index in indices))
    delta = float(
        np.log(max(full_sse, 1e-15) / max(reduced_sse, 1e-15))
        + np.log(max(support, 2)) / max(support, 1)
    )
    return support, full_sse, reduced_sse, delta, _probe_state(full_sse, reduced_sse, delta)


def _client_gains(
    full: CandidateEquation,
    reduced: CandidateEquation,
    selector_packets: Sequence[SufficientPacket],
    probe_packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    indices: tuple[int, ...],
) -> tuple[tuple[float, ...], float | None, float]:
    gains: list[float] = []
    for index in indices:
        selector_gain = float(
            _packet_sse(selector_packets[index], all_terms, reduced)
            - _packet_sse(selector_packets[index], all_terms, full)
        )
        probe_gain = float(
            _packet_sse(probe_packets[index], all_terms, reduced)
            - _packet_sse(probe_packets[index], all_terms, full)
        )
        gains.append(selector_gain + probe_gain)
    if not gains:
        return (), None, 0.0
    med = float(median(gains))
    positive_fraction = float(sum(value > 0.0 for value in gains) / len(gains))
    return tuple(float(value) for value in gains), med, positive_fraction


def _consensus_pass(pooled_delta: float | None, client_median_gain: float | None) -> bool:
    return bool(
        pooled_delta is not None
        and pooled_delta < 0.0
        and client_median_gain is not None
        and client_median_gain > 0.0
    )


def _qualify_source(
    core_anchor: CandidateEquation,
    source: str,
    fit_packets: Sequence[SufficientPacket],
    selector_packets: Sequence[SufficientPacket],
    probe_packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    role: V8RoleHypothesis,
    catalog: TermCatalog,
    *,
    source_in_bank: bool,
    split_veto: bool,
) -> tuple[V10SourceDiagnostic, CandidateEquation | None]:
    if source in core_anchor.active_terms:
        coef = float(dict(zip(core_anchor.active_terms, core_anchor.coefficients))[source])
        return V10SourceDiagnostic(
            source_term=source,
            source_in_core_anchor=True,
            source_in_bank=source_in_bank,
            source_coefficient=coef,
            selector_support=0,
            selector_full_sse=None,
            selector_reduced_sse=None,
            selector_delta=None,
            selector_state="SUPPORTED",
            probe_support=0,
            probe_full_sse=None,
            probe_reduced_sse=None,
            probe_delta=None,
            probe_state="SUPPORTED",
            pooled_delta=-1.0,
            client_gains=(),
            client_median_gain=1.0,
            client_positive_fraction=1.0,
            qualified=True,
            invariant=True,
        ), core_anchor

    if not source_in_bank or not role.admissible:
        return V10SourceDiagnostic(
            source_term=source,
            source_in_core_anchor=False,
            source_in_bank=source_in_bank,
            source_coefficient=None,
            selector_support=0,
            selector_full_sse=None,
            selector_reduced_sse=None,
            selector_delta=None,
            selector_state="CONTRADICTED",
            probe_support=0,
            probe_full_sse=None,
            probe_reduced_sse=None,
            probe_delta=None,
            probe_state="CONTRADICTED",
            pooled_delta=None,
            client_gains=(),
            client_median_gain=None,
            client_positive_fraction=0.0,
            qualified=False,
            invariant=False,
        ), None

    full, reduced, beta = _source_model(
        core_anchor,
        source,
        fit_packets,
        all_terms,
        role.outside_indices,
        catalog,
    )
    invariant = _pair_invariant(full, reduced, source)
    ss, sf, sr, sd, selector_state = _conditional_summary(
        full, reduced, selector_packets, all_terms, role.outside_indices
    )
    ps, pf, pr, pd, probe_state = _conditional_summary(
        full, reduced, probe_packets, all_terms, role.outside_indices
    )
    pooled = _pooled_delta(ss, sf, sr, ps, pf, pr)
    gains, med, frac = _client_gains(
        full,
        reduced,
        selector_packets,
        probe_packets,
        all_terms,
        role.outside_indices,
    )
    evidence_ok = (
        _v9_evidence_pass(selector_state, probe_state, pooled)
        if split_veto
        else _consensus_pass(pooled, med)
    )
    qualified = bool(invariant and evidence_ok)
    diag = V10SourceDiagnostic(
        source_term=source,
        source_in_core_anchor=False,
        source_in_bank=True,
        source_coefficient=float(beta),
        selector_support=int(ss),
        selector_full_sse=sf,
        selector_reduced_sse=sr,
        selector_delta=sd,
        selector_state=selector_state,
        probe_support=int(ps),
        probe_full_sse=pf,
        probe_reduced_sse=pr,
        probe_delta=pd,
        probe_state=probe_state,
        pooled_delta=pooled,
        client_gains=gains,
        client_median_gain=med,
        client_positive_fraction=frac,
        qualified=qualified,
        invariant=bool(invariant),
    )
    return diag, full if qualified else None


def scsv_aqcc_v10_method(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    max_shared_terms: int = 6,
    max_operational_exceptions: int = 2,
    max_final_terms: int = 10,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
    quarantine_anchor: bool = True,
    split_veto: bool = False,
) -> SCSVAQCCV10Output:
    """Run v6 anchor, quarantine exception terms, and apply v10 client consensus."""

    start = perf_counter()
    if max_shared_terms != 6 or max_operational_exceptions != 2 or max_final_terms != 10:
        raise ValueError("v10 caps are frozen at shared=6, exceptions=2, final=10")

    anchor = scsv_cert_method(
        datasets,
        catalog,
        seed=seed,
        max_terms=max_shared_terms,
        target_mse=target_mse,
        min_repair_score=min_repair_score,
        use_score_proposer=True,
    )
    anchor_set = set(anchor.selector_structure)
    bank_set = set(anchor.bank.candidate_terms)
    anchor_exceptions = _anchor_exception_terms(anchor, catalog)
    ordinary_anchor = _ordinary_anchor_terms(anchor, catalog)
    core_anchor = _filtered_anchor_candidate(anchor, catalog, quarantine_anchor=quarantine_anchor)

    if quarantine_anchor:
        quarantined = tuple(anchor_exceptions)
    else:
        quarantined = ()

    grammar_exceptions = tuple(
        term
        for term in catalog.names()
        if catalog.get(term).kind == "exception"
        and catalog.get(term).source_term is not None
        and (
            (quarantine_anchor and term in anchor_set)
            or (term not in anchor_set and catalog.get(term).source_term in bank_set)
        )
    )
    candidates = tuple(dict.fromkeys(quarantined + grammar_exceptions))

    final_structure = tuple(anchor.selector_structure) if not quarantine_anchor else tuple(ordinary_anchor)
    final_candidate = anchor.candidate
    diagnostics: list[V10DeviationDiagnostic] = []
    source_diags_by_source: dict[str, V10SourceDiagnostic] = {}
    candidate_deviations: list[str] = []
    role_proposed: list[str] = []
    positive_terms: list[str] = []
    positive_sources: dict[str, list[str]] = {}
    source_ambiguity = False
    global_ambiguity = False
    extra_communication = 0
    partitions = None

    if candidates:
        partitions = partition_clients(datasets, seed=seed, validation_fraction=0.30)
        selectors, probes = split_selector_probe(partitions, seed=seed)
        all_terms = tuple(
            dict.fromkeys(
                ("1",)
                + tuple(anchor.selector_structure)
                + tuple(anchor.bank.candidate_terms)
                + tuple(candidates)
            )
        )
        fit_packets, selector_packets, probe_packets, packet_bytes = _build_packets(
            partitions, selectors, probes, catalog, all_terms
        )
        extra_communication += int(packet_bytes)

        for term in candidates:
            metadata = catalog.get(term)
            source = metadata.source_term
            if source is None:
                continue
            was_anchor_exception = term in anchor_set and metadata.kind == "exception"
            in_bank = term in bank_set
            role = _role_hypothesis(fit_packets, all_terms, term)
            proposed = bool(not was_anchor_exception and role.admissible and not in_bank)
            admitted = bool(was_anchor_exception or in_bank or proposed)
            if not admitted:
                continue
            candidate_deviations.append(term)
            if proposed:
                role_proposed.append(term)

            if not role.admissible:
                diagnostics.append(
                    V10DeviationDiagnostic(
                        term=term,
                        source_term=source,
                        was_anchor_exception=was_anchor_exception,
                        quarantined=bool(quarantine_anchor and was_anchor_exception),
                        in_response_bank=in_bank,
                        role_proposed=proposed,
                        role_admissible=False,
                        role_client_ids=(),
                        outside_client_ids=tuple(item.client_id for item in fit_packets),
                        occupancy_gap=float(role.separation_gap),
                        role_mean_occupancy=float(role.role_mean_occupancy),
                        outside_mean_occupancy=float(role.outside_mean_occupancy),
                        source_in_core_anchor=source in set(core_anchor.active_terms),
                        source_qualified=False,
                        source_coefficient=None,
                        deviation_coefficient=None,
                        selector_support=0,
                        selector_full_sse=None,
                        selector_reduced_sse=None,
                        selector_delta=None,
                        selector_state="CONTRADICTED",
                        probe_support=0,
                        probe_full_sse=None,
                        probe_reduced_sse=None,
                        probe_delta=None,
                        probe_state="CONTRADICTED",
                        pooled_delta=None,
                        client_gains=(),
                        client_median_gain=None,
                        client_positive_fraction=0.0,
                        selector_outside_full_sse=0.0,
                        selector_outside_reduced_sse=0.0,
                        selector_outside_safe=False,
                        probe_outside_full_sse=0.0,
                        probe_outside_reduced_sse=0.0,
                        probe_outside_safe=False,
                        pair_invariant=False,
                        positive_pre_ambiguity=False,
                        rejection_reason="ROLE-NOT-IDENTIFIED",
                    )
                )
                continue

            source_diag, pair_anchor = _qualify_source(
                core_anchor,
                source,
                fit_packets,
                selector_packets,
                probe_packets,
                all_terms,
                role,
                catalog,
                source_in_bank=source in bank_set,
                split_veto=split_veto,
            )
            source_diags_by_source.setdefault(source, source_diag)
            if not source_diag.qualified or pair_anchor is None:
                diagnostics.append(
                    V10DeviationDiagnostic(
                        term=term,
                        source_term=source,
                        was_anchor_exception=was_anchor_exception,
                        quarantined=bool(quarantine_anchor and was_anchor_exception),
                        in_response_bank=in_bank,
                        role_proposed=proposed,
                        role_admissible=True,
                        role_client_ids=role.role_client_ids,
                        outside_client_ids=role.outside_client_ids,
                        occupancy_gap=float(role.separation_gap),
                        role_mean_occupancy=float(role.role_mean_occupancy),
                        outside_mean_occupancy=float(role.outside_mean_occupancy),
                        source_in_core_anchor=source in set(core_anchor.active_terms),
                        source_qualified=False,
                        source_coefficient=source_diag.source_coefficient,
                        deviation_coefficient=None,
                        selector_support=0,
                        selector_full_sse=None,
                        selector_reduced_sse=None,
                        selector_delta=None,
                        selector_state="CONTRADICTED",
                        probe_support=0,
                        probe_full_sse=None,
                        probe_reduced_sse=None,
                        probe_delta=None,
                        probe_state="CONTRADICTED",
                        pooled_delta=None,
                        client_gains=(),
                        client_median_gain=None,
                        client_positive_fraction=0.0,
                        selector_outside_full_sse=0.0,
                        selector_outside_reduced_sse=0.0,
                        selector_outside_safe=False,
                        probe_outside_full_sse=0.0,
                        probe_outside_reduced_sse=0.0,
                        probe_outside_safe=False,
                        pair_invariant=False,
                        positive_pre_ambiguity=False,
                        rejection_reason="SOURCE-NOT-QUALIFIED",
                    )
                )
                continue

            full, reduced, beta_source, delta = _estimate_pair(
                pair_anchor,
                source,
                term,
                fit_packets,
                all_terms,
                role,
                catalog,
            )
            invariant = _pair_invariant(full, reduced, term)
            ss, sf, sr, sd, selector_state = _conditional_summary(
                full, reduced, selector_packets, all_terms, role.role_indices
            )
            ps, pf, pr, pd, probe_state = _conditional_summary(
                full, reduced, probe_packets, all_terms, role.role_indices
            )
            pooled = _pooled_delta(ss, sf, sr, ps, pf, pr)
            gains, med, frac = _client_gains(
                full,
                reduced,
                selector_packets,
                probe_packets,
                all_terms,
                role.role_indices,
            )
            sof, sor, sos = _outside_safety(
                full, reduced, selector_packets, all_terms, role.outside_indices
            )
            pof, por, pos = _outside_safety(
                full, reduced, probe_packets, all_terms, role.outside_indices
            )
            evidence_positive = (
                _v9_evidence_pass(selector_state, probe_state, pooled)
                if split_veto
                else _consensus_pass(pooled, med)
            )
            positive = bool(
                source_diag.qualified
                and invariant
                and sos
                and pos
                and evidence_positive
            )
            if positive:
                positive_terms.append(term)
                positive_sources.setdefault(source, []).append(term)

            reason = "ACCEPTED" if positive else (
                "PAIR-INVARIANT-FAIL"
                if not invariant
                else "OUTSIDE-INVARIANT-FAIL"
                if not (sos and pos)
                else "HELDOUT-SPLIT-CONTRADICTION"
                if split_veto and (selector_state == "CONTRADICTED" or probe_state == "CONTRADICTED")
                else "POOLED-NOT-SUPPORTED"
                if pooled is None or pooled >= 0.0
                else "CLIENT-MEDIAN-CONTRADICTED"
                if med is None or med <= 0.0
                else "EVIDENCE-NOT-SUPPORTED"
            )
            diagnostics.append(
                V10DeviationDiagnostic(
                    term=term,
                    source_term=source,
                    was_anchor_exception=was_anchor_exception,
                    quarantined=bool(quarantine_anchor and was_anchor_exception),
                    in_response_bank=in_bank,
                    role_proposed=proposed,
                    role_admissible=True,
                    role_client_ids=role.role_client_ids,
                    outside_client_ids=role.outside_client_ids,
                    occupancy_gap=float(role.separation_gap),
                    role_mean_occupancy=float(role.role_mean_occupancy),
                    outside_mean_occupancy=float(role.outside_mean_occupancy),
                    source_in_core_anchor=source in set(core_anchor.active_terms),
                    source_qualified=True,
                    source_coefficient=float(beta_source),
                    deviation_coefficient=float(delta),
                    selector_support=int(ss),
                    selector_full_sse=sf,
                    selector_reduced_sse=sr,
                    selector_delta=sd,
                    selector_state=selector_state,
                    probe_support=int(ps),
                    probe_full_sse=pf,
                    probe_reduced_sse=pr,
                    probe_delta=pd,
                    probe_state=probe_state,
                    pooled_delta=pooled,
                    client_gains=gains,
                    client_median_gain=med,
                    client_positive_fraction=frac,
                    selector_outside_full_sse=float(sof),
                    selector_outside_reduced_sse=float(sor),
                    selector_outside_safe=bool(sos),
                    probe_outside_full_sse=float(pof),
                    probe_outside_reduced_sse=float(por),
                    probe_outside_safe=bool(pos),
                    pair_invariant=bool(invariant),
                    positive_pre_ambiguity=positive,
                    rejection_reason=reason,
                )
            )

        ambiguous_sources = {source for source, terms in positive_sources.items() if len(terms) > 1}
        source_ambiguity = bool(ambiguous_sources)
        accepted = tuple(
            term
            for term in positive_terms
            if catalog.get(term).source_term not in ambiguous_sources
        )
        if len(accepted) > max_operational_exceptions:
            global_ambiguity = True
            accepted = ()
    else:
        accepted = ()

    added_sources = tuple(
        dict.fromkeys(
            catalog.get(term).source_term
            for term in accepted
            if catalog.get(term).source_term not in set(core_anchor.active_terms)
        )
    )
    base_terms = set(anchor.selector_structure) if not quarantine_anchor else set(ordinary_anchor)
    final_structure = _ordered_terms(
        catalog,
        (base_terms - {"1"}) | set(accepted) | set(added_sources),
    )
    if len(final_structure) > max_final_terms:
        raise RuntimeError("v10 final structure exceeded frozen ten-term cap")

    ordinary_set = set(ordinary_anchor)
    if not ordinary_set.issubset(set(final_structure)):
        raise RuntimeError("v10 deleted an ordinary/core anchor term")
    if len(accepted) > max_operational_exceptions:
        raise RuntimeError("v10 accepted too many operational exceptions")

    if tuple(final_structure) != tuple(anchor.selector_structure):
        if partitions is None:
            partitions = partition_clients(datasets, seed=seed, validation_fraction=0.30)
        final_candidate, refit_bytes = _refit(
            partitions,
            catalog,
            final_structure,
            include_validation=True,
            candidate_id=(
                "scsv-aqcc-v10-full-final"
                if quarantine_anchor and not split_veto
                else "scsv-aqcc-v10-no-quarantine-final"
                if not quarantine_anchor
                else "scsv-aqcc-v10-split-veto-final"
            ),
        )
        extra_communication += int(refit_bytes)
    else:
        final_candidate = anchor.candidate

    recertified_anchor = tuple(term for term in accepted if term in set(anchor_exceptions))
    removed_anchor = tuple(
        term
        for term in anchor_exceptions
        if quarantine_anchor and term not in set(recertified_anchor)
    )
    method = (
        "scsv-aqcc-v10-full"
        if quarantine_anchor and not split_veto
        else "scsv-aqcc-v10-no-quarantine"
        if not quarantine_anchor
        else "scsv-aqcc-v10-split-veto"
    )
    stop_reason = (
        f"SCSV-AQCC v10; quarantine={int(quarantine_anchor)}; split_veto={int(split_veto)}; "
        f"anchor={','.join(anchor.selector_structure)}; ordinary={','.join(ordinary_anchor)}; "
        f"quarantined={','.join(quarantined)}; bank={','.join(anchor.bank.candidate_terms)}; "
        f"candidates={','.join(candidate_deviations)}; role_proposed={','.join(role_proposed)}; "
        f"accepted={','.join(accepted)}; removed_anchor={','.join(removed_anchor)}; "
        f"added_sources={','.join(added_sources)}; source_ambiguity={int(source_ambiguity)}; "
        f"global_ambiguity={int(global_ambiguity)}; final={','.join(final_structure)}"
    )
    return SCSVAQCCV10Output(
        method=method,
        candidate=final_candidate,
        anchor=anchor,
        anchor_structure=tuple(anchor.selector_structure),
        ordinary_anchor_structure=tuple(ordinary_anchor),
        quarantined_anchor_exceptions=tuple(quarantined),
        final_structure=tuple(final_structure),
        bank_terms=tuple(anchor.bank.candidate_terms),
        candidate_deviations=tuple(candidate_deviations),
        role_proposed_candidates=tuple(role_proposed),
        diagnostics=tuple(diagnostics),
        source_diagnostics=tuple(source_diags_by_source.values()),
        accepted_deviations=tuple(accepted),
        recertified_anchor_exceptions=tuple(recertified_anchor),
        removed_anchor_exceptions=tuple(removed_anchor),
        added_sources=tuple(added_sources),
        source_ambiguity=bool(source_ambiguity),
        global_ambiguity=bool(global_ambiguity),
        communication_bytes=int(anchor.communication_bytes + extra_communication),
        runtime_seconds=float(perf_counter() - start),
        stop_reason=stop_reason,
    )
