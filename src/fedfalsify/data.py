"""Synthetic heterogeneous client generation with known ground truth."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

Array = np.ndarray


@dataclass(frozen=True)
class ClientDataset:
    """Private data owned by one simulated institution."""

    client_id: str
    x: Array
    y: Array

    def __post_init__(self) -> None:
        if self.x.ndim != 2 or self.x.shape[1] != 3:
            raise ValueError("x must have shape (n_samples, 3)")
        if self.y.ndim != 1 or self.y.shape[0] != self.x.shape[0]:
            raise ValueError("y must have shape (n_samples,)")
        if self.x.shape[0] < 10:
            raise ValueError("Each client needs at least 10 observations")


def ground_truth(x: Array) -> Array:
    """Hidden mechanism used only by the synthetic data generator."""

    return 2.0 * x[:, 0] + np.sin(x[:, 1]) + 0.5 * x[:, 2] ** 2


def generate_heterogeneous_clients(
    *,
    samples_per_client: int = 500,
    noise_std: float = 0.03,
    seed: int = 2026,
) -> list[ClientDataset]:
    """Create four clients observing complementary regions of the mechanism.

    No client covers the complete input domain. The federation must combine
    falsification evidence across institutions to recover all three true terms.
    """

    if samples_per_client < 50:
        raise ValueError("Use at least 50 samples per client for a stable demo")
    if noise_std < 0:
        raise ValueError("noise_std cannot be negative")

    rng = np.random.default_rng(seed)
    ranges = [
        ((-2.5, -0.1), (-np.pi, 0.2), (-2.0, 1.0)),
        ((0.1, 2.5), (-0.2, np.pi), (-1.0, 2.0)),
        ((-1.2, 1.2), (-np.pi, np.pi), (-2.0, 2.0)),
        ((1.0, 3.0), (-1.2, 1.2), (-2.5, 2.5)),
    ]

    clients: list[ClientDataset] = []
    for index, client_ranges in enumerate(ranges, start=1):
        columns = [
            rng.uniform(low, high, size=samples_per_client)
            for low, high in client_ranges
        ]
        x = np.column_stack(columns)
        y = ground_truth(x) + rng.normal(0.0, noise_std, size=samples_per_client)
        clients.append(ClientDataset(f"client-{index}", x, y))
    return clients
