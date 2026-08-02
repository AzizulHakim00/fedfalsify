"""Reproducible benchmark entry points for FedFalsify claims."""

from __future__ import annotations

from dataclasses import dataclass

from .basis import TermCatalog
from .client import FederatedFalsifierClient
from .data import (
    generate_exception_clients,
    generate_spurious_correlation_clients,
)
from .server import DiscoveryResult, FedFalsifyDiscovery


@dataclass(frozen=True)
class BenchmarkResult:
    name: str
    result: DiscoveryResult
    expected_core_terms: tuple[str, ...]
    expected_exception_terms: tuple[str, ...] = ()
    rejected_terms: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        active = set(self.result.candidate.active_terms)
        return (
            set(self.expected_core_terms).issubset(active)
            and set(self.expected_exception_terms).issubset(active)
            and active.isdisjoint(self.rejected_terms)
        )


def run_spurious_correlation_benchmark(
    *, seed: int = 2027, samples_per_client: int = 600, noise_std: float = 0.03
) -> BenchmarkResult:
    catalog = TermCatalog()
    datasets = generate_spurious_correlation_clients(
        seed=seed,
        samples_per_client=samples_per_client,
        noise_std=noise_std,
    )
    clients = [FederatedFalsifierClient(dataset, catalog) for dataset in datasets]
    result = FedFalsifyDiscovery(
        clients,
        catalog,
        target_mse=max(noise_std**2 * 2.5, 1e-5),
        max_rounds=7,
        max_terms=5,
        min_repair_score=0.05,
        min_core_support_fraction=0.6,
    ).discover()
    return BenchmarkResult(
        name="spurious-correlation rejection",
        result=result,
        expected_core_terms=("1", "x1", "x2^2"),
        rejected_terms=("x3",),
    )


def run_exception_benchmark(
    *, seed: int = 2028, samples_per_client: int = 700, noise_std: float = 0.02
) -> BenchmarkResult:
    catalog = TermCatalog(include_exception_terms=True)
    datasets = generate_exception_clients(
        seed=seed,
        samples_per_client=samples_per_client,
        noise_std=noise_std,
    )
    clients = [FederatedFalsifierClient(dataset, catalog) for dataset in datasets]
    result = FedFalsifyDiscovery(
        clients,
        catalog,
        target_mse=max(noise_std**2 * 3.0, 1e-5),
        max_rounds=8,
        max_terms=6,
        min_repair_score=0.045,
        min_core_support_fraction=0.6,
        min_exception_support_fraction=0.8,
    ).discover()
    return BenchmarkResult(
        name="invariant-core and domain-exception discovery",
        result=result,
        expected_core_terms=("1", "x1", "sin(x2)"),
        expected_exception_terms=("I(x3>1)*x3^2",),
    )
