from __future__ import annotations

import numpy as np

from fedfalsify.external_beijing_study import SELECTED_FEATURES, build_catalog as build_beijing_catalog
from fedfalsify.external_common import ExternalClientData, fit_standardization, standardized_clients
from fedfalsify.external_srsd_study import _clients, _with_dummies
from fedfalsify.external_srsd_study_fixed import PROBLEMS, build_catalog as build_srsd_catalog


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


def test_srsd_true_term_reconstructs_physical_coordinates_after_scaling() -> None:
    spec = PROBLEMS[0]
    rng = np.random.default_rng(2)
    physical_x = rng.uniform(1.0, 4.0, size=(80, spec.true_variables))
    physical_x = _with_dummies(physical_x, seed=99)
    y = physical_x[:, 0] * physical_x[:, 1]
    raw_clients = _clients(physical_x, y)
    scaling = fit_standardization(raw_clients)
    standardized = standardized_clients(raw_clients, scaling)
    catalog = build_srsd_catalog(spec, physical_x.shape[1], scaling, include_truth=True)
    reconstructed = np.concatenate([
        catalog.get(spec.truth_name).evaluate(client.x) for client in standardized
    ])
    expected = np.concatenate([
        client.y * scaling.y_scale + scaling.y_mean for client in standardized
    ])
    assert np.allclose(reconstructed, expected)


def test_srsd_misspecified_catalog_excludes_truth_and_keeps_dummies() -> None:
    spec = PROBLEMS[2]
    x = np.random.default_rng(3).normal(size=(80, spec.true_variables + 3))
    y = np.random.default_rng(4).normal(size=80)
    scaling = fit_standardization([
        ExternalClientData("a", x[:40], y[:40]),
        ExternalClientData("b", x[40:], y[40:]),
    ])
    catalog = build_srsd_catalog(spec, x.shape[1], scaling, include_truth=False)
    assert spec.truth_name not in catalog.names()
    assert any("dummy" in name for name in catalog.names())


def test_srsd_misspecification_removes_algebraic_truth_duplicates() -> None:
    rng = np.random.default_rng(8)
    for spec in (PROBLEMS[0], PROBLEMS[1], PROBLEMS[4]):
        x = rng.normal(size=(80, spec.true_variables + 3))
        y = rng.normal(size=80)
        scaling = fit_standardization([
            ExternalClientData("a", x[:40], y[:40]),
            ExternalClientData("b", x[40:], y[40:]),
        ])
        catalog = build_srsd_catalog(spec, x.shape[1], scaling, include_truth=False)
        assert spec.truth_name not in catalog.names()
        if spec.problem in {"feynman-i.12.1", "feynman-i.14.3"}:
            assert "v0*v1" not in catalog.names()
        if spec.problem == "feynman-ii.27.18":
            assert "x0^2" not in catalog.names()
