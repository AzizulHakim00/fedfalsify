"""Fresh SCSV-RCD v7 benchmark grammar and generators.

This module is deliberately separate from historical benchmark modules. It does
not mutate the frozen v6 grammar or any sealed historical evidence path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from .basis import BasisTerm
from .benchmarks import BenchmarkClientDataset, BenchmarkSpec, BenchmarkTermCatalog, evaluate_terms
from .scsv_v6_independent import BalanceProfile, independent_client_sizes

RoleProfile = Literal["single", "quarter", "none"]

QUADRATIC_DEV = "I(x3>1)*x3^2"
LINEAR_DEV = "I(x1>1)*x1"
TRIG_DEV = "I(x2>1)*sin(x2)"
INTERACTION_DEV = "I(x2<-1)*x1*x2"

V7_DEVIATIONS = (QUADRATIC_DEV, LINEAR_DEV, TRIG_DEV, INTERACTION_DEV)


class V7TermCatalog(BenchmarkTermCatalog):
    """Existing finite grammar plus four source-linked role deviations."""

    def __init__(self) -> None:
        super().__init__(include_exception_terms=False)
        self._terms.update(
            {
                QUADRATIC_DEV: BasisTerm(
                    QUADRATIC_DEV,
                    lambda x: np.where(x[:, 2] > 1.0, x[:, 2] ** 2, 0.0),
                    4,
                    "𝟙[x₃>1]·x₃²",
                    kind="exception",
                    validity="x3 > 1",
                    source_term="x3^2",
                ),
                LINEAR_DEV: BasisTerm(
                    LINEAR_DEV,
                    lambda x: np.where(x[:, 0] > 1.0, x[:, 0], 0.0),
                    3,
                    "𝟙[x₁>1]·x₁",
                    kind="exception",
                    validity="x1 > 1",
                    source_term="x1",
                ),
                TRIG_DEV: BasisTerm(
                    TRIG_DEV,
                    lambda x: np.where(x[:, 1] > 1.0, np.sin(x[:, 1]), 0.0),
                    4,
                    "𝟙[x₂>1]·sin(x₂)",
                    kind="exception",
                    validity="x2 > 1",
                    source_term="sin(x2)",
                ),
                INTERACTION_DEV: BasisTerm(
                    INTERACTION_DEV,
                    lambda x: np.where(x[:, 1] < -1.0, x[:, 0] * x[:, 1], 0.0),
                    5,
                    "𝟙[x₂<-1]·x₁x₂",
                    kind="exception",
                    validity="x2 < -1",
                    source_term="x1*x2",
                ),
            }
        )


def v7_catalog() -> V7TermCatalog:
    return V7TermCatalog()


V7_FAMILIES: dict[str, BenchmarkSpec] = {
    "quadratic_role": BenchmarkSpec(
        "quadratic_role",
        "Cubic/periodic shared structure with a quadratic role deviation.",
        (("x1^3", 0.8), ("sin(x2)", 1.0), ("x3^2", 0.6)),
    ),
    "linear_role": BenchmarkSpec(
        "linear_role",
        "Linear/quadratic/cosine shared structure with a linear role deviation.",
        (("x1", 1.0), ("x2^2", 0.8), ("cos(x3)", 0.7)),
    ),
    "trig_role": BenchmarkSpec(
        "trig_role",
        "Periodic/quadratic/linear shared structure with a trigonometric role deviation.",
        (("sin(x2)", 0.9), ("x1^2", 0.7), ("x3", 0.6)),
    ),
    "interaction_role": BenchmarkSpec(
        "interaction_role",
        "Interaction/quadratic/cosine shared structure with an interaction role deviation.",
        (("x1*x2", 1.0), ("x3^2", 0.7), ("cos(x1)", 0.6)),
    ),
    "null_role": BenchmarkSpec(
        "null_role",
        "Shared structure with no true role deviation and all deviation distractors exposed.",
        (("x1", 1.0), ("sin(x2)", 0.8), ("x3^2", 0.6)),
    ),
    "dual_role": BenchmarkSpec(
        "dual_role",
        "Shared structure with two non-overlapping source-linked role deviations.",
        (("x1", 0.9), ("sin(x2)", 0.7), ("x3^2", 0.6)),
    ),
}

TRUE_DEVIATIONS: dict[str, tuple[tuple[str, float], ...]] = {
    "quadratic_role": ((QUADRATIC_DEV, 0.75),),
    "linear_role": ((LINEAR_DEV, 0.70),),
    "trig_role": ((TRIG_DEV, 0.70),),
    "interaction_role": ((INTERACTION_DEV, 0.65),),
    "null_role": (),
    "dual_role": ((LINEAR_DEV, 0.60), (QUADRATIC_DEV, 0.65)),
}


@dataclass(frozen=True)
class V7GeneratedBenchmark:
    spec: BenchmarkSpec
    family: str
    clients: tuple[BenchmarkClientDataset, ...]
    target_coefficients: tuple[tuple[str, float], ...]
    true_deviations: tuple[str, ...]
    noise_std: float
    role_profile: RoleProfile
    balance_profile: BalanceProfile
    num_clients: int
    nominal_samples_per_client: int

    @property
    def target_terms(self) -> tuple[str, ...]:
        return tuple(term for term, _ in self.target_coefficients)



def _role_count(num_clients: int, profile: RoleProfile) -> int:
    if profile == "single":
        return 1
    if profile == "quarter":
        return max(1, num_clients // 4)
    if profile == "none":
        return 0
    raise ValueError(f"unknown role profile: {profile}")


def _single_role_indices(num_clients: int, profile: RoleProfile) -> set[int]:
    count = _role_count(num_clients, profile)
    return set(range(num_clients - count, num_clients)) if count else set()


def _base_draws(rng: np.random.Generator, size: int, phase: float) -> tuple[np.ndarray, ...]:
    x1 = rng.uniform(-2.8 + 0.8 * phase, 2.2 + 0.6 * phase, size=size)
    x2 = rng.uniform(-np.pi + 0.6 * phase, np.pi - 0.2 * phase, size=size)
    x3 = rng.uniform(-2.5 + 0.5 * phase, 2.3 + 0.2 * phase, size=size)
    x4 = rng.normal(0.0, 1.0, size=size)
    return x1, x2, x3, x4


def _apply_single_role_gate(
    family: str,
    *,
    eligible: bool,
    rng: np.random.Generator,
    x1: np.ndarray,
    x2: np.ndarray,
    x3: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    size = len(x1)
    if family == "quadratic_role":
        x3 = rng.uniform(1.10, 2.50, size=size) if eligible else rng.uniform(-2.50, 0.90, size=size)
    elif family == "linear_role":
        x1 = rng.uniform(1.10, 2.80, size=size) if eligible else rng.uniform(-2.80, 0.90, size=size)
    elif family == "trig_role":
        x2 = rng.uniform(1.10, np.pi, size=size) if eligible else rng.uniform(-np.pi, 0.90, size=size)
    elif family == "interaction_role":
        x2 = rng.uniform(-np.pi, -1.10, size=size) if eligible else rng.uniform(-0.90, np.pi, size=size)
    return x1, x2, x3


def generate_v7_benchmark(
    family: str,
    *,
    nominal_samples_per_client: int = 100,
    noise_ratio: float = 0.10,
    seed: int = 24101,
    num_clients: int = 4,
    balance_profile: BalanceProfile = "balanced",
    role_profile: RoleProfile = "single",
) -> V7GeneratedBenchmark:
    if family not in V7_FAMILIES:
        raise KeyError(f"unknown v7 family: {family}")
    if num_clients not in {4, 8, 16}:
        raise ValueError("v7 development supports 4, 8, or 16 clients")
    if noise_ratio not in {0.10, 0.30}:
        raise ValueError("v7 development noise must be 0.10 or 0.30")
    if family == "null_role" and role_profile != "none":
        raise ValueError("null_role requires role_profile='none'")
    if family == "dual_role":
        if role_profile != "quarter" or num_clients not in {8, 16}:
            raise ValueError("dual_role requires quarter profile with 8 or 16 clients")
    elif family != "null_role" and role_profile not in {"single", "quarter"}:
        raise ValueError("single-deviation families require single or quarter role profile")

    sizes = independent_client_sizes(
        nominal_samples_per_client,
        num_clients,
        profile=balance_profile,
        seed=seed,
    )
    spec = V7_FAMILIES[family]
    deviations = TRUE_DEVIATIONS[family]
    target_coefficients = tuple(spec.coefficients) + tuple(deviations)
    catalog = v7_catalog()
    rng = np.random.default_rng(seed)

    single_role = _single_role_indices(num_clients, role_profile) if family not in {"null_role", "dual_role"} else set()
    quarter = max(1, num_clients // 4)
    quad_role = set(range(num_clients - quarter, num_clients)) if family == "dual_role" else set()
    linear_role = set(range(num_clients - 2 * quarter, num_clients - quarter)) if family == "dual_role" else set()

    raw_x: list[np.ndarray] = []
    noiseless_targets: list[np.ndarray] = []
    for client_index, client_size in enumerate(sizes):
        phase = client_index / max(num_clients - 1, 1)
        x1, x2, x3, x4 = _base_draws(rng, client_size, phase)

        if family in {"quadratic_role", "linear_role", "trig_role", "interaction_role"}:
            x1, x2, x3 = _apply_single_role_gate(
                family,
                eligible=client_index in single_role,
                rng=rng,
                x1=x1,
                x2=x2,
                x3=x3,
            )
        elif family == "dual_role":
            # Enforce non-overlap of the two *true* role gates. Other distractor
            # gates remain observable through x2 and are not truth-labeled to the method.
            x1 = (
                rng.uniform(1.10, 2.80, size=client_size)
                if client_index in linear_role
                else rng.uniform(-2.80, 0.90, size=client_size)
            )
            x3 = (
                rng.uniform(1.10, 2.50, size=client_size)
                if client_index in quad_role
                else rng.uniform(-2.50, 0.90, size=client_size)
            )

        x = np.column_stack([x1, x2, x3, x4])
        noiseless = evaluate_terms(x, target_coefficients, catalog)
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
    return V7GeneratedBenchmark(
        spec=spec,
        family=family,
        clients=clients,
        target_coefficients=target_coefficients,
        true_deviations=tuple(term for term, _ in deviations),
        noise_std=noise_std,
        role_profile=role_profile,
        balance_profile=balance_profile,
        num_clients=num_clients,
        nominal_samples_per_client=nominal_samples_per_client,
    )


def generate_v7_global_test_data(
    generated: V7GeneratedBenchmark,
    *,
    samples: int = 4000,
    seed: int = 97001,
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
    y = evaluate_terms(x, generated.target_coefficients, v7_catalog())
    return x, y
