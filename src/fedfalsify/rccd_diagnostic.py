"""Role-Contrast Conditional Deviation spent-seed mechanism diagnostic.

RCCD is post-independent exploratory tooling only. It calls frozen SCSV-Cert v6,
keeps the selected shared term set intact, jointly identifies a banked source-
linked exception on discovery sufficient statistics, and certifies only the
single deviation coefficient on disjoint selector and probe packets.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from time import perf_counter
from typing import Sequence

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .crossfit_redesign import _ordered_terms, partition_clients
from .crossfit_surrogate import split_selector_probe
from .scsv_diagnostic import _build_packets, _fit_from_packets, _packet_sse
from .scsv_v6 import SCSVV6Output, scsv_cert_method


@dataclass(frozen=True)
class RCCDOutput:
    method: str
    candidate: CandidateEquation
    anchor: SCSVV6Output
    anchor_structure: tuple[str, ...]
    final_structure: tuple[str, ...]
    bank_terms: tuple[str, ...]
    exception_term: str | None
    source_term: str | None
    exception_in_bank: bool
    exception_in_anchor: bool
    source_in_anchor: bool
    attempted: bool
    discovery_full_structure: tuple[str, ...]
    discovery_full_coefficients: tuple[float, ...]
    exception_coefficient: float | None
    selector_eligible_clients: tuple[str, ...]
    selector_eligible_support: int
    selector_full_sse: float | None
    selector_zero_sse: float | None
    selector_delta: float | None
    selector_passed: bool
    probe_eligible_clients: tuple[str, ...]
    probe_eligible_support: int
    probe_full_sse: float | None
    probe_zero_sse: float | None
    probe_delta: float | None
    probe_passed: bool
    selector_outside_anchor_sse: float | None
    selector_outside_full_sse: float | None
    selector_outside_safe: bool
    probe_outside_anchor_sse: float | None
    probe_outside_full_sse: float | None
    probe_outside_safe: bool
    accepted: bool
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _anchor_discovery_candidate(anchor: SCSVV6Output) -> CandidateEquation:
    if tuple(anchor.selector_profile.terms) != tuple(anchor.selector_structure):
        raise RuntimeError("RCCD v6 selector profile/structure mismatch")
    return CandidateEquation(
        tuple(anchor.selector_structure),
        tuple(float(value) for value in anchor.selector_profile.coefficients),
        "rccd-frozen-v6-discovery-anchor",
    )


def _banked_exception(
    anchor: SCSVV6Output,
    catalog: TermCatalog,
) -> tuple[str | None, str | None, bool, bool, bool]:
    exception_terms = tuple(
        term
        for term in anchor.bank.candidate_terms
        if catalog.get(term).kind == "exception"
    )
    if len(exception_terms) > 1:
        raise RuntimeError("RCCD spent diagnostic supports at most one exception term")
    if not exception_terms:
        return None, None, False, False, False
    exception = exception_terms[0]
    source = catalog.get(exception).source_term
    anchor_set = set(anchor.selector_structure)
    return (
        exception,
        source,
        True,
        exception in anchor_set,
        bool(source is not None and source in anchor_set),
    )


def _role_indices(packets, all_terms: tuple[str, ...], term: str) -> tuple[int, ...]:
    term_index = all_terms.index(term)
    eligible: list[int] = []
    for index, packet in enumerate(packets):
        floor = max(3, int(ceil(0.10 * packet.support)))
        if packet.observed_support[term_index] >= floor:
            eligible.append(index)
    return tuple(eligible)


def _zero_exception(
    full: CandidateEquation,
    exception_term: str,
) -> CandidateEquation:
    if exception_term not in full.active_terms:
        raise ValueError("fixed-reduced RCCD comparator requires the exception term")
    coefficients = tuple(
        0.0 if term == exception_term else float(value)
        for term, value in zip(full.active_terms, full.coefficients)
    )
    return CandidateEquation(
        full.active_terms,
        coefficients,
        "rccd-fixed-reduced-zero-deviation",
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
    full_sse = float(
        sum(_packet_sse(packets[index], all_terms, full) for index in eligible)
    )
    zero_sse = float(
        sum(_packet_sse(packets[index], all_terms, zero) for index in eligible)
    )
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
    anchor_sse = float(
        sum(_packet_sse(packets[index], all_terms, anchor) for index in outside)
    )
    full_sse = float(
        sum(_packet_sse(packets[index], all_terms, full) for index in outside)
    )
    return anchor_sse, full_sse, bool(full_sse <= anchor_sse + 1e-10)


def rccd_diagnostic_method(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    max_terms: int = 6,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
) -> RCCDOutput:
    """Run frozen v6 plus source-linked conditional deviation certification."""

    start = perf_counter()
    anchor = scsv_cert_method(
        datasets,
        catalog,
        seed=seed,
        max_terms=max_terms,
        target_mse=target_mse,
        min_repair_score=min_repair_score,
        use_score_proposer=True,
    )
    anchor_discovery = _anchor_discovery_candidate(anchor)
    exception, source, in_bank, in_anchor, source_in_anchor = _banked_exception(
        anchor, catalog
    )

    attempted = False
    accepted = False
    final_candidate = anchor.candidate
    final_structure = anchor.selector_structure
    discovery_full_structure: tuple[str, ...] = ()
    discovery_full_coefficients: tuple[float, ...] = ()
    exception_coefficient: float | None = None

    selector_ids: tuple[str, ...] = ()
    selector_support = 0
    selector_full_sse: float | None = None
    selector_zero_sse: float | None = None
    selector_delta: float | None = None
    selector_passed = False

    probe_ids: tuple[str, ...] = ()
    probe_support = 0
    probe_full_sse: float | None = None
    probe_zero_sse: float | None = None
    probe_delta: float | None = None
    probe_passed = False

    selector_out_anchor: float | None = None
    selector_out_full: float | None = None
    selector_out_safe = False
    probe_out_anchor: float | None = None
    probe_out_full: float | None = None
    probe_out_safe = False

    extra_communication = 0
    can_attempt = bool(
        in_bank
        and not in_anchor
        and source_in_anchor
        and exception is not None
        and source is not None
        and len(anchor.selector_structure) < max_terms
    )

    if can_attempt:
        attempted = True
        partitions = partition_clients(datasets, seed=seed, validation_fraction=0.30)
        selectors, probes = split_selector_probe(partitions, seed=seed)
        all_terms = ("1",) + tuple(anchor.bank.candidate_terms)
        fit_packets, selector_packets, probe_packets, packet_bytes = _build_packets(
            partitions, selectors, probes, catalog, all_terms
        )
        extra_communication += int(packet_bytes)

        full_terms = _ordered_terms(
            catalog,
            (set(anchor.selector_structure) - {"1"}) | {exception},
        )
        if len(full_terms) > max_terms:
            raise RuntimeError("RCCD nested structure exceeded frozen size cap")
        full = _fit_from_packets(
            fit_packets,
            all_terms,
            full_terms,
            candidate_id="rccd-discovery-full",
        )
        zero = _zero_exception(full, exception)
        discovery_full_structure = full.active_terms
        discovery_full_coefficients = tuple(float(value) for value in full.coefficients)
        exception_coefficient = float(
            dict(zip(full.active_terms, full.coefficients))[exception]
        )

        # Fixed-reduced integrity: every shared coefficient must be byte-for-byte
        # identical between the full and zero-deviation candidates.
        full_map = dict(zip(full.active_terms, full.coefficients))
        zero_map = dict(zip(zero.active_terms, zero.coefficients))
        for term, value in full_map.items():
            if term == exception:
                if zero_map[term] != 0.0:
                    raise RuntimeError("RCCD fixed-reduced exception was not zeroed")
            elif zero_map[term] != value:
                raise RuntimeError("RCCD fixed-reduced comparator refit a shared coefficient")

        selector_eligible = _role_indices(selector_packets, all_terms, exception)
        probe_eligible = _role_indices(probe_packets, all_terms, exception)
        selector_ids = tuple(selector_packets[index].client_id for index in selector_eligible)
        probe_ids = tuple(probe_packets[index].client_id for index in probe_eligible)

        (
            selector_support,
            selector_full_sse,
            selector_zero_sse,
            selector_delta,
            selector_passed,
        ) = _conditional_test(
            full, zero, selector_packets, all_terms, selector_eligible
        )
        (
            probe_support,
            probe_full_sse,
            probe_zero_sse,
            probe_delta,
            probe_passed,
        ) = _conditional_test(full, zero, probe_packets, all_terms, probe_eligible)

        selector_out_anchor, selector_out_full, selector_out_safe = _outside_safety(
            anchor_discovery,
            full,
            selector_packets,
            all_terms,
            selector_eligible,
        )
        probe_out_anchor, probe_out_full, probe_out_safe = _outside_safety(
            anchor_discovery,
            full,
            probe_packets,
            all_terms,
            probe_eligible,
        )

        accepted = bool(
            selector_passed
            and probe_passed
            and selector_out_safe
            and probe_out_safe
        )
        if accepted:
            # Keep discovery-fitted coefficients for the formal diagnostic so
            # selector/probe rows remain certification-only, never refit inputs.
            final_candidate = full
            final_structure = full.active_terms

    if not set(anchor.selector_structure).issubset(set(final_structure)):
        raise RuntimeError("RCCD deleted or replaced a frozen v6 selected term")
    if accepted and exception not in set(final_structure):
        raise RuntimeError("RCCD accepted a deviation without retaining it")

    stop_reason = (
        "RCCD spent-seed diagnostic; "
        f"anchor={','.join(anchor.selector_structure)}; "
        f"bank={','.join(anchor.bank.candidate_terms)}; "
        f"exception={exception or ''}; source={source or ''}; "
        f"in_bank={int(in_bank)}; in_anchor={int(in_anchor)}; "
        f"source_in_anchor={int(source_in_anchor)}; attempted={int(attempted)}; "
        f"selector_eligible={','.join(selector_ids)}; selector_N={selector_support}; "
        f"selector_delta={selector_delta}; selector_pass={int(selector_passed)}; "
        f"probe_eligible={','.join(probe_ids)}; probe_N={probe_support}; "
        f"probe_delta={probe_delta}; probe_pass={int(probe_passed)}; "
        f"selector_outside_safe={int(selector_out_safe)}; "
        f"probe_outside_safe={int(probe_out_safe)}; accepted={int(accepted)}; "
        f"final={','.join(final_structure)}; wrapper_overhead_unoptimized=1"
    )
    return RCCDOutput(
        method="rccd-spent-diagnostic",
        candidate=final_candidate,
        anchor=anchor,
        anchor_structure=anchor.selector_structure,
        final_structure=final_structure,
        bank_terms=tuple(anchor.bank.candidate_terms),
        exception_term=exception,
        source_term=source,
        exception_in_bank=bool(in_bank),
        exception_in_anchor=bool(in_anchor),
        source_in_anchor=bool(source_in_anchor),
        attempted=bool(attempted),
        discovery_full_structure=discovery_full_structure,
        discovery_full_coefficients=discovery_full_coefficients,
        exception_coefficient=exception_coefficient,
        selector_eligible_clients=selector_ids,
        selector_eligible_support=int(selector_support),
        selector_full_sse=selector_full_sse,
        selector_zero_sse=selector_zero_sse,
        selector_delta=selector_delta,
        selector_passed=bool(selector_passed),
        probe_eligible_clients=probe_ids,
        probe_eligible_support=int(probe_support),
        probe_full_sse=probe_full_sse,
        probe_zero_sse=probe_zero_sse,
        probe_delta=probe_delta,
        probe_passed=bool(probe_passed),
        selector_outside_anchor_sse=selector_out_anchor,
        selector_outside_full_sse=selector_out_full,
        selector_outside_safe=bool(selector_out_safe),
        probe_outside_anchor_sse=probe_out_anchor,
        probe_outside_full_sse=probe_out_full,
        probe_outside_safe=bool(probe_out_safe),
        accepted=bool(accepted),
        communication_bytes=int(anchor.communication_bytes + extra_communication),
        runtime_seconds=float(perf_counter() - start),
        stop_reason=stop_reason,
    )