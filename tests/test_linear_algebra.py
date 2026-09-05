import numpy as np

from fedfalsify.linear_algebra import RankPolicy, fit_from_sufficient_stats
from fedfalsify.scsv_v10_benchmarks import generate_v10_benchmark, v10_catalog
from fedfalsify.sufficient_stats import SufficientStatsPacket, aggregate_packets, packet_from_dataset


def test_sufficient_stat_fit_matches_centralized_least_squares():
    generated = generate_v10_benchmark(
        "quadratic_role_v10",
        seed=29001,
        num_clients=4,
        balance_profile="balanced",
        role_profile="single",
        noise_ratio=0.10,
    )
    catalog = v10_catalog()
    selected_terms = ("1", "x1", "x3^2")

    packets = tuple(
        packet_from_dataset(client, catalog, selected_terms)
        for client in generated.clients
    )
    pooled = aggregate_packets(packets)
    fit = fit_from_sufficient_stats(pooled, selected_terms, RankPolicy())

    x_concat = np.concatenate([client.x for client in generated.clients], axis=0)
    y_concat = np.concatenate([client.y for client in generated.clients], axis=0)
    design = catalog.matrix(x_concat, selected_terms)
    beta_central, *_ = np.linalg.lstsq(design, y_concat, rcond=None)
    sse_central = float(np.sum((y_concat - design @ beta_central) ** 2))
    rank_central = int(np.linalg.matrix_rank(design))

    np.testing.assert_allclose(fit.coefficients, beta_central, rtol=1e-10, atol=1e-10)
    assert abs(fit.sse - sse_central) <= 1e-8
    assert fit.rank == rank_central
    assert fit.full_rank is True
    assert fit.residual_df == len(y_concat) - rank_central


def test_rank_deficient_sufficient_statistics_are_reported_not_hidden():
    packet = SufficientStatsPacket(
        client_id="rank-deficient",
        support=4,
        terms=("a", "b"),
        gram=np.asarray([[4.0, 4.0], [4.0, 4.0]], dtype=float),
        target=np.asarray([2.0, 2.0], dtype=float),
        target_energy=2.0,
        observed_support=(4, 4),
    )
    fit = fit_from_sufficient_stats(packet, ("a", "b"), RankPolicy())
    assert fit.rank == 1
    assert fit.full_rank is False
    assert fit.residual_df == 3
