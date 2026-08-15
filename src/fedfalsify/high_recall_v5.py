"""High-Recall Verified Forward Search (HR-VFS) for FedFalsify v5.

The implementation follows the frozen v5 development protocol. Candidate
proposal uses discovery-only aggregate information; selector and structural
probe data remain disjoint. Score-only evidence may propose terms but never
accept them. Correlated core-term pairs may be accepted only after joint
selector/probe checks and leave-one-member-out necessity tests. There is no
backward pruning.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from math import sqrt
from time import perf_counter
from typing import Sequence

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .baselines import score_only_federated
from .crossfit_redesign import (
    PartitionedClient,
    ValidationProfile,
    _admissible_fallback,
    _federated_clients,
    _nonzero_terms,
    _ordered_terms,
    _refit,
    _validation_profile,
    partition_clients,
)
from .crossfit_surrogate import StructuralProbeProfile, _probe_profile, split_selector_probe
from .role_conditional import (
    RoleCandidateProfile,
    TermwiseDecision,
    _role_probe_profile,
    build_role_candidate_profile,
    run_role_fold_directions,
)
from .stability_screen import _split_discovery_folds


@dataclass(frozen=True)
class CorrelatedPair:
    first: str
    second: str
    absolute_correlation: float

    @property
    def terms(self) -> tuple[str, str]:
        return (self.first, self.second)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class HighRecallBankProfile:
    candidate_terms: tuple[str, ...]
    anchor_terms: tuple[str, ...]
    role_terms: tuple[str, ...]
    score_terms: tuple[str, ...]
    correlated_pairs: tuple[CorrelatedPair, ...]
    score_proposer_enabled: bool
    bundle_rescue_enabled: bool
    role_conditioning: bool
    communication_bytes: int

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_terms": self.candidate_terms,
            "anchor_terms": self.anchor_terms,
            "role_terms": self.role_terms,
            "score_terms": self.score_terms,
            "correlated_pairs": [pair.to_dict() for pair in self.correlated_pairs],
            "score_proposer_enabled": self.score_proposer_enabled,
            "bundle_rescue_enabled": self.bundle_rescue_enabled,
            "role_conditioning": self.role_conditioning,
            "communication_bytes": self.communication_bytes,
        }


@dataclass(frozen=True)
class PairDecision:
    stage: str
    terms: tuple[str, str]
    source: str
    selector_passed: bool
    joint_probe_passed: bool
    first_necessary: bool
    second_necessary: bool
    accepted: bool
    selector_reason: str
    joint_probe_reason: str
    first_necessity_reason: str
    second_necessity_reason: str
    before_terms: tuple[str, ...]
    after_terms: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class HighRecallOutput:
    method: str
    candidate: CandidateEquation
    anchor_candidate: CandidateEquation
    candidate_profile: HighRecallBankProfile
    role_profile: RoleCandidateProfile
    forward_decisions: tuple[TermwiseDecision, ...]
    pair_decisions: tuple[PairDecision, ...]
    probe_profiles: tuple[StructuralProbeProfile, ...]
    validation_profile: ValidationProfile
    anchor_validation_profile: ValidationProfile
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _discovery_score_terms(
    partitions: Sequence[PartitionedClient],
    catalog: TermCatalog,
    *,
    max_terms: int,
) -> tuple[tuple[str, ...], int]:
    clients = _federated_clients(partitions, catalog, include_validation=False)
    output = score_only_federated(
        clients,
        catalog,
        max_terms=max_terms,
        min_improvement=1e-5,
    )
    selected = _nonzero_terms(output.candidate)
    ordered = tuple(
        term
        for term in output.candidate.active_terms
        if term != "1" and term in selected
    )
    return ordered, int(output.communication_bytes)


def _aggregate_column_correlations(
    partitions: Sequence[PartitionedClient],
    catalog: TermCatalog,
) -> tuple[dict[tuple[str, str], float], int]:
    """Compute discovery-only correlations from additive client sufficient stats."""

    names = tuple(
        name
        for name in catalog.names()
        if name != "1" and catalog.get(name).kind != "exception"
    )
    n_total = 0
    sums = {name: 0.0 for name in names}
    squares = {name: 0.0 for name in names}
    crosses = {(a, b): 0.0 for i, a in enumerate(names) for b in names[i + 1 :]}
    communication = 0

    for partition in partitions:
        x = partition.discovery.x
        values = {name: np.asarray(catalog.get(name).evaluate(x), dtype=float) for name in names}
        payload = {
            "client_id": partition.client_id,
            "n": int(len(x)),
            "sum": {name: float(np.sum(values[name])) for name in names},
            "sumsq": {name: float(values[name] @ values[name]) for name in names},
            "cross": {
                f"{a}|{b}": float(values[a] @ values[b])
                for a, b in crosses
            },
        }
        communication += len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        n_total += int(payload["n"])
        for name in names:
            sums[name] += payload["sum"][name]
            squares[name] += payload["sumsq"][name]
        for a, b in crosses:
            crosses[(a, b)] += payload["cross"][f"{a}|{b}"]

    correlations: dict[tuple[str, str], float] = {}
    for a, b in crosses:
        cov = crosses[(a, b)] - sums[a] * sums[b] / max(n_total, 1)
        var_a = squares[a] - sums[a] ** 2 / max(n_total, 1)
        var_b = squares[b] - sums[b] ** 2 / max(n_total, 1)
        denom = sqrt(max(var_a, 0.0) * max(var_b, 0.0))
        correlation = 0.0 if denom <= 1e-15 else float(cov / denom)
        correlations[(a, b)] = float(abs(correlation))
    return correlations, communication


def _role_diagnostic_map(profile: RoleCandidateProfile):
    return {item.term: item for item in profile.diagnostics}


def _candidate_signal(
    term: str,
    role_profile: RoleCandidateProfile,
    score_terms: set[str],
) -> bool:
    diagnostic = _role_diagnostic_map(role_profile)[term]
    return bool(
        diagnostic.selected_fold_count >= 1
        or diagnostic.top3_repair_fold_count >= 1
        or diagnostic.median_abs_residual_correlation > 1e-12
        or term in score_terms
    )


def _eligible_pairs(
    partitions: Sequence[PartitionedClient],
    catalog: TermCatalog,
    role_profile: RoleCandidateProfile,
    initial_terms: set[str],
    score_terms: set[str],
    *,
    threshold: float = 0.80,
    maximum_pairs: int = 4,
) -> tuple[tuple[CorrelatedPair, ...], int]:
    correlations, communication = _aggregate_column_correlations(partitions, catalog)
    pairs: list[CorrelatedPair] = []
    for (first, second), value in correlations.items():
        if value < threshold:
            continue
        if first not in initial_terms and second not in initial_terms:
            continue
        if not (
            _candidate_signal(first, role_profile, score_terms)
            and _candidate_signal(second, role_profile, score_terms)
        ):
            continue
        pairs.append(CorrelatedPair(first, second, float(value)))
    pairs.sort(
        key=lambda item: (
            -item.absolute_correlation,
            catalog.get(item.first).complexity + catalog.get(item.second).complexity,
            item.first,
            item.second,
        )
    )
    return tuple(pairs[:maximum_pairs]), communication


def build_high_recall_bank(
    partitions: Sequence[PartitionedClient],
    catalog: TermCatalog,
    role_profile: RoleCandidateProfile,
    *,
    max_terms: int,
    use_score_proposer: bool,
    use_bundle_rescue: bool,
    role_conditioning: bool,
    maximum_size: int = 10,
) -> HighRecallBankProfile:
    selected_sets = [set(items) - {"1"} for items in role_profile.fold_selected_terms]
    intersection = set(selected_sets[0])
    for selected in selected_sets[1:]:
        intersection &= selected
    anchor = set(intersection)

    role_terms = set(role_profile.candidate_terms)
    score_order: tuple[str, ...] = ()
    communication = 0
    if use_score_proposer:
        score_order, communication = _discovery_score_terms(
            partitions, catalog, max_terms=max_terms
        )
    score_set = set(score_order)
    initial = set(anchor) | role_terms | score_set

    pairs: tuple[CorrelatedPair, ...] = ()
    if use_bundle_rescue:
        pairs, pair_bytes = _eligible_pairs(
            partitions,
            catalog,
            role_profile,
            initial,
            score_set,
        )
        communication += pair_bytes

    eligible = set(initial)
    if use_bundle_rescue:
        for pair in pairs:
            eligible.update(pair.terms)

    diagnostics = _role_diagnostic_map(role_profile)
    score_rank = {term: index for index, term in enumerate(score_order)}
    ordered = sorted(
        eligible,
        key=lambda term: (
            -int(term in anchor),
            -diagnostics[term].channels_passed,
            -diagnostics[term].selected_fold_count,
            -diagnostics[term].best_repair_fold_count,
            -diagnostics[term].top3_repair_fold_count,
            score_rank.get(term, 10_000),
            -diagnostics[term].median_abs_residual_correlation,
            -diagnostics[term].coefficient_sign_stability,
            catalog.get(term).complexity,
            term,
        ),
    )
    bank = tuple(ordered[:maximum_size])
    bank_set = set(bank)
    kept_pairs = tuple(
        pair for pair in pairs if pair.first in bank_set and pair.second in bank_set
    )
    return HighRecallBankProfile(
        candidate_terms=bank,
        anchor_terms=_ordered_terms(catalog, anchor),
        role_terms=tuple(term for term in role_profile.candidate_terms if term in bank_set),
        score_terms=tuple(term for term in score_order if term in bank_set),
        correlated_pairs=kept_pairs,
        score_proposer_enabled=use_score_proposer,
        bundle_rescue_enabled=use_bundle_rescue,
        role_conditioning=role_conditioning,
        communication_bytes=communication,
    )


def _first_probe_reason(profile: StructuralProbeProfile) -> str:
    if not profile.term_diagnostics:
        return "no term diagnostic"
    failures = [item.reason for item in profile.term_diagnostics if not item.passed]
    return failures[0] if failures else "independent structural probe passed"


def _fit_terms(
    current: CandidateEquation,
    added: set[str],
    partitions: Sequence[PartitionedClient],
    catalog: TermCatalog,
    *,
    candidate_id: str,
) -> tuple[CandidateEquation, int]:
    terms = _ordered_terms(
        catalog,
        set(term for term in current.active_terms if term != "1") | added,
    )
    return _refit(
        partitions,
        catalog,
        terms,
        include_validation=False,
        candidate_id=candidate_id,
    )


def high_recall_verified_forward_method(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    max_terms: int = 6,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
    use_bundle_rescue: bool = True,
    use_score_proposer: bool = True,
    role_conditioning: bool = True,
) -> HighRecallOutput:
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
        role_conditioning=role_conditioning,
        path_persistence=True,
    )
    bank = build_high_recall_bank(
        partitions,
        catalog,
        role_profile,
        max_terms=max_terms,
        use_score_proposer=use_score_proposer,
        use_bundle_rescue=use_bundle_rescue,
        role_conditioning=role_conditioning,
        maximum_size=10,
    )
    communication += bank.communication_bytes

    anchor, payload = _refit(
        partitions,
        catalog,
        bank.anchor_terms,
        include_validation=False,
        candidate_id="hr-v5-anchor",
    )
    communication += payload
    anchor_profile, payload = _validation_profile(
        "hr-v5-anchor", anchor, selectors, catalog
    )
    communication += payload

    current = anchor
    current_profile = anchor_profile
    single_decisions: list[TermwiseDecision] = []
    pair_decisions: list[PairDecision] = []
    probe_profiles: list[StructuralProbeProfile] = []

    for rank, term in enumerate(bank.candidate_terms, start=1):
        if term in set(current.active_terms):
            continue
        if len(current.active_terms) >= max_terms:
            single_decisions.append(
                TermwiseDecision(
                    stage="v5-forward-single",
                    term=term,
                    source=f"hr-v5-single-{rank:02d}",
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
        proposal, payload = _fit_terms(
            current,
            {term},
            partitions,
            catalog,
            candidate_id=f"hr-v5-single-{rank:02d}-{term}",
        )
        communication += payload
        proposal_profile, payload = _validation_profile(
            f"hr-v5-single-{rank:02d}", proposal, selectors, catalog
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
                f"hr-v5-single-{rank:02d}",
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
            probe_reason = _first_probe_reason(probe)
        else:
            probe_passed = False
            probe_reason = "not evaluated"

        accepted = bool(allowed and probe_passed)
        if accepted:
            current = proposal
            current_profile = proposal_profile
        single_decisions.append(
            TermwiseDecision(
                stage="v5-forward-single",
                term=term,
                source=f"hr-v5-single-{rank:02d}",
                selector_passed=bool(allowed),
                probe_passed=bool(probe_passed),
                accepted=accepted,
                selector_reason=selector_reason,
                probe_reason=probe_reason,
                before_terms=before,
                after_terms=current.active_terms,
            )
        )

    if use_bundle_rescue:
        for index, pair in enumerate(bank.correlated_pairs, start=1):
            before = current.active_terms
            missing = set(pair.terms) - set(current.active_terms)
            if not missing:
                continue
            if len(current.active_terms) + len(missing) > max_terms:
                pair_decisions.append(
                    PairDecision(
                        stage="v5-pair-rescue",
                        terms=pair.terms,
                        source=f"hr-v5-pair-{index:02d}",
                        selector_passed=False,
                        joint_probe_passed=False,
                        first_necessary=False,
                        second_necessary=False,
                        accepted=False,
                        selector_reason="maximum final structure reached",
                        joint_probe_reason="not evaluated",
                        first_necessity_reason="not evaluated",
                        second_necessity_reason="not evaluated",
                        before_terms=before,
                        after_terms=before,
                    )
                )
                continue

            proposal, payload = _fit_terms(
                current,
                set(pair.terms),
                partitions,
                catalog,
                candidate_id=f"hr-v5-pair-{index:02d}",
            )
            communication += payload
            proposal_profile, payload = _validation_profile(
                f"hr-v5-pair-{index:02d}", proposal, selectors, catalog
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

            joint_passed = False
            joint_reason = "not evaluated"
            first_necessary = False
            second_necessary = False
            first_reason = "not evaluated"
            second_reason = "not evaluated"

            if allowed:
                joint_probe = _probe_profile(
                    f"hr-v5-pair-{index:02d}-joint",
                    current,
                    proposal,
                    selectors,
                    probes,
                    catalog,
                )
                probe_profiles.append(joint_probe)
                communication += joint_probe.communication_bytes
                joint_passed = joint_probe.passed
                joint_reason = _first_probe_reason(joint_probe)

            if allowed and joint_passed:
                first, second = pair.terms
                primary_without_second, payload = _fit_terms(
                    current,
                    {first},
                    partitions,
                    catalog,
                    candidate_id=f"hr-v5-pair-{index:02d}-without-{second}",
                )
                communication += payload
                second_probe = _role_probe_profile(
                    f"hr-v5-pair-{index:02d}-need-{second}",
                    second,
                    primary_without_second,
                    proposal,
                    selectors,
                    probes,
                    catalog,
                    role_conditioning=False,
                )
                probe_profiles.append(second_probe)
                communication += second_probe.communication_bytes
                second_necessary = second_probe.passed
                second_reason = _first_probe_reason(second_probe)

                primary_without_first, payload = _fit_terms(
                    current,
                    {second},
                    partitions,
                    catalog,
                    candidate_id=f"hr-v5-pair-{index:02d}-without-{first}",
                )
                communication += payload
                first_probe = _role_probe_profile(
                    f"hr-v5-pair-{index:02d}-need-{first}",
                    first,
                    primary_without_first,
                    proposal,
                    selectors,
                    probes,
                    catalog,
                    role_conditioning=False,
                )
                probe_profiles.append(first_probe)
                communication += first_probe.communication_bytes
                first_necessary = first_probe.passed
                first_reason = _first_probe_reason(first_probe)

            accepted = bool(
                allowed
                and joint_passed
                and first_necessary
                and second_necessary
            )
            if accepted:
                current = proposal
                current_profile = proposal_profile
            pair_decisions.append(
                PairDecision(
                    stage="v5-pair-rescue",
                    terms=pair.terms,
                    source=f"hr-v5-pair-{index:02d}",
                    selector_passed=bool(allowed),
                    joint_probe_passed=bool(joint_passed),
                    first_necessary=bool(first_necessary),
                    second_necessary=bool(second_necessary),
                    accepted=accepted,
                    selector_reason=selector_reason,
                    joint_probe_reason=joint_reason,
                    first_necessity_reason=first_reason,
                    second_necessity_reason=second_reason,
                    before_terms=before,
                    after_terms=current.active_terms,
                )
            )

    final_candidate, payload = _refit(
        partitions,
        catalog,
        current.active_terms,
        include_validation=True,
        candidate_id="high-recall-verified-forward-v5-final",
    )
    communication += payload

    stop_reason = (
        "HR-VFS v5; "
        f"score={int(use_score_proposer)},bundle={int(use_bundle_rescue)},"
        f"role={int(role_conditioning)}; "
        f"anchor={','.join(anchor.active_terms)}; "
        f"bank={','.join(bank.candidate_terms)}; "
        f"final={','.join(current.active_terms)}"
    )
    return HighRecallOutput(
        method="high-recall-verified-forward-v5",
        candidate=final_candidate,
        anchor_candidate=anchor,
        candidate_profile=bank,
        role_profile=role_profile,
        forward_decisions=tuple(single_decisions),
        pair_decisions=tuple(pair_decisions),
        probe_profiles=tuple(probe_profiles),
        validation_profile=current_profile,
        anchor_validation_profile=anchor_profile,
        communication_bytes=int(communication),
        runtime_seconds=float(perf_counter() - start),
        stop_reason=stop_reason,
    )
