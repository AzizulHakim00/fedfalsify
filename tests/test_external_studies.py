from __future__ import annotations

import numpy as np

from fedfalsify.external_beijing_study import SELECTED_FEATURES, build_catalog as build_beijing_catalog
from fedfalsify.external_common import ExternalClientData, fit_standardization, standardized_clients
from fedfalsify.external_srsd_study import _clients, _with_dummies
from fedfalsify.external_srsd_study_v3 import build_catalog as build_raw_srsd_catalog
from fedfalsify.external_srsd_study_v4 import PROBLEMS, normalize_catalog


def test_beijing_catalog_is_finite_and_contains_declared_terms() -> None:
    catalog = build_beijing_catalog(SELECTED_FEATURES)
    x = np.random.default_rng(1).normal(size=(20, len(SELECTED_FEATURES)))
    matrix = catalog.matrix(x, catalog.names())
    assert np.all(np.isfinite(matrix))
    assert "pm10" in catalog.names()
    assert "pm10*co" in catalog.names()


def test_srsd_corrected_problem_dimensions_match_physical_formulas() -> None:
    dimensions = {spec.problem: spec.true_variables for spec in PROBLEMS}
    assert dimensions == {
        "feynman-i.12.1": 2,
        "feynman-i.14.3": 2,
        "feynman-i.18.12": 3,
        "feynman-ii.15.4": 3,
        "feynman-ii.27.18": 1,
    }


def _scaling_and_clients(spec, seed: int = 99):
    rng = np.random.default_rng(seed)
    physical_x = rng.uniform(1e-9, 4.0, size=(80, spec.true_variables))
    physical_x = _with_dummies(physical_x, seed=seed + 1)
    y = spec.truth_values(physical_x)
    raw_clients = _clients(physical_x, y)
    scaling = fit_standardization(raw_clients)
    clients = standardized_clients(raw_clients, scaling)
    return physical_x, y, scaling, clients


def test_srsd_true_term_reconstructs_physical_coordinates_after_scaling() -> None:
    spec = PROBLEMS[0]
    _, _, scaling, clients = _scaling_and_clients(spec)
    catalog = build_raw_srsd_catalog(
        spec, clients[0].x.shape[1], scaling, include_truth=True
    )
    reconstructed = np.concatenate([
        catalog.get(spec.truth_name).evaluate(client.x) for client in clients
    ])
    expected = np.concatenate([
        client.y * scaling.y_scale + scaling.y_mean for client in clients
    ])
    assert np.allclose(reconstructed, expected)


def test_srsd_misspecified_catalog_excludes_truth_and_keeps_dummies() -> None:
    spec = PROBLEMS[2]
    _, _, scaling, clients = _scaling_and_clients(spec, seed=3)
    catalog = build_raw_srsd_catalog(
        spec, clients[0].x.shape[1], scaling, include_truth=False
    )
    assert spec.truth_name not in catalog.names()
    assert any("dummy" in name for name in catalog.names())


def test_srsd_catalog_has_one_identifiable_truth_representation() -> None:
    for spec in (PROBLEMS[0], PROBLEMS[1], PROBLEMS[4]):
        _, _, scaling, clients = _scaling_and_clients(spec, seed=8)
        supported = build_raw_srsd_catalog(
            spec, clients[0].x.shape[1], scaling, include_truth=True
        )
        misspecified = build_raw_srsd_catalog(
            spec, clients[0].x.shape[1], scaling, include_truth=False
        )
        assert spec.truth_name in supported.names()
        assert spec.truth_name not in misspecified.names()
        if spec.problem in {"feynman-i.12.1", "feynman-i.14.3"}:
            assert "v0*v1" not in supported.names()
            assert "v0*v1" not in misspecified.names()
        if spec.problem == "feynman-ii.27.18":
            assert "x0^2" not in supported.names()
            assert "x0^2" not in misspecified.names()


def test_srsd_nonconstant_basis_columns_are_training_unit_variance() -> None:
    spec = PROBLEMS[3]
    _, _, scaling, clients = _scaling_and_clients(spec, seed=17)
    raw = build_raw_srsd_catalog(
        spec, clients[0].x.shape[1], scaling, include_truth=True
    )
    normalized, metadata = normalize_catalog(raw, clients)
    for name in normalized.names():
        values = np.concatenate([
            normalized.get(name).evaluate(client.x) for client in clients
        ])
        if name == "1":
            assert np.allclose(values, 1.0)
            continue
        raw_values = np.concatenate([
            raw.get(name).evaluate(client.x) for client in clients
        ])
        if np.var(raw_values) > 0.0:
            assert np.isclose(np.mean(values), 0.0, atol=1e-10)
            assert np.isclose(np.var(values), 1.0, atol=1e-10)
            assert metadata[name]["scale"] > 0.0
