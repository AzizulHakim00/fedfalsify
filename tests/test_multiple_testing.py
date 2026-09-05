import math

import pytest

from fedfalsify.multiple_testing import bh_adjust, holm_adjust


def test_holm_known_vector_preserves_original_order():
    out = holm_adjust(("a", "b", "c", "d"), (0.01, 0.04, 0.03, 0.20), alpha=0.05)

    assert out.names == ("a", "b", "c", "d")
    assert out.raw_values == (0.01, 0.04, 0.03, 0.20)
    assert out.adjusted_values == pytest.approx((0.04, 0.09, 0.09, 0.20), abs=1e-12)
    assert out.rejected == ("a",)


def test_bh_known_vector_matches_reference():
    out = bh_adjust(("a", "b", "c", "d"), (0.01, 0.02, 0.04, 0.20), q=0.05)

    assert out.adjusted_values == pytest.approx((0.04, 0.04, 0.05333333333333334, 0.20), abs=1e-12)
    assert out.rejected == ("a", "b")


def test_bh_ties_are_deterministic_and_return_original_order():
    first = bh_adjust(("a", "b", "c"), (0.02, 0.02, 0.50), q=0.10)
    second = bh_adjust(("a", "b", "c"), (0.02, 0.02, 0.50), q=0.10)

    assert first == second
    assert first.adjusted_values == pytest.approx((0.03, 0.03, 0.50), abs=1e-12)
    assert first.rejected == ("a", "b")


def test_multiplicity_rejects_invalid_inputs():
    with pytest.raises(ValueError):
        holm_adjust(("a", "a"), (0.01, 0.02), alpha=0.05)
    with pytest.raises(ValueError):
        bh_adjust(("a",), (math.nan,), q=0.10)
    with pytest.raises(ValueError):
        holm_adjust(("a",), (1.01,), alpha=0.05)
    with pytest.raises(ValueError):
        bh_adjust(("a",), (0.01,), q=0.0)


def test_rejection_set_is_exactly_adjusted_values_below_threshold():
    names = ("a", "b", "c", "d")
    out = holm_adjust(names, (0.001, 0.02, 0.20, 0.80), alpha=0.05)
    expected = tuple(
        name for name, adjusted in zip(out.names, out.adjusted_values) if adjusted <= 0.05
    )
    assert out.rejected == expected
