"""Phase-3B composition of frozen v11, SCR, NCEE, and full SCSV-NCSC.

The first branch is the unmodified v11 comparator. The three Phase-3 branches
share one packet/statistical infrastructure so ablation differences reflect the
prespecified scientific mechanisms rather than duplicated implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from time import perf_counter
from typing import Sequence

from .baselines import fit_federated
from .basis import CandidateEquation, TermCatalog
from .crossfit_redesign import _federated_clients, _ordered_terms, _refit, partition_clients
from .crossfit_surrogate import split_selector_probe
from .legacy_v11_adapter import LegacyV11LocalizedOutput, certify_v11_localized_from_core
from .localized_certification import (
    LocalizedCertificationResult,
    SelectorScreeningResult,
    certify_on_probe,
    screen_on_selector,
)
from .role_localization_v12 import (
    FrozenLocalizedHypothesis,
    RoleRejection,
    discover_localized_role,
)
from .scsv_v11 import SCSVELRCV11Output, scsv_elrc_v11_method
from .shared_recertification import (
    SharedRecertificationResult,
    certify_shared_core,
    nominate_shared_family,
)
from .sufficient_stats import SufficientStatsPacket, packet_from_dataset

PHASE3_METHODS = (
    "scsv-elrc-v11-full",
    "scr-only",
    "ncee-only",
    "scsv-ncsc",
)


@dataclass(frozen=True)
class Phase3MechanismLedger:
    shared_mode: str
    shared_candidate_family: tuple[str, ...]
    shared_diagnostics: tuple[object, ...]
    shared_rank_abstentions: tuple[str, ...]
    shared_capacity_truncated: bool
    localized_mode: str
    localized_candidate_family: tuple[str, ...]
    discovery_localized_diagnostics: tuple[object, ...]
    selector_diagnostics: tuple[object, ...]
    probe_diagnostics: tuple[object, ...]
    final_shared_structure: tuple[str, ...]
    final_accepted_localized: tuple[str, ...]
    final_complete_structure: tuple[str, ...]


@dataclass(frozen=True)
class SCSVV12Output:
    method: str
    candidate: CandidateEquation
    anchor: object
    shared_mode: str
    localized_mode: str
    shared_structure: tuple[str, ...]
    accepted_deviations: tuple[str, ...]
    final_structure: tuple[str, ...]
    ledger: Phase3MechanismLedger
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _packet_payload_bytes(packet: SufficientStatsPacket) -> int:
    payload = {
        "client_id": packet.client_id,
        "support": packet.support,
        "terms": packet.terms,
        "gram": packet.gram.tolist(),
        "target": packet.target.tolist(),
        "target_energy": packet.target_energy,
        "observed_support": packet.observed_support,
    }
    return len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))


def _localized_family(
    anchor,
    shared_terms: tuple[str, ...],
    catalog: TermCatalog,
) -> tuple[str, ...]:
    provenance = set(anchor.bank.candidate_terms) | set(shared_terms)
    return tuple(
        term
        for term in catalog.names()
        if term != "1"
        and catalog.get(term).kind == "exception"
        and catalog.get(term).source_term is not None
        and catalog.get(term).source_term in provenance
    )


def _phase3_packet_terms(anchor, catalog: TermCatalog) -> tuple[str, ...]:
    shared_family = nominate_shared_family(anchor, catalog)
    possible_sources = set(anchor.bank.candidate_terms) | set(shared_family)
    localized = {
        term
        for term in catalog.names()
        if catalog.get(term).kind == "exception"
        and catalog.get(term).source_term is not None
        and catalog.get(term).source_term in possible_sources
    }
    selected = set(shared_family) | localized
    return ("1",) + tuple(
        term for term in catalog.names() if term != "1" and term in selected
    )


def _build_phase3_packets(partitions, selectors, probes, catalog, terms):
    discovery = tuple(packet_from_dataset(item.discovery, catalog, terms) for item in partitions)
    selector = tuple(packet_from_dataset(item.validation, catalog, terms) for item in selectors)
    probe = tuple(packet_from_dataset(item.validation, catalog, terms) for item in probes)
    communication = sum(
        _packet_payload_bytes(packet)
        for group in (discovery, selector, probe)
        for packet in group
    )
    return discovery, selector, probe, int(communication)


def _refit_preserving_structure(
    partitions,
    catalog: TermCatalog,
    terms: tuple[str, ...],
    *,
    include_validation: bool,
    candidate_id: str,
) -> tuple[CandidateEquation, int]:
    terms = tuple(terms)
    candidate, communication = _refit(
        partitions,
        catalog,
        terms,
        include_validation=include_validation,
        candidate_id=candidate_id,
    )
    if tuple(candidate.active_terms) == terms:
        return candidate, int(communication)

    # `_refit` is a predecessor convenience wrapper that prunes coefficients
    # below 1e-3. Structural acceptance is already frozen here, so a numerical
    # refit must not silently delete an accepted term. Refit the same fixed
    # structure once without pruning and preserve the exact term identity.
    clients = _federated_clients(
        partitions,
        catalog,
        include_validation=include_validation,
    )
    raw, extra = fit_federated(clients, terms)
    if tuple(raw.active_terms) != terms:
        raise RuntimeError("fixed-structure refit changed term identity")
    return (
        CandidateEquation(terms, tuple(float(v) for v in raw.coefficients), candidate_id),
        int(communication + extra),
    )


def _run_ncee(
    *,
    anchor,
    shared_terms: tuple[str, ...],
    discovery_packets: tuple[SufficientStatsPacket, ...],
    selector_packets: tuple[SufficientStatsPacket, ...],
    probe_packets: tuple[SufficientStatsPacket, ...],
    catalog: TermCatalog,
):
    family = _localized_family(anchor, shared_terms, catalog)
    discovery_results: list[object] = []
    hypotheses: list[FrozenLocalizedHypothesis] = []
    for term in family:
        source = catalog.get(term).source_term
        result = discover_localized_role(
            shared_terms,
            discovery_packets,
            catalog,
            term=term,
            source_term=source,
            discovery_bank_terms=anchor.bank.candidate_terms,
        )
        discovery_results.append(result)
        if isinstance(result, FrozenLocalizedHypothesis):
            hypotheses.append(result)

    selector_result: SelectorScreeningResult = screen_on_selector(
        tuple(hypotheses),
        shared_terms,
        selector_packets,
        catalog,
    )
    probe_result: LocalizedCertificationResult = certify_on_probe(
        selector_result.surviving_hypotheses,
        shared_terms,
        probe_packets,
        catalog,
    )
    return family, tuple(discovery_results), selector_result, probe_result


def _make_output(
    *,
    method: str,
    anchor,
    shared_mode: str,
    localized_mode: str,
    shared_structure: tuple[str, ...],
    accepted_deviations: tuple[str, ...],
    candidate: CandidateEquation,
    communication_bytes: int,
    runtime_seconds: float,
    ledger: Phase3MechanismLedger,
) -> SCSVV12Output:
    final_structure = _ordered_terms(
        anchor.catalog if hasattr(anchor, "catalog") else None, ()
    ) if False else tuple(candidate.active_terms)
    return SCSVV12Output(
        method=method,
        candidate=candidate,
        anchor=anchor,
        shared_mode=shared_mode,
        localized_mode=localized_mode,
        shared_structure=tuple(shared_structure),
        accepted_deviations=tuple(accepted_deviations),
        final_structure=tuple(final_structure),
        ledger=ledger,
        communication_bytes=int(communication_bytes),
        runtime_seconds=float(runtime_seconds),
        stop_reason=(
            f"{method}; shared={','.join(shared_structure)}; "
            f"localized={','.join(accepted_deviations)}; "
            f"final={','.join(final_structure)}"
        ),
    )


def run_scsv_v12_branches(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    target_mse: float,
    min_repair_score: float = 0.05,
) -> tuple[object, ...]:
    """Run the four prespecified Phase-3 scientific branches in fixed order."""
    v11: SCSVELRCV11Output = scsv_elrc_v11_method(
        datasets,
        catalog,
        seed=seed,
        target_mse=target_mse,
        min_repair_score=min_repair_score,
    )

    partitions = partition_clients(datasets, seed=seed, validation_fraction=0.30)
    selectors, probes = split_selector_probe(partitions, seed=seed)
    packet_terms = _phase3_packet_terms(v11.anchor, catalog)
    discovery_packets, selector_packets, probe_packets, packet_bytes = _build_phase3_packets(
        partitions, selectors, probes, catalog, packet_terms
    )

    # Shared re-certification is computed once and reused by SCR-only/full.
    scr_result: SharedRecertificationResult = certify_shared_core(
        v11.anchor,
        selector_packets,
        catalog,
    )
    scr_shared = tuple(scr_result.accepted_shared_terms)

    # SCR-only: new shared structure + exact predecessor localized logic.
    scr_start = perf_counter()
    scr_core, scr_core_bytes = _refit_preserving_structure(
        partitions,
        catalog,
        scr_shared,
        include_validation=False,
        candidate_id="scr-only-discovery-core",
    )
    legacy: LegacyV11LocalizedOutput = certify_v11_localized_from_core(
        datasets,
        catalog,
        seed=seed,
        anchor=v11.anchor,
        core_candidate=scr_core,
    )
    scr_final = _ordered_terms(
        catalog,
        (set(scr_shared) - {"1"}) | set(legacy.accepted_deviations),
    )
    scr_candidate, scr_refit_bytes = _refit_preserving_structure(
        partitions,
        catalog,
        scr_final,
        include_validation=True,
        candidate_id="scr-only-final",
    )
    scr_ledger = Phase3MechanismLedger(
        shared_mode="scr",
        shared_candidate_family=tuple(scr_result.candidate_family),
        shared_diagnostics=tuple(scr_result.diagnostics),
        shared_rank_abstentions=tuple(scr_result.rank_abstentions),
        shared_capacity_truncated=bool(scr_result.capacity_truncated),
        localized_mode="v11-adapter",
        localized_candidate_family=tuple(legacy.candidate_deviations),
        discovery_localized_diagnostics=tuple(legacy.diagnostics),
        selector_diagnostics=(),
        probe_diagnostics=(),
        final_shared_structure=scr_shared,
        final_accepted_localized=tuple(legacy.accepted_deviations),
        final_complete_structure=tuple(scr_final),
    )
    scr_only = SCSVV12Output(
        method="scr-only",
        candidate=scr_candidate,
        anchor=v11.anchor,
        shared_mode="scr",
        localized_mode="v11-adapter",
        shared_structure=scr_shared,
        accepted_deviations=tuple(legacy.accepted_deviations),
        final_structure=tuple(scr_final),
        ledger=scr_ledger,
        communication_bytes=int(v11.anchor.communication_bytes + scr_core_bytes + legacy.communication_bytes + scr_refit_bytes),
        runtime_seconds=float(v11.anchor.runtime_seconds + (perf_counter() - scr_start)),
        stop_reason=(
            f"SCR-only; shared={','.join(scr_shared)}; "
            f"localized={','.join(legacy.accepted_deviations)}; final={','.join(scr_final)}"
        ),
    )

    # NCEE-only: predecessor ordinary shared structure exactly + new localized path.
    ncee_start = perf_counter()
    v11_shared = tuple(v11.ordinary_anchor_structure)
    ncee_family, ncee_discovery, ncee_selector, ncee_probe = _run_ncee(
        anchor=v11.anchor,
        shared_terms=v11_shared,
        discovery_packets=discovery_packets,
        selector_packets=selector_packets,
        probe_packets=probe_packets,
        catalog=catalog,
    )
    ncee_final = _ordered_terms(
        catalog,
        (set(v11_shared) - {"1"}) | set(ncee_probe.accepted_terms),
    )
    ncee_candidate, ncee_refit_bytes = _refit_preserving_structure(
        partitions,
        catalog,
        ncee_final,
        include_validation=True,
        candidate_id="ncee-only-final",
    )
    ncee_ledger = Phase3MechanismLedger(
        shared_mode="frozen-v11",
        shared_candidate_family=v11_shared,
        shared_diagnostics=(),
        shared_rank_abstentions=(),
        shared_capacity_truncated=False,
        localized_mode="ncee",
        localized_candidate_family=tuple(ncee_family),
        discovery_localized_diagnostics=tuple(ncee_discovery),
        selector_diagnostics=tuple(ncee_selector.diagnostics),
        probe_diagnostics=tuple(ncee_probe.diagnostics),
        final_shared_structure=v11_shared,
        final_accepted_localized=tuple(ncee_probe.accepted_terms),
        final_complete_structure=tuple(ncee_final),
    )
    ncee_only = SCSVV12Output(
        method="ncee-only",
        candidate=ncee_candidate,
        anchor=v11.anchor,
        shared_mode="frozen-v11",
        localized_mode="ncee",
        shared_structure=v11_shared,
        accepted_deviations=tuple(ncee_probe.accepted_terms),
        final_structure=tuple(ncee_final),
        ledger=ncee_ledger,
        communication_bytes=int(v11.anchor.communication_bytes + packet_bytes + ncee_refit_bytes),
        runtime_seconds=float(v11.anchor.runtime_seconds + (perf_counter() - ncee_start)),
        stop_reason=(
            f"NCEE-only; shared={','.join(v11_shared)}; "
            f"localized={','.join(ncee_probe.accepted_terms)}; final={','.join(ncee_final)}"
        ),
    )

    # Full: SCR shared structure + NCEE localized certification.
    full_start = perf_counter()
    full_family, full_discovery, full_selector, full_probe = _run_ncee(
        anchor=v11.anchor,
        shared_terms=scr_shared,
        discovery_packets=discovery_packets,
        selector_packets=selector_packets,
        probe_packets=probe_packets,
        catalog=catalog,
    )
    full_structure = _ordered_terms(
        catalog,
        (set(scr_shared) - {"1"}) | set(full_probe.accepted_terms),
    )
    full_candidate, full_refit_bytes = _refit_preserving_structure(
        partitions,
        catalog,
        full_structure,
        include_validation=True,
        candidate_id="scsv-ncsc-final",
    )
    full_ledger = Phase3MechanismLedger(
        shared_mode="scr",
        shared_candidate_family=tuple(scr_result.candidate_family),
        shared_diagnostics=tuple(scr_result.diagnostics),
        shared_rank_abstentions=tuple(scr_result.rank_abstentions),
        shared_capacity_truncated=bool(scr_result.capacity_truncated),
        localized_mode="ncee",
        localized_candidate_family=tuple(full_family),
        discovery_localized_diagnostics=tuple(full_discovery),
        selector_diagnostics=tuple(full_selector.diagnostics),
        probe_diagnostics=tuple(full_probe.diagnostics),
        final_shared_structure=scr_shared,
        final_accepted_localized=tuple(full_probe.accepted_terms),
        final_complete_structure=tuple(full_structure),
    )
    full = SCSVV12Output(
        method="scsv-ncsc",
        candidate=full_candidate,
        anchor=v11.anchor,
        shared_mode="scr",
        localized_mode="ncee",
        shared_structure=scr_shared,
        accepted_deviations=tuple(full_probe.accepted_terms),
        final_structure=tuple(full_structure),
        ledger=full_ledger,
        communication_bytes=int(v11.anchor.communication_bytes + packet_bytes + full_refit_bytes),
        runtime_seconds=float(v11.anchor.runtime_seconds + (perf_counter() - full_start)),
        stop_reason=(
            f"SCSV-NCSC; shared={','.join(scr_shared)}; "
            f"localized={','.join(full_probe.accepted_terms)}; final={','.join(full_structure)}"
        ),
    )

    outputs = (v11, scr_only, ncee_only, full)
    if tuple(item.method for item in outputs) != PHASE3_METHODS:
        raise RuntimeError("Phase-3 branch order drifted from the frozen method order")
    return outputs
