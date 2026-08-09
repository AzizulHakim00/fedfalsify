"""Independent benchmark adapters for frozen SCSV-Cert v6 validation.

This module changes only benchmark composition and federation geometry.  It does
not copy or modify the v6 discovery/selection algorithm.
"""

from __future__ import annotations

from typing import Literal

import numpy as np

from .benchmarks import (
    BenchmarkClientDataset,
    BenchmarkSpec,
    GeneratedBenchmark,
    benchmark_catalog,
    evaluate_terms,
)

BalanceProfile = Literal["balanced", "imbalanced"]
Scenario = Literal["complementary", "spurious", "exception"]

INDEPENDENT_BENCHMARKS: dict[str, BenchmarkSpec] = {
    "cubic_cross": BenchmarkSpec(
        "cubic_cross",
        "Cubic, bilinear and quadratic mechanism on three physical inputs.",
        (("x1^3", 0.8), ("x1*x2", 1.2), ("x3^2", 0.5)),
    ),
    "fourier_quadratic": BenchmarkSpec(
        "fourier_quadratic",
        "Cosine and sine terms with a quadratic contribution.",
        (("cos(x1)", 1.0), ("sin(x3)", 0.9), ("x2^2", 0.7)),
    ),
    "nested_mixed": BenchmarkSpec(
        "nested_mixed",
        "Nested periodic term plus linear and quadratic effects.",
        (("sin(x1+x1^2)", 1.0), ("x2", 0.6), ("x3^2", 0.8)),
    ),
    "multi_quadratic": BenchmarkSpec(
        "multi_quadratic",
        "Three simultaneous quadratic effects.",
        (("x1^2", 0.6), ("x2^2", 0.5), ("x3^2", 0.8)),
    ),
    "trig_cross": BenchmarkSpec(
        "trig_cross",
        "Trigonometric interaction with cosine and linear effects.",
        (("sin(x1)*cos(x2)", 1.2), ("cos(x3)", 0.7), ("x1", 0.5)),
    ),
}


def independent_client_sizes(
    nominal_samples_per_client: int,
    num_clients: int,
    *,
    profile: BalanceProfile,
    seed: int,
) -> tuple[int, ...]:
    """Return deterministic balanced or truth-independent imbalanced sizes."""

    if num_clients < 3:
        raise ValueError("independent validation requires at least three clients")
    if nominal_samples_per_client < 70:
        raise ValueError("nominal samples/client must be at least 70")
    if profile == "balanced":
        return (int(nominal_samples_per_client),) * num_clients
    if profile != "imbalanced":
        raise ValueError(f"unknown balance profile: {profile}")

    # The frozen v6 selector/probe implementation requires at least 20 rows in
    # the 30% held-out partition.  A 70-row client yields at least 21 held-out
    # rows, so the independent adapter clips only for structural feasibility.
    multipliers = np.geomspace(0.50, 1.50, num_clients)
    sizes = np.asarray(
        [max(70, int(round(nominal_samples_per_client * value))) for value in multipliers],
        dtype=int,
    )
    sizes = np.roll(sizes, int(seed) % num_clients)
    return tuple(int(value) for value in sizes)


def generate_independent_benchmark(
    name: str,
    *,
    scenario: Scenario = "complementary",
    nominal_samples_per_client: int = 100,
    noise_ratio: float = 0.20,
    seed: int = 20101,
    num_clients: int = 4,
    balance_profile: BalanceProfile = "balanced",
) -> GeneratedBenchmark:
    """Generate a preregistered independent truth family under frozen grammar."""

    if name not in INDEPENDENT_BENCHMARKS:
        raise KeyError(f"unknown independent benchmark: {name}")
    if scenario not in {"complementary", "spurious", "exception"}:
        raise ValueError(f"unknown scenario: {scenario}")
    if noise_ratio < 0:
        raise ValueError("noise_ratio cannot be negative")

    spec = INDEPENDENT_BENCHMARKS[name]
    catalog = benchmark_catalog(scenario=scenario)
    target = list(spec.coefficients)
    if scenario == "exception":
        target.append(("I(x3>1)*x3^2", 0.75))
    target_coefficients = tuple(target)
    sizes = independent_client_sizes(
        nominal_samples_per_client,
        num_clients,
        profile=balance_profile,
        seed=seed,
    )

    rng = np.random.default_rng(seed)
    raw_x: list[np.ndarray] = []
    noiseless_targets: list[np.ndarray] = []
    for client_index, client_size in enumerate(sizes):
        phase = client_index / max(num_clients - 1, 1)
        if scenario == "exception" and client_index == num_clients - 1:
            x3 = rng.uniform(1.05, 2.5, size=client_size)
        elif scenario == "exception":
            x3 = rng.uniform(-2.5 + 0.3 * phase, 0.95, size=client_size)
        else:
            x3 = rng.uniform(-2.5 + phase, 1.5 + phase, size=client_size)
        x1 = rng.uniform(-2.8 + 1.4 * phase, 1.0 + 2.0 * phase, size=client_size)
        x2 = rng.uniform(
            -np.pi + 1.2 * phase,
            0.6 + (np.pi - 0.6) * phase,
            size=client_size,
        )
        x4 = rng.normal(0.0, 1.0, size=client_size)
        x = np.column_stack([x1, x2, x3, x4])
        noiseless = evaluate_terms(x, target_coefficients, catalog)

        # x4 is nuisance-only in every independent truth family.  This retains
        # the historical local-shortcut stress without changing the true y.
        if scenario == "spurious" and client_index == 0:
            standardized = (noiseless - noiseless.mean()) / max(noiseless.std(), 1e-12)
            x[:, 3] = standardized + rng.normal(0.0, 0.03, size=client_size)

        raw_x.append(x)
        noiseless_targets.append(noiseless)

    pooled_scale = max(float(np.std(np.concatenate(noiseless_targets))), 1e-12)
    noise_std = float(noise_ratio) * pooled_scale
    clients = tuple(
        BenchmarkClientDataset(
            f"client-{index + 1}",
            x,
            noiseless + rng.normal(0.0, noise_std, size=len(noiseless)),
        )
        for index, (x, noiseless) in enumerate(zip(raw_x, noiseless_targets))
    )
    return GeneratedBenchmark(
        spec=spec,
        scenario=scenario,
        clients=clients,
        target_coefficients=target_coefficients,
        noise_std=noise_std,
    )
