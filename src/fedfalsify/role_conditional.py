"""Role-conditioned dual-evidence structural search for FedFalsify v4.

This module is a new development path motivated by the frozen v3 NO-GO.  It
keeps selector/probe thresholds unchanged while changing candidate evidence
architecture: residual-rank evidence is fused with fold-level path persistence,
restricted exceptions use an eligible-client denominator, and every forward or
backward structural change is tested termwise on disjoint selector/probe data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from math import ceil
from statistics import median
from time import perf_counter
from typing import Sequence

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .crossfit_redesign import (
    PartitionedClient,
    SplitFederatedFalsifierClient,
    ValidationProfile,
    _admissible_fallback,
    _discovery_communication,
    _nonzero_terms,
    _ordered_terms,
    _refit,
    _validation_profile,
    partition_clients,
)
from .crossfit_surrogate import (
    ProbeTermDiagnostic,
    StructuralProbeProfile,
    _probe_profile,
    _term_probe_diagnostic,
    split_selector_probe,
)
from .stability_screen import (
    FoldTermEvidence,
    _fold_observability_floor,
    _join_folds,
    _passes_stability_rule,
    _record_evidence,
    _sign_agreement,
    _split_discovery_folds,
)
from .server import DiscoveryResult, FedFalsifyDiscovery


@dataclass(frozen=True)
class RoleFoldDirection:
    result: DiscoveryResult
    selected_terms: tuple[str, ...]
    best_terms: tuple[str, ...]
    top3_terms: tuple[str, ...]
    term_evidence: dict[str, FoldTermEvidence]
    exception_heterogeneity: tuple[tuple[str, float], ...]
    observability_floor: int
    communication_bytes: int


@dataclass(frozen=True)
class RoleTermDiagnostic:
    term: str
    kind: str
    selected_fold_count: int
    best_repair_fold_count: int
    top3_repair_fold_count: int
    median_abs_residual_correlation: float
    residual_sign_agreement: float
    coefficient_sign_stability: float
    client_coverage: float
    observable_client_folds: int
    exception_valid_fold_count: int
    residual_channel_passed: bool
    path_channel_passed: bool
    channels_passed: int
    admitted: bool
    admission_reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RoleCandidateProfile:
    candidate_terms: tuple[str, ...]
    diagnostics: tuple[RoleTermDiagnostic, ...]
    fold_selected_terms: tuple[tuple[str, ...], ...]
    maximum_size: int
    role_conditioning: bool
    path_persistence: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_terms": self.candidate_terms,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "fold_selected_terms": self.fold_selected_terms,
            "maximum_size": self.maximum_size,
            "role_conditioning": self.role_conditioning,
            "path_persistence": self.path_persistence,
        }


@dataclass(frozen=True)
class TermwiseDecision:
    stage: str
    term: str
    source: str
    selector_passed: bool
    probe_passed: bool
    accepted: bool
    selector_reason: str
    probe_reason: str
    before_terms: tuple[str, ...]
    after_terms: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RoleConditionalOutput:
    method: str
    candidate: CandidateEquation
    forward_candidate: CandidateEquation
    anchor_candidate: CandidateEquation
    candidate_profile: RoleCandidateProfile
    anchor_terms: tuple[str, ...]
    forward_terms: tuple[str, ...]
    final_terms: tuple[str, ...]
    forward_decisions: tuple[TermwiseDecision, ...]
    backward_decisions: tuple[TermwiseDecision, ...]
    probe_profiles: tuple[StructuralProbeProfile, ...]
    validation_profile: ValidationProfile
    forward_validation_profile: ValidationProfile
    anchor_validation_profile: ValidationProfile
    communication_bytes: int
    forward_communication_bytes: int
    anchor_communication_bytes: int
    runtime_seconds: float
    forward_runtime_seconds: float
    anchor_runtime_seconds: float
    stop_reason: str


def _max_exception_heterogeneity(
    engine: FedFalsifyDiscovery,
    result: DiscoveryResult,
    clients: Sequence[SplitFederatedFalsifierClient],
    catalog: TermCatalog,
) -> tuple[tuple[str, float], ...]:
    """Maximum valid exception heterogeneity seen while replaying one direction."""

    exception_terms = [
        term
        for term in catalog.names()
        if term != "1"
        and catalog.get(term).kind == "exception"
        and catalog.get(term).source_term is not None
    ]
    if not exception_terms:
        return ()
    candidates = [record.candidate for record in result.history] or [result.candidate]
    best = {term: 0.0 for term in exception_terms}
    for candidate in candidates:
        certificates = tuple(client.falsify(candidate) for client in clients)
        for term in exception_terms:
            source = catalog.get(term).source_term
            if source is None:
                continue
            score, _, _ = engine._exception_heterogeneity(  # noqa: SLF001
                term, source, certificates
            )
            best[term] = max(best[term], float(score))
    return tuple(sorted(best.items()))


def run_role_fold_directions(
    folds_by_client,
    catalog: TermCatalog,
    *,
    max_terms: int,
    target_mse: float,
    min_repair_score: float,
) -> tuple[RoleFoldDirection, ...]:
    directions: list[RoleFoldDirection] = []
    for heldout in range(5):
        clients: list[SplitFederatedFalsifierClient] = []
        sizes: list[int] = []
        for folds in folds_by_client:
            certificate = folds[heldout]
            sizes.append(len(certificate.y))
            clients.append(
                SplitFederatedFalsifierClient(
                    _join_folds(folds, heldout), certificate, catalog
                )
            )
        floor = _fold_observability_floor(min(sizes))
        engine = FedFalsifyDiscovery(
            clients,  # type: ignore[arg-type]
            catalog,
            max_rounds=max_terms + 2,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=min_repair_score,
            min_observed_support=floor,
            use_coefficient_heterogeneity=True,
        )
        result = engine.discover()
        best, top3, evidence = _record_evidence(
            engine, result, clients, catalog, floor
        )
        heterogeneity = _max_exception_heterogeneity(
            engine, result, clients, catalog
        )
        directions.append(
            RoleFoldDirection(
                result=result,
                selected_terms=_ordered_terms(
                    catalog, _nonzero_terms(result.candidate)
                ),
                best_terms=best,
                top3_terms=top3,
                term_evidence=evidence,
                exception_heterogeneity=heterogeneity,
                observability_floor=floor,
                communication_bytes=_discovery_communication(result, clients),
            )
        )
    return tuple(directions)


def _heterogeneity_map(direction: RoleFoldDirection) -> dict[str, float]:
    return dict(direction.exception_heterogeneity)


def build_role_candidate_profile(
    directions: Sequence[RoleFoldDirection],
    catalog: TermCatalog,
    *,
    client_count: int,
    maximum_size: int = 8,
    role_conditioning: bool = True,
    path_persistence: bool = True,
) -> RoleCandidateProfile:
    if len(directions) != 5:
        raise ValueError("v4 requires five discovery directions")
    selected_sets = [set(item.selected_terms) - {"1"} for item in directions]
    diagnostics: list[RoleTermDiagnostic] = []

    for term in catalog.names():
        if term == "1":
            continue
        correlations: list[tuple[str, float, float]] = []
        adjustments: list[tuple[str, float, float]] = []
        for direction in directions:
            evidence = direction.term_evidence[term]
            correlations.extend(evidence.correlations)
            adjustments.extend(evidence.adjustments)

        observed_clients = {
            client for client, _, _ in correlations + adjustments
        }
        selected_count = sum(term in selected for selected in selected_sets)
        best_count = sum(term in item.best_terms for item in directions)
        top3_count = sum(term in item.top3_terms for item in directions)
        residual_sign = _sign_agreement(correlations)
        coefficient_sign = _sign_agreement(adjustments)
        coverage = len(observed_clients) / max(client_count, 1)
        abs_correlations = [
            abs(value) for _, value, _ in correlations if np.isfinite(value)
        ]
        median_abs = float(median(abs_correlations)) if abs_correlations else 0.0
        kind = catalog.get(term).kind
        valid_exception_folds = sum(
            _heterogeneity_map(item).get(term, 0.0) >= 0.20
            for item in directions
        )

        if role_conditioning and kind == "exception":
            residual_channel = (
                best_count >= 2
                and valid_exception_folds >= 3
                and coefficient_sign >= 0.60
            )
            path_channel = (
                path_persistence
                and selected_count >= 3
                and valid_exception_folds >= 3
                and coefficient_sign >= 0.60
            )
            admitted = residual_channel or path_channel
            reason = (
                "role-conditioned exception residual/path evidence"
                if admitted
                else "restricted exception lacked repeated eligible evidence"
            )
        else:
            residual_channel, _ = _passes_stability_rule(
                best_repair_fold_count=best_count,
                top3_repair_fold_count=top3_count,
                weighted_sign_agreement=residual_sign,
                client_coverage=coverage,
            )
            path_channel = bool(
                path_persistence
                and selected_count >= 3
                and coefficient_sign >= 0.60
                and residual_sign >= 0.60
                and coverage >= 0.50
            )
            admitted = bool(residual_channel or path_channel)
            if residual_channel and path_channel:
                reason = "core residual-rank and path-persistence evidence"
            elif residual_channel:
                reason = "core residual-rank evidence"
            elif path_channel:
                reason = "core path-persistence evidence"
            else:
                reason = "no frozen core evidence channel passed"

        diagnostics.append(
            RoleTermDiagnostic(
                term=term,
                kind=kind,
                selected_fold_count=selected_count,
                best_repair_fold_count=best_count,
                top3_repair_fold_count=top3_count,
                median_abs_residual_correlation=median_abs,
                residual_sign_agreement=residual_sign,
                coefficient_sign_stability=coefficient_sign,
                client_coverage=coverage,
                observable_client_folds=len(correlations),
                exception_valid_fold_count=valid_exception_folds,
                residual_channel_passed=bool(residual_channel),
                path_channel_passed=bool(path_channel),
                channels_passed=int(bool(residual_channel)) + int(bool(path_channel)),
                admitted=bool(admitted),
                admission_reason=reason,
            )
        )

    ranked = sorted(
        (item for item in diagnostics if item.admitted),
        key=lambda item: (
            -item.channels_passed,
            -item.selected_fold_count,
            -item.best_repair_fold_count,
            -item.top3_repair_fold_count,
            -item.median_abs_residual_correlation,
            -item.coefficient_sign_stability,
            catalog.get(item.term).complexity,
            item.term,
        ),
    )
    return RoleCandidateProfile(
        candidate_terms=tuple(item.term for item in ranked[:maximum_size]),
        diagnostics=tuple(diagnostics),
        fold_selected_terms=tuple(item.selected_terms for item in directions),
        maximum_size=maximum_size,
        role_conditioning=role_conditioning,
        path_persistence=path_persistence,
    )


def _eligible_exception_partitions(
    selectors: Sequence[PartitionedClient],
    probes: Sequence[PartitionedClient],
    catalog: TermCatalog,
    term: str,
) -> tuple[tuple[PartitionedClient, ...], tuple[PartitionedClient, ...]]:
    selected: list[PartitionedClient] = []
    heldout: list[PartitionedClient] = []
    basis = catalog.get(term)
    for selector, probe in zip(selectors, probes):
        selector_values = basis.evaluate(selector.validation.x)
        probe_values = basis.evaluate(probe.validation.x)
        selector_floor = max(3, int(ceil(0.10 * len(selector_values))))
        probe_floor = max(3, int(ceil(0.10 * len(probe_values))))
        selector_support = int(np.sum(np.abs(selector_values) > 1e-12))
        probe_support = int(np.sum(np.abs(probe_values) > 1e-12))
        if selector_support >= selector_floor and probe_support >= probe_floor:
            selected.append(selector)
            heldout.append(probe)
    return tuple(selected), tuple(heldout)


def _failed_probe(source: str, term: str, reason: str) -> StructuralProbeProfile:
    diagnostic = ProbeTermDiagnostic(
        term=term,
        rivals=(),
        proposed_probe_improvement=0.0,
        best_rival=None,
        best_rival_probe_improvement=0.0,
        relative_advantage=-1.0,
        client_win_fraction=0.0,
        selector_sign_agreement=0.0,
        passed=False,
        reason=reason,
    )
    payload = len(
        json.dumps(diagnostic.to_dict(), separators=(",", ":")).encode("utf-8")
    )
    return StructuralProbeProfile(
        source=source,
        passed=False,
        term_diagnostics=(diagnostic,),
        communication_bytes=payload,
    )


def _role_probe_profile(
    source: str,
    term: str,
    primary: CandidateEquation,
    candidate: CandidateEquation,
    selectors: Sequence[PartitionedClient],
    probes: Sequence[PartitionedClient],
    catalog: TermCatalog,
    *,
    role_conditioning: bool,
) -> StructuralProbeProfile:
    if role_conditioning and catalog.get(term).kind == "exception":
        eligible_selectors, eligible_probes = _eligible_exception_partitions(
            selectors, probes, catalog, term
        )
        if not eligible_selectors:
            return _failed_probe(
                source, term, "no eligible gated client in selector/probe data"
            )
        diagnostic = _term_probe_diagnostic(
            term,
            primary,
            candidate,
            eligible_selectors,
            eligible_probes,
            catalog,
        )
        payload = len(
            json.dumps(diagnostic.to_dict(), separators=(",", ":")).encode("utf-8")
        )
        return StructuralProbeProfile(
            source=source,
            passed=diagnostic.passed,
            term_diagnostics=(diagnostic,),
            communication_bytes=payload,
        )
    return _probe_profile(source, primary, candidate, selectors, probes, catalog)


def _candidate_terms(candidate: CandidateEquation) -> tuple[str, ...]:
    return tuple(term for term in candidate.active_terms if term != "1")


def role_conditional_method(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    max_terms: int = 6,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
    role_conditioning: bool = True,
    path_persistence: bool = True,
    backward_audit: bool = True,
) -> RoleConditionalOutput:
    start = perf_counter()
    partitions = partition_clients(
        datasets, seed=seed, validation_fraction=0.30
    )
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
    profile = build_role_candidate_profile(
        directions,
        catalog,
        client_count=len(partitions),
        maximum_size=8,
        role_conditioning=role_conditioning,
        path_persistence=path_persistence,
    )

    selected_sets = [set(item.selected_terms) - {"1"} for item in directions]
    intersection = set(selected_sets[0])
    for selected in selected_sets[1:]:
        intersection &= selected
    anchor_terms = _ordered_terms(catalog, intersection)
    anchor, payload = _refit(
        partitions,
        catalog,
        anchor_terms,
        include_validation=False,
        candidate_id="v4-anchor",
    )
    communication += payload
    anchor_profile, payload = _validation_profile(
        "v4-anchor", anchor, selectors, catalog
    )
    communication += payload
    anchor_comm_snapshot = communication
    anchor_runtime_snapshot = perf_counter() - start

    current = anchor
    current_profile = anchor_profile
    forward_decisions: list[TermwiseDecision] = []
    probe_profiles: list[StructuralProbeProfile] = []
    accepted_order: list[str] = []

    for rank, term in enumerate(profile.candidate_terms, start=1):
        if term in set(current.active_terms):
            continue
        if len(current.active_terms) >= max_terms:
            forward_decisions.append(
                TermwiseDecision(
                    stage="forward",
                    term=term,
                    source=f"v4-forward-{rank:02d}",
                    selector_passed=False,
                    probe_passed=False,
                    accepted=False,
                    selector_reason="maximum final structure reached",
                    probe_reason="not evaluated",
                    before_terms=current.active_terms,
                    after_terms=current.active_terms,
                )
            )
            continue
        before = current.active_terms
        proposal_terms = _ordered_terms(
            catalog, set(_candidate_terms(current)) | {term}
        )
        proposal, payload = _refit(
            partitions,
            catalog,
            proposal_terms,
            include_validation=False,
            candidate_id=f"v4-forward-{rank:02d}-{term}",
        )
        communication += payload
        proposal_profile, payload = _validation_profile(
            f"v4-forward-{rank:02d}", proposal, selectors, catalog
        )
        communication += payload
        allowed, payload, selector_reason = _admissible_fallback(
            current,
            current_profile,
            proposal,
            proposal_profile,
            selectors,
            catalog,
        )
        communication += payload
        if allowed:
            probe = _role_probe_profile(
                f"v4-forward-{rank:02d}",
                term,
                current,
                proposal,
                selectors,
                probes,
                catalog,
                role_conditioning=role_conditioning,
            )
            probe_profiles.append(probe)
            communication += probe.communication_bytes
            probe_passed = probe.passed
            probe_reason = (
                probe.term_diagnostics[0].reason
                if probe.term_diagnostics
                else "no term diagnostic"
            )
        else:
            probe_passed = False
            probe_reason = "not evaluated"
        accepted = bool(allowed and probe_passed)
        if accepted:
            current = proposal
            current_profile = proposal_profile
            accepted_order.append(term)
        forward_decisions.append(
            TermwiseDecision(
                stage="forward",
                term=term,
                source=f"v4-forward-{rank:02d}",
                selector_passed=bool(allowed),
                probe_passed=bool(probe_passed),
                accepted=accepted,
                selector_reason=selector_reason,
                probe_reason=probe_reason,
                before_terms=before,
                after_terms=current.active_terms,
            )
        )

    forward = current
    forward_profile = current_profile
    forward_comm_snapshot = communication
    forward_runtime_snapshot = perf_counter() - start

    backward_decisions: list[TermwiseDecision] = []
    if backward_audit:
        current_terms = [term for term in current.active_terms if term != "1"]
        reverse_order = list(reversed(accepted_order))
        reverse_order.extend(
            term
            for term in reversed(current_terms)
            if term not in set(reverse_order)
        )
        for index, term in enumerate(reverse_order, start=1):
            if term not in set(current.active_terms):
                continue
            before = current.active_terms
            deletion_terms = _ordered_terms(
                catalog,
                set(_candidate_terms(current)) - {term},
            )
            deletion, payload = _refit(
                partitions,
                catalog,
                deletion_terms,
                include_validation=False,
                candidate_id=f"v4-backward-{index:02d}-drop-{term}",
            )
            communication += payload
            deletion_profile, payload = _validation_profile(
                f"v4-backward-{index:02d}-drop",
                deletion,
                selectors,
                catalog,
            )
            communication += payload
            retain, payload, selector_reason = _admissible_fallback(
                deletion,
                deletion_profile,
                current,
                current_profile,
                selectors,
                catalog,
            )
            communication += payload
            if retain:
                probe = _role_probe_profile(
                    f"v4-backward-{index:02d}-retain",
                    term,
                    deletion,
                    current,
                    selectors,
                    probes,
                    catalog,
                    role_conditioning=role_conditioning,
                )
                probe_profiles.append(probe)
                communication += probe.communication_bytes
                probe_passed = probe.passed
                probe_reason = (
                    probe.term_diagnostics[0].reason
                    if probe.term_diagnostics
                    else "no term diagnostic"
                )
            else:
                probe_passed = False
                probe_reason = "not evaluated"
            retained = bool(retain and probe_passed)
            if not retained:
                current = deletion
                current_profile = deletion_profile
            backward_decisions.append(
                TermwiseDecision(
                    stage="backward-retention",
                    term=term,
                    source=f"v4-backward-{index:02d}",
                    selector_passed=bool(retain),
                    probe_passed=bool(probe_passed),
                    accepted=retained,
                    selector_reason=selector_reason,
                    probe_reason=probe_reason,
                    before_terms=before,
                    after_terms=current.active_terms,
                )
            )

    final_profile = current_profile
    full_comm_snapshot = communication
    full_runtime_snapshot = perf_counter() - start

    final_start = perf_counter()
    final_candidate, final_payload = _refit(
        partitions,
        catalog,
        current.active_terms,
        include_validation=True,
        candidate_id="role-conditional-v4-final",
    )
    final_runtime = perf_counter() - final_start

    forward_start = perf_counter()
    final_forward, forward_payload = _refit(
        partitions,
        catalog,
        forward.active_terms,
        include_validation=True,
        candidate_id="role-conditional-v4-forward-final",
    )
    forward_refit_runtime = perf_counter() - forward_start

    anchor_start = perf_counter()
    final_anchor, anchor_payload = _refit(
        partitions,
        catalog,
        anchor.active_terms,
        include_validation=True,
        candidate_id="role-conditional-v4-anchor-final",
    )
    anchor_refit_runtime = perf_counter() - anchor_start

    config = (
        f"role={int(role_conditioning)},path={int(path_persistence)},"
        f"backward={int(backward_audit)}"
    )
    stop_reason = (
        f"RC-DES v4 {config}; anchor={','.join(anchor.active_terms)}; "
        f"pool={','.join(profile.candidate_terms)}; "
        f"forward={','.join(forward.active_terms)}; "
        f"final={','.join(current.active_terms)}"
    )

    return RoleConditionalOutput(
        method="role-conditional-v4",
        candidate=final_candidate,
        forward_candidate=final_forward,
        anchor_candidate=final_anchor,
        candidate_profile=profile,
        anchor_terms=anchor.active_terms,
        forward_terms=forward.active_terms,
        final_terms=current.active_terms,
        forward_decisions=tuple(forward_decisions),
        backward_decisions=tuple(backward_decisions),
        probe_profiles=tuple(probe_profiles),
        validation_profile=final_profile,
        forward_validation_profile=forward_profile,
        anchor_validation_profile=anchor_profile,
        communication_bytes=full_comm_snapshot + final_payload,
        forward_communication_bytes=forward_comm_snapshot + forward_payload,
        anchor_communication_bytes=anchor_comm_snapshot + anchor_payload,
        runtime_seconds=full_runtime_snapshot + final_runtime,
        forward_runtime_seconds=forward_runtime_snapshot + forward_refit_runtime,
        anchor_runtime_seconds=anchor_runtime_snapshot + anchor_refit_runtime,
        stop_reason=stop_reason,
    )
