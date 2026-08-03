from __future__ import annotations

import numpy as np

from fedfalsify.basis import BasisTerm
from fedfalsify.external_common import (
    ExternalClientData,
    FlexibleTermCatalog,
    fit_standardization,
    regression_metrics,
    standardized_clients,
    systematic_indices,
)


def test_external_clients_support_arbitrary_feature_counts() -> None:
    client = ExternalClientData("site-a", np.ones((12, 7)), np.arange(12.0))
    assert client.x.shape == (12, 7)


def test_aggregate_standardization_is_finite_and_invertible() -> None:
    clients = [
        ExternalClientData("a", np.arange(30.0).reshape(10, 3), np.arange(10.0)),
        ExternalClientData("b", np.arange(30.0, 60.0).reshape(10, 3), np.arange(10.0, 20.0)),
    ]
    scaling = fit_standardization(clients)
    transformed = standardized_clients(clients, scaling)
    pooled_x = np.concatenate([client.x for client in transformed])
    pooled_y = np.concatenate([client.y for client in transformed])
    assert np.allclose(pooled_x.mean(axis=0), 0.0)
    assert np.isclose(pooled_y.mean(), 0.0)
    assert np.allclose(scaling.inverse_y(pooled_y), np.arange(20.0))


def test_flexible_catalog_is_core_protocol_compatible() -> None:
    catalog = FlexibleTermCatalog([
        BasisTerm("1", lambda x: np.ones(len(x)), 1, "1"),
        BasisTerm("x0", lambda x: x[:, 0], 1, "x0"),
        BasisTerm("x0^2", lambda x: x[:, 0] ** 2, 2, "x0²"),
    ])
    x = np.arange(12.0).reshape(6, 2)
    matrix = catalog.matrix(x, ("1", "x0", "x0^2"))
    assert matrix.shape == (6, 3)
    assert catalog.complexity(("1", "x0^2")) == 3


def test_systematic_sampling_and_metrics() -> None:
    indices = systematic_indices(100, 11)
    assert len(indices) == 11
    assert indices[0] == 0 and indices[-1] == 99
    metrics = regression_metrics(np.asarray([1.0, 2.0]), np.asarray([1.0, 3.0]))
    assert metrics["mae"] == 0.5
    assert metrics["rmse"] > 0.0
