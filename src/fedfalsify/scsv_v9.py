"""FedFalsify v9: SCSV with Role-Contrast Evidence Fusion.

Scientific rules are frozen in research/TRANSACTIONS_SCSV_RCEF_V9_PROTOCOL.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Sequence

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .crossfit_redesign import _ordered_terms, _refit, partition_clients
from .crossfit_surrogate import split_selector_probe
from .scsv_diagnostic import SufficientPacket, _build_packets
from .scsv_v6 import SCSVV6Output, scsv_cert_method
from .scsv_v8 import (
    ProbeState,
    V8RoleHypothesis,
    _anchor_discovery_candidate,
    _conditional_test,
    _estimate_pair,
    _outside_safety,
    _pair_invariant,
    _probe_state,
    _residual_cross,
    _role_hypothesis,
)


@dataclass(frozen=True)
class V9SourceDiagnostic:
    source_term: str
    source_in_anchor: bool
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
    qualified: bool
    invariant: bool


@dataclass(frozen=True)
class V9DeviationDiagnostic:
    term: str
    source_term: str
    in_response_bank: bool
    role_proposed: bool
    role_admissible: bool
    role_client_ids: tuple[str, ...]
    outside_client_ids: tuple[str, ...]
    occupancy_gap: float
    role_mean_occupancy: float
    outside_mean_occupancy: float
    source_in_anchor: bool
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
class SCSVRCEFV9Output:
    method: str
    candidate: CandidateEquation
    anchor: SCSVV6Output
    anchor_structure: tuple[str, ...]
    final_structure: tuple[str, ...]
    bank_terms: tuple[str, ...]
    candidate_deviations: tuple[str, ...]
    role_proposed_candidates: tuple[str, ...]
    diagnostics: tuple[V9DeviationDiagnostic, ...]
    source_diagnostics: tuple[V9SourceDiagnostic, ...]
    accepted_deviations: tuple[str, ...]
    added_sources: tuple[str, ...]
    source_ambiguity: bool
    global_ambiguity: bool
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _pooled_delta(
    selector_support: int,
    selector_full: float | None,
    selector_reduced: float | None,
    probe_support: int,
    probe_full: float | None,
    probe_reduced: float | None,
) -> float | None:
    if None in (selector_full, selector_reduced, probe_full, probe_reduced):
        return None
    support = int(selector_support + probe_support)
    if support <= 0:
        return None
    full = float(selector_full) + float(probe_full)
    reduced = float(selector_reduced) + float(probe_reduced)
    return float(
        np.log(max(full, 1e-15) / max(reduced, 1e-15))
        + np.log(max(support, 2)) / max(support, 1)
    )


def _evidence_pass(
    selector_state: ProbeState,
    probe_state: ProbeState,
    pooled_delta: float | None,
) -> bool:
    return bool(
        selector_state != "CONTRADICTED"
        and probe_state != "CONTRADICTED"
        and pooled_delta is not None
        and pooled_delta < 0.0
    )


def _source_model(
    anchor_discovery: CandidateEquation,
    source: str,
    fit_packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    outside_indices: tuple[int, ...],
    catalog: TermCatalog,
) -> tuple[CandidateEquation, CandidateEquation, float]:
    if source in anchor_discovery.active_terms:
        raise ValueError("source qualification is only for a source absent from anchor")
    if not outside_indices:
        raise ValueError("source qualification requires outside-role clients")

    anchor_map = dict(zip(anchor_discovery.active_terms, anchor_discovery.coefficients))
    frozen_terms = tuple(anchor_discovery.active_terms)
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

    structure = _ordered_terms(
        catalog,
        (set(anchor_discovery.active_terms) - {"1"}) | {source},
    )
    coefficient_map = {term: float(value) for term, value in anchor_map.items()}
    coefficient_map[source] = beta
    full = CandidateEquation(
        structure,
        tuple(float(coefficient_map[term]) for term in structure),
        f"scsv-rcef-v9-source-full-{source}",
    )
    reduced = CandidateEquation(
        structure,
        tuple(0.0 if term == source else float(coefficient_map[term]) for term in structure),
        f"scsv-rcef-v9-source-zero-{source}",
    )
    return full, reduced, beta


def _source_invariant(full: CandidateEquation, reduced: CandidateEquation, source: str) -> bool:
    return _pair_invariant(full, reduced, source)


def _qualify_source(
    anchor_discovery: CandidateEquation,
    source: str,
    fit_packets: Sequence[SufficientPacket],
    selector_packets: Sequence[SufficientPacket],
    probe_packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    role: V8RoleHypothesis,
    catalog: TermCatalog,
    *,
    source_in_bank: bool,
) -> tuple[V9SourceDiagnostic, CandidateEquation | None]:
    if source in anchor_discovery.active_terms:
        diag = V9SourceDiagnostic(
            source_term=source,
            source_in_anchor=True,
            source_in_bank=source_in_bank,
            source_coefficient=float(dict(zip(anchor_discovery.active_terms, anchor_discovery.coefficients))[source]),
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
            qualified=True,
            invariant=True,
        )
        return diag, anchor_discovery

    if not source_in_bank or not role.admissible:
        diag = V9SourceDiagnostic(
            source_term=source,
            source_in_anchor=False,
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
            qualified=False,
            invariant=False,
        )
        return diag, None

    full, reduced, beta = _source_model(
        anchor_discovery,
        source,
        fit_packets,
        all_terms,
        role.outside_indices,
        catalog,
    )
    invariant = _source_invariant(full, reduced, source)
    ss, sf, sr, sd, _ = _conditional_test(
        full, reduced, selector_packets, all_terms, role.outside_indices
    )
    ps, pf, pr, pd, _ = _conditional_test(
        full, reduced, probe_packets, all_terms, role.outside_indices
    )
    selector_state = _probe_state(sf, sr, sd)
    probe_state = _probe_state(pf, pr, pd)
    pooled = _pooled_delta(ss, sf, sr, ps, pf, pr)
    qualified = bool(invariant and _evidence_pass(selector_state, probe_state, pooled))
    diag = V9SourceDiagnostic(
        source_term=source,
        source_in_anchor=False,
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
        qualified=qualified,
        invariant=bool(invariant),
    )
    return diag, full if qualified else None


def scsv_rcef_v9_method(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    max_shared_terms: int = 6,
    max_added_deviations: int = 2,
    max_final_terms: int = 10,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
    use_role_proposer: bool = True,
    evidence_fusion: bool = True,
) -> SCSVRCEFV9Output:
    """Run frozen v6 anchor followed by v9 role-contrast evidence fusion."""

    start = perf_counter()
    if max_shared_terms != 6 or max_added_deviations != 2 or max_final_terms != 10:
        raise ValueError("v9 caps are frozen at shared=6, deviations=2, final=10")

    anchor = scsv_cert_method(
        datasets,
        catalog,
        seed=seed,
        max_terms=max_shared_terms,
        target_mse=target_mse,
        min_repair_score=min_repair_score,
        use_score_proposer=True,
    )
    anchor_discovery = _anchor_discovery_candidate(anchor)
    anchor_set = set(anchor.selector_structure)
    bank_set = set(anchor.bank.candidate_terms)

    grammar_exceptions = tuple(
        term
        for term in catalog.names()
        if catalog.get(term).kind == "exception"
        and term not in anchor_set
        and catalog.get(term).source_term is not None
        and catalog.get(term).source_term in bank_set
    )

    final_structure = tuple(anchor.selector_structure)
    final_candidate = anchor.candidate
    diagnostics: list[V9DeviationDiagnostic] = []
    source_diags_by_source: dict[str, V9SourceDiagnostic] = {}
    candidate_deviations: list[str] = []
    role_proposed: list[str] = []
    positive_terms: list[str] = []
    positive_sources: dict[str, list[str]] = {}
    extra_communication = 0
    source_ambiguity = False
    global_ambiguity = False
    partitions = None

    if grammar_exceptions:
        partitions = partition_clients(datasets, seed=seed, validation_fraction=0.30)
        selectors, probes = split_selector_probe(partitions, seed=seed)
        all_terms = tuple(
            dict.fromkeys(
                ("1",)
                + tuple(anchor.selector_structure)
                + tuple(anchor.bank.candidate_terms)
                + tuple(grammar_exceptions)
            )
        )
        fit_packets, selector_packets, probe_packets, packet_bytes = _build_packets(
            partitions, selectors, probes, catalog, all_terms
        )
        extra_communication += int(packet_bytes)

        for term in grammar_exceptions:
            metadata = catalog.get(term)
            source = metadata.source_term
            if source is None:
                continue
            role = _role_hypothesis(fit_packets, all_terms, term)
            in_bank = term in bank_set
            proposed = bool(use_role_proposer and role.admissible and not in_bank)
            admitted = bool(in_bank or proposed)
            if not admitted:
                continue
            candidate_deviations.append(term)
            if proposed:
                role_proposed.append(term)

            if not role.admissible:
                diagnostics.append(
                    V9DeviationDiagnostic(
                        term=term,
                        source_term=source,
                        in_response_bank=in_bank,
                        role_proposed=proposed,
                        role_admissible=False,
                        role_client_ids=(),
                        outside_client_ids=tuple(item.client_id for item in fit_packets),
                        occupancy_gap=float(role.separation_gap),
                        role_mean_occupancy=float(role.role_mean_occupancy),
                        outside_mean_occupancy=float(role.outside_mean_occupancy),
                        source_in_anchor=source in anchor_set,
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
                anchor_discovery,
                source,
                fit_packets,
                selector_packets,
                probe_packets,
                all_terms,
                role,
                catalog,
                source_in_bank=source in bank_set,
            )
            source_diags_by_source.setdefault(source, source_diag)
            if not source_diag.qualified or pair_anchor is None:
                diagnostics.append(
                    V9DeviationDiagnostic(
                        term=term,
                        source_term=source,
                        in_response_bank=in_bank,
                        role_proposed=proposed,
                        role_admissible=True,
                        role_client_ids=role.role_client_ids,
                        outside_client_ids=role.outside_client_ids,
                        occupancy_gap=float(role.separation_gap),
                        role_mean_occupancy=float(role.role_mean_occupancy),
                        outside_mean_occupancy=float(role.outside_mean_occupancy),
                        source_in_anchor=source in anchor_set,
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
            ss, sf, sr, sd, selector_supported = _conditional_test(
                full, reduced, selector_packets, all_terms, role.role_indices
            )
            ps, pf, pr, pd, _ = _conditional_test(
                full, reduced, probe_packets, all_terms, role.role_indices
            )
            selector_state = _probe_state(sf, sr, sd)
            probe_state = _probe_state(pf, pr, pd)
            pooled = _pooled_delta(ss, sf, sr, ps, pf, pr)
            sof, sor, sos = _outside_safety(
                full, reduced, selector_packets, all_terms, role.outside_indices
            )
            pof, por, pos = _outside_safety(
                full, reduced, probe_packets, all_terms, role.outside_indices
            )

            if evidence_fusion:
                evidence_positive = _evidence_pass(selector_state, probe_state, pooled)
            else:
                evidence_positive = bool(selector_supported and probe_state != "CONTRADICTED")
            positive = bool(
                source_diag.qualified
                and invariant
                and sos
                and pos
                and evidence_positive
            )
            reason = "ACCEPTED" if positive else (
                "PAIR-INVARIANT-FAIL"
                if not invariant
                else "OUTSIDE-INVARIANT-FAIL"
                if not (sos and pos)
                else "SELECTOR-NOT-SUPPORTED"
                if not evidence_fusion and not selector_supported
                else "HELDOUT-CONTRADICTION"
                if selector_state == "CONTRADICTED" or probe_state == "CONTRADICTED"
                else "POOLED-NOT-SUPPORTED"
            )
            if positive:
                positive_terms.append(term)
                positive_sources.setdefault(source, []).append(term)

            diagnostics.append(
                V9DeviationDiagnostic(
                    term=term,
                    source_term=source,
                    in_response_bank=in_bank,
                    role_proposed=proposed,
                    role_admissible=True,
                    role_client_ids=role.role_client_ids,
                    outside_client_ids=role.outside_client_ids,
                    occupancy_gap=float(role.separation_gap),
                    role_mean_occupancy=float(role.role_mean_occupancy),
                    outside_mean_occupancy=float(role.outside_mean_occupancy),
                    source_in_anchor=source in anchor_set,
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
        if ambiguous_sources:
            source_ambiguity = True
        accepted = tuple(term for term in positive_terms if catalog.get(term).source_term not in ambiguous_sources)
        if len(accepted) > max_added_deviations:
            global_ambiguity = True
            accepted = ()

        added_sources = tuple(
            dict.fromkeys(
                catalog.get(term).source_term
                for term in accepted
                if catalog.get(term).source_term not in anchor_set
            )
        )
        final_structure = _ordered_terms(
            catalog,
            (set(anchor.selector_structure) - {"1"}) | set(accepted) | set(added_sources),
        )
        if len(final_structure) > max_final_terms:
            raise RuntimeError("v9 final structure exceeded frozen ten-term cap")

        if accepted:
            final_candidate, refit_bytes = _refit(
                partitions,
                catalog,
                final_structure,
                include_validation=True,
                candidate_id=(
                    "scsv-rcef-v9-full-final"
                    if evidence_fusion and use_role_proposer
                    else "scsv-rcef-v9-ablation-final"
                ),
            )
            extra_communication += int(refit_bytes)
    else:
        accepted = ()
        added_sources = ()

    if not set(anchor.selector_structure).issubset(set(final_structure)):
        raise RuntimeError("v9 deleted or replaced a frozen anchor term")
    if len(accepted) > max_added_deviations:
        raise RuntimeError("v9 accepted too many deviations")

    method = (
        "scsv-rcef-v9-full"
        if use_role_proposer and evidence_fusion
        else "scsv-rcef-v9-no-role-proposer"
        if not use_role_proposer and evidence_fusion
        else "scsv-rcef-v9-selector-only"
    )
    stop_reason = (
        f"SCSV-RCEF v9; role_proposer={int(use_role_proposer)}; fusion={int(evidence_fusion)}; "
        f"anchor={','.join(anchor.selector_structure)}; bank={','.join(anchor.bank.candidate_terms)}; "
        f"candidates={','.join(candidate_deviations)}; role_proposed={','.join(role_proposed)}; "
        f"accepted={','.join(accepted)}; added_sources={','.join(added_sources)}; "
        f"source_ambiguity={int(source_ambiguity)}; global_ambiguity={int(global_ambiguity)}; "
        f"final={','.join(final_structure)}"
    )
    return SCSVRCEFV9Output(
        method=method,
        candidate=final_candidate,
        anchor=anchor,
        anchor_structure=tuple(anchor.selector_structure),
        final_structure=tuple(final_structure),
        bank_terms=tuple(anchor.bank.candidate_terms),
        candidate_deviations=tuple(candidate_deviations),
        role_proposed_candidates=tuple(role_proposed),
        diagnostics=tuple(diagnostics),
        source_diagnostics=tuple(source_diags_by_source.values()),
        accepted_deviations=tuple(accepted),
        added_sources=tuple(added_sources),
        source_ambiguity=bool(source_ambiguity),
        global_ambiguity=bool(global_ambiguity),
        communication_bytes=int(anchor.communication_bytes + extra_communication),
        runtime_seconds=float(perf_counter() - start),
        stop_reason=stop_reason,
    )
