"""Preregistered finite-grammar benchmarks for mechanism-discovery experiments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from .basis import BasisTerm, TermCatalog

Scenario = Literal["complementary", "spurious", "exception"]


@dataclass(frozen=True)
class BenchmarkSpec:
    name: str
    description: str
    coefficients: tuple[tuple[str, float], ...]

    @property
    def target_terms(self) -> tuple[str, ...]:
        return tuple(term for term, _ in self.coefficients)


@dataclass(frozen=True)
class BenchmarkClientDataset:
    client_id: str
    x: np.ndarray
    y: np.ndarray


class BenchmarkTermCatalog(TermCatalog):
    """Research-only extension of the frozen v0.2 finite grammar."""

    def __init__(self, *, include_exception_terms: bool = False) -> None:
        super().__init__(include_exception_terms=include_exception_terms)
        self._terms.update(
            {
                "x1^3": BasisTerm("x1^3", lambda x: x[:, 0] ** 3, 3, "x₁³"),
                "x1*x2": BasisTerm("x1*x2", lambda x: x[:, 0] * x[:, 1], 2, "x₁x₂"),
                "sin(x1+x1^2)": BasisTerm(
                    "sin(x1+x1^2)",
                    lambda x: np.sin(x[:, 0] + x[:, 0] ** 2),
                    4,
                    "sin(x₁+x₁²)",
                ),
                "sin(x1)*cos(x2)": BasisTerm(
                    "sin(x1)*cos(x2)",
                    lambda x: np.sin(x[:, 0]) * np.cos(x[:, 1]),
                    4,
                    "sin(x₁)cos(x₂)",
                ),
                "x4": BasisTerm("x4", lambda x: x[:, 3], 1, "x₄"),
                "x4^2": BasisTerm("x4^2", lambda x: x[:, 3] ** 2, 2, "x₄²"),
            }
        )


@dataclass(frozen=True)
class GeneratedBenchmark:
    spec: BenchmarkSpec
    scenario: Scenario
    clients: tuple[BenchmarkClientDataset, ...]
    target_coefficients: tuple[tuple[str, float], ...]
    noise_std: float

    @property
    def target_terms(self) -> tuple[str, ...]:
        return tuple(term for term, _ in self.target_coefficients)


BENCHMARKS: dict[str, BenchmarkSpec] = {
    "base": BenchmarkSpec(
        "base",
        "Mixed linear, periodic and quadratic mechanism.",
        (("x1", 2.0), ("sin(x2)", 1.0), ("x3^2", 0.5)),
    ),
    "poly3": BenchmarkSpec(
        "poly3",
        "Third-order univariate polynomial.",
        (("x1", 1.0), ("x1^2", 1.0), ("x1^3", 1.0)),
    ),
    "nested_sine": BenchmarkSpec(
        "nested_sine",
        "Two periodic components including a composite phase.",
        (("sin(x1)", 1.0), ("sin(x1+x1^2)", 1.0)),
    ),
    "trig_product": BenchmarkSpec(
        "trig_product",
        "Multiplicative trigonometric interaction.",
        (("sin(x1)*cos(x2)", 2.0),),
    ),
    "interaction": BenchmarkSpec(
        "interaction",
        "Bilinear interaction plus quadratic effect.",
        (("x1*x2", 1.0), ("x3^2", 0.5)),
    ),
}


def benchmark_catalog(*, scenario: Scenario) -> TermCatalog:
    return BenchmarkTermCatalog(include_exception_terms=scenario == "exception")


def evaluate_terms(
    x: np.ndarray,
    coefficients: tuple[tuple[str, float], ...],
    catalog: TermCatalog,
) -> np.ndarray:
    y = np.zeros(x.shape[0], dtype=float)
    for term, coefficient in coefficients:
        y += coefficient * catalog.get(term).evaluate(x)
    return y


def generate_benchmark(
    name: str,
    *,
    scenario: Scenario = "complementary",
    samples_per_client: int = 300,
    noise_ratio: float = 0.03,
    seed: int = 2026,
    num_clients: int = 4,
) -> GeneratedBenchmark:
    if name not in BENCHMARKS:
        raise KeyError(f"Unknown benchmark: {name}")
    if scenario not in {"complementary", "spurious", "exception"}:
        raise ValueError(f"Unknown scenario: {scenario}")
    if num_clients < 3:
        raise ValueError("Use at least three clients")
    if samples_per_client < 50:
        raise ValueError("Use at least 50 samples per client")
    if noise_ratio < 0:
        raise ValueError("noise_ratio cannot be negative")

    spec = BENCHMARKS[name]
    catalog = benchmark_catalog(scenario=scenario)
    target = list(spec.coefficients)
    if scenario == "exception":
        target.append(("I(x3>1)*x3^2", 0.75))
    target_coefficients = tuple(target)
    rng = np.random.default_rng(seed)

    raw_x: list[np.ndarray] = []
    noiseless_targets: list[np.ndarray] = []
    for client_index in range(num_clients):
        phase = client_index / max(num_clients - 1, 1)
        if scenario == "exception" and client_index == num_clients - 1:
            x3 = rng.uniform(1.05, 2.5, size=samples_per_client)
        elif scenario == "exception":
            x3 = rng.uniform(-2.5 + 0.3 * phase, 0.95, size=samples_per_client)
        else:
            x3 = rng.uniform(-2.5 + phase, 1.5 + phase, size=samples_per_client)
        x1 = rng.uniform(-2.8 + 1.4 * phase, 1.0 + 2.0 * phase, size=samples_per_client)
        x2 = rng.uniform(-np.pi + 1.2 * phase, 0.6 + (np.pi - 0.6) * phase, size=samples_per_client)
        x4 = rng.normal(0.0, 1.0, size=samples_per_client)
        x = np.column_stack([x1, x2, x3, x4])
        noiseless = evaluate_terms(x, target_coefficients, catalog)
        if scenario == "spurious" and client_index == 0:
            standardized = (noiseless - noiseless.mean()) / max(noiseless.std(), 1e-12)
            x[:, 3] = standardized + rng.normal(0.0, 0.03, size=samples_per_client)
        raw_x.append(x)
        noiseless_targets.append(noiseless)

    pooled_scale = max(float(np.std(np.concatenate(noiseless_targets))), 1e-12)
    noise_std = noise_ratio * pooled_scale
    clients = tuple(
        BenchmarkClientDataset(
            f"client-{index + 1}",
            x,
            noiseless + rng.normal(0.0, noise_std, size=samples_per_client),
        )
        for index, (x, noiseless) in enumerate(zip(raw_x, noiseless_targets))
    )
    return GeneratedBenchmark(spec, scenario, clients, target_coefficients, noise_std)


def generate_global_test_data(
    generated: GeneratedBenchmark,
    *,
    samples: int = 4000,
    seed: int = 9001,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = np.column_stack(
        [
            rng.uniform(-3.0, 3.0, size=samples),
            rng.uniform(-np.pi, np.pi, size=samples),
            rng.uniform(-2.5, 2.5, size=samples),
            rng.normal(0.0, 1.0, size=samples),
        ]
    )
    catalog = benchmark_catalog(scenario=generated.scenario)
    y = evaluate_terms(x, generated.target_coefficients, catalog)
    return x, y


# Backward-compatible v0.2 benchmark entry points used by the demo and tests.
from .client import FederatedFalsifierClient
from .data import generate_exception_clients, generate_spurious_correlation_clients
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
