"""FedFalsify v11: Effect-Localized Role Certification (ELRC).

V11 is an additive successor to the frozen SCSV-AQCC v10 path. It keeps the
v6 high-recall anchor, exception quarantine, independent selector/probe
certification, pair invariance, and outside-role non-degradation. The only
scientific redesign is that client roles are discovered from cross-fitted
*effect evidence* on discovery data; gate occupancy is used only as an
estimability guard. A source term provides structural provenance through the
high-recall bank and need not be globally operational when its gated child is
certified.
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
from .scsv_diagnostic import SufficientPacket, _build_packets, _packet, _packet_sse
from .scsv_v6 import SCSVV6Output, scsv_cert_method
from .scsv_v8 import ProbeState, _outside_safety, _pair_invariant, _residual_cross
from .scsv_v9 import _pooled_delta
from .scsv_v10 import (
    _anchor_exception_terms,
    _client_gains,
    _conditional_summary,
    _consensus_pass,
    _ordinary_anchor_terms,
)
from .stability_screen import _join_folds, _split_discovery_folds

ROLE_FOLDS = 5
MIN_ESTIMABLE_FOLDS = 4
MIN_POSITIVE_FOLDS = 4
MIN_SIGN_AGREEMENT = 0.80
MIN_HELDOUT_ACTIVE_ROWS = 2
MAX_ROLE_FRACTION = 0.50


@dataclass(frozen=True)
class V11ClientEffectDiagnostic:
    client_id: str
    estimable_folds: int
    positive_folds: int
    coefficient_sign_agreement: float
    median_gain: float | None
    median_coefficient: float | None
    supported: bool


@dataclass(frozen=True)
class V11EffectRole:
    term: str
    admissible: bool
    role_indices: tuple[int, ...]
    outside_indices: tuple[int, ...]
    role_client_ids: tuple[str, ...]
    outside_client_ids: tuple[str, ...]
    eligible_client_ids: tuple[str, ...]
    client_effects: tuple[V11ClientEffectDiagnostic, ...]
    reason: str


@dataclass(frozen=True)
class V11DeviationDiagnostic:
    term: str
    source_term: str
    was_anchor_exception: bool
    quarantined: bool
    in_response_bank: bool
    source_in_core_anchor: bool
    source_in_bank: bool
    weak_heredity_passed: bool
    role_admissible: bool
    role_client_ids: tuple[str, ...]
    outside_client_ids: tuple[str, ...]
    eligible_client_ids: tuple[str, ...]
    client_effects: tuple[V11ClientEffectDiagnostic, ...]
    role_reason: str
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
class SCSVELRCV11Output:
    method: str
    candidate: CandidateEquation
    anchor: SCSVV6Output
    anchor_structure: tuple[str, ...]
    ordinary_anchor_structure: tuple[str, ...]
    quarantined_anchor_exceptions: tuple[str, ...]
    final_structure: tuple[str, ...]
    bank_terms: tuple[str, ...]
    candidate_deviations: tuple[str, ...]
    diagnostics: tuple[V11DeviationDiagnostic, ...]
    accepted_deviations: tuple[str, ...]
    recertified_anchor_exceptions: tuple[str, ...]
    removed_anchor_exceptions: tuple[str, ...]
    provenance_only_sources: tuple[str, ...]
    source_ambiguity: bool
    global_ambiguity: bool
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _core_anchor_candidate(anchor: SCSVV6Output, catalog: TermCatalog) -> CandidateEquation:
    """Freeze only ordinary v6 discovery-anchor terms for v11 certification."""
    profile_terms = tuple(anchor.selector_profile.terms)
    profile_coefficients = tuple(float(v) for v in anchor.selector_profile.coefficients)
    if profile_terms != tuple(anchor.selector_structure):
        raise RuntimeError("v11 anchor selector profile/structure mismatch")
    keep = set(_ordinary_anchor_terms(anchor, catalog))
    terms = tuple(term for term in profile_terms if term in keep)
    coefficients = tuple(
        value for term, value in zip(profile_terms, profile_coefficients) if term in keep
    )
    return CandidateEquation(terms, coefficients, "scsv-elrc-v11-core-anchor-discovery")


def _weak_heredity_pass(
    source: str, core_anchor: CandidateEquation, bank_terms: Sequence[str]
) -> bool:
    """A parent is provenance-valid if globally operational or in the v6 bank."""
    return bool(source in set(core_anchor.active_terms) or source in set(bank_terms))


def _effect_pair(
    core_anchor: CandidateEquation,
    deviation: str,
    packets: Sequence[SufficientPacket],
    all_terms: tuple[str, ...],
    catalog: TermCatalog,
    *,
    candidate_prefix: str,
) -> tuple[CandidateEquation, CandidateEquation, float]:
    """Estimate only a gated deviation while freezing the ordinary core anchor."""
    if deviation in core_anchor.active_terms:
        raise ValueError("v11 effect pair expects a deviation outside the core anchor")
    if not packets:
        raise ValueError("v11 effect pair needs discovery packets")

    frozen_terms = tuple(core_anchor.active_terms)
    frozen_coefficients = tuple(float(v) for v in core_anchor.coefficients)
    deviation_index = all_terms.index(deviation)
    numerator = 0.0
    denominator = 0.0
    for packet in packets:
        numerator += _residual_cross(
            packet,
            target_term=deviation,
            frozen_terms=frozen_terms,
            frozen_coefficients=frozen_coefficients,
            all_terms=all_terms,
        )
        denominator += float(packet.gram[deviation_index, deviation_index])
    delta = float(numerator / (denominator + 1e-10))

    structure = _ordered_terms(
        catalog, (set(core_anchor.active_terms) - {"1"}) | {deviation}
    )
    coefficient_map = {
        term: float(value)
        for term, value in zip(core_anchor.active_terms, core_anchor.coefficients)
    }
    coefficient_map[deviation] = delta
    full = CandidateEquation(
        structure,
        tuple(float(coefficient_map[term]) for term in structure),
        f"{candidate_prefix}-full-{deviation}",
    )
    reduced = CandidateEquation(
        structure,
        tuple(
            0.0 if term == deviation else float(coefficient_map[term])
            for term in structure
        ),
        f"{candidate_prefix}-reduced-{deviation}",
    )
    return full, reduced, delta


def _sign_agreement(coefficients: Sequence[float]) -> float:
    signs = [1 if value > 1e-12 else -1 if value < -1e-12 else 0 for value in coefficients]
    nonzero = [value for value in signs if value != 0]
    if not nonzero:
        return 0.0
    positive = sum(value > 0 for value in nonzero)
    negative = len(nonzero) - positive
    return float(max(positive, negative) / len(nonzero))


def _role_from_client_effects(
    term: str, client_effects: Sequence[V11ClientEffectDiagnostic]
) -> V11EffectRole:
    """Convert frozen per-client cross-fit evidence into a localized role."""
    client_effects = tuple(client_effects)
    supported_indices = tuple(
        index for index, item in enumerate(client_effects) if item.supported
    )
    eligible = tuple(
        item.client_id
        for item in client_effects
        if item.estimable_folds >= MIN_ESTIMABLE_FOLDS
    )
    maximum = max(1, int(np.floor(MAX_ROLE_FRACTION * len(client_effects))))
    localized = bool(
        supported_indices
        and len(supported_indices) <= maximum
        and len(supported_indices) < len(client_effects)
    )
    if localized:
        role_set = set(supported_indices)
        outside = tuple(i for i in range(len(client_effects)) if i not in role_set)
        return V11EffectRole(
            term=term,
            admissible=True,
            role_indices=supported_indices,
            outside_indices=outside,
            role_client_ids=tuple(client_effects[i].client_id for i in supported_indices),
            outside_client_ids=tuple(client_effects[i].client_id for i in outside),
            eligible_client_ids=eligible,
            client_effects=client_effects,
            reason="discovery cross-fit effect localized to a non-global client subset",
        )

    reason = (
        "no client had stable positive discovery effect"
        if not supported_indices
        else "effect support was not localized to at most half of clients"
    )
    return V11EffectRole(
        term=term,
        admissible=False,
        role_indices=(),
        outside_indices=tuple(range(len(client_effects))),
        role_client_ids=(),
        outside_client_ids=tuple(item.client_id for item in client_effects),
        eligible_client_ids=eligible,
        client_effects=client_effects,
        reason=reason,
    )


def _localize_effect_role(
    partitions,
    core_anchor: CandidateEquation,
    all_terms: tuple[str, ...],
    term: str,
    catalog: TermCatalog,
    *,
    seed: int,
) -> tuple[V11EffectRole, int]:
    """Five-fold discovery-only effect localization with gate estimability guards."""
    folds_by_client = _split_discovery_folds(partitions, seed=seed)
    diagnostics: list[V11ClientEffectDiagnostic] = []
    communication = 0
    term_index = all_terms.index(term)

    for client_folds in folds_by_client:
        gains: list[float] = []
        coefficients: list[float] = []
        estimable = 0
        positive = 0

        for heldout in range(ROLE_FOLDS):
            train_data = _join_folds(client_folds, heldout)
            heldout_data = client_folds[heldout]
            train_packet = _packet(train_data, catalog, all_terms)
            heldout_packet = _packet(heldout_data, catalog, all_terms)
            communication += train_packet.communication_bytes + heldout_packet.communication_bytes

            active_train = int(train_packet.observed_support[term_index])
            active_heldout = int(heldout_packet.observed_support[term_index])
            if (
                active_train < 4 * MIN_HELDOUT_ACTIVE_ROWS
                or active_heldout < MIN_HELDOUT_ACTIVE_ROWS
            ):
                continue

            estimable += 1
            full, reduced, delta = _effect_pair(
                core_anchor,
                term,
                (train_packet,),
                all_terms,
                catalog,
                candidate_prefix="scsv-elrc-v11-role-crossfit",
            )
            gain = float(
                _packet_sse(heldout_packet, all_terms, reduced)
                - _packet_sse(heldout_packet, all_terms, full)
            )
            gains.append(gain)
            coefficients.append(delta)
            if gain > 0.0:
                positive += 1

        med_gain = float(median(gains)) if gains else None
        med_coef = float(median(coefficients)) if coefficients else None
        agreement = _sign_agreement(coefficients)
        supported = bool(
            estimable >= MIN_ESTIMABLE_FOLDS
            and positive >= MIN_POSITIVE_FOLDS
            and med_gain is not None
            and med_gain > 0.0
            and agreement >= MIN_SIGN_AGREEMENT
        )
        diagnostics.append(
            V11ClientEffectDiagnostic(
                client_id=str(client_folds[0].client_id),
                estimable_folds=int(estimable),
                positive_folds=int(positive),
                coefficient_sign_agreement=float(agreement),
                median_gain=med_gain,
                median_coefficient=med_coef,
                supported=supported,
            )
        )

    return _role_from_client_effects(term, diagnostics), int(communication)


def _empty_diag(
    *,
    term: str,
    source: str,
    was_anchor_exception: bool,
    in_bank: bool,
    source_in_core: bool,
    source_in_bank: bool,
    weak_ok: bool,
    role: V11EffectRole,
    reason: str,
    quarantine_anchor: bool,
) -> V11DeviationDiagnostic:
    return V11DeviationDiagnostic(
        term=term,
        source_term=source,
        was_anchor_exception=was_anchor_exception,
        quarantined=bool(quarantine_anchor and was_anchor_exception),
        in_response_bank=in_bank,
        source_in_core_anchor=source_in_core,
        source_in_bank=source_in_bank,
        weak_heredity_passed=weak_ok,
        role_admissible=role.admissible,
        role_client_ids=role.role_client_ids,
        outside_client_ids=role.outside_client_ids,
        eligible_client_ids=role.eligible_client_ids,
        client_effects=role.client_effects,
        role_reason=role.reason,
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
        rejection_reason=reason,
    )


def scsv_elrc_v11_method(
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
) -> SCSVELRCV11Output:
    """Run v11 effect-localized role certification.

    Selector/probe packets are never used for role discovery. Gate occupancy
    only decides whether a fold can estimate the candidate; role identity is
    determined by stable positive cross-fitted discovery effect.
    """
    start = perf_counter()
    if max_shared_terms != 6 or max_operational_exceptions != 2 or max_final_terms != 10:
        raise ValueError("v11 caps are frozen at shared=6, exceptions=2, final=10")
    if not quarantine_anchor:
        raise ValueError("v11 scientific path requires anchor quarantine")

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
    ordinary_anchor = _ordinary_anchor_terms(anchor, catalog)
    anchor_exceptions = _anchor_exception_terms(anchor, catalog)
    core_anchor = _core_anchor_candidate(anchor, catalog)

    grammar_exceptions = tuple(
        term
        for term in catalog.names()
        if term != "1"
        and catalog.get(term).kind == "exception"
        and catalog.get(term).source_term is not None
        and (
            term in anchor_set
            or catalog.get(term).source_term in bank_set
            or catalog.get(term).source_term in set(core_anchor.active_terms)
        )
    )
    candidates = tuple(dict.fromkeys(tuple(anchor_exceptions) + grammar_exceptions))

    diagnostics: list[V11DeviationDiagnostic] = []
    candidate_deviations: list[str] = []
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
            was_anchor_exception = term in anchor_set
            in_bank = term in bank_set
            source_in_core = source in set(core_anchor.active_terms)
            source_in_bank = source in bank_set
            weak_ok = _weak_heredity_pass(source, core_anchor, anchor.bank.candidate_terms)
            candidate_deviations.append(term)

            if not weak_ok:
                role = V11EffectRole(
                    term=term,
                    admissible=False,
                    role_indices=(),
                    outside_indices=tuple(range(len(fit_packets))),
                    role_client_ids=(),
                    outside_client_ids=tuple(item.client_id for item in fit_packets),
                    eligible_client_ids=(),
                    client_effects=(),
                    reason="source absent from both ordinary core anchor and v6 high-recall bank",
                )
                diagnostics.append(
                    _empty_diag(
                        term=term,
                        source=source,
                        was_anchor_exception=was_anchor_exception,
                        in_bank=in_bank,
                        source_in_core=source_in_core,
                        source_in_bank=source_in_bank,
                        weak_ok=False,
                        role=role,
                        reason="SOURCE-PROVENANCE-MISSING",
                        quarantine_anchor=quarantine_anchor,
                    )
                )
                continue

            role, role_bytes = _localize_effect_role(
                partitions,
                core_anchor,
                all_terms,
                term,
                catalog,
                seed=seed,
            )
            extra_communication += int(role_bytes)
            if not role.admissible:
                diagnostics.append(
                    _empty_diag(
                        term=term,
                        source=source,
                        was_anchor_exception=was_anchor_exception,
                        in_bank=in_bank,
                        source_in_core=source_in_core,
                        source_in_bank=source_in_bank,
                        weak_ok=True,
                        role=role,
                        reason="EFFECT-ROLE-NOT-LOCALIZED",
                        quarantine_anchor=quarantine_anchor,
                    )
                )
                continue

            full, reduced, delta = _effect_pair(
                core_anchor,
                term,
                tuple(fit_packets[index] for index in role.role_indices),
                all_terms,
                catalog,
                candidate_prefix="scsv-elrc-v11-discovery",
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
                full, reduced, selector_packets, probe_packets, all_terms, role.role_indices
            )
            sof, sor, sos = _outside_safety(
                full, reduced, selector_packets, all_terms, role.outside_indices
            )
            pof, por, pos = _outside_safety(
                full, reduced, probe_packets, all_terms, role.outside_indices
            )
            evidence_positive = _consensus_pass(pooled, med)
            positive = bool(invariant and sos and pos and evidence_positive)
            if positive:
                positive_terms.append(term)
                positive_sources.setdefault(source, []).append(term)

            reason = (
                "ACCEPTED"
                if positive
                else "PAIR-INVARIANT-FAIL"
                if not invariant
                else "OUTSIDE-NONDEGRADATION-FAIL"
                if not (sos and pos)
                else "POOLED-NOT-SUPPORTED"
                if pooled is None or pooled >= 0.0
                else "CLIENT-MEDIAN-CONTRADICTED"
                if med is None or med <= 0.0
                else "EVIDENCE-NOT-SUPPORTED"
            )
            diagnostics.append(
                V11DeviationDiagnostic(
                    term=term,
                    source_term=source,
                    was_anchor_exception=was_anchor_exception,
                    quarantined=bool(quarantine_anchor and was_anchor_exception),
                    in_response_bank=in_bank,
                    source_in_core_anchor=source_in_core,
                    source_in_bank=source_in_bank,
                    weak_heredity_passed=True,
                    role_admissible=True,
                    role_client_ids=role.role_client_ids,
                    outside_client_ids=role.outside_client_ids,
                    eligible_client_ids=role.eligible_client_ids,
                    client_effects=role.client_effects,
                    role_reason=role.reason,
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

        ambiguous_sources = {
            source for source, linked in positive_sources.items() if len(linked) > 1
        }
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

    base_terms = set(ordinary_anchor)
    final_structure = _ordered_terms(catalog, (base_terms - {"1"}) | set(accepted))
    if len(final_structure) > max_final_terms:
        raise RuntimeError("v11 final structure exceeded frozen ten-term cap")
    if not set(ordinary_anchor).issubset(set(final_structure)):
        raise RuntimeError("v11 deleted an ordinary/core anchor term")
    if len(accepted) > max_operational_exceptions:
        raise RuntimeError("v11 accepted too many operational exceptions")

    if tuple(final_structure) != tuple(anchor.selector_structure):
        if partitions is None:
            partitions = partition_clients(datasets, seed=seed, validation_fraction=0.30)
        final_candidate, refit_bytes = _refit(
            partitions,
            catalog,
            final_structure,
            include_validation=True,
            candidate_id="scsv-elrc-v11-final",
        )
        extra_communication += int(refit_bytes)
    else:
        final_candidate = anchor.candidate

    recertified_anchor = tuple(term for term in accepted if term in set(anchor_exceptions))
    removed_anchor = tuple(
        term for term in anchor_exceptions if term not in set(recertified_anchor)
    )
    provenance_only_sources = tuple(
        dict.fromkeys(
            catalog.get(term).source_term
            for term in accepted
            if catalog.get(term).source_term not in set(core_anchor.active_terms)
        )
    )
    stop_reason = (
        "SCSV-ELRC v11; "
        f"anchor={','.join(anchor.selector_structure)}; "
        f"ordinary={','.join(ordinary_anchor)}; "
        f"quarantined={','.join(anchor_exceptions)}; "
        f"bank={','.join(anchor.bank.candidate_terms)}; "
        f"candidates={','.join(candidate_deviations)}; "
        f"accepted={','.join(accepted)}; "
        f"removed_anchor={','.join(removed_anchor)}; "
        f"provenance_only_sources={','.join(provenance_only_sources)}; "
        f"source_ambiguity={int(source_ambiguity)}; "
        f"global_ambiguity={int(global_ambiguity)}; "
        f"final={','.join(final_structure)}"
    )
    return SCSVELRCV11Output(
        method="scsv-elrc-v11-full",
        candidate=final_candidate,
        anchor=anchor,
        anchor_structure=tuple(anchor.selector_structure),
        ordinary_anchor_structure=tuple(ordinary_anchor),
        quarantined_anchor_exceptions=tuple(anchor_exceptions),
        final_structure=tuple(final_structure),
        bank_terms=tuple(anchor.bank.candidate_terms),
        candidate_deviations=tuple(candidate_deviations),
        diagnostics=tuple(diagnostics),
        accepted_deviations=tuple(accepted),
        recertified_anchor_exceptions=tuple(recertified_anchor),
        removed_anchor_exceptions=tuple(removed_anchor),
        provenance_only_sources=tuple(provenance_only_sources),
        source_ambiguity=bool(source_ambiguity),
        global_ambiguity=bool(global_ambiguity),
        communication_bytes=int(anchor.communication_bytes + extra_communication),
        runtime_seconds=float(perf_counter() - start),
        stop_reason=stop_reason,
    )
