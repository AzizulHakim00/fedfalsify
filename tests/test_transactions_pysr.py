from __future__ import annotations

import math

import pytest

from fedfalsify.transactions_pysr import (
    _parse_ints,
    run_condition,
    validate_fresh_seeds,
)


def test_frozen_pysr_seeds_are_rejected() -> None:
    with pytest.raises(ValueError, match="frozen seeds"):
        validate_fresh_seeds((9001, 10001))


def test_pysr_seed_ranges_are_parsed() -> None:
    assert _parse_ints("10001-10003,10005") == (
        10001,
        10002,
        10003,
        10005,
    )


def test_exception_grammar_is_reported_as_unsupported_not_failed() -> None:
    row = run_condition(
        benchmark="base",
        scenario="exception",
        noise_ratio=0.03,
        samples_per_client=60,
        num_clients=4,
        seed=10001,
        niterations=5,
        populations=2,
        population_size=20,
        maxsize=14,
        semantic_samples=200,
    )
    assert row.grammar_supported is False
    assert row.completed is False
    assert row.package_available is True
    assert math.isnan(row.semantic_all_1e3)
    assert "Unsupported condition" in row.note


def test_duplicate_pysr_seeds_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        validate_fresh_seeds((10001, 10001))
