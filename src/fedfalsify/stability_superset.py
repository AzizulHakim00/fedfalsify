"""Frozen stability-selected candidate generation and unchanged v2 probing."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Iterable, Sequence

from .basis import CandidateEquation, TermCatalog
from .crossfit_redesign import (
    ValidationProfile,
    _admissible_fallback,
    _ordered_terms,
    _refit,
    _validation_profile,
    partition_clients,
)
from .crossfit_surrogate import (
    StructuralProbeProfile,
    _probe_profile,
    split_selector_probe,
)
from .stability_screen import (
    StabilitySupersetProfile,
    _fold_observability_floor,
    _passes_stability_rule,
    _split_discovery_folds,
    build_stability_profile,
    run_fold_directions,
)


@dataclass(frozen=True)
class StabilitySupersetOutput:
    method: str
    candidate: CandidateEquation
    intersection_candidate: CandidateEquation
    selected_source: str
    continuation_selected: bool
    intersection_terms: tuple[str, ...]
    majority_terms: tuple[str, ...]
    stability_profile: StabilitySupersetProfile
    validation_profile: ValidationProfile
    validation_profiles: tuple[ValidationProfile, ...]
    probe_profiles: tuple[StructuralProbeProfile, ...]
    communication_bytes: int
    intersection_communication_bytes: int
    runtime_seconds: float
    intersection_runtime_seconds: float
    stop_reason: str


def _clip_terms(
    catalog: TermCatalog,
    selected: Iterable[str],
    ranking: Sequence[str],
    *,
    max_terms: int,
) -> tuple[str, ...]:
    selected_set = set(selected) - {"1"}
    ordered = [term for term in ranking if term in selected_set]
    ordered.extend(
        term
        for term in catalog.names()
        if term != "1" and term in selected_set and term not in ordered
    )
    return _ordered_terms(catalog, ordered[: max(max_terms - 1, 0)])


def stability_superset_method(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    max_terms: int = 6,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
) -> StabilitySupersetOutput:
    start = perf_counter()
    partitions = partition_clients(
        datasets, seed=seed, validation_fraction=0.30
    )
    selectors, probes = split_selector_probe(partitions, seed=seed)
    folds = _split_discovery_folds(partitions, seed=seed)
    directions = run_fold_directions(
        folds,
        catalog,
        max_terms=max_terms,
        target_mse=target_mse,
        min_repair_score=min_repair_score,
    )
    communication = sum(item.communication_bytes for item in directions)
    profile = build_stability_profile(
        directions, catalog, client_count=len(partitions), maximum_size=8
    )
    ranking = profile.stable_terms
    stable = set(ranking)
    selected_sets = [set(item.selected_terms) - {"1"} for item in directions]

    intersection = set(selected_sets[0])
    for selected in selected_sets[1:]:
        intersection &= selected
    majority = intersection | {
        term
        for term in catalog.names()
        if (
            term != "1"
            and term in stable
            and sum(term in selected for selected in selected_sets) >= 3
        )
    }
    union = intersection | (set().union(*selected_sets) & stable)
    intersection_terms = _clip_terms(
        catalog, intersection, ranking, max_terms=max_terms
    )
    majority_terms = _clip_terms(
        catalog, majority, ranking, max_terms=max_terms
    )

    source_terms = [
        ("stability-intersection", intersection_terms),
        ("stability-majority", majority_terms),
    ]
    path = list(intersection_terms[1:])
    for index, term in enumerate(ranking, start=1):
        if term in path or len(path) >= max_terms - 1:
            continue
        path.append(term)
        source_terms.append(
            (f"stability-path-{index:02d}", _ordered_terms(catalog, path))
        )
    source_terms.append(
        (
            "stability-union",
            _clip_terms(catalog, union, ranking, max_terms=max_terms),
        )
    )

    candidates, seen = [], set()
    for source, terms in source_terms:
        if terms in seen:
            continue
        seen.add(terms)
        candidate, payload = _refit(
            partitions,
            catalog,
            terms,
            include_validation=False,
            candidate_id=f"v3-{source}",
        )
        candidates.append((source, candidate))
        communication += payload

    by_source = dict(candidates)
    primary = by_source["stability-intersection"]
    profiles, profile_by_source = [], {}
    for source, candidate in candidates:
        validation, payload = _validation_profile(
            source, candidate, selectors, catalog
        )
        profiles.append(validation)
        profile_by_source[source] = validation
        communication += payload
    primary_profile = profile_by_source["stability-intersection"]

    probes_used, admissible, decisions = [], [], []
    for source, candidate in candidates:
        if source == "stability-intersection":
            continue
        allowed, payload, reason = _admissible_fallback(
            primary,
            primary_profile,
            candidate,
            profile_by_source[source],
            selectors,
            catalog,
        )
        communication += payload
        if not allowed:
            decisions.append(f"{source}: prediction gate failed ({reason})")
            continue
        probe = _probe_profile(
            source, primary, candidate, selectors, probes, catalog
        )
        probes_used.append(probe)
        communication += probe.communication_bytes
        if probe.passed:
            admissible.append((profile_by_source[source], candidate))
            decisions.append(f"{source}: both gates passed")
        else:
            reasons = ", ".join(
                f"{item.term}={item.reason}"
                for item in probe.term_diagnostics
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
        selected_profile, selected_candidate = primary_profile, primary
        selected_source = "stability-intersection"

    shared_communication = communication
    shared_runtime = perf_counter() - start
    final_start = perf_counter()
    final_candidate, final_payload = _refit(
        partitions,
        catalog,
        selected_candidate.active_terms,
        include_validation=True,
        candidate_id="stability-superset-v3-final",
    )
    final_runtime = perf_counter() - final_start
    intersection_start = perf_counter()
    final_intersection, intersection_payload = _refit(
        partitions,
        catalog,
        primary.active_terms,
        include_validation=True,
        candidate_id="stability-v3-intersection-final",
    )
    intersection_runtime = perf_counter() - intersection_start

    return StabilitySupersetOutput(
        method="stability-superset-v3",
        candidate=final_candidate,
        intersection_candidate=final_intersection,
        selected_source=selected_source,
        continuation_selected=selected_source != "stability-intersection",
        intersection_terms=intersection_terms,
        majority_terms=majority_terms,
        stability_profile=profile,
        validation_profile=selected_profile,
        validation_profiles=tuple(profiles),
        probe_profiles=tuple(probes_used),
        communication_bytes=shared_communication + final_payload,
        intersection_communication_bytes=(
            shared_communication + intersection_payload
        ),
        runtime_seconds=shared_runtime + final_runtime,
        intersection_runtime_seconds=(
            shared_runtime + intersection_runtime
        ),
        stop_reason=(
            f"five-fold candidate generation; selected={selected_source}; "
            f"stable_terms={','.join(profile.stable_terms)}; "
            + " | ".join(decisions)
        ),
    )
