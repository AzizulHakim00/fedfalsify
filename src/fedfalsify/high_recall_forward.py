"""High-Recall Verified Forward Search (HR-VFS), FedFalsify v5.

The scientific protocol is frozen in
research/TRANSACTIONS_HIGH_RECALL_VERIFIED_FORWARD_V5_PROTOCOL.md.
This module intentionally reuses v4 discovery evidence and the existing
selector/probe gates. Score-only search has proposal authority only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from time import perf_counter
from typing import Sequence

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .baselines import score_only_federated
from .client import FederatedFalsifierClient
from .crossfit_redesign import (
    PartitionedClient,
    ValidationProfile,
    _admissible_fallback,
    _ordered_terms,
    _refit,
    _validation_profile,
    partition_clients,
)
from .crossfit_surrogate import StructuralProbeProfile, split_selector_probe
from .role_conditional import (
    RoleCandidateProfile,
    TermwiseDecision,
    _candidate_terms,
    _role_probe_profile,
    build_role_candidate_profile,
    run_role_fold_directions,
)
from .stability_screen import _split_discovery_folds


@dataclass(frozen=True)
class CorrelationBundle:
    terms: tuple[str, str]
    absolute_correlation: float
    joint_complexity: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PairDecision:
    terms: tuple[str, str]
    source: str
    selector_passed: bool
    joint_probe_passed: bool
    first_necessity_passed: bool
    second_necessity_passed: bool
    accepted: bool
    reason: str
    before_terms: tuple[str, ...]
    after_terms: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class HighRecallProfile:
    anchor_terms: tuple[str, ...]
    role_terms: tuple[str, ...]
    score_terms: tuple[str, ...]
    candidate_terms: tuple[str, ...]
    bundles: tuple[CorrelationBundle, ...]
    role_profile: RoleCandidateProfile
    maximum_bank_size: int
    use_score_proposer: bool
    use_bundle_rescue: bool
    role_conditioning: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "anchor_terms": self.anchor_terms,
            "role_terms": self.role_terms,
            "score_terms": self.score_terms,
            "candidate_terms": self.candidate_terms,
            "bundles": [item.to_dict() for item in self.bundles],
            "role_profile": self.role_profile.to_dict(),
            "maximum_bank_size": self.maximum_bank_size,
            "use_score_proposer": self.use_score_proposer,
            "use_bundle_rescue": self.use_bundle_rescue,
            "role_conditioning": self.role_conditioning,
        }


@dataclass(frozen=True)
class HighRecallOutput:
    method: str
    candidate: CandidateEquation
    anchor_candidate: CandidateEquation
    profile: HighRecallProfile
    validation_profile: ValidationProfile
    anchor_validation_profile: ValidationProfile
    single_decisions: tuple[TermwiseDecision, ...]
    pair_decisions: tuple[PairDecision, ...]
    probe_profiles: tuple[StructuralProbeProfile, ...]
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _discovery_clients(
    partitions: Sequence[PartitionedClient], catalog: TermCatalog
) -> list[FederatedFalsifierClient]:
    return [FederatedFalsifierClient(item.discovery, catalog) for item in partitions]


def _score_proposal_terms(
    partitions: Sequence[PartitionedClient],
    catalog: TermCatalog,
    *,
    max_terms: int,
) -> tuple[tuple[str, ...], int]:
    output = score_only_federated(
        _discovery_clients(partitions, catalog),
        catalog,
        max_terms=max_terms,
    )
    terms = tuple(term for term in output.candidate.active_terms if term != "1")
    return terms, int(output.communication_bytes)


def _aggregate_correlation(
    partitions: Sequence[PartitionedClient],
    catalog: TermCatalog,
    left: str,
    right: str,
) -> tuple[float, int]:
    # Each client contributes only additive sufficient statistics.
    n = sx = sy = sxx = syy = sxy = 0.0
    communication = 0
    for partition in partitions:
        x = partition.discovery.x
        a = np.asarray(catalog.get(left).evaluate(x), dtype=float)
        b = np.asarray(catalog.get(right).evaluate(x), dtype=float)
        local = (
            float(len(a)),
            float(a.sum()),
            float(b.sum()),
            float(a @ a),
            float(b @ b),
            float(a @ b),
        )
        n += local[0]
        sx += local[1]
        sy += local[2]
        sxx += local[3]
        syy += local[4]
        sxy += local[5]
        communication += len(json.dumps(local, separators=(",", ":")).encode("utf-8"))
    if n <= 1:
        return 0.0, communication
    vx = sxx - sx * sx / n
    vy = syy - sy * sy / n
    if vx <= 1e-12 or vy <= 1e-12:
        return 0.0, communication
    covariance = sxy - sx * sy / n
    return abs(float(covariance / np.sqrt(vx * vy))), communication


def _diagnostic_map(profile: RoleCandidateProfile):
    return {item.term: item for item in profile.diagnostics}


def _has_discovery_signal(term: str, profile: RoleCandidateProfile) -> bool:
    item = _diagnostic_map(profile)[term]
    return bool(
        item.selected_fold_count > 0
        or item.top3_repair_fold_count > 0
        or item.median_abs_residual_correlation > 0.0
    )


def build_high_recall_profile(
    partitions: Sequence[PartitionedClient],
    catalog: TermCatalog,
    role_profile: RoleCandidateProfile,
    anchor_terms: Sequence[str],
    score_terms: Sequence[str],
    *,
    maximum_bank_size: int = 10,
    use_score_proposer: bool = True,
    use_bundle_rescue: bool = True,
) -> tuple[HighRecallProfile, int]:
    anchor = tuple(term for term in anchor_terms if term != "1")
    role = tuple(role_profile.candidate_terms)
    score = tuple(score_terms) if use_score_proposer else ()
    initial = set(anchor) | set(role) | set(score)
    communication = 0

    bundles: list[CorrelationBundle] = []
    if use_bundle_rescue:
        core = [
            term for term in catalog.names()
            if term != "1" and catalog.get(term).kind != "exception"
        ]
        for i, left in enumerate(core):
            for right in core[i + 1:]:
                if left not in initial and right not in initial:
                    continue
                other = right if left in initial else left
                if other not in initial and not _has_discovery_signal(other, role_profile):
                    continue
                corr, payload = _aggregate_correlation(
                    partitions, catalog, left, right
                )
                communication += payload
                if corr < 0.80:
                    continue
                bundles.append(
                    CorrelationBundle(
                        terms=(left, right),
                        absolute_correlation=corr,
                        joint_complexity=(
                            catalog.get(left).complexity + catalog.get(right).complexity
                        ),
                    )
                )
        bundles.sort(
            key=lambda item: (
                -item.absolute_correlation,
                item.joint_complexity,
                item.terms,
            )
        )
        bundles = bundles[:4]

    eligible = set(initial)
    for bundle in bundles:
        eligible.update(bundle.terms)

    diag = _diagnostic_map(role_profile)
    score_order = {term: index for index, term in enumerate(score)}

    def ranking(term: str):
        item = diag[term]
        return (
            0 if term in set(anchor) else 1,
            -item.channels_passed,
            -item.selected_fold_count,
            -item.best_repair_fold_count,
            -item.top3_repair_fold_count,
            score_order.get(term, 10_000),
            -item.median_abs_residual_correlation,
            -item.coefficient_sign_stability,
            catalog.get(term).complexity,
            term,
        )

    ordered = tuple(sorted(eligible, key=ranking)[:maximum_bank_size])
    retained = set(ordered)
    retained_bundles = tuple(
        item for item in bundles
        if set(item.terms).issubset(retained)
    )
    return (
        HighRecallProfile(
            anchor_terms=_ordered_terms(catalog, set(anchor)),
            role_terms=_ordered_terms(catalog, set(role)),
            score_terms=_ordered_terms(catalog, set(score)),
            candidate_terms=ordered,
            bundles=retained_bundles,
            role_profile=role_profile,
            maximum_bank_size=maximum_bank_size,
            use_score_proposer=use_score_proposer,
            use_bundle_rescue=use_bundle_rescue,
            role_conditioning=role_profile.role_conditioning,
        ),
        communication,
    )


def _probe_validation(
    source: str,
    candidate: CandidateEquation,
    probes: Sequence[PartitionedClient],
    catalog: TermCatalog,
) -> tuple[ValidationProfile, int]:
    return _validation_profile(source, candidate, probes, catalog)


def _pair_probe(
    source: str,
    pair: tuple[str, str],
    current: CandidateEquation,
    joint: CandidateEquation,
    partitions: Sequence[PartitionedClient],
    selectors: Sequence[PartitionedClient],
    probes: Sequence[PartitionedClient],
    catalog: TermCatalog,
    *,
    role_conditioning: bool,
) -> tuple[bool, bool, bool, int, str, tuple[StructuralProbeProfile, ...]]:
    left, right = pair
    communication = 0
    current_probe, payload = _probe_validation(source + "-base", current, probes, catalog)
    communication += payload
    joint_probe, payload = _probe_validation(source + "-joint", joint, probes, catalog)
    communication += payload
    joint_improved = joint_probe.weighted_mse < current_probe.weighted_mse

    left_candidate, payload = _refit(
        partitions, catalog,
        _ordered_terms(catalog, set(_candidate_terms(current)) | {left}),
        include_validation=False,
        candidate_id=source + "-left",
    )
    communication += payload
    right_candidate, payload = _refit(
        partitions, catalog,
        _ordered_terms(catalog, set(_candidate_terms(current)) | {right}),
        include_validation=False,
        candidate_id=source + "-right",
    )
    communication += payload

    need_right = _role_probe_profile(
        source + "-need-right", right, left_candidate, joint,
        selectors, probes, catalog, role_conditioning=role_conditioning,
    )
    need_left = _role_probe_profile(
        source + "-need-left", left, right_candidate, joint,
        selectors, probes, catalog, role_conditioning=role_conditioning,
    )
    communication += need_right.communication_bytes + need_left.communication_bytes

    left_probe, payload = _probe_validation(source + "-left-probe", left_candidate, probes, catalog)
    communication += payload
    right_probe, payload = _probe_validation(source + "-right-probe", right_candidate, probes, catalog)
    communication += payload
    best_single = min(left_probe.weighted_mse, right_probe.weighted_mse)
    joint_beats_singles = joint_probe.weighted_mse < best_single

    passed = bool(
        joint_improved and joint_beats_singles and need_left.passed and need_right.passed
    )
    if not joint_improved:
        reason = "joint proposal did not improve independent probe MSE"
    elif not joint_beats_singles:
        reason = "best one-member explanation matched or beat joint proposal"
    elif not need_left.passed:
        reason = "left member failed conditional necessity"
    elif not need_right.passed:
        reason = "right member failed conditional necessity"
    else:
        reason = "joint probe and both conditional necessity tests passed"
    return (
        passed,
        need_left.passed,
        need_right.passed,
        communication,
        reason,
        (need_left, need_right),
    )


def high_recall_forward_method(
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

    selected_sets = [set(item.selected_terms) - {"1"} for item in directions]
    intersection = set(selected_sets[0])
    for selected in selected_sets[1:]:
        intersection &= selected
    anchor_terms = _ordered_terms(catalog, intersection)
    anchor, payload = _refit(
        partitions, catalog, anchor_terms,
        include_validation=False, candidate_id="v5-anchor",
    )
    communication += payload
    anchor_profile, payload = _validation_profile(
        "v5-anchor", anchor, selectors, catalog
    )
    communication += payload

    score_terms: tuple[str, ...] = ()
    if use_score_proposer:
        score_terms, payload = _score_proposal_terms(
            partitions, catalog, max_terms=max_terms
        )
        communication += payload

    profile, payload = build_high_recall_profile(
        partitions,
        catalog,
        role_profile,
        anchor_terms,
        score_terms,
        maximum_bank_size=10,
        use_score_proposer=use_score_proposer,
        use_bundle_rescue=use_bundle_rescue,
    )
    communication += payload

    current = anchor
    current_profile = anchor_profile
    singles: list[TermwiseDecision] = []
    pair_decisions: list[PairDecision] = []
    probes_out: list[StructuralProbeProfile] = []

    for rank, term in enumerate(profile.candidate_terms, start=1):
        if term in set(current.active_terms):
            continue
        if len(current.active_terms) >= max_terms:
            singles.append(TermwiseDecision(
                stage="v5-forward", term=term, source=f"v5-single-{rank:02d}",
                selector_passed=False, probe_passed=False, accepted=False,
                selector_reason="maximum final structure reached",
                probe_reason="not evaluated",
                before_terms=current.active_terms, after_terms=current.active_terms,
            ))
            continue
        before = current.active_terms
        proposal, payload = _refit(
            partitions, catalog,
            _ordered_terms(catalog, set(_candidate_terms(current)) | {term}),
            include_validation=False,
            candidate_id=f"v5-single-{rank:02d}-{term}",
        )
        communication += payload
        proposal_profile, payload = _validation_profile(
            f"v5-single-{rank:02d}", proposal, selectors, catalog
        )
        communication += payload
        allowed, payload, selector_reason = _admissible_fallback(
            current, current_profile, proposal, proposal_profile,
            selectors, catalog,
        )
        communication += payload
        if allowed:
            probe = _role_probe_profile(
                f"v5-single-{rank:02d}", term, current, proposal,
                selectors, probes, catalog, role_conditioning=role_conditioning,
            )
            probes_out.append(probe)
            communication += probe.communication_bytes
            probe_passed = probe.passed
            probe_reason = (
                probe.term_diagnostics[0].reason
                if probe.term_diagnostics else "no term diagnostic"
            )
        else:
            probe_passed = False
            probe_reason = "not evaluated"
        accepted = bool(allowed and probe_passed)
        if accepted:
            current = proposal
            current_profile = proposal_profile
        singles.append(TermwiseDecision(
            stage="v5-forward", term=term, source=f"v5-single-{rank:02d}",
            selector_passed=bool(allowed), probe_passed=bool(probe_passed),
            accepted=accepted, selector_reason=selector_reason,
            probe_reason=probe_reason, before_terms=before,
            after_terms=current.active_terms,
        ))

    if use_bundle_rescue:
        for index, bundle in enumerate(profile.bundles, start=1):
            left, right = bundle.terms
            active = set(_candidate_terms(current))
            if left in active and right in active:
                continue
            missing = {left, right} - active
            if len(current.active_terms) + len(missing) > max_terms:
                continue
            before = current.active_terms
            joint, payload = _refit(
                partitions, catalog,
                _ordered_terms(catalog, active | {left, right}),
                include_validation=False,
                candidate_id=f"v5-pair-{index:02d}-{left}-{right}",
            )
            communication += payload
            joint_profile, payload = _validation_profile(
                f"v5-pair-{index:02d}", joint, selectors, catalog
            )
            communication += payload
            allowed, payload, selector_reason = _admissible_fallback(
                current, current_profile, joint, joint_profile,
                selectors, catalog,
            )
            communication += payload
            if allowed:
                (
                    joint_probe_passed,
                    left_needed,
                    right_needed,
                    payload,
                    probe_reason,
                    pair_probes,
                ) = _pair_probe(
                    f"v5-pair-{index:02d}", (left, right),
                    current, joint, partitions, selectors, probes, catalog,
                    role_conditioning=role_conditioning,
                )
                communication += payload
                probes_out.extend(pair_probes)
            else:
                joint_probe_passed = left_needed = right_needed = False
                probe_reason = "selector rejected joint proposal"
            accepted = bool(
                allowed and joint_probe_passed and left_needed and right_needed
            )
            if accepted:
                current = joint
                current_profile = joint_profile
            pair_decisions.append(PairDecision(
                terms=(left, right), source=f"v5-pair-{index:02d}",
                selector_passed=bool(allowed),
                joint_probe_passed=bool(joint_probe_passed),
                first_necessity_passed=bool(left_needed),
                second_necessity_passed=bool(right_needed),
                accepted=accepted,
                reason=selector_reason + "; " + probe_reason,
                before_terms=before, after_terms=current.active_terms,
            ))

    return HighRecallOutput(
        method="high-recall-verified-forward-v5",
        candidate=current,
        anchor_candidate=anchor,
        profile=profile,
        validation_profile=current_profile,
        anchor_validation_profile=anchor_profile,
        single_decisions=tuple(singles),
        pair_decisions=tuple(pair_decisions),
        probe_profiles=tuple(probes_out),
        communication_bytes=communication,
        runtime_seconds=perf_counter() - start,
        stop_reason=(
            "forward-only verified search exhausted; "
            f"bank={len(profile.candidate_terms)}; "
            f"pairs={len(profile.bundles)}"
        ),
    )
