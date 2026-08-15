"""Structure-aware cross-fitted redesign with an independent probe gate.

This v2 development implementation builds on the frozen v1 cross-fit machinery.
It excludes raw score-only candidates from structural selection and requires every
added term to beat correlated finite-catalog rivals on disjoint probe rows.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from time import perf_counter
from typing import Sequence

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .crossfit_redesign import (
    PartitionedClient,
    SplitFederatedFalsifierClient,
    ValidationProfile,
    _admissible_fallback,
    _nonzero_terms,
    _ordered_terms,
    _refit,
    _run_direction,
    _validation_profile,
    partition_clients,
)
from .external_common import ExternalClientData


@dataclass(frozen=True)
class ProbeTermDiagnostic:
    term: str
    rivals: tuple[str, ...]
    proposed_probe_improvement: float
    best_rival: str | None
    best_rival_probe_improvement: float
    relative_advantage: float
    client_win_fraction: float
    selector_sign_agreement: float
    passed: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class StructuralProbeProfile:
    source: str
    passed: bool
    term_diagnostics: tuple[ProbeTermDiagnostic, ...]
    communication_bytes: int

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "passed": self.passed,
            "term_diagnostics": [item.to_dict() for item in self.term_diagnostics],
            "communication_bytes": self.communication_bytes,
        }


@dataclass(frozen=True)
class StructuralRedesignOutput:
    method: str
    candidate: CandidateEquation
    selected_source: str
    continuation_selected: bool
    direction_a_terms: tuple[str, ...]
    direction_b_terms: tuple[str, ...]
    intersection_terms: tuple[str, ...]
    validation_profile: ValidationProfile
    validation_profiles: tuple[ValidationProfile, ...]
    probe_profiles: tuple[StructuralProbeProfile, ...]
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _stable_seed(seed: int, client_id: str, label: str) -> int:
    digest = hashlib.sha256(f"{seed}:{client_id}:{label}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def split_selector_probe(
    partitions: Sequence[PartitionedClient], *, seed: int
) -> tuple[tuple[PartitionedClient, ...], tuple[PartitionedClient, ...]]:
    """Split the held-out partition into disjoint selector and probe halves."""

    selectors: list[PartitionedClient] = []
    probes: list[PartitionedClient] = []
    for partition in partitions:
        count = len(partition.validation.y)
        if count < 20:
            raise ValueError("selector/probe split requires at least 20 held-out rows")
        rng = np.random.default_rng(_stable_seed(seed, partition.client_id, "probe"))
        order = rng.permutation(count)
        selector_count = count // 2
        selector_index = order[:selector_count]
        probe_index = order[selector_count:]

        def subset(indices: np.ndarray) -> ExternalClientData:
            return ExternalClientData(
                partition.client_id,
                partition.validation.x[indices],
                partition.validation.y[indices],
            )

        selectors.append(
            PartitionedClient(
                partition.client_id,
                partition.fold_a,
                partition.fold_b,
                subset(selector_index),
                partition.full,
            )
        )
        probes.append(
            PartitionedClient(
                partition.client_id,
                partition.fold_a,
                partition.fold_b,
                subset(probe_index),
                partition.full,
            )
        )
    return tuple(selectors), tuple(probes)


def _residualized_term(
    x: np.ndarray,
    catalog: TermCatalog,
    primary_terms: tuple[str, ...],
    term: str,
    projection: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    nuisance = catalog.matrix(x, primary_terms)
    values = catalog.get(term).evaluate(x)
    if projection is None:
        gram = nuisance.T @ nuisance + 1e-10 * np.eye(nuisance.shape[1])
        projection = np.linalg.pinv(gram) @ (nuisance.T @ values)
    return values - nuisance @ projection, projection


def _selector_rivals(
    term: str,
    primary_terms: tuple[str, ...],
    candidate_terms: tuple[str, ...],
    selectors: Sequence[PartitionedClient],
    catalog: TermCatalog,
    *,
    correlation_threshold: float = 0.70,
    maximum_rivals: int = 5,
) -> tuple[str, ...]:
    proposed = np.concatenate(
        [catalog.get(term).evaluate(partition.validation.x) for partition in selectors]
    )
    proposed = proposed - proposed.mean()
    proposed_energy = float(proposed @ proposed)
    if proposed_energy <= 1e-12:
        return ()
    rivals: list[tuple[float, str]] = []
    excluded = set(primary_terms) | set(candidate_terms) | {"1"}
    proposed_kind = catalog.get(term).kind
    for rival in catalog.names():
        if rival in excluded or catalog.get(rival).kind != proposed_kind:
            continue
        values = np.concatenate(
            [catalog.get(rival).evaluate(partition.validation.x) for partition in selectors]
        )
        values = values - values.mean()
        energy = float(values @ values)
        if energy <= 1e-12:
            continue
        correlation = abs(float((proposed @ values) / np.sqrt(proposed_energy * energy)))
        if correlation >= correlation_threshold:
            rivals.append((correlation, rival))
    rivals.sort(key=lambda item: (-item[0], item[1]))
    return tuple(name for _, name in rivals[:maximum_rivals])


def _term_probe_diagnostic(
    term: str,
    primary: CandidateEquation,
    candidate: CandidateEquation,
    selectors: Sequence[PartitionedClient],
    probes: Sequence[PartitionedClient],
    catalog: TermCatalog,
    *,
    minimum_relative_advantage: float = 0.01,
    minimum_client_win_fraction: float = 0.60,
    minimum_sign_agreement: float = 0.60,
) -> ProbeTermDiagnostic:
    rivals = _selector_rivals(
        term,
        primary.active_terms,
        candidate.active_terms,
        selectors,
        catalog,
    )
    proposed_improvements: list[float] = []
    proposed_signs: list[float] = []
    rival_improvements: dict[str, list[float]] = {rival: [] for rival in rivals}

    for selector, probe in zip(selectors, probes):
        selector_base = selector.validation.y - primary.predict(
            selector.validation.x, catalog
        )
        probe_base = probe.validation.y - primary.predict(probe.validation.x, catalog)

        selector_term, projection = _residualized_term(
            selector.validation.x, catalog, primary.active_terms, term
        )
        probe_term, _ = _residualized_term(
            probe.validation.x,
            catalog,
            primary.active_terms,
            term,
            projection,
        )
        energy = float(selector_term @ selector_term)
        slope = 0.0 if energy <= 1e-12 else float((selector_term @ selector_base) / energy)
        proposed_signs.append(float(np.sign(slope)))
        proposed_improvements.append(
            float(probe_base @ probe_base - (probe_base - slope * probe_term) @ (probe_base - slope * probe_term))
        )

        for rival in rivals:
            selector_rival, rival_projection = _residualized_term(
                selector.validation.x, catalog, primary.active_terms, rival
            )
            probe_rival, _ = _residualized_term(
                probe.validation.x,
                catalog,
                primary.active_terms,
                rival,
                rival_projection,
            )
            rival_energy = float(selector_rival @ selector_rival)
            rival_slope = (
                0.0
                if rival_energy <= 1e-12
                else float((selector_rival @ selector_base) / rival_energy)
            )
            rival_improvements[rival].append(
                float(
                    probe_base @ probe_base
                    - (probe_base - rival_slope * probe_rival)
                    @ (probe_base - rival_slope * probe_rival)
                )
            )

    proposed_total = float(sum(proposed_improvements))
    rival_totals = {
        rival: float(sum(values)) for rival, values in rival_improvements.items()
    }
    if rival_totals:
        best_rival = max(rival_totals, key=rival_totals.get)
        best_rival_total = rival_totals[best_rival]
        relative_advantage = (proposed_total - best_rival_total) / max(
            abs(proposed_total), 1e-12
        )
        client_wins = np.mean(
            np.asarray(proposed_improvements)
            > np.asarray(rival_improvements[best_rival])
        )
    else:
        best_rival = None
        best_rival_total = 0.0
        relative_advantage = 1.0 if proposed_total > 0 else -1.0
        client_wins = np.mean(np.asarray(proposed_improvements) > 0)

    nonzero_signs = np.asarray([value for value in proposed_signs if value != 0.0])
    sign_agreement = (
        0.0
        if nonzero_signs.size == 0
        else abs(float(np.mean(nonzero_signs)))
    )

    passed = True
    reason = "independent structural probe passed"
    if proposed_total <= 0:
        passed, reason = False, "proposed term did not reduce aggregate probe SSE"
    elif relative_advantage < minimum_relative_advantage:
        passed, reason = False, "correlated rival matched or beat probe improvement"
    elif float(client_wins) < minimum_client_win_fraction:
        passed, reason = False, "proposed term did not beat rival on enough clients"
    elif sign_agreement < minimum_sign_agreement:
        passed, reason = False, "selector coefficient signs were unstable across clients"

    return ProbeTermDiagnostic(
        term=term,
        rivals=rivals,
        proposed_probe_improvement=proposed_total,
        best_rival=best_rival,
        best_rival_probe_improvement=best_rival_total,
        relative_advantage=float(relative_advantage),
        client_win_fraction=float(client_wins),
        selector_sign_agreement=sign_agreement,
        passed=passed,
        reason=reason,
    )


def _probe_profile(
    source: str,
    primary: CandidateEquation,
    candidate: CandidateEquation,
    selectors: Sequence[PartitionedClient],
    probes: Sequence[PartitionedClient],
    catalog: TermCatalog,
) -> StructuralProbeProfile:
    added = [
        term
        for term in candidate.active_terms
        if term not in set(primary.active_terms) and term != "1"
    ]
    diagnostics = tuple(
        _term_probe_diagnostic(
            term, primary, candidate, selectors, probes, catalog
        )
        for term in added
    )
    communication = sum(
        len(json.dumps(item.to_dict(), separators=(",", ":")).encode("utf-8"))
        for item in diagnostics
    )
    return StructuralProbeProfile(
        source=source,
        passed=bool(diagnostics) and all(item.passed for item in diagnostics),
        term_diagnostics=diagnostics,
        communication_bytes=communication,
    )


def structural_crossfit_method(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    max_terms: int = 6,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
) -> StructuralRedesignOutput:
    """Run v2 cross-fitting with selector/probe separation and no score fallback."""

    start = perf_counter()
    partitions = partition_clients(
        datasets, seed=seed, validation_fraction=0.30
    )
    selectors, probes = split_selector_probe(partitions, seed=seed)

    direction_a_clients = [
        SplitFederatedFalsifierClient(item.fold_a, item.fold_b, catalog)
        for item in partitions
    ]
    direction_b_clients = [
        SplitFederatedFalsifierClient(item.fold_b, item.fold_a, catalog)
        for item in partitions
    ]
    direction_a, bytes_a = _run_direction(
        direction_a_clients,
        catalog,
        max_terms=max_terms,
        target_mse=target_mse,
        min_repair_score=min_repair_score,
    )
    direction_b, bytes_b = _run_direction(
        direction_b_clients,
        catalog,
        max_terms=max_terms,
        target_mse=target_mse,
        min_repair_score=min_repair_score,
    )

    terms_a = _nonzero_terms(direction_a.candidate)
    terms_b = _nonzero_terms(direction_b.candidate)
    source_terms = (
        ("crossfit-intersection", _ordered_terms(catalog, terms_a & terms_b)),
        ("direction-a", _ordered_terms(catalog, terms_a)),
        ("direction-b", _ordered_terms(catalog, terms_b)),
        ("crossfit-union", _ordered_terms(catalog, terms_a | terms_b)),
    )

    communication = bytes_a + bytes_b
    candidates: list[tuple[str, CandidateEquation]] = []
    seen: set[tuple[str, ...]] = set()
    for source, terms in source_terms:
        if terms in seen:
            continue
        seen.add(terms)
        candidate, payload = _refit(
            partitions,
            catalog,
            terms,
            include_validation=False,
            candidate_id=f"v2-{source}",
        )
        candidates.append((source, candidate))
        communication += payload

    by_source = {source: candidate for source, candidate in candidates}
    primary = by_source["crossfit-intersection"]
    profiles: list[ValidationProfile] = []
    profile_by_source: dict[str, ValidationProfile] = {}
    for source, candidate in candidates:
        profile, payload = _validation_profile(source, candidate, selectors, catalog)
        profiles.append(profile)
        profile_by_source[source] = profile
        communication += payload
    primary_profile = profile_by_source["crossfit-intersection"]

    probe_profiles: list[StructuralProbeProfile] = []
    admissible: list[tuple[ValidationProfile, CandidateEquation]] = []
    decisions: list[str] = []
    for source, candidate in candidates:
        if source == "crossfit-intersection":
            continue
        prediction_allowed, payload, prediction_reason = _admissible_fallback(
            primary,
            primary_profile,
            candidate,
            profile_by_source[source],
            selectors,
            catalog,
        )
        communication += payload
        if not prediction_allowed:
            decisions.append(f"{source}: prediction gate failed ({prediction_reason})")
            continue
        probe_profile = _probe_profile(
            source, primary, candidate, selectors, probes, catalog
        )
        probe_profiles.append(probe_profile)
        communication += probe_profile.communication_bytes
        if probe_profile.passed:
            admissible.append((profile_by_source[source], candidate))
            decisions.append(f"{source}: prediction and structural probe gates passed")
        else:
            reasons = ", ".join(
                f"{item.term}={item.reason}" for item in probe_profile.term_diagnostics
            )
            decisions.append(f"{source}: structural probe failed ({reasons})")

    if admissible:
        selected_profile, selected_candidate = min(
            admissible,
            key=lambda item: (
                item[0].information_score,
                item[0].complexity,
                item[0].source,
            ),
        )
        selected_source = selected_profile.source
    else:
        selected_profile = primary_profile
        selected_candidate = primary
        selected_source = "crossfit-intersection"

    final_candidate, payload = _refit(
        partitions,
        catalog,
        selected_candidate.active_terms,
        include_validation=True,
        candidate_id="crossfit-structural-v2-final",
    )
    communication += payload
    stop_reason = (
        f"direction A: {direction_a.stop_reason}; direction B: {direction_b.stop_reason}; "
        f"selected={selected_source}; " + " | ".join(decisions)
    )
    return StructuralRedesignOutput(
        method="crossfit-structural-v2",
        candidate=final_candidate,
        selected_source=selected_source,
        continuation_selected=selected_source != "crossfit-intersection",
        direction_a_terms=_ordered_terms(catalog, terms_a),
        direction_b_terms=_ordered_terms(catalog, terms_b),
        intersection_terms=_ordered_terms(catalog, terms_a & terms_b),
        validation_profile=selected_profile,
        validation_profiles=tuple(profiles),
        probe_profiles=tuple(probe_profiles),
        communication_bytes=communication,
        runtime_seconds=perf_counter() - start,
        stop_reason=stop_reason,
    )
