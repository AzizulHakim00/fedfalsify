from __future__ import annotations

import numpy as np

from fedfalsify.basis import BasisTerm, CandidateEquation
from fedfalsify.baselines import MethodOutput
from fedfalsify.crossfit import cross_fitted_fedfalsify, make_crossfit_folds
from fedfalsify.external_common import ExternalClientData, FlexibleTermCatalog


def _catalog() -> FlexibleTermCatalog:
    return FlexibleTermCatalog(
        [
            BasisTerm("1", lambda x: np.ones(len(x)), 1, "1"),
            BasisTerm("x0", lambda x: x[:, 0], 1, "x0"),
            BasisTerm("x0^2", lambda x: x[:, 0] ** 2, 2, "x0²"),
        ]
    )


def _datasets() -> list[ExternalClientData]:
    output = []
    for index, offset in enumerate((0.0, 0.4), start=1):
        x0 = np.linspace(-2.0 + offset, 2.0 + offset, 80)
        x = np.column_stack([x0, np.arange(80.0)])
        y = 1.5 + 2.0 * x0
        output.append(ExternalClientData(f"client-{index}", x, y))
    return output


def test_crossfit_partitions_are_deterministic_and_disjoint() -> None:
    catalog = _catalog()
    datasets = _datasets()
    first = make_crossfit_folds(datasets, catalog, folds=2, seed=13001)
    second = make_crossfit_folds(datasets, catalog, folds=2, seed=13001)
    assert len(first) == 2
    for fold_a, fold_b in zip(first, second):
        assert fold_a.training_rows == fold_a.validation_rows == 80
        for train_a, validation_a, train_b, validation_b in zip(
            fold_a.training, fold_a.validation, fold_b.training, fold_b.validation
        ):
            train_ids = set(train_a._dataset.x[:, 1])
            validation_ids = set(validation_a._dataset.x[:, 1])
            assert train_ids.isdisjoint(validation_ids)
            assert train_ids | validation_ids == set(np.arange(80.0))
            assert np.array_equal(train_a._dataset.x, train_b._dataset.x)
            assert np.array_equal(validation_a._dataset.x, validation_b._dataset.x)


def test_governed_fallback_activates_only_from_heldout_gain(monkeypatch) -> None:
    catalog = _catalog()
    datasets = _datasets()

    def full(*args, **kwargs):
        return MethodOutput(
            "fedfalsify",
            (CandidateEquation(("1",), (0.0,), "full"),),
            1,
            0,
            0.0,
            "certificate stopped",
        )

    def score(*args, **kwargs):
        return MethodOutput(
            "score-only-federated",
            (CandidateEquation(("1", "x0"), (0.0, 0.0), "score"),),
            1,
            0,
            0.0,
            "aggregate search",
        )

    monkeypatch.setattr("fedfalsify.crossfit.fedfalsify_method", full)
    monkeypatch.setattr("fedfalsify.crossfit.score_only_federated", score)
    result = cross_fitted_fedfalsify(
        datasets,
        catalog,
        seed=13002,
        fallback_min_relative_improvement=0.02,
    )
    assert result.fallback_activated
    assert result.selected_source == "score-only-federated"
    assert result.candidate.active_terms == ("1", "x0")
    assert result.validations[0].mean_mse < result.validations[-1].mean_mse


def test_fallback_is_blocked_when_complexity_gate_fails(monkeypatch) -> None:
    catalog = _catalog()
    datasets = _datasets()

    def full(*args, **kwargs):
        return MethodOutput(
            "fedfalsify",
            (CandidateEquation(("1",), (0.0,), "full"),),
            1,
            0,
            0.0,
            "certificate stopped",
        )

    def score(*args, **kwargs):
        return MethodOutput(
            "score-only-federated",
            (CandidateEquation(("1", "x0", "x0^2"), (0.0, 0.0, 0.0), "score"),),
            1,
            0,
            0.0,
            "aggregate search",
        )

    monkeypatch.setattr("fedfalsify.crossfit.fedfalsify_method", full)
    monkeypatch.setattr("fedfalsify.crossfit.score_only_federated", score)
    result = cross_fitted_fedfalsify(
        datasets,
        catalog,
        seed=13003,
        fallback_complexity_slack=0,
    )
    assert not result.fallback_activated
    assert result.selected_source == "fedfalsify"
    assert result.candidate.active_terms == ("1",)
