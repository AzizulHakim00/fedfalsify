"""Fresh-development SCSV-Cert v6 implementation.

The operational structure is the selector-chosen finite-bank set. Independent
probe diagnostics are non-destructive certificates only.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from time import perf_counter
from typing import Sequence

from .basis import CandidateEquation, TermCatalog
from .crossfit_redesign import _refit, partition_clients
from .crossfit_surrogate import split_selector_probe
from .high_recall_v5 import HighRecallBankProfile, build_high_recall_bank
from .role_conditional import RoleCandidateProfile, build_role_candidate_profile, run_role_fold_directions
from .scsv_diagnostic import (
    SelectorSetProfile,
    SetTermDiagnostic,
    _build_packets,
    _enumerate_selector,
    _validate_selector_set,
)
from .stability_screen import _split_discovery_folds


@dataclass(frozen=True)
class SCSVV6Output:
    method: str
    candidate: CandidateEquation
    selector_structure: tuple[str, ...]
    bank: HighRecallBankProfile
    role_profile: RoleCandidateProfile
    selector_profile: SelectorSetProfile
    probe_certified: bool
    term_diagnostics: tuple[SetTermDiagnostic, ...]
    candidate_sets_evaluated: int
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def scsv_cert_method(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    max_terms: int = 6,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
    use_score_proposer: bool = True,
) -> SCSVV6Output:
    start = perf_counter()
    partitions = partition_clients(datasets, seed=seed, validation_fraction=0.30)
    selectors, probes = split_selector_probe(partitions, seed=seed)

    folds = _split_discovery_folds(partitions, seed=seed)
    directions = run_role_fold_directions(
        folds,
        catalog,
        max_terms=max_terms,
        target_mse=target_mse,
        min_repair_score=min_repair_score,
    )
    communication = sum(item.communication_bytes for item in directions)

    role_profile = build_role_candidate_profile(
        directions,
        catalog,
        client_count=len(partitions),
        maximum_size=8,
        role_conditioning=True,
        path_persistence=True,
    )
    bank = build_high_recall_bank(
        partitions,
        catalog,
        role_profile,
        max_terms=max_terms,
        use_score_proposer=use_score_proposer,
        use_bundle_rescue=False,
        role_conditioning=True,
        maximum_size=10,
    )
    communication += bank.communication_bytes

    all_terms = ("1",) + tuple(bank.candidate_terms)
    fit_packets, selector_packets, probe_packets, packet_bytes = _build_packets(
        partitions, selectors, probes, catalog, all_terms
    )
    communication += packet_bytes

    selector_fit, selector_profile, evaluated = _enumerate_selector(
        bank.candidate_terms,
        fit_packets,
        selector_packets,
        all_terms,
        catalog,
        max_terms=max_terms,
    )
    probe_certified, diagnostics = _validate_selector_set(
        selector_fit,
        fit_packets,
        selector_packets,
        probe_packets,
        all_terms,
        bank.candidate_terms,
        catalog,
    )

    # V6 operational rule: the independent probe is audit-only. It never
    # deletes terms and never replaces the selector-chosen structure.
    candidate, final_payload = _refit(
        partitions,
        catalog,
        selector_fit.active_terms,
        include_validation=True,
        candidate_id="scsv-cert-v6-final",
    )
    communication += final_payload

    stop_reason = (
        "SCSV-Cert v6; "
        f"score={int(use_score_proposer)}; "
        f"bank={','.join(bank.candidate_terms)}; "
        f"selector={','.join(selector_fit.active_terms)}; "
        f"probe_certified={int(probe_certified)}; "
        f"sets={evaluated}; diagnostics="
        + json.dumps(
            [item.to_dict() for item in diagnostics],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return SCSVV6Output(
        method="scsv-cert-v6",
        candidate=candidate,
        selector_structure=selector_fit.active_terms,
        bank=bank,
        role_profile=role_profile,
        selector_profile=selector_profile,
        probe_certified=bool(probe_certified),
        term_diagnostics=diagnostics,
        candidate_sets_evaluated=evaluated,
        communication_bytes=int(communication),
        runtime_seconds=float(perf_counter() - start),
        stop_reason=stop_reason,
    )