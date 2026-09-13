from __future__ import annotations

import inspect

import numpy as np

from fedfalsify.phase3d_fixtures import (
    PHASE3D_FIXTURE_NAMES,
    build_phase3d_fixtures,
    split_fixture_clients,
)
from fedfalsify.scope_contrast_v13 import (
    FrozenScopeHypothesis,
    discover_scope_contrast,
    scope_contrast_test,
)
from fedfalsify.scsv_v10_benchmarks import QUADRATIC_DEV_V10, v10_catalog
from fedfalsify.scsv_v13 import PHASE3D_MODELS, run_phase3d_model


EXPECTED_FIXTURES = (
    "quadratic_scope_shift",
    "linear_scope_shift",
    "trig_scope_shift",
    "interaction_scope_shift",
    "weak_source_scope_shift",
    "dual_scope_shift",
    "null_no_localized",
    "anchor_contamination_null",
)

EXPECTED_MODELS = (
    "v11-frozen",
    "v12-frozen",
    "scope-contrast-only",
    "v13-full",
)


def _fixture(name: str):
    return {item.name: item for item in build_phase3d_fixtures()}[name]


def test_phase3d_fixture_registry_is_exact_and_seedless():
    assert PHASE3D_FIXTURE_NAMES == EXPECTED_FIXTURES
    assert "seed" not in inspect.signature(build_phase3d_fixtures).parameters
    assert "seed" not in inspect.signature(split_fixture_clients).parameters

    fixtures_a = build_phase3d_fixtures()
    fixtures_b = build_phase3d_fixtures()
    assert len(fixtures_a) == 8
    for left, right in zip(fixtures_a, fixtures_b):
        assert left.name == right.name
        assert left.true_shared_terms == right.true_shared_terms
        assert left.true_localized_terms == right.true_localized_terms
        assert left.truth_scopes == right.truth_scopes
        for client_a, client_b in zip(left.clients, right.clients):
            assert client_a.client_id == client_b.client_id
            np.testing.assert_array_equal(client_a.x, client_b.x)
            np.testing.assert_array_equal(client_a.y, client_b.y)


def test_phase3d_split_is_deterministic_disjoint_and_complete():
    fixture = _fixture("quadratic_scope_shift")
    discovery, selector, probe = split_fixture_clients(fixture, outer_fold=0)
    assert len(discovery) == len(selector) == len(probe) == 8

    for original, d, s, p in zip(fixture.clients, discovery, selector, probe):
        assert d.client_id == s.client_id == p.client_id == original.client_id
        assert len(d.y) + len(s.y) + len(p.y) == len(original.y)
        assert len(d.y) == len(s.y) == len(p.y) == 40

        original_rows = {tuple(row) for row in np.column_stack([original.x, original.y])}
        split_rows = [
            {tuple(row) for row in np.column_stack([part.x, part.y])}
            for part in (d, s, p)
        ]
        assert not (split_rows[0] & split_rows[1])
        assert not (split_rows[0] & split_rows[2])
        assert not (split_rows[1] & split_rows[2])
        assert set().union(*split_rows) == original_rows


def test_quadratic_role_client_is_locally_collinear_but_scope_contrast_is_identifiable():
    fixture = _fixture("quadratic_scope_shift")
    discovery, _, _ = split_fixture_clients(fixture, outer_fold=0)
    catalog = v10_catalog()
    shared = ("1", "x3^2", "sin(x2)", "x1")

    role_ids = dict(fixture.truth_scopes)[QUADRATIC_DEV_V10]
    role_indices = tuple(
        index for index, client in enumerate(discovery) if client.client_id in role_ids
    )
    role_client = discovery[role_indices[0]]

    shared_design = catalog.matrix(role_client.x, shared)
    source_column = catalog.get("x3^2").evaluate(role_client.x)[:, None]
    assert np.linalg.matrix_rank(np.column_stack([shared_design, source_column])) == np.linalg.matrix_rank(shared_design)

    result = scope_contrast_test(
        discovery,
        catalog,
        shared_terms=shared,
        source_term="x3^2",
        role_indices=role_indices,
    )
    assert result.admissible
    assert result.full_rank == result.reduced_rank + 1
    assert result.full_sse < 1e-8
    assert result.candidate_sign == 1
    assert result.p_value == 0.0


def test_discovery_recovers_quadratic_scope_from_role_outside_contrast():
    fixture = _fixture("quadratic_scope_shift")
    discovery, _, _ = split_fixture_clients(fixture, outer_fold=0)
    catalog = v10_catalog()
    shared = ("1", "x3^2", "sin(x2)", "x1")

    result = discover_scope_contrast(
        fixture,
        discovery,
        catalog,
        shared_terms=shared,
        localized_term=QUADRATIC_DEV_V10,
        source_term="x3^2",
    )
    assert isinstance(result, FrozenScopeHypothesis)
    assert result.role_client_ids == dict(fixture.truth_scopes)[QUADRATIC_DEV_V10]
    assert result.outside_client_ids == tuple(
        client.client_id for client in discovery if client.client_id not in result.role_client_ids
    )
    assert result.discovery_sign == 1


def test_phase3d_model_registry_is_frozen():
    assert PHASE3D_MODELS == EXPECTED_MODELS


def test_scope_contrast_only_recovers_every_true_localized_scope():
    for fixture in build_phase3d_fixtures():
        result = run_phase3d_model(fixture, "scope-contrast-only", outer_fold=0)
        assert result.exact_localized
        assert result.exact_scope
        if fixture.true_localized_terms:
            assert set(result.accepted_localized) == set(fixture.true_localized_terms)
        else:
            assert result.accepted_localized == ()


def test_v13_full_exactly_recovers_all_eight_deterministic_fixtures():
    for fixture in build_phase3d_fixtures():
        result = run_phase3d_model(fixture, "v13-full", outer_fold=0)
        assert result.exact_shared, (fixture.name, result.shared_structure)
        assert result.exact_localized, (fixture.name, result.accepted_localized)
        assert result.exact_scope, (fixture.name, result.localized_scopes)
        assert result.exact_structure, fixture.name


def test_v13_null_fixtures_accept_no_localized_mechanism():
    for name in ("null_no_localized", "anchor_contamination_null"):
        result = run_phase3d_model(_fixture(name), "v13-full", outer_fold=0)
        assert result.accepted_localized == ()
        assert result.localized_scopes == ()
        assert result.exact_structure
