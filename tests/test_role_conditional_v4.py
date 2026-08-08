from __future__ import annotations

import numpy as np
import pytest

from fedfalsify.benchmarks import benchmark_catalog, generate_benchmark
from fedfalsify.crossfit_redesign import partition_clients
from fedfalsify.crossfit_surrogate import split_selector_probe
from fedfalsify.role_conditional import (
    RoleFoldDirection,
    _eligible_exception_partitions,
    build_role_candidate_profile,
    role_conditional_method,
)
from fedfalsify.role_conditional_study import (
    DEVELOPMENT_SEEDS,
    SMOKE_SEED,
    _validate_seeds,
)
from fedfalsify.stability_screen import FoldTermEvidence


def _blank_evidence():
    return FoldTermEvidence(0.0, (), ())


def _direction(
    catalog,
    *,
    selected: tuple[str, ...] = ("1",),
    best: tuple[str, ...] = (),
    top3: tuple[str, ...] = (),
    supported_term: str | None = None,
    supported_clients: tuple[str, ...] = ("client-1", "client-2"),
    heterogeneity: tuple[tuple[str, float], ...] = (),
) -> RoleFoldDirection:
    evidence = {
        term: _blank_evidence()
        for term in catalog.names()
        if term != "1"
    }
    if supported_term is not None:
        observations = tuple(
            (client, 0.8, 20.0) for client in supported_clients
        )
        evidence[supported_term] = FoldTermEvidence(
            0.2,
            observations,
            observations,
        )
    return RoleFoldDirection(
        result=None,  # type: ignore[arg-type]
        selected_terms=selected,
        best_terms=best,
        top3_terms=top3,
        term_evidence=evidence,
        exception_heterogeneity=heterogeneity,
        observability_floor=3,
        communication_bytes=0,
    )


def test_v4_engineering_smoke_seed_is_not_evidence() -> None:
    assert SMOKE_SEED == 16001
    assert DEVELOPMENT_SEEDS == tuple(range(16101, 16106))
    assert SMOKE_SEED not in set(DEVELOPMENT_SEEDS)
    _validate_seeds(DEVELOPMENT_SEEDS, allow_engineering_smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((SMOKE_SEED,), allow_engineering_smoke=False)
    _validate_seeds((SMOKE_SEED,), allow_engineering_smoke=True)
    with pytest.raises(ValueError):
        _validate_seeds((15101,), allow_engineering_smoke=True)


def test_core_path_persistence_is_distinct_from_residual_rank() -> None:
    catalog = benchmark_catalog(scenario="complementary")
    directions = tuple(
        _direction(
            catalog,
            selected=("1", "x1^2") if index < 3 else ("1",),
            supported_term="x1^2",
        )
        for index in range(5)
    )
    profile = build_role_candidate_profile(
        directions,
        catalog,
        client_count=4,
        role_conditioning=True,
        path_persistence=True,
    )
    diagnostic = next(item for item in profile.diagnostics if item.term == "x1^2")
    assert diagnostic.best_repair_fold_count == 0
    assert diagnostic.top3_repair_fold_count == 0
    assert diagnostic.selected_fold_count == 3
    assert not diagnostic.residual_channel_passed
    assert diagnostic.path_channel_passed
    assert diagnostic.admitted
    assert "x1^2" in profile.candidate_terms


def test_restricted_exception_uses_eligible_role_not_global_coverage() -> None:
    catalog = benchmark_catalog(scenario="exception")
    term = "I(x3>1)*x3^2"
    directions = tuple(
        _direction(
            catalog,
            selected=("1", term) if index < 3 else ("1",),
            supported_term=term,
            supported_clients=("client-4",),
            heterogeneity=((term, 0.30),) if index < 3 else ((term, 0.0),),
        )
        for index in range(5)
    )
    role_profile = build_role_candidate_profile(
        directions,
        catalog,
        client_count=4,
        role_conditioning=True,
        path_persistence=True,
    )
    core_like_profile = build_role_candidate_profile(
        directions,
        catalog,
        client_count=4,
        role_conditioning=False,
        path_persistence=True,
    )
    role_item = next(item for item in role_profile.diagnostics if item.term == term)
    core_item = next(item for item in core_like_profile.diagnostics if item.term == term)
    assert role_item.client_coverage == 0.25
    assert role_item.exception_valid_fold_count == 3
    assert role_item.path_channel_passed
    assert role_item.admitted
    assert not core_item.path_channel_passed
    assert not core_item.admitted


def test_exception_probe_filters_to_gated_clients() -> None:
    generated = generate_benchmark(
        "interaction",
        scenario="exception",
        samples_per_client=120,
        noise_ratio=0.20,
        seed=SMOKE_SEED,
    )
    catalog = benchmark_catalog(scenario="exception")
    partitions = partition_clients(
        generated.clients,
        seed=SMOKE_SEED,
        validation_fraction=0.30,
    )
    selectors, probes = split_selector_probe(partitions, seed=SMOKE_SEED)
    eligible_selectors, eligible_probes = _eligible_exception_partitions(
        selectors,
        probes,
        catalog,
        "I(x3>1)*x3^2",
    )
    assert len(eligible_selectors) == 1
    assert len(eligible_probes) == 1
    assert eligible_selectors[0].client_id == "client-4"
    assert eligible_probes[0].client_id == "client-4"


def test_v4_smoke_respects_structure_and_evidence_boundaries() -> None:
    generated = generate_benchmark(
        "poly3",
        scenario="complementary",
        samples_per_client=120,
        noise_ratio=0.20,
        seed=SMOKE_SEED,
    )
    catalog = benchmark_catalog(scenario="complementary")
    output = role_conditional_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        max_terms=6,
        target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
        min_repair_score=0.05,
    )
    assert len(output.candidate_profile.fold_selected_terms) == 5
    assert len(output.candidate_profile.candidate_terms) <= 8
    assert len(output.candidate.active_terms) <= 6
    assert len(output.forward_candidate.active_terms) <= 6
    assert len(output.anchor_candidate.active_terms) <= 6
    assert output.method == "role-conditional-v4"
    assert all(item.stage == "forward" for item in output.forward_decisions)
    assert all(
        item.stage == "backward-retention"
        for item in output.backward_decisions
    )
    assert np.isfinite(output.runtime_seconds)
    assert output.communication_bytes >= 0
