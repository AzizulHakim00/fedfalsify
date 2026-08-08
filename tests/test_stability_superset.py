from __future__ import annotations

import numpy as np
import pytest

from fedfalsify.benchmarks import benchmark_catalog, generate_benchmark
from fedfalsify.crossfit_redesign import partition_clients
from fedfalsify.stability_study import DEVELOPMENT_SEEDS, SMOKE_SEED, _validate_seeds
from fedfalsify.stability_superset import (
    _fold_observability_floor,
    _passes_stability_rule,
    _split_discovery_folds,
    stability_superset_method,
)


def _sorted_rows(x: np.ndarray, y: np.ndarray) -> list[tuple[float, ...]]:
    return sorted(
        tuple(float(value) for value in row) + (float(target),)
        for row, target in zip(x, y)
    )


def test_engineering_smoke_seed_is_excluded_from_evidence() -> None:
    assert SMOKE_SEED not in set(DEVELOPMENT_SEEDS)
    assert DEVELOPMENT_SEEDS == tuple(range(15101, 15106))
    _validate_seeds(DEVELOPMENT_SEEDS, allow_engineering_smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((SMOKE_SEED,), allow_engineering_smoke=False)
    _validate_seeds((SMOKE_SEED,), allow_engineering_smoke=True)


def test_five_fold_split_is_deterministic_disjoint_and_exhaustive() -> None:
    generated = generate_benchmark(
        "base",
        scenario="complementary",
        samples_per_client=120,
        noise_ratio=0.10,
        seed=15001,
    )
    partitions = partition_clients(
        generated.clients,
        seed=15001,
        validation_fraction=0.30,
    )
    first = _split_discovery_folds(partitions, seed=15001)
    second = _split_discovery_folds(partitions, seed=15001)
    assert len(first) == len(partitions)
    for partition, first_folds, second_folds in zip(
        partitions,
        first,
        second,
    ):
        assert len(first_folds) == 5
        assert [len(fold.y) for fold in first_folds] == [
            len(fold.y) for fold in second_folds
        ]
        flattened = [
            row
            for fold in first_folds
            for row in _sorted_rows(fold.x, fold.y)
        ]
        assert sorted(flattened) == _sorted_rows(
            partition.discovery.x,
            partition.discovery.y,
        )
        for left in range(5):
            left_rows = set(
                _sorted_rows(first_folds[left].x, first_folds[left].y)
            )
            for right in range(left + 1, 5):
                right_rows = set(
                    _sorted_rows(first_folds[right].x, first_folds[right].y)
                )
                assert left_rows.isdisjoint(right_rows)


def test_fold_observability_floor_is_size_aware_and_frozen() -> None:
    assert _fold_observability_floor(16) == 3
    assert _fold_observability_floor(60) == 6
    assert _fold_observability_floor(240) == 24


def test_stability_rules_match_frozen_protocol() -> None:
    assert _passes_stability_rule(
        best_repair_fold_count=2,
        top3_repair_fold_count=0,
        weighted_sign_agreement=0.0,
        client_coverage=0.0,
    )[0]
    assert _passes_stability_rule(
        best_repair_fold_count=1,
        top3_repair_fold_count=3,
        weighted_sign_agreement=0.60,
        client_coverage=0.50,
    )[0]
    assert not _passes_stability_rule(
        best_repair_fold_count=1,
        top3_repair_fold_count=3,
        weighted_sign_agreement=0.59,
        client_coverage=1.0,
    )[0]
    assert not _passes_stability_rule(
        best_repair_fold_count=1,
        top3_repair_fold_count=2,
        weighted_sign_agreement=1.0,
        client_coverage=1.0,
    )[0]


def test_v3_never_uses_score_only_as_structural_source() -> None:
    generated = generate_benchmark(
        "poly3",
        scenario="complementary",
        samples_per_client=120,
        noise_ratio=0.20,
        seed=15001,
    )
    catalog = benchmark_catalog(scenario="complementary")
    output = stability_superset_method(
        generated.clients,
        catalog,
        seed=15001,
        max_terms=6,
        target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
        min_repair_score=0.05,
    )
    assert output.selected_source != "score-only"
    assert output.selected_source.startswith("stability-")
    assert len(output.stability_profile.fold_selected_terms) == 5
    assert len(output.stability_profile.stable_terms) <= 8
    assert len(output.candidate.active_terms) <= 6
    assert {
        item.term for item in output.stability_profile.diagnostics
    } == {
        term for term in catalog.names() if term != "1"
    }
