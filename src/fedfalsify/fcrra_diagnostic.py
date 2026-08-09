"""Frozen-Core Role Residual Augmentation spent-seed mechanism diagnostic.

Post-independent forensic tooling only.  FCRRA calls the frozen SCSV-Cert v6
method unchanged, freezes the selector-fit shared coefficients, and may estimate
only a banked declared exception coefficient from role-eligible discovery
residual sufficient statistics.
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
from .scsv_diagnostic import (
    SetTermDiagnostic,
    _build_packets,
    _packet_sse,
    _profile,
    _validate_selector_set,
)
from .scsv_v6 import SCSVV6Output, scsv_cert_method


@dataclass(frozen=True)
class FCRRAOutput:
    method: str
    candidate: CandidateEquation
    anchor: SCSVV6Output
    anchor_structure: tuple[str, ...]
    final_structure: tuple[str, ...]
    anchor_discovery_coefficients: tuple[float, ...]
    final_coefficients: tuple[float, ...]
    exception_term: str | None
    exception_in_bank: bool
    exception_in_anchor: bool
    attempted: bool
    eligible_discovery_clients: tuple[str, ...]
    eligible_discovery_support: int
    eligible_selector_clients: tuple[str, ...]
    eligible_selector_support: int
    residual_numerator: float | None
    residual_denominator: float | None
    exception_coefficient: float | None
    anchor_role_information_score: float | None
    augmented_role_information_score: float | None
    outside_selector_sse_max_difference: float | None
    outside_selector_prediction_max_difference: float | None
    augmentation_accepted: bool
    probe_certified: bool
    term_diagnostics: tuple[SetTermDiagnostic, ...]
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _role_indices(packets, all_terms: tuple[str, ...], term: str) -> tuple[int, ...]:
    """Return clients whose local support satisfies the frozen 10% role floor."""

    term_index = all_terms.index(term)
    eligible: list[int] = []
    for index, packet in enumerate(packets):
        floor = max(3, int(ceil(0.10 * packet.support)))
        if packet.observed_support[term_index] >= floor:
            eligible.append(index)
    return tuple(eligible)


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
        raise RuntimeError("FCRRA diagnostic is frozen for at most one exception term")
    if not exception_terms:
        return None, False, False
    term = exception_terms[0]
    return term, True, term in set(anchor.selector_structure)


def _anchor_discovery_candidate(anchor: SCSVV6Output) -> CandidateEquation:
    """Recover the selector-fit candidate without refitting any shared coefficient."""

    if tuple(anchor.selector_profile.terms) != tuple(anchor.selector_structure):
        raise RuntimeError("v6 selector profile/structure mismatch")
    return CandidateEquation(
        tuple(anchor.selector_structure),
        tuple(float(value) for value in anchor.selector_profile.coefficients),
        "fcrra-frozen-discovery-anchor",
    )


def _residual_exception_coefficient(
    fit_packets,
    all_terms: tuple[str, ...],
    anchor: CandidateEquation,
    exception_term: str,
    eligible: tuple[int, ...],
) -> tuple[float, float, float]:
    """Estimate only gamma from eligible discovery residual sufficient statistics."""

    if not eligible:
        raise ValueError("FCRRA residual coefficient requires eligible discovery clients")
    mapping = {term: index for index, term in enumerate(all_terms)}
    e_index = mapping[exception_term]
    anchor_index = np.asarray([mapping[term] for term in anchor.active_terms], dtype=int)
    beta = np.asarray(anchor.coefficients, dtype=float)

    numerator = 0.0
    denominator = 0.0
    for index in eligible:
        packet = fit_packets[index]
        numerator += float(
            packet.target[e_index]
            - packet.gram[e_index, anchor_index] @ beta
        )
        denominator += float(packet.gram[e_index, e_index])
    gamma = float(numerator / (denominator + 1e-10))
    return float(numerator), float(denominator), gamma


def _augment_frozen_anchor(
    anchor: CandidateEquation,
    catalog: TermCatalog,
    exception_term: str,
    gamma: float,
) -> CandidateEquation:
    """Add one restricted coefficient while preserving every shared coefficient."""

    terms = _ordered_terms(
        catalog,
        (set(anchor.active_terms) - {"1"}) | {exception_term},
    )
    coefficient_map = {
        term: float(value)
        for term, value in zip(anchor.active_terms, anchor.coefficients)
    }
    coefficient_map[exception_term] = float(gamma)
    coefficients = tuple(float(coefficient_map[term]) for term in terms)
    return CandidateEquation(terms, coefficients, "fcrra-frozen-core-augmented")


def _outside_selector_differences(
    anchor: CandidateEquation,
    augmented: CandidateEquation,
    selectors,
    selector_packets,
    all_terms: tuple[str, ...],
    eligible: tuple[int, ...],
    catalog: TermCatalog,
) -> tuple[float, float]:
    eligible_set = set(eligible)
    max_sse = 0.0
    max_prediction = 0.0
    for index, packet in enumerate(selector_packets):
        if index in eligible_set:
            continue
        anchor_sse = _packet_sse(packet, all_terms, anchor)
        augmented_sse = _packet_sse(packet, all_terms, augmented)
        max_sse = max(max_sse, abs(float(augmented_sse - anchor_sse)))
        x = selectors[index].validation.x
        delta = np.asarray(
            augmented.predict(x, catalog) - anchor.predict(x, catalog), dtype=float
        )
        if delta.size:
            max_prediction = max(max_prediction, float(np.max(np.abs(delta))))
    return float(max_sse), float(max_prediction)


def fcrra_diagnostic_method(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    max_terms: int = 6,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
) -> FCRRAOutput:
    """Run frozen v6 plus residual-only role-local exception augmentation."""

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

    anchor_discovery = _anchor_discovery_candidate(anchor)
    final_candidate = anchor.candidate
    final_structure = anchor.selector_structure
    attempted = False
    accepted = False
    discovery_ids: tuple[str, ...] = ()
    selector_ids: tuple[str, ...] = ()
    discovery_support = 0
    selector_support = 0
    numerator: float | None = None
    denominator: float | None = None
    gamma: float | None = None
    anchor_role_score: float | None = None
    augmented_role_score: float | None = None
    outside_sse_diff: float | None = None
    outside_prediction_diff: float | None = None
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
        partitions = partition_clients(datasets, seed=seed, validation_fraction=0.30)
        selectors, probes = split_selector_probe(partitions, seed=seed)
        all_terms = ("1",) + tuple(anchor.bank.candidate_terms)
        fit_packets, selector_packets, probe_packets, packet_bytes = _build_packets(
            partitions, selectors, probes, catalog, all_terms
        )
        extra_communication += int(packet_bytes)

        discovery_eligible = _role_indices(fit_packets, all_terms, exception_term)
        selector_eligible = _role_indices(selector_packets, all_terms, exception_term)
        discovery_ids = tuple(fit_packets[index].client_id for index in discovery_eligible)
        selector_ids = tuple(selector_packets[index].client_id for index in selector_eligible)
        discovery_support = int(sum(fit_packets[index].support for index in discovery_eligible))
        selector_support = int(
            sum(selector_packets[index].support for index in selector_eligible)
        )

        if discovery_eligible and selector_eligible:
            numerator, denominator, gamma = _residual_exception_coefficient(
                fit_packets,
                all_terms,
                anchor_discovery,
                exception_term,
                discovery_eligible,
            )
            augmented = _augment_frozen_anchor(
                anchor_discovery, catalog, exception_term, gamma
            )
            if len(augmented.active_terms) > max_terms:
                raise RuntimeError("FCRRA augmentation exceeded frozen size cap")

            # Shared coefficients must be exactly inherited from the discovery anchor.
            anchor_map = dict(zip(anchor_discovery.active_terms, anchor_discovery.coefficients))
            augmented_map = dict(zip(augmented.active_terms, augmented.coefficients))
            for term, value in anchor_map.items():
                if augmented_map.get(term) != value:
                    raise RuntimeError("FCRRA modified a frozen shared coefficient")

            eligible_packets = tuple(selector_packets[index] for index in selector_eligible)
            anchor_profile = _profile(
                anchor_discovery, eligible_packets, all_terms, catalog
            )
            augmented_profile = _profile(
                augmented, eligible_packets, all_terms, catalog
            )
            anchor_role_score = float(anchor_profile.information_score)
            augmented_role_score = float(augmented_profile.information_score)
            outside_sse_diff, outside_prediction_diff = _outside_selector_differences(
                anchor_discovery,
                augmented,
                selectors,
                selector_packets,
                all_terms,
                selector_eligible,
                catalog,
            )
            if outside_sse_diff > 1e-10 or outside_prediction_diff > 1e-10:
                raise RuntimeError(
                    "FCRRA restricted augmentation changed an outside-role prediction"
                )

            accepted = bool(augmented_role_score < anchor_role_score)
            if accepted:
                final_candidate = augmented
                final_structure = augmented.active_terms
                probe_certified, diagnostics = _validate_selector_set(
                    augmented,
                    fit_packets,
                    selector_packets,
                    probe_packets,
                    all_terms,
                    tuple(anchor.bank.candidate_terms),
                    catalog,
                )

    if not set(anchor.selector_structure).issubset(set(final_structure)):
        raise RuntimeError("FCRRA deleted or replaced a frozen v6 selected term")

    stop_reason = (
        "FCRRA spent-seed diagnostic; "
        f"anchor={','.join(anchor.selector_structure)}; "
        f"exception={exception_term or ''}; "
        f"in_bank={int(exception_in_bank)}; "
        f"in_anchor={int(exception_in_anchor)}; "
        f"attempted={int(attempted)}; "
        f"eligible_discovery={','.join(discovery_ids)}; "
        f"eligible_selector={','.join(selector_ids)}; "
        f"numerator={numerator}; denominator={denominator}; gamma={gamma}; "
        f"anchor_role_ic={anchor_role_score}; "
        f"augmented_role_ic={augmented_role_score}; "
        f"outside_sse_max_diff={outside_sse_diff}; "
        f"outside_prediction_max_diff={outside_prediction_diff}; "
        f"accepted={int(accepted)}; final={','.join(final_structure)}; "
        "wrapper_overhead_unoptimized=1"
    )
    return FCRRAOutput(
        method="fcrra-spent-diagnostic",
        candidate=final_candidate,
        anchor=anchor,
        anchor_structure=anchor.selector_structure,
        final_structure=final_structure,
        anchor_discovery_coefficients=tuple(anchor_discovery.coefficients),
        final_coefficients=tuple(final_candidate.coefficients),
        exception_term=exception_term,
        exception_in_bank=bool(exception_in_bank),
        exception_in_anchor=bool(exception_in_anchor),
        attempted=bool(attempted),
        eligible_discovery_clients=discovery_ids,
        eligible_discovery_support=discovery_support,
        eligible_selector_clients=selector_ids,
        eligible_selector_support=selector_support,
        residual_numerator=numerator,
        residual_denominator=denominator,
        exception_coefficient=gamma,
        anchor_role_information_score=anchor_role_score,
        augmented_role_information_score=augmented_role_score,
        outside_selector_sse_max_difference=outside_sse_diff,
        outside_selector_prediction_max_difference=outside_prediction_diff,
        augmentation_accepted=bool(accepted),
        probe_certified=bool(probe_certified),
        term_diagnostics=tuple(diagnostics),
        communication_bytes=int(anchor.communication_bytes + extra_communication),
        runtime_seconds=float(perf_counter() - start),
        stop_reason=stop_reason,
    )
