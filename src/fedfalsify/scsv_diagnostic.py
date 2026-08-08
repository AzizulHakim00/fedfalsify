"""Set-Conditional Structural Verification exploratory diagnostic.

This module implements the frozen spent-seed mechanism diagnostic in
research/TRANSACTIONS_SCSV_EXPLORATORY_PROTOCOL.md.  It is not a v6 evidence
implementation and it must not be used with fresh successor seeds.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
import json
from math import ceil
from time import perf_counter
from typing import Sequence

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .crossfit_redesign import PartitionedClient, _ordered_terms, _refit, partition_clients
from .crossfit_surrogate import split_selector_probe
from .high_recall_v5 import HighRecallBankProfile, build_high_recall_bank
from .role_conditional import RoleCandidateProfile, build_role_candidate_profile, run_role_fold_directions
from .stability_screen import _split_discovery_folds


@dataclass(frozen=True)
class SufficientPacket:
    client_id: str
    support: int
    terms: tuple[str, ...]
    gram: np.ndarray
    target: np.ndarray
    target_energy: float
    observed_support: tuple[int, ...]
    communication_bytes: int


@dataclass(frozen=True)
class SelectorSetProfile:
    terms: tuple[str, ...]
    coefficients: tuple[float, ...]
    weighted_mse: float
    worst_client_mse: float
    information_score: float
    complexity: int
    support: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SetTermDiagnostic:
    term: str
    kind: str
    necessity_gain: float
    loco_min_necessity_gain: float | None
    necessity_passed: bool
    best_swap_rival: str | None
    best_swap_gain: float | None
    loco_min_swap_gain: float | None
    swap_passed: bool
    eligible_clients: tuple[str, ...]
    outside_nondegradation_passed: bool
    passed: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SCSVOutput:
    method: str
    selector_candidate: CandidateEquation
    validated_candidate: CandidateEquation
    selector_structure: tuple[str, ...]
    validated_structure: tuple[str, ...]
    anchor_structure: tuple[str, ...]
    bank: HighRecallBankProfile
    role_profile: RoleCandidateProfile
    selector_profile: SelectorSetProfile
    probe_passed: bool
    term_diagnostics: tuple[SetTermDiagnostic, ...]
    candidate_sets_evaluated: int
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _json_bytes(payload: object) -> int:
    return len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))


def _packet(dataset, catalog: TermCatalog, terms: tuple[str, ...]) -> SufficientPacket:
    design = catalog.matrix(dataset.x, terms)
    gram = design.T @ design
    target = design.T @ dataset.y
    observed = tuple(
        int(np.count_nonzero(np.abs(catalog.get(term).evaluate(dataset.x)) > 1e-12))
        for term in terms
    )
    target_energy = float(dataset.y @ dataset.y)
    payload = {
        "client_id": str(dataset.client_id),
        "support": int(len(dataset.y)),
        "terms": terms,
        "gram": gram.tolist(),
        "target": target.tolist(),
        "target_energy": target_energy,
        "observed_support": observed,
    }
    return SufficientPacket(
        client_id=str(dataset.client_id),
        support=int(len(dataset.y)),
        terms=terms,
        gram=np.asarray(gram, dtype=float),
        target=np.asarray(target, dtype=float),
        target_energy=target_energy,
        observed_support=observed,
        communication_bytes=_json_bytes(payload),
    )


def _build_packets(
    partitions: Sequence[PartitionedClient],
    selectors: Sequence[PartitionedClient],
    probes: Sequence[PartitionedClient],
    catalog: TermCatalog,
    terms: tuple[str, ...],
) -> tuple[
    tuple[SufficientPacket, ...],
    tuple[SufficientPacket, ...],
    tuple[SufficientPacket, ...],
    int,
]:
    fit_packets = tuple(_packet(item.discovery, catalog, terms) for item in partitions)
    selector_packets = tuple(_packet(item.validation, catalog, terms) for item in selectors)
    probe_packets = tuple(_packet(item.validation, catalog, terms) for item in probes)
    communication = sum(
        item.communication_bytes
        for group in (fit_packets, selector_packets, probe_packets)
        for item in group
    )
    return fit_packets, selector_packets, probe_packets, int(communication)


def _indices(all_terms: tuple[str, ...], selected: tuple[str, ...]) -> np.ndarray:
    mapping = {term: index for index, term in enumerate(all_terms)}
    return np.asarray([mapping[term] for term in selected], dtype=int)


def _fit_from_packets(
    packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    selected: tuple[str, ...],
    *,
    candidate_id: str,
) -> CandidateEquation:
    index = _indices(all_terms, selected)
    gram = sum(
        (packet.gram[np.ix_(index, index)] for packet in packets),
        start=np.zeros((len(index), len(index))),
    )
    target = sum(
        (packet.target[index] for packet in packets),
        start=np.zeros(len(index)),
    )
    ridge = 1e-10 * np.eye(len(index))
    beta = np.linalg.pinv(gram + ridge) @ target
    return CandidateEquation(selected, tuple(float(value) for value in beta), candidate_id)


def _packet_sse(
    packet: SufficientPacket,
    all_terms: tuple[str, ...],
    candidate: CandidateEquation,
) -> float:
    index = _indices(all_terms, candidate.active_terms)
    beta = np.asarray(candidate.coefficients, dtype=float)
    gram = packet.gram[np.ix_(index, index)]
    target = packet.target[index]
    sse = packet.target_energy - 2.0 * float(beta @ target) + float(beta @ gram @ beta)
    return float(max(sse, 0.0))


def _profile(
    candidate: CandidateEquation,
    packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    catalog: TermCatalog,
) -> SelectorSetProfile:
    sses = [_packet_sse(packet, all_terms, candidate) for packet in packets]
    support = sum(packet.support for packet in packets)
    weighted_mse = float(sum(sses) / max(support, 1))
    worst = float(
        max(sse / max(packet.support, 1) for sse, packet in zip(sses, packets))
    )
    complexity = int(catalog.complexity(candidate.active_terms))
    information_score = float(
        np.log(max(weighted_mse, 1e-15))
        + complexity * np.log(max(support, 2)) / max(support, 1)
    )
    return SelectorSetProfile(
        terms=candidate.active_terms,
        coefficients=candidate.coefficients,
        weighted_mse=weighted_mse,
        worst_client_mse=worst,
        information_score=information_score,
        complexity=complexity,
        support=support,
    )


def _enumerate_selector(
    bank_terms: tuple[str, ...],
    fit_packets: Sequence[SufficientPacket],
    selector_packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    catalog: TermCatalog,
    *,
    max_terms: int,
) -> tuple[CandidateEquation, SelectorSetProfile, int]:
    records: list[tuple[tuple[object, ...], CandidateEquation, SelectorSetProfile]] = []
    maximum = min(len(bank_terms), max(max_terms - 1, 0))
    evaluated = 0
    for size in range(maximum + 1):
        for combo in combinations(bank_terms, size):
            selected = _ordered_terms(catalog, combo)
            candidate = _fit_from_packets(
                fit_packets,
                all_terms,
                selected,
                candidate_id=f"scsv-selector-{evaluated:04d}",
            )
            profile = _profile(candidate, selector_packets, all_terms, catalog)
            key = (
                profile.information_score,
                profile.complexity,
                len(selected) - 1,
                selected,
            )
            records.append((key, candidate, profile))
            evaluated += 1
    if not records:
        raise RuntimeError("SCSV enumerated no selector structures")
    records.sort(key=lambda item: item[0])
    _, candidate, profile = records[0]
    return candidate, profile, evaluated


def _sse_vector(
    packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    candidate: CandidateEquation,
) -> np.ndarray:
    return np.asarray(
        [_packet_sse(packet, all_terms, candidate) for packet in packets],
        dtype=float,
    )


def _loco_positive(gains: np.ndarray) -> tuple[bool, float | None]:
    if gains.size < 3:
        return True, None
    total = float(np.sum(gains))
    leave_one_out = np.asarray([total - float(value) for value in gains], dtype=float)
    return bool(np.all(leave_one_out > 0.0)), float(np.min(leave_one_out))


def _eligible_exception_indices(
    selector_packets: Sequence[SufficientPacket],
    probe_packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    term: str,
) -> tuple[int, ...]:
    term_index = all_terms.index(term)
    eligible: list[int] = []
    for index, (selector, probe) in enumerate(zip(selector_packets, probe_packets)):
        selector_floor = max(3, int(ceil(0.10 * selector.support)))
        probe_floor = max(3, int(ceil(0.10 * probe.support)))
        if (
            selector.observed_support[term_index] >= selector_floor
            and probe.observed_support[term_index] >= probe_floor
        ):
            eligible.append(index)
    return tuple(eligible)


def _nondegraded_outside(
    full: CandidateEquation,
    reduced: CandidateEquation,
    selector_packets: Sequence[SufficientPacket],
    probe_packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    eligible: tuple[int, ...],
) -> bool:
    outside = tuple(
        index for index in range(len(selector_packets)) if index not in set(eligible)
    )
    if not outside:
        return True
    for packets in (selector_packets, probe_packets):
        full_sse = sum(
            _packet_sse(packets[index], all_terms, full) for index in outside
        )
        reduced_sse = sum(
            _packet_sse(packets[index], all_terms, reduced) for index in outside
        )
        if full_sse > reduced_sse + 1e-10:
            return False
    return True


def _validate_selector_set(
    selected: CandidateEquation,
    fit_packets: Sequence[SufficientPacket],
    selector_packets: Sequence[SufficientPacket],
    probe_packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    bank_terms: tuple[str, ...],
    catalog: TermCatalog,
) -> tuple[bool, tuple[SetTermDiagnostic, ...]]:
    selected_set = set(selected.active_terms)
    full_probe = _sse_vector(probe_packets, all_terms, selected)
    diagnostics: list[SetTermDiagnostic] = []

    for term in selected.active_terms:
        if term == "1":
            continue
        kind = catalog.get(term).kind
        reduced_terms = _ordered_terms(catalog, selected_set - {term, "1"})
        reduced = _fit_from_packets(
            fit_packets,
            all_terms,
            reduced_terms,
            candidate_id=f"scsv-without-{term}",
        )
        reduced_probe = _sse_vector(probe_packets, all_terms, reduced)

        eligible_ids: tuple[str, ...]
        outside_ok = True
        if kind == "exception":
            eligible = _eligible_exception_indices(
                selector_packets, probe_packets, all_terms, term
            )
            eligible_ids = tuple(probe_packets[index].client_id for index in eligible)
            if not eligible:
                necessity_gain = float("-inf")
                necessity_passed = False
                loco_min = None
                outside_ok = False
            else:
                gains = reduced_probe[list(eligible)] - full_probe[list(eligible)]
                necessity_gain = float(np.sum(gains))
                necessity_passed = necessity_gain > 0.0
                loco_min = None
                outside_ok = _nondegraded_outside(
                    selected,
                    reduced,
                    selector_packets,
                    probe_packets,
                    all_terms,
                    eligible,
                )
                necessity_passed = bool(necessity_passed and outside_ok)
        else:
            eligible_ids = tuple(packet.client_id for packet in probe_packets)
            gains = reduced_probe - full_probe
            necessity_gain = float(np.sum(gains))
            loco_ok, loco_min = _loco_positive(gains)
            necessity_passed = bool(necessity_gain > 0.0 and loco_ok)

        best_rival: str | None = None
        best_swap_gain: float | None = None
        loco_swap_min: float | None = None
        swap_passed = True

        if kind == "core":
            rivals = [
                rival
                for rival in bank_terms
                if rival not in selected_set
                and catalog.get(rival).kind == "core"
                and catalog.get(rival).complexity <= catalog.get(term).complexity + 1
            ]
            for rival in rivals:
                swap_terms = _ordered_terms(
                    catalog,
                    (selected_set - {term, "1"}) | {rival},
                )
                swap = _fit_from_packets(
                    fit_packets,
                    all_terms,
                    swap_terms,
                    candidate_id=f"scsv-swap-{term}-to-{rival}",
                )
                swap_probe = _sse_vector(probe_packets, all_terms, swap)
                swap_gains = swap_probe - full_probe
                aggregate_gain = float(np.sum(swap_gains))
                loco_ok, local_min = _loco_positive(swap_gains)
                passed = bool(aggregate_gain > 0.0 and loco_ok)
                if (
                    best_swap_gain is None
                    or aggregate_gain < best_swap_gain
                    or (aggregate_gain == best_swap_gain and rival < str(best_rival))
                ):
                    best_rival = rival
                    best_swap_gain = aggregate_gain
                    loco_swap_min = local_min
                if not passed:
                    swap_passed = False

        passed = bool(necessity_passed and swap_passed)
        if not necessity_passed:
            reason = "conditional necessity failed"
        elif not swap_passed:
            reason = "surrogate one-swap falsification failed"
        else:
            reason = "set-conditional structural verification passed"

        diagnostics.append(
            SetTermDiagnostic(
                term=term,
                kind=kind,
                necessity_gain=float(necessity_gain),
                loco_min_necessity_gain=loco_min,
                necessity_passed=bool(necessity_passed),
                best_swap_rival=best_rival,
                best_swap_gain=best_swap_gain,
                loco_min_swap_gain=loco_swap_min,
                swap_passed=bool(swap_passed),
                eligible_clients=eligible_ids,
                outside_nondegradation_passed=bool(outside_ok),
                passed=passed,
                reason=reason,
            )
        )

    return bool(all(item.passed for item in diagnostics)), tuple(diagnostics)


def scsv_diagnostic_method(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    max_terms: int = 6,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
) -> SCSVOutput:
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
        use_score_proposer=True,
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

    probe_passed, diagnostics = _validate_selector_set(
        selector_fit,
        fit_packets,
        selector_packets,
        probe_packets,
        all_terms,
        bank.candidate_terms,
        catalog,
    )

    anchor_structure = tuple(bank.anchor_terms)
    validated_structure = selector_fit.active_terms if probe_passed else anchor_structure

    selector_candidate, _ = _refit(
        partitions,
        catalog,
        selector_fit.active_terms,
        include_validation=True,
        candidate_id="scsv-selector-final",
    )
    validated_candidate, final_payload = _refit(
        partitions,
        catalog,
        validated_structure,
        include_validation=True,
        candidate_id="scsv-validated-final",
    )
    communication += final_payload

    stop_reason = (
        "SCSV exploratory; "
        f"bank={','.join(bank.candidate_terms)}; "
        f"selector={','.join(selector_fit.active_terms)}; "
        f"probe_passed={int(probe_passed)}; "
        f"validated={','.join(validated_structure)}; "
        f"sets={evaluated}; diagnostics="
        + json.dumps(
            [item.to_dict() for item in diagnostics],
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return SCSVOutput(
        method="scsv-exploratory",
        selector_candidate=selector_candidate,
        validated_candidate=validated_candidate,
        selector_structure=selector_fit.active_terms,
        validated_structure=validated_structure,
        anchor_structure=anchor_structure,
        bank=bank,
        role_profile=role_profile,
        selector_profile=selector_profile,
        probe_passed=bool(probe_passed),
        term_diagnostics=diagnostics,
        candidate_sets_evaluated=evaluated,
        communication_bytes=int(communication),
        runtime_seconds=float(perf_counter() - start),
        stop_reason=stop_reason,
    )
