"""Role-Conditional Set Augmentation spent-seed mechanism diagnostic.

This wrapper is post-independent forensic tooling only.  It calls the frozen
SCSV-Cert v6 method unchanged, preserves its selected core structure, and may
only add a banked declared exception term using selector-only role-local
information evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from time import perf_counter
from typing import Sequence

from .basis import CandidateEquation, TermCatalog
from .crossfit_redesign import _ordered_terms, _refit, partition_clients
from .crossfit_surrogate import split_selector_probe
from .scsv_diagnostic import (
    SetTermDiagnostic,
    _build_packets,
    _fit_from_packets,
    _packet_sse,
    _profile,
    _validate_selector_set,
)
from .scsv_v6 import SCSVV6Output, scsv_cert_method


@dataclass(frozen=True)
class RCSAOutput:
    method: str
    candidate: CandidateEquation
    anchor: SCSVV6Output
    anchor_structure: tuple[str, ...]
    final_structure: tuple[str, ...]
    exception_term: str | None
    exception_in_bank: bool
    exception_in_anchor: bool
    attempted: bool
    eligible_selector_clients: tuple[str, ...]
    eligible_selector_support: int
    anchor_role_information_score: float | None
    augmented_role_information_score: float | None
    outside_selector_sse_anchor: float | None
    outside_selector_sse_augmented: float | None
    augmentation_accepted: bool
    probe_certified: bool
    term_diagnostics: tuple[SetTermDiagnostic, ...]
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _selector_exception_indices(
    selector_packets,
    all_terms: tuple[str, ...],
    term: str,
) -> tuple[int, ...]:
    """Determine exception eligibility from selector support only."""

    term_index = all_terms.index(term)
    eligible: list[int] = []
    for index, packet in enumerate(selector_packets):
        floor = max(3, int(ceil(0.10 * packet.support)))
        if packet.observed_support[term_index] >= floor:
            eligible.append(index)
    return tuple(eligible)


def _selector_outside_sse(
    candidate: CandidateEquation,
    selector_packets,
    all_terms: tuple[str, ...],
    eligible: tuple[int, ...],
) -> float:
    eligible_set = set(eligible)
    return float(
        sum(
            _packet_sse(packet, all_terms, candidate)
            for index, packet in enumerate(selector_packets)
            if index not in eligible_set
        )
    )


def _missing_banked_exception(
    anchor: SCSVV6Output,
    catalog: TermCatalog,
) -> tuple[str | None, bool, bool]:
    exception_terms = tuple(
        term
        for term in anchor.bank.candidate_terms
        if catalog.get(term).kind == "exception"
    )
    if len(exception_terms) > 1:
        raise RuntimeError(
            "RCSA spent diagnostic is frozen for at most one declared exception term"
        )
    if not exception_terms:
        return None, False, False
    term = exception_terms[0]
    in_anchor = term in set(anchor.selector_structure)
    return term, True, in_anchor


def rcsa_diagnostic_method(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    max_terms: int = 6,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
) -> RCSAOutput:
    """Run the frozen-v6 anchor and selector-only role-conditioned augmentation."""

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
    exception_term, exception_in_bank, exception_in_anchor = _missing_banked_exception(
        anchor, catalog
    )

    attempted = False
    accepted = False
    eligible_ids: tuple[str, ...] = ()
    eligible_support = 0
    anchor_role_score: float | None = None
    augmented_role_score: float | None = None
    outside_anchor: float | None = None
    outside_augmented: float | None = None
    final_structure = anchor.selector_structure
    final_candidate = anchor.candidate
    probe_certified = anchor.probe_certified
    diagnostics = anchor.term_diagnostics
    extra_communication = 0

    can_attempt = (
        exception_in_bank
        and not exception_in_anchor
        and exception_term is not None
        and len(anchor.selector_structure) < max_terms
    )

    if can_attempt:
        attempted = True
        partitions = partition_clients(
            datasets, seed=seed, validation_fraction=0.30
        )
        selectors, probes = split_selector_probe(partitions, seed=seed)
        all_terms = ("1",) + tuple(anchor.bank.candidate_terms)
        fit_packets, selector_packets, probe_packets, packet_bytes = _build_packets(
            partitions, selectors, probes, catalog, all_terms
        )
        extra_communication += int(packet_bytes)

        anchor_fit = _fit_from_packets(
            fit_packets,
            all_terms,
            anchor.selector_structure,
            candidate_id="rcsa-anchor-fit",
        )
        augmented_terms = _ordered_terms(
            catalog,
            (set(anchor.selector_structure) - {"1"}) | {exception_term},
        )
        if len(augmented_terms) > max_terms:
            raise RuntimeError("RCSA augmentation exceeded the frozen size cap")
        augmented_fit = _fit_from_packets(
            fit_packets,
            all_terms,
            augmented_terms,
            candidate_id="rcsa-augmented-fit",
        )

        eligible = _selector_exception_indices(
            selector_packets, all_terms, exception_term
        )
        eligible_ids = tuple(selector_packets[index].client_id for index in eligible)
        eligible_support = int(sum(selector_packets[index].support for index in eligible))

        if eligible:
            eligible_packets = tuple(selector_packets[index] for index in eligible)
            anchor_profile = _profile(anchor_fit, eligible_packets, all_terms, catalog)
            augmented_profile = _profile(
                augmented_fit, eligible_packets, all_terms, catalog
            )
            anchor_role_score = float(anchor_profile.information_score)
            augmented_role_score = float(augmented_profile.information_score)
            outside_anchor = _selector_outside_sse(
                anchor_fit, selector_packets, all_terms, eligible
            )
            outside_augmented = _selector_outside_sse(
                augmented_fit, selector_packets, all_terms, eligible
            )
            accepted = bool(
                augmented_role_score < anchor_role_score
                and outside_augmented <= outside_anchor + 1e-10
            )

        if accepted:
            final_structure = augmented_terms
            probe_certified, diagnostics = _validate_selector_set(
                augmented_fit,
                fit_packets,
                selector_packets,
                probe_packets,
                all_terms,
                tuple(anchor.bank.candidate_terms),
                catalog,
            )
            final_candidate, payload = _refit(
                partitions,
                catalog,
                final_structure,
                include_validation=True,
                candidate_id="rcsa-spent-diagnostic-final",
            )
            extra_communication += int(payload)

    if not set(anchor.selector_structure).issubset(set(final_structure)):
        raise RuntimeError("RCSA deleted or replaced a frozen v6 selected term")

    stop_reason = (
        "RCSA spent-seed diagnostic; "
        f"anchor={','.join(anchor.selector_structure)}; "
        f"exception={exception_term or ''}; "
        f"in_bank={int(exception_in_bank)}; "
        f"in_anchor={int(exception_in_anchor)}; "
        f"attempted={int(attempted)}; "
        f"eligible={','.join(eligible_ids)}; "
        f"anchor_role_ic={anchor_role_score}; "
        f"augmented_role_ic={augmented_role_score}; "
        f"outside_anchor_sse={outside_anchor}; "
        f"outside_augmented_sse={outside_augmented}; "
        f"accepted={int(accepted)}; "
        f"final={','.join(final_structure)}; "
        "wrapper_overhead_unoptimized=1"
    )
    return RCSAOutput(
        method="rcsa-spent-diagnostic",
        candidate=final_candidate,
        anchor=anchor,
        anchor_structure=anchor.selector_structure,
        final_structure=final_structure,
        exception_term=exception_term,
        exception_in_bank=bool(exception_in_bank),
        exception_in_anchor=bool(exception_in_anchor),
        attempted=bool(attempted),
        eligible_selector_clients=eligible_ids,
        eligible_selector_support=eligible_support,
        anchor_role_information_score=anchor_role_score,
        augmented_role_information_score=augmented_role_score,
        outside_selector_sse_anchor=outside_anchor,
        outside_selector_sse_augmented=outside_augmented,
        augmentation_accepted=bool(accepted),
        probe_certified=bool(probe_certified),
        term_diagnostics=tuple(diagnostics),
        communication_bytes=int(anchor.communication_bytes + extra_communication),
        runtime_seconds=float(perf_counter() - start),
        stop_reason=stop_reason,
    )
