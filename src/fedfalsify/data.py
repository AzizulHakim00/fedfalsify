"""Synthetic heterogeneous client generators with known mechanisms."""

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
    """Base hidden mechanism for complementary-domain recovery."""

    return 2.0 * x[:, 0] + np.sin(x[:, 1]) + 0.5 * x[:, 2] ** 2


def generate_heterogeneous_clients(
    *,
    samples_per_client: int = 500,
    noise_std: float = 0.03,
    seed: int = 2026,
) -> list[ClientDataset]:
    """Create four clients observing complementary regions of one mechanism."""

    _validate_generation_args(samples_per_client, noise_std)
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


def spurious_ground_truth(x: Array) -> Array:
    """Mechanism that deliberately excludes x3."""

    return 3.0 * x[:, 0] + 0.8 * x[:, 1] ** 2


def generate_spurious_correlation_clients(
    *,
    samples_per_client: int = 600,
    noise_std: float = 0.03,
    seed: int = 2027,
) -> list[ClientDataset]:
    """Create a local shortcut: x3 predicts y only at the first client.

    All clients share the same true mechanism. At client 1, x3 is generated as
    a noisy standardized copy of the noiseless outcome, creating a strong local
    correlation that should not survive cross-client falsification.
    """

    _validate_generation_args(samples_per_client, noise_std)
    rng = np.random.default_rng(seed)
    clients: list[ClientDataset] = []
    for index in range(1, 5):
        x1 = rng.uniform(-2.5, 2.5, size=samples_per_client)
        x2 = rng.uniform(-2.0, 2.0, size=samples_per_client)
        preliminary = np.column_stack([x1, x2, np.zeros(samples_per_client)])
        noiseless = spurious_ground_truth(preliminary)
        if index == 1:
            standardized = (noiseless - noiseless.mean()) / max(noiseless.std(), 1e-12)
            x3 = standardized + rng.normal(0.0, 0.05, size=samples_per_client)
        else:
            x3 = rng.normal(0.0, 1.0, size=samples_per_client)
        x = np.column_stack([x1, x2, x3])
        y = spurious_ground_truth(x) + rng.normal(
            0.0, noise_std, size=samples_per_client
        )
        clients.append(ClientDataset(f"client-{index}", x, y))
    return clients


def exception_ground_truth(x: Array) -> Array:
    """Invariant core with a domain-restricted nonlinear exception."""

    exception = np.where(x[:, 2] > 1.0, 0.75 * x[:, 2] ** 2, 0.0)
    return 2.0 * x[:, 0] + np.sin(x[:, 1]) + exception


def generate_exception_clients(
    *,
    samples_per_client: int = 700,
    noise_std: float = 0.02,
    seed: int = 2028,
) -> list[ClientDataset]:
    """Create clients with an invariant core and a partially observed exception.

    Clients 1--3 observe x3 <= 0.95 and therefore cannot verify or falsify the
    x3 > 1 exception. Client 4 observes only the exceptional domain. The correct
    output is an invariant core plus a provisional domain-restricted term.
    """

    _validate_generation_args(samples_per_client, noise_std)
    rng = np.random.default_rng(seed)
    x3_ranges = [(-2.5, 0.95), (-2.0, 0.95), (-1.5, 0.95), (1.05, 2.5)]
    clients: list[ClientDataset] = []
    for index, (x3_low, x3_high) in enumerate(x3_ranges, start=1):
        x1 = rng.uniform(-2.5, 2.5, size=samples_per_client)
        x2 = rng.uniform(-np.pi, np.pi, size=samples_per_client)
        x3 = rng.uniform(x3_low, x3_high, size=samples_per_client)
        x = np.column_stack([x1, x2, x3])
        y = exception_ground_truth(x) + rng.normal(
            0.0, noise_std, size=samples_per_client
        )
        clients.append(ClientDataset(f"client-{index}", x, y))
    return clients


def _validate_generation_args(samples_per_client: int, noise_std: float) -> None:
    if samples_per_client < 50:
        raise ValueError("Use at least 50 samples per client for a stable demo")
    if noise_std < 0:
        raise ValueError("noise_std cannot be negative")
