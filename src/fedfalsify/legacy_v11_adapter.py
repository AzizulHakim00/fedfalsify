"""Frozen-v11 localized certification adapter for Phase-3 SCR-only ablation.

This module does not modify the frozen v11 comparator. It reuses v11 scientific
helpers and constants while allowing an externally supplied ordinary shared
core. The adapter never reads benchmark truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .basis import CandidateEquation, TermCatalog
from .crossfit_redesign import _ordered_terms, partition_clients
from .crossfit_surrogate import split_selector_probe
from .scsv_diagnostic import _build_packets
from .scsv_v6 import SCSVV6Output
from .scsv_v8 import _outside_safety, _pair_invariant
from .scsv_v9 import _pooled_delta
from .scsv_v10 import (
    _anchor_exception_terms,
    _client_gains,
    _conditional_summary,
    _consensus_pass,
)
from .scsv_v11 import (
    V11DeviationDiagnostic,
    V11EffectRole,
    _effect_pair,
    _empty_diag,
    _localize_effect_role,
    _weak_heredity_pass,
)


@dataclass(frozen=True)
class LegacyV11LocalizedOutput:
    candidate_deviations: tuple[str, ...]
    diagnostics: tuple[V11DeviationDiagnostic, ...]
    accepted_deviations: tuple[str, ...]
    final_structure: tuple[str, ...]
    source_ambiguity: bool
    global_ambiguity: bool
    communication_bytes: int


def _validate_core(
    core_candidate: CandidateEquation,
    anchor: SCSVV6Output,
    catalog: TermCatalog,
) -> None:
    if tuple(core_candidate.active_terms)[0] != "1":
        raise ValueError("v11 adapter core must keep intercept first")
    if any(catalog.get(term).kind == "exception" for term in core_candidate.active_terms):
        raise ValueError("v11 adapter core must contain ordinary terms only")
    allowed = set(anchor.selector_structure) | set(anchor.bank.candidate_terms) | {"1"}
    if not set(core_candidate.active_terms).issubset(allowed):
        raise ValueError("v11 adapter core must come from frozen anchor/bank provenance")


def certify_v11_localized_from_core(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    anchor: SCSVV6Output,
    core_candidate: CandidateEquation,
    max_operational_exceptions: int = 2,
    quarantine_anchor: bool = True,
) -> LegacyV11LocalizedOutput:
    """Run exact v11 localized logic around a supplied ordinary shared core."""
    if max_operational_exceptions != 2:
        raise ValueError("v11 localized capacity is frozen at two exceptions")
    if not quarantine_anchor:
        raise ValueError("v11 localized adapter requires anchor quarantine")
    _validate_core(core_candidate, anchor, catalog)

    anchor_set = set(anchor.selector_structure)
    bank_set = set(anchor.bank.candidate_terms)
    anchor_exceptions = _anchor_exception_terms(anchor, catalog)

    grammar_exceptions = tuple(
        term
        for term in catalog.names()
        if term != "1"
        and catalog.get(term).kind == "exception"
        and catalog.get(term).source_term is not None
        and (
            term in anchor_set
            or catalog.get(term).source_term in bank_set
            or catalog.get(term).source_term in set(core_candidate.active_terms)
        )
    )
    candidates = tuple(dict.fromkeys(tuple(anchor_exceptions) + grammar_exceptions))

    diagnostics: list[V11DeviationDiagnostic] = []
    candidate_deviations: list[str] = []
    positive_terms: list[str] = []
    positive_sources: dict[str, list[str]] = {}
    extra_communication = 0

    if candidates:
        partitions = partition_clients(datasets, seed=seed, validation_fraction=0.30)
        selectors, probes = split_selector_probe(partitions, seed=seed)
        all_terms = tuple(
            dict.fromkeys(
                ("1",)
                + tuple(anchor.selector_structure)
                + tuple(anchor.bank.candidate_terms)
                + tuple(core_candidate.active_terms)
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
            source_in_core = source in set(core_candidate.active_terms)
            source_in_bank = source in bank_set
            weak_ok = _weak_heredity_pass(source, core_candidate, anchor.bank.candidate_terms)
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
                core_candidate,
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
                core_candidate,
                term,
                tuple(fit_packets[index] for index in role.role_indices),
                all_terms,
                catalog,
                candidate_prefix="scsv-elrc-v11-adapter-discovery",
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
    global_ambiguity = bool(len(accepted) > max_operational_exceptions)
    if global_ambiguity:
        accepted = ()

    final_structure = _ordered_terms(
        catalog,
        (set(core_candidate.active_terms) - {"1"}) | set(accepted),
    )
    return LegacyV11LocalizedOutput(
        candidate_deviations=tuple(candidate_deviations),
        diagnostics=tuple(diagnostics),
        accepted_deviations=tuple(accepted),
        final_structure=tuple(final_structure),
        source_ambiguity=bool(source_ambiguity),
        global_ambiguity=bool(global_ambiguity),
        communication_bytes=int(extra_communication),
    )
