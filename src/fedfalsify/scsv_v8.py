"""FedFalsify v8: SCSV with Source-Pair Contrast Certification.

Scientific rules are frozen in research/TRANSACTIONS_SCSV_SPCC_V8_PROTOCOL.md.
The implementation calls SCSV-Cert v6 unchanged, infers client-level roles from
response-free gate occupancy, freezes unrelated shared-anchor coefficients,
estimates only a shared-source/deviation pair on discovery sufficient statistics,
and certifies the fixed pair on disjoint selector/probe packets.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Literal, Sequence

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .crossfit_redesign import _ordered_terms, _refit, partition_clients
from .crossfit_surrogate import split_selector_probe
from .scsv_diagnostic import SufficientPacket, _build_packets, _packet_sse
from .scsv_v6 import SCSVV6Output, scsv_cert_method

ProbeState = Literal["SUPPORTED", "INCONCLUSIVE-DIRECTIONAL", "CONTRADICTED"]


@dataclass(frozen=True)
class V8RoleHypothesis:
    term: str
    admissible: bool
    role_indices: tuple[int, ...]
    outside_indices: tuple[int, ...]
    role_client_ids: tuple[str, ...]
    outside_client_ids: tuple[str, ...]
    occupancies: tuple[float, ...]
    separation_gap: float
    role_mean_occupancy: float
    outside_mean_occupancy: float
    reason: str


@dataclass(frozen=True)
class V8DeviationDiagnostic:
    term: str
    source_term: str
    in_bank: bool
    source_in_anchor: bool
    role_admissible: bool
    role_client_ids: tuple[str, ...]
    outside_client_ids: tuple[str, ...]
    occupancy_gap: float
    role_mean_occupancy: float
    outside_mean_occupancy: float
    source_coefficient: float | None
    deviation_coefficient: float | None
    selector_support: int
    selector_full_sse: float | None
    selector_reduced_sse: float | None
    selector_delta: float | None
    selector_supported: bool
    selector_outside_full_sse: float
    selector_outside_reduced_sse: float
    selector_outside_safe: bool
    probe_support: int
    probe_full_sse: float | None
    probe_reduced_sse: float | None
    probe_delta: float | None
    probe_state: ProbeState
    probe_outside_full_sse: float
    probe_outside_reduced_sse: float
    probe_outside_safe: bool
    pair_invariant: bool
    positive: bool
    rejection_reason: str


@dataclass(frozen=True)
class SCSVSPCCV8Output:
    method: str
    candidate: CandidateEquation
    anchor: SCSVV6Output
    anchor_structure: tuple[str, ...]
    final_structure: tuple[str, ...]
    bank_terms: tuple[str, ...]
    source_linked_candidates: tuple[str, ...]
    diagnostics: tuple[V8DeviationDiagnostic, ...]
    accepted_deviations: tuple[str, ...]
    source_ambiguity: bool
    global_ambiguity: bool
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _anchor_discovery_candidate(anchor: SCSVV6Output) -> CandidateEquation:
    if tuple(anchor.selector_profile.terms) != tuple(anchor.selector_structure):
        raise RuntimeError("v8 anchor selector profile/structure mismatch")
    return CandidateEquation(
        tuple(anchor.selector_structure),
        tuple(float(value) for value in anchor.selector_profile.coefficients),
        "scsv-spcc-v8-frozen-anchor-discovery",
    )


def _source_linked_missing(anchor: SCSVV6Output, catalog: TermCatalog) -> tuple[str, ...]:
    anchor_set = set(anchor.selector_structure)
    eligible: list[str] = []
    for term in anchor.bank.candidate_terms:
        metadata = catalog.get(term)
        if metadata.kind != "exception" or term in anchor_set:
            continue
        source = metadata.source_term
        if source is not None and source in anchor_set:
            eligible.append(term)
    return tuple(eligible)


def _occupancy(packet: SufficientPacket, all_terms: tuple[str, ...], term: str) -> float:
    index = all_terms.index(term)
    return float(packet.observed_support[index] / max(packet.support, 1))


def _role_hypothesis(
    fit_packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    term: str,
) -> V8RoleHypothesis:
    if len(fit_packets) < 2:
        return V8RoleHypothesis(
            term=term,
            admissible=False,
            role_indices=(),
            outside_indices=tuple(range(len(fit_packets))),
            role_client_ids=(),
            outside_client_ids=tuple(item.client_id for item in fit_packets),
            occupancies=tuple(_occupancy(item, all_terms, term) for item in fit_packets),
            separation_gap=0.0,
            role_mean_occupancy=0.0,
            outside_mean_occupancy=0.0,
            reason="fewer than two clients",
        )

    occupancies = tuple(_occupancy(item, all_terms, term) for item in fit_packets)
    ordered = sorted(
        ((value, fit_packets[index].client_id, index) for index, value in enumerate(occupancies)),
        key=lambda item: (item[0], item[1]),
    )
    choices: list[tuple[float, int, tuple[str, ...], tuple[int, ...]]] = []
    maximum = len(fit_packets) // 2
    for k in range(1, maximum + 1):
        boundary = len(ordered) - k
        gap = float(ordered[boundary][0] - ordered[boundary - 1][0])
        role_slice = ordered[boundary:]
        role_ids = tuple(sorted(item[1] for item in role_slice))
        role_indices = tuple(sorted(item[2] for item in role_slice))
        choices.append((gap, k, role_ids, role_indices))

    choices.sort(key=lambda item: (-item[0], item[1], item[2]))
    gap, _, _, role_indices = choices[0]
    role_set = set(role_indices)
    outside_indices = tuple(index for index in range(len(fit_packets)) if index not in role_set)
    role_values = [occupancies[index] for index in role_indices]
    outside_values = [occupancies[index] for index in outside_indices]
    role_mean = float(np.mean(role_values)) if role_values else 0.0
    outside_mean = float(np.mean(outside_values)) if outside_values else 0.0
    admissible = bool(
        role_indices
        and outside_indices
        and gap >= 0.50
        and role_mean >= 0.75
        and outside_mean <= 0.25
    )
    reason = (
        "response-free client-level gate contrast"
        if admissible
        else "gate occupancy lacked frozen client-level contrast"
    )
    return V8RoleHypothesis(
        term=term,
        admissible=admissible,
        role_indices=role_indices if admissible else (),
        outside_indices=outside_indices if admissible else tuple(range(len(fit_packets))),
        role_client_ids=(
            tuple(fit_packets[index].client_id for index in role_indices) if admissible else ()
        ),
        outside_client_ids=(
            tuple(fit_packets[index].client_id for index in outside_indices)
            if admissible
            else tuple(item.client_id for item in fit_packets)
        ),
        occupancies=occupancies,
        separation_gap=float(gap),
        role_mean_occupancy=role_mean,
        outside_mean_occupancy=outside_mean,
        reason=reason,
    )


def _index_map(all_terms: tuple[str, ...]) -> dict[str, int]:
    return {term: index for index, term in enumerate(all_terms)}


def _residual_cross(
    packet: SufficientPacket,
    *,
    target_term: str,
    frozen_terms: tuple[str, ...],
    frozen_coefficients: tuple[float, ...],
    all_terms: tuple[str, ...],
) -> float:
    mapping = _index_map(all_terms)
    target_index = mapping[target_term]
    value = float(packet.target[target_index])
    for term, coefficient in zip(frozen_terms, frozen_coefficients):
        value -= float(coefficient) * float(packet.gram[target_index, mapping[term]])
    return float(value)


def _estimate_pair(
    anchor_discovery: CandidateEquation,
    source: str,
    deviation: str,
    fit_packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    role: V8RoleHypothesis,
    catalog: TermCatalog,
) -> tuple[CandidateEquation, CandidateEquation, float, float]:
    if not role.admissible or not role.role_indices or not role.outside_indices:
        raise ValueError("pair estimation requires an admissible non-vacuous role")
    if source not in anchor_discovery.active_terms:
        raise ValueError("pair estimation requires source in frozen anchor")

    anchor_map = dict(zip(anchor_discovery.active_terms, anchor_discovery.coefficients))
    frozen_terms = tuple(term for term in anchor_discovery.active_terms if term != source)
    frozen_coefficients = tuple(float(anchor_map[term]) for term in frozen_terms)
    mapping = _index_map(all_terms)
    source_index = mapping[source]
    deviation_index = mapping[deviation]

    source_num = 0.0
    source_den = 0.0
    for index in role.outside_indices:
        packet = fit_packets[index]
        source_num += _residual_cross(
            packet,
            target_term=source,
            frozen_terms=frozen_terms,
            frozen_coefficients=frozen_coefficients,
            all_terms=all_terms,
        )
        source_den += float(packet.gram[source_index, source_index])
    beta_source = float(source_num / (source_den + 1e-10))

    deviation_num = 0.0
    deviation_den = 0.0
    for index in role.role_indices:
        packet = fit_packets[index]
        value = _residual_cross(
            packet,
            target_term=deviation,
            frozen_terms=frozen_terms,
            frozen_coefficients=frozen_coefficients,
            all_terms=all_terms,
        )
        value -= beta_source * float(packet.gram[deviation_index, source_index])
        deviation_num += value
        deviation_den += float(packet.gram[deviation_index, deviation_index])
    delta = float(deviation_num / (deviation_den + 1e-10))

    structure = _ordered_terms(
        catalog,
        (set(anchor_discovery.active_terms) - {"1"}) | {deviation},
    )
    coefficient_map = {term: float(value) for term, value in anchor_map.items()}
    coefficient_map[source] = beta_source
    coefficient_map[deviation] = delta
    full = CandidateEquation(
        structure,
        tuple(float(coefficient_map[term]) for term in structure),
        f"scsv-spcc-v8-full-{deviation}",
    )
    reduced = CandidateEquation(
        structure,
        tuple(0.0 if term == deviation else float(coefficient_map[term]) for term in structure),
        f"scsv-spcc-v8-reduced-{deviation}",
    )
    return full, reduced, beta_source, delta


def _pair_invariant(full: CandidateEquation, reduced: CandidateEquation, term: str) -> bool:
    if full.active_terms != reduced.active_terms or term not in full.active_terms:
        return False
    for name, full_value, reduced_value in zip(
        full.active_terms, full.coefficients, reduced.coefficients
    ):
        if name == term:
            if float(reduced_value) != 0.0:
                return False
        elif float(full_value) != float(reduced_value):
            return False
    return True


def _conditional_test(
    full: CandidateEquation,
    reduced: CandidateEquation,
    packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    role_indices: tuple[int, ...],
) -> tuple[int, float | None, float | None, float | None, bool]:
    if not role_indices:
        return 0, None, None, None, False
    support = int(sum(packets[index].support for index in role_indices))
    full_sse = float(sum(_packet_sse(packets[index], all_terms, full) for index in role_indices))
    reduced_sse = float(sum(_packet_sse(packets[index], all_terms, reduced) for index in role_indices))
    delta = float(
        np.log(max(full_sse, 1e-15) / max(reduced_sse, 1e-15))
        + np.log(max(support, 2)) / max(support, 1)
    )
    return support, full_sse, reduced_sse, delta, bool(delta < 0.0)


def _probe_state(
    full_sse: float | None,
    reduced_sse: float | None,
    delta: float | None,
) -> ProbeState:
    if full_sse is None or reduced_sse is None or delta is None:
        return "CONTRADICTED"
    if delta < 0.0:
        return "SUPPORTED"
    if full_sse < reduced_sse - 1e-12:
        return "INCONCLUSIVE-DIRECTIONAL"
    return "CONTRADICTED"


def _outside_safety(
    full: CandidateEquation,
    reduced: CandidateEquation,
    packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    outside_indices: tuple[int, ...],
) -> tuple[float, float, bool]:
    if not outside_indices:
        return 0.0, 0.0, False
    full_sse = float(sum(_packet_sse(packets[index], all_terms, full) for index in outside_indices))
    reduced_sse = float(
        sum(_packet_sse(packets[index], all_terms, reduced) for index in outside_indices)
    )
    return full_sse, reduced_sse, bool(full_sse <= reduced_sse + 1e-10)


def scsv_spcc_v8_method(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    max_shared_terms: int = 6,
    max_added_deviations: int = 2,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
    strict_probe: bool = False,
) -> SCSVSPCCV8Output:
    """Run frozen SCSV anchor followed by isolated source-pair certificates."""

    start = perf_counter()
    if max_shared_terms != 6 or max_added_deviations != 2:
        raise ValueError("v8 scientific caps are frozen at shared=6 and added deviations=2")

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
    candidates = _source_linked_missing(anchor, catalog)

    final_structure = tuple(anchor.selector_structure)
    final_candidate = anchor.candidate
    diagnostics: list[V8DeviationDiagnostic] = []
    positives: list[str] = []
    extra_communication = 0
    source_ambiguity = False
    global_ambiguity = False

    if candidates:
        partitions = partition_clients(datasets, seed=seed, validation_fraction=0.30)
        selectors, probes = split_selector_probe(partitions, seed=seed)
        all_terms = ("1",) + tuple(anchor.bank.candidate_terms)
        fit_packets, selector_packets, probe_packets, packet_bytes = _build_packets(
            partitions, selectors, probes, catalog, all_terms
        )
        extra_communication += int(packet_bytes)

        for term in candidates:
            metadata = catalog.get(term)
            source = metadata.source_term
            if source is None or source not in set(anchor.selector_structure):
                raise RuntimeError("v8 source-linked list admitted an orphan deviation")

            role = _role_hypothesis(fit_packets, all_terms, term)
            if not role.admissible:
                diagnostics.append(
                    V8DeviationDiagnostic(
                        term=term,
                        source_term=source,
                        in_bank=True,
                        source_in_anchor=True,
                        role_admissible=False,
                        role_client_ids=(),
                        outside_client_ids=tuple(item.client_id for item in fit_packets),
                        occupancy_gap=role.separation_gap,
                        role_mean_occupancy=role.role_mean_occupancy,
                        outside_mean_occupancy=role.outside_mean_occupancy,
                        source_coefficient=None,
                        deviation_coefficient=None,
                        selector_support=0,
                        selector_full_sse=None,
                        selector_reduced_sse=None,
                        selector_delta=None,
                        selector_supported=False,
                        selector_outside_full_sse=0.0,
                        selector_outside_reduced_sse=0.0,
                        selector_outside_safe=False,
                        probe_support=0,
                        probe_full_sse=None,
                        probe_reduced_sse=None,
                        probe_delta=None,
                        probe_state="CONTRADICTED",
                        probe_outside_full_sse=0.0,
                        probe_outside_reduced_sse=0.0,
                        probe_outside_safe=False,
                        pair_invariant=False,
                        positive=False,
                        rejection_reason="ROLE-NOT-IDENTIFIED",
                    )
                )
                continue

            full, reduced, beta_source, delta_coef = _estimate_pair(
                anchor_discovery,
                source,
                term,
                fit_packets,
                all_terms,
                role,
                catalog,
            )
            invariant = _pair_invariant(full, reduced, term)
            if not invariant:
                raise RuntimeError("v8 FULL/REDUCED pair invariant failed")

            (
                selector_support,
                selector_full,
                selector_reduced,
                selector_delta,
                selector_supported,
            ) = _conditional_test(
                full,
                reduced,
                selector_packets,
                all_terms,
                role.role_indices,
            )
            (
                probe_support,
                probe_full,
                probe_reduced,
                probe_delta,
                _,
            ) = _conditional_test(
                full,
                reduced,
                probe_packets,
                all_terms,
                role.role_indices,
            )
            probe_state = _probe_state(probe_full, probe_reduced, probe_delta)
            selector_out_full, selector_out_reduced, selector_out_safe = _outside_safety(
                full,
                reduced,
                selector_packets,
                all_terms,
                role.outside_indices,
            )
            probe_out_full, probe_out_reduced, probe_out_safe = _outside_safety(
                full,
                reduced,
                probe_packets,
                all_terms,
                role.outside_indices,
            )

            probe_ok = (
                probe_state == "SUPPORTED"
                if strict_probe
                else probe_state in {"SUPPORTED", "INCONCLUSIVE-DIRECTIONAL"}
            )
            positive = bool(
                selector_supported
                and selector_out_safe
                and probe_ok
                and probe_out_safe
                and invariant
            )
            if positive:
                positives.append(term)

            if not selector_supported:
                reason = "SELECTOR-NOT-SUPPORTED"
            elif not selector_out_safe:
                reason = "SELECTOR-OUTSIDE-UNSAFE"
            elif not probe_ok:
                reason = f"PROBE-{probe_state}"
            elif not probe_out_safe:
                reason = "PROBE-OUTSIDE-UNSAFE"
            else:
                reason = "ACCEPTED" if positive else "PAIR-INVARIANT-FAIL"

            diagnostics.append(
                V8DeviationDiagnostic(
                    term=term,
                    source_term=source,
                    in_bank=True,
                    source_in_anchor=True,
                    role_admissible=True,
                    role_client_ids=role.role_client_ids,
                    outside_client_ids=role.outside_client_ids,
                    occupancy_gap=role.separation_gap,
                    role_mean_occupancy=role.role_mean_occupancy,
                    outside_mean_occupancy=role.outside_mean_occupancy,
                    source_coefficient=beta_source,
                    deviation_coefficient=delta_coef,
                    selector_support=int(selector_support),
                    selector_full_sse=selector_full,
                    selector_reduced_sse=selector_reduced,
                    selector_delta=selector_delta,
                    selector_supported=bool(selector_supported),
                    selector_outside_full_sse=float(selector_out_full),
                    selector_outside_reduced_sse=float(selector_out_reduced),
                    selector_outside_safe=bool(selector_out_safe),
                    probe_support=int(probe_support),
                    probe_full_sse=probe_full,
                    probe_reduced_sse=probe_reduced,
                    probe_delta=probe_delta,
                    probe_state=probe_state,
                    probe_outside_full_sse=float(probe_out_full),
                    probe_outside_reduced_sse=float(probe_out_reduced),
                    probe_outside_safe=bool(probe_out_safe),
                    pair_invariant=bool(invariant),
                    positive=positive,
                    rejection_reason=reason,
                )
            )

        accepted: tuple[str, ...]
        if len(positives) > max_added_deviations:
            global_ambiguity = True
            accepted = ()
        else:
            by_source: dict[str, list[str]] = {}
            for term in positives:
                source = catalog.get(term).source_term
                if source is None:
                    raise RuntimeError("positive v8 deviation lost source metadata")
                by_source.setdefault(source, []).append(term)
            ambiguous_sources = {source for source, terms in by_source.items() if len(terms) > 1}
            source_ambiguity = bool(ambiguous_sources)
            accepted = tuple(
                term
                for term in positives
                if catalog.get(term).source_term not in ambiguous_sources
            )

        if accepted:
            final_structure = _ordered_terms(
                catalog,
                (set(anchor.selector_structure) - {"1"}) | set(accepted),
            )
            if len(final_structure) > max_shared_terms + max_added_deviations:
                raise RuntimeError("v8 final structure exceeded frozen eight-term cap")
            final_candidate, refit_bytes = _refit(
                partitions,
                catalog,
                final_structure,
                include_validation=True,
                candidate_id=(
                    "scsv-spcc-v8-strict-probe-final"
                    if strict_probe
                    else "scsv-spcc-v8-full-final"
                ),
            )
            extra_communication += int(refit_bytes)
    else:
        accepted = ()

    if not set(anchor.selector_structure).issubset(set(final_structure)):
        raise RuntimeError("v8 deleted or replaced a frozen anchor term")
    if global_ambiguity and final_structure != tuple(anchor.selector_structure):
        raise RuntimeError("v8 global ambiguity failed to restore anchor")
    if len(accepted) > max_added_deviations:
        raise RuntimeError("v8 accepted too many deviations")

    method = "scsv-spcc-v8-strict-probe" if strict_probe else "scsv-spcc-v8-full"
    stop_reason = (
        f"SCSV-SPCC v8; strict_probe={int(strict_probe)}; "
        f"anchor={','.join(anchor.selector_structure)}; "
        f"bank={','.join(anchor.bank.candidate_terms)}; "
        f"source_linked={','.join(candidates)}; "
        f"accepted={','.join(accepted)}; source_ambiguity={int(source_ambiguity)}; "
        f"global_ambiguity={int(global_ambiguity)}; final={','.join(final_structure)}"
    )
    return SCSVSPCCV8Output(
        method=method,
        candidate=final_candidate,
        anchor=anchor,
        anchor_structure=tuple(anchor.selector_structure),
        final_structure=tuple(final_structure),
        bank_terms=tuple(anchor.bank.candidate_terms),
        source_linked_candidates=tuple(candidates),
        diagnostics=tuple(diagnostics),
        accepted_deviations=accepted,
        source_ambiguity=bool(source_ambiguity),
        global_ambiguity=bool(global_ambiguity),
        communication_bytes=int(anchor.communication_bytes + extra_communication),
        runtime_seconds=float(perf_counter() - start),
        stop_reason=stop_reason,
    )
