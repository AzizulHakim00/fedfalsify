import numpy as np
import pytest
from scipy.stats import f as f_distribution

from fedfalsify.nested_tests import aggregate_scope, partial_nested_f
from fedfalsify.sufficient_stats import SufficientStatsPacket, aggregate_packets


def _packet(client_id: str, x: np.ndarray, y: np.ndarray) -> SufficientStatsPacket:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    design = np.column_stack([np.ones(len(x), dtype=float), x])
    return SufficientStatsPacket(
        client_id=client_id,
        support=len(y),
        terms=("1", "x1"),
        gram=np.asarray(design.T @ design, dtype=float),
        target=np.asarray(design.T @ y, dtype=float),
        target_energy=float(y @ y),
        observed_support=(len(y), int(np.count_nonzero(np.abs(x) > 1e-12))),
    )


def test_nested_f_matches_direct_ols_and_scipy_reference():
    x = np.asarray([-2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    y = 1.5 + 2.0 * x + np.asarray([0.10, -0.20, 0.05, 0.10, -0.10, 0.05, 0.20, -0.15])
    packet = _packet("central", x, y)

    out = partial_nested_f(packet, ("1",), ("1", "x1"), candidate_term="x1")

    reduced_design = np.ones((len(x), 1), dtype=float)
    full_design = np.column_stack([np.ones(len(x), dtype=float), x])
    reduced_beta, *_ = np.linalg.lstsq(reduced_design, y, rcond=None)
    full_beta, *_ = np.linalg.lstsq(full_design, y, rcond=None)
    reduced_sse = float(np.sum((y - reduced_design @ reduced_beta) ** 2))
    full_sse = float(np.sum((y - full_design @ full_beta) ** 2))
    full_rank = int(np.linalg.matrix_rank(full_design))
    residual_df = len(y) - full_rank
    expected_f = ((reduced_sse - full_sse) / 1.0) / (full_sse / residual_df)
    expected_p = float(f_distribution.sf(expected_f, 1, residual_df))

    assert out.admissible
    assert out.reason == "OK"
    assert out.full_rank == out.reduced_rank + 1
    assert out.residual_df == residual_df
    assert out.reduced_sse == pytest.approx(reduced_sse, rel=1e-10, abs=1e-10)
    assert out.full_sse == pytest.approx(full_sse, rel=1e-10, abs=1e-10)
    assert out.f_statistic == pytest.approx(expected_f, rel=1e-10, abs=1e-10)
    assert out.p_value == pytest.approx(expected_p, rel=1e-10, abs=1e-12)
    assert out.candidate_coefficient == pytest.approx(float(full_beta[1]), rel=1e-10, abs=1e-10)
    assert out.candidate_sign == 1


def test_nested_f_abstains_on_exact_collinearity():
    x = np.asarray([-2.0, -1.0, 0.0, 1.0, 2.0, 3.0])
    y = 0.5 + 1.25 * x
    design = np.column_stack([np.ones(len(x), dtype=float), x, x])
    packet = SufficientStatsPacket(
        client_id="collinear",
        support=len(y),
        terms=("1", "x1", "x1_copy"),
        gram=np.asarray(design.T @ design, dtype=float),
        target=np.asarray(design.T @ y, dtype=float),
        target_energy=float(y @ y),
        observed_support=(len(y), len(y) - 1, len(y) - 1),
    )

    out = partial_nested_f(
        packet,
        ("1", "x1"),
        ("1", "x1", "x1_copy"),
        candidate_term="x1_copy",
    )

    assert not out.admissible
    assert out.reason == "STRUCTURAL-RANK-AMBIGUOUS"
    assert out.p_value is None
    assert out.f_statistic is None


def test_nested_f_zero_full_sse_returns_infinite_f_and_zero_p():
    x = np.asarray([-2.0, -1.0, 0.0, 1.0, 2.0, 3.0])
    y = 1.0 + 3.0 * x
    out = partial_nested_f(_packet("perfect", x, y), ("1",), ("1", "x1"), candidate_term="x1")

    assert out.admissible
    assert np.isinf(out.f_statistic)
    assert out.p_value == 0.0
    assert out.raw_gain > 0.0


def test_aggregate_scope_matches_direct_packet_aggregation():
    packets = (
        _packet("c0", np.asarray([-2.0, -1.0, 0.0]), np.asarray([-3.0, -1.0, 1.0])),
        _packet("c1", np.asarray([1.0, 2.0, 3.0]), np.asarray([3.0, 5.0, 7.0])),
        _packet("c2", np.asarray([4.0, 5.0, 6.0]), np.asarray([9.0, 11.0, 13.0])),
    )
    scoped = aggregate_scope(packets, (0, 2))
    direct = aggregate_packets((packets[0], packets[2]))

    assert scoped.support == direct.support
    assert scoped.terms == direct.terms
    np.testing.assert_allclose(scoped.gram, direct.gram, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(scoped.target, direct.target, rtol=0.0, atol=1e-12)
    assert scoped.target_energy == pytest.approx(direct.target_energy, rel=0.0, abs=1e-12)


def test_nested_f_requires_exact_one_term_nesting():
    packet = _packet("nesting", np.asarray([-1.0, 0.0, 1.0, 2.0]), np.asarray([-1.0, 1.0, 3.0, 5.0]))
    with pytest.raises(ValueError):
        partial_nested_f(packet, ("1",), ("1",), candidate_term="x1")
