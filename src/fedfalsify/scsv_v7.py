"""FedFalsify v7: SCSV with source-linked Role-Contrast Deviations.

Scientific rules are frozen in research/TRANSACTIONS_SCSV_RCD_V7_PROTOCOL.md.
The module calls frozen SCSV-Cert v6 unchanged, jointly identifies banked
source-linked deviations using discovery sufficient statistics, and certifies
each deviation on disjoint selector and probe packets before any final refit.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from time import perf_counter
from typing import Sequence

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .crossfit_redesign import _ordered_terms, _refit, partition_clients
from .crossfit_surrogate import split_selector_probe
from .scsv_diagnostic import _build_packets, _fit_from_packets, _packet_sse
from .scsv_v6 import SCSVV6Output, scsv_cert_method


@dataclass(frozen=True)
class V7DeviationDiagnostic:
    term: str
    source_term: str
    selector_eligible_clients: tuple[str, ...]
    selector_support: int
    selector_full_sse: float | None
    selector_zero_sse: float | None
    selector_delta: float | None
    selector_passed: bool
    probe_eligible_clients: tuple[str, ...]
    probe_support: int
    probe_full_sse: float | None
    probe_zero_sse: float | None
    probe_delta: float | None
    probe_passed: bool
    selector_outside_anchor_sse: float
    selector_outside_full_sse: float
    selector_outside_safe: bool
    probe_outside_anchor_sse: float
    probe_outside_full_sse: float
    probe_outside_safe: bool
    certificate_positive: bool


@dataclass(frozen=True)
class SCSVRCDV7Output:
    method: str
    candidate: CandidateEquation
    anchor: SCSVV6Output
    anchor_structure: tuple[str, ...]
    final_structure: tuple[str, ...]
    bank_terms: tuple[str, ...]
    source_linked_candidates: tuple[str, ...]
    discovery_joint_structure: tuple[str, ...]
    discovery_joint_coefficients: tuple[float, ...]
    diagnostics: tuple[V7DeviationDiagnostic, ...]
    accepted_deviations: tuple[str, ...]
    ambiguity_guard: bool
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _anchor_discovery_candidate(anchor: SCSVV6Output) -> CandidateEquation:
    if tuple(anchor.selector_profile.terms) != tuple(anchor.selector_structure):
        raise RuntimeError("v7 anchor selector profile/structure mismatch")
    return CandidateEquation(
        tuple(anchor.selector_structure),
        tuple(float(value) for value in anchor.selector_profile.coefficients),
        "scsv-rcd-v7-frozen-anchor-discovery",
    )


def _source_linked_missing(
    anchor: SCSVV6Output,
    catalog: TermCatalog,
) -> tuple[str, ...]:
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


def _role_indices(packets, all_terms: tuple[str, ...], term: str) -> tuple[int, ...]:
    term_index = all_terms.index(term)
    eligible: list[int] = []
    for index, packet in enumerate(packets):
        floor = max(3, int(ceil(0.10 * packet.support)))
        if packet.observed_support[term_index] >= floor:
            eligible.append(index)
    return tuple(eligible)


def _zero_one(
    full: CandidateEquation,
    term: str,
) -> CandidateEquation:
    if term not in full.active_terms:
        raise ValueError("v7 fixed-reduced comparator requires active deviation term")
    return CandidateEquation(
        full.active_terms,
        tuple(
            0.0 if name == term else float(value)
            for name, value in zip(full.active_terms, full.coefficients)
        ),
        f"scsv-rcd-v7-zero-{term}",
    )


def _conditional_test(
    full: CandidateEquation,
    zero: CandidateEquation,
    packets,
    all_terms: tuple[str, ...],
    eligible: tuple[int, ...],
) -> tuple[int, float | None, float | None, float | None, bool]:
    if not eligible:
        return 0, None, None, None, False
    support = int(sum(packets[index].support for index in eligible))
    full_sse = float(sum(_packet_sse(packets[index], all_terms, full) for index in eligible))
    zero_sse = float(sum(_packet_sse(packets[index], all_terms, zero) for index in eligible))
    delta = float(
        np.log(max(full_sse, 1e-15) / max(zero_sse, 1e-15))
        + np.log(max(support, 2)) / max(support, 1)
    )
    return support, full_sse, zero_sse, delta, bool(delta < 0.0)


def _outside_safety(
    anchor: CandidateEquation,
    full: CandidateEquation,
    packets,
    all_terms: tuple[str, ...],
    eligible: tuple[int, ...],
) -> tuple[float, float, bool]:
    eligible_set = set(eligible)
    outside = tuple(index for index in range(len(packets)) if index not in eligible_set)
    anchor_sse = float(sum(_packet_sse(packets[index], all_terms, anchor) for index in outside))
    full_sse = float(sum(_packet_sse(packets[index], all_terms, full) for index in outside))
    return anchor_sse, full_sse, bool(full_sse <= anchor_sse + 1e-10)


def _candidate_from_joint(
    full: CandidateEquation,
    final_structure: tuple[str, ...],
) -> CandidateEquation:
    coefficient_map = dict(zip(full.active_terms, full.coefficients))
    return CandidateEquation(
        final_structure,
        tuple(float(coefficient_map[term]) for term in final_structure),
        "scsv-rcd-v7-certified-discovery-structure",
    )


def scsv_rcd_v7_method(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    max_shared_terms: int = 6,
    max_added_deviations: int = 2,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
    require_probe: bool = True,
) -> SCSVRCDV7Output:
    """Run frozen v6 anchor followed by frozen source-linked deviation certificates."""

    start = perf_counter()
    if max_shared_terms != 6 or max_added_deviations != 2:
        raise ValueError("v7 scientific caps are frozen at shared=6 and added deviations=2")

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
    joint_structure: tuple[str, ...] = ()
    joint_coefficients: tuple[float, ...] = ()
    diagnostics: list[V7DeviationDiagnostic] = []
    accepted: tuple[str, ...] = ()
    ambiguity_guard = False
    extra_communication = 0

    if candidates:
        partitions = partition_clients(datasets, seed=seed, validation_fraction=0.30)
        selectors, probes = split_selector_probe(partitions, seed=seed)
        all_terms = ("1",) + tuple(anchor.bank.candidate_terms)
        fit_packets, selector_packets, probe_packets, packet_bytes = _build_packets(
            partitions, selectors, probes, catalog, all_terms
        )
        extra_communication += int(packet_bytes)

        joint_structure = _ordered_terms(
            catalog,
            (set(anchor.selector_structure) - {"1"}) | set(candidates),
        )
        full = _fit_from_packets(
            fit_packets,
            all_terms,
            joint_structure,
            candidate_id="scsv-rcd-v7-discovery-joint",
        )
        joint_coefficients = tuple(float(value) for value in full.coefficients)
        full_map = dict(zip(full.active_terms, full.coefficients))

        positives: list[str] = []
        for term in candidates:
            source = catalog.get(term).source_term
            if source is None or source not in set(anchor.selector_structure):
                raise RuntimeError("v7 admitted an orphan deviation")
            zero = _zero_one(full, term)
            zero_map = dict(zip(zero.active_terms, zero.coefficients))
            for name, value in full_map.items():
                if name == term:
                    if zero_map[name] != 0.0:
                        raise RuntimeError("v7 fixed-reduced deviation was not zeroed")
                elif zero_map[name] != value:
                    raise RuntimeError("v7 fixed-reduced comparator changed another coefficient")

            selector_eligible = _role_indices(selector_packets, all_terms, term)
            probe_eligible = _role_indices(probe_packets, all_terms, term)
            selector_ids = tuple(selector_packets[index].client_id for index in selector_eligible)
            probe_ids = tuple(probe_packets[index].client_id for index in probe_eligible)

            (
                selector_support,
                selector_full,
                selector_zero,
                selector_delta,
                selector_passed,
            ) = _conditional_test(full, zero, selector_packets, all_terms, selector_eligible)
            (
                probe_support,
                probe_full,
                probe_zero,
                probe_delta,
                probe_passed,
            ) = _conditional_test(full, zero, probe_packets, all_terms, probe_eligible)
            selector_out_anchor, selector_out_full, selector_out_safe = _outside_safety(
                anchor_discovery, full, selector_packets, all_terms, selector_eligible
            )
            probe_out_anchor, probe_out_full, probe_out_safe = _outside_safety(
                anchor_discovery, full, probe_packets, all_terms, probe_eligible
            )

            certificate_positive = bool(
                selector_passed
                and selector_out_safe
                and (
                    (probe_passed and probe_out_safe)
                    if require_probe
                    else True
                )
            )
            if certificate_positive:
                positives.append(term)

            diagnostics.append(
                V7DeviationDiagnostic(
                    term=term,
                    source_term=source,
                    selector_eligible_clients=selector_ids,
                    selector_support=int(selector_support),
                    selector_full_sse=selector_full,
                    selector_zero_sse=selector_zero,
                    selector_delta=selector_delta,
                    selector_passed=bool(selector_passed),
                    probe_eligible_clients=probe_ids,
                    probe_support=int(probe_support),
                    probe_full_sse=probe_full,
                    probe_zero_sse=probe_zero,
                    probe_delta=probe_delta,
                    probe_passed=bool(probe_passed),
                    selector_outside_anchor_sse=float(selector_out_anchor),
                    selector_outside_full_sse=float(selector_out_full),
                    selector_outside_safe=bool(selector_out_safe),
                    probe_outside_anchor_sse=float(probe_out_anchor),
                    probe_outside_full_sse=float(probe_out_full),
                    probe_outside_safe=bool(probe_out_safe),
                    certificate_positive=certificate_positive,
                )
            )

        if len(positives) > max_added_deviations:
            ambiguity_guard = True
            accepted = ()
        else:
            accepted = tuple(positives)

        if accepted:
            final_structure = _ordered_terms(
                catalog,
                (set(anchor.selector_structure) - {"1"}) | set(accepted),
            )
            if len(final_structure) > max_shared_terms + max_added_deviations:
                raise RuntimeError("v7 final structure exceeded frozen eight-term cap")
            _candidate_from_joint(full, final_structure)  # integrity check before refit
            final_candidate, refit_bytes = _refit(
                partitions,
                catalog,
                final_structure,
                include_validation=True,
                candidate_id=(
                    "scsv-rcd-v7-full-final"
                    if require_probe
                    else "scsv-rcd-v7-no-probe-final"
                ),
            )
            extra_communication += int(refit_bytes)

    if not set(anchor.selector_structure).issubset(set(final_structure)):
        raise RuntimeError("v7 deleted or replaced a frozen shared-anchor term")
    if len(accepted) > max_added_deviations:
        raise RuntimeError("v7 accepted too many deviations")
    if ambiguity_guard and final_structure != tuple(anchor.selector_structure):
        raise RuntimeError("v7 ambiguity guard failed to restore frozen anchor")

    method = "scsv-rcd-v7-full" if require_probe else "scsv-rcd-v7-no-probe"
    stop_reason = (
        f"SCSV-RCD v7; probe_required={int(require_probe)}; "
        f"anchor={','.join(anchor.selector_structure)}; "
        f"bank={','.join(anchor.bank.candidate_terms)}; "
        f"source_linked={','.join(candidates)}; "
        f"accepted={','.join(accepted)}; ambiguity={int(ambiguity_guard)}; "
        f"final={','.join(final_structure)}"
    )
    return SCSVRCDV7Output(
        method=method,
        candidate=final_candidate,
        anchor=anchor,
        anchor_structure=tuple(anchor.selector_structure),
        final_structure=tuple(final_structure),
        bank_terms=tuple(anchor.bank.candidate_terms),
        source_linked_candidates=tuple(candidates),
        discovery_joint_structure=joint_structure,
        discovery_joint_coefficients=joint_coefficients,
        diagnostics=tuple(diagnostics),
        accepted_deviations=accepted,
        ambiguity_guard=bool(ambiguity_guard),
        communication_bytes=int(anchor.communication_bytes + extra_communication),
        runtime_seconds=float(perf_counter() - start),
        stop_reason=stop_reason,
    )
