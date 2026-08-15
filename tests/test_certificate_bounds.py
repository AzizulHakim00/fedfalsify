from __future__ import annotations

from fedfalsify.certificate_bounds import (
    invariant_retention_lower_bound,
    normal_cdf,
    null_family_acceptance_upper_bound,
    shortcut_acceptance_upper_bound,
    simulate_certificate_cell,
    standardized_effect_lower_bound,
)


def test_normal_cdf_reference_values() -> None:
    assert abs(normal_cdf(0.0) - 0.5) < 1e-12
    assert abs(normal_cdf(1.96) - 0.9750021048517795) < 1e-10


def test_invariant_bound_improves_with_client_count_when_separated() -> None:
    small = invariant_retention_lower_bound(
        observable_clients=4,
        standardized_effect=4.0,
        z_threshold=1.96,
        support_fraction=0.60,
    )
    large = invariant_retention_lower_bound(
        observable_clients=32,
        standardized_effect=4.0,
        z_threshold=1.96,
        support_fraction=0.60,
    )
    assert 0.0 <= small <= 1.0
    assert 0.0 <= large <= 1.0
    assert large > small


def test_shortcut_bound_decreases_with_client_count_below_support_threshold() -> None:
    small = shortcut_acceptance_upper_bound(
        observable_clients=4,
        active_client_fraction=0.20,
        z_threshold=1.96,
        support_fraction=0.60,
    )
    large = shortcut_acceptance_upper_bound(
        observable_clients=32,
        active_client_fraction=0.20,
        z_threshold=1.96,
        support_fraction=0.60,
    )
    assert 0.0 <= large < small <= 1.0


def test_family_bound_is_capped_at_one() -> None:
    value = null_family_acceptance_upper_bound(
        observable_clients=4,
        candidate_count=1_000_000,
        z_threshold=1.96,
        support_fraction=0.60,
    )
    assert value == 1.0


def test_standardized_effect_corollary() -> None:
    value = standardized_effect_lower_bound(
        coefficient=0.5,
        minimum_samples=100,
        minimum_residualized_variance=0.25,
        maximum_noise_standard_deviation=1.0,
    )
    assert abs(value - 2.5) < 1e-12


def test_monte_carlo_cell_respects_bounds_with_tolerance() -> None:
    row = simulate_certificate_cell(
        observable_clients=16,
        standardized_effect=4.0,
        active_client_fraction=0.20,
        z_threshold=1.96,
        support_fraction=0.60,
        trials=20000,
        seed=13001,
    )
    assert row.empirical_invariant_retention + 0.03 >= row.invariant_retention_lower_bound
    assert row.empirical_shortcut_acceptance - 0.03 <= row.shortcut_acceptance_upper_bound
