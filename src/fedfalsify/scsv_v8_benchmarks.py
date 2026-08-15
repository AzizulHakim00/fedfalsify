"""Frozen SCSV-SPCC v8 benchmark grammar.

This module is separate from v7.  It implements the preregistered finite grammar
in research/TRANSACTIONS_SCSV_SPCC_V8_PROTOCOL.md and must not be modified after
fresh v8 development evidence begins.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from .basis import BasisTerm
from .benchmarks import BenchmarkClientDataset, BenchmarkSpec, BenchmarkTermCatalog, evaluate_terms
from .scsv_v6_independent import BalanceProfile, independent_client_sizes

RoleProfile = Literal["single", "quarter", "none"]

QUADRATIC_DEV_V8 = "I(x1<-0.75)*x1^2"
LINEAR_DEV_V8 = "I(x3>0.75)*x3"
TRIG_DEV_V8 = "I(x1>0.75)*cos(x1)"
INTERACTION_DEV_V8 = "I(x2<-0.75)*x1*x2"

V8_DEVIATIONS = (
    QUADRATIC_DEV_V8,
    LINEAR_DEV_V8,
    TRIG_DEV_V8,
    INTERACTION_DEV_V8,
)


class V8TermCatalog(BenchmarkTermCatalog):
    """Existing finite grammar plus four new source-linked gated deviations."""

    def __init__(self) -> None:
        super().__init__(include_exception_terms=False)
        self._terms.update(
            {
                QUADRATIC_DEV_V8: BasisTerm(
                    QUADRATIC_DEV_V8,
                    lambda x: np.where(x[:, 0] < -0.75, x[:, 0] ** 2, 0.0),
                    4,
                    "𝟙[x₁<-0.75]·x₁²",
                    kind="exception",
                    validity="x1 < -0.75",
                    source_term="x1^2",
                ),
                LINEAR_DEV_V8: BasisTerm(
                    LINEAR_DEV_V8,
                    lambda x: np.where(x[:, 2] > 0.75, x[:, 2], 0.0),
                    3,
                    "𝟙[x₃>0.75]·x₃",
                    kind="exception",
                    validity="x3 > 0.75",
                    source_term="x3",
                ),
                TRIG_DEV_V8: BasisTerm(
                    TRIG_DEV_V8,
                    lambda x: np.where(x[:, 0] > 0.75, np.cos(x[:, 0]), 0.0),
                    4,
                    "𝟙[x₁>0.75]·cos(x₁)",
                    kind="exception",
                    validity="x1 > 0.75",
                    source_term="cos(x1)",
                ),
                INTERACTION_DEV_V8: BasisTerm(
                    INTERACTION_DEV_V8,
                    lambda x: np.where(x[:, 1] < -0.75, x[:, 0] * x[:, 1], 0.0),
                    5,
                    "𝟙[x₂<-0.75]·x₁x₂",
                    kind="exception",
                    validity="x2 < -0.75",
                    source_term="x1*x2",
                ),
            }
        )


def v8_catalog() -> V8TermCatalog:
    return V8TermCatalog()


V8_FAMILIES: dict[str, BenchmarkSpec] = {
    "quadratic_role_v8": BenchmarkSpec(
        "quadratic_role_v8",
        "New periodic/quadratic/linear shared structure with a quadratic deviation.",
        (("x1^2", 0.85), ("sin(x3)", 0.75), ("x2", 0.55)),
    ),
    "linear_role_v8": BenchmarkSpec(
        "linear_role_v8",
        "New linear/cosine/quadratic shared structure with a linear deviation.",
        (("x3", 0.90), ("cos(x1)", 0.70), ("x2^2", 0.65)),
    ),
    "trig_role_v8": BenchmarkSpec(
        "trig_role_v8",
        "New cosine/quadratic/periodic shared structure with a trigonometric deviation.",
        (("cos(x1)", 0.85), ("x3^2", 0.65), ("sin(x2)", 0.60)),
    ),
    "interaction_role_v8": BenchmarkSpec(
        "interaction_role_v8",
        "New interaction/quadratic/cosine shared structure with an interaction deviation.",
        (("x1*x2", 0.90), ("x3^2", 0.60), ("cos(x2)", 0.55)),
    ),
    "null_role_v8": BenchmarkSpec(
        "null_role_v8",
        "Source-rich null structure exposing every v8 deviation distractor.",
        (("x1^2", 0.65), ("x3", 0.60), ("cos(x1)", 0.55), ("x1*x2", 0.50)),
    ),
    "diffuse_null_v8": BenchmarkSpec(
        "diffuse_null_v8",
        "Null structure with deliberately diffuse within-client gate occupancy.",
        (("x1^2", 0.65), ("x3", 0.60), ("cos(x1)", 0.55), ("x1*x2", 0.50)),
    ),
    "dual_role_v8": BenchmarkSpec(
        "dual_role_v8",
        "Two non-overlapping source-linked deviations with distinct sources.",
        (("x1^2", 0.70), ("x3", 0.65), ("sin(x2)", 0.55)),
    ),
}

TRUE_DEVIATIONS_V8: dict[str, tuple[tuple[str, float], ...]] = {
    "quadratic_role_v8": ((QUADRATIC_DEV_V8, 0.70),),
    "linear_role_v8": ((LINEAR_DEV_V8, 0.68),),
    "trig_role_v8": ((TRIG_DEV_V8, 0.70),),
    "interaction_role_v8": ((INTERACTION_DEV_V8, 0.62),),
    "null_role_v8": (),
    "diffuse_null_v8": (),
    "dual_role_v8": ((QUADRATIC_DEV_V8, 0.62), (LINEAR_DEV_V8, 0.60)),
}

SINGLE_FAMILIES_V8 = (
    "quadratic_role_v8",
    "linear_role_v8",
    "trig_role_v8",
    "interaction_role_v8",
)


@dataclass(frozen=True)
class V8GeneratedBenchmark:
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


def _role_indices(num_clients: int, profile: RoleProfile) -> set[int]:
    count = _role_count(num_clients, profile)
    return set(range(num_clients - count, num_clients)) if count else set()


def _base_draws(rng: np.random.Generator, size: int, phase: float) -> tuple[np.ndarray, ...]:
    x1 = rng.uniform(-2.7 + 0.35 * phase, 2.7 - 0.20 * phase, size=size)
    x2 = rng.uniform(-np.pi + 0.30 * phase, np.pi - 0.15 * phase, size=size)
    x3 = rng.uniform(-2.4 + 0.25 * phase, 2.4 - 0.10 * phase, size=size)
    x4 = rng.normal(0.0, 1.0, size=size)
    return x1, x2, x3, x4


def _force_single_gate(
    family: str,
    *,
    eligible: bool,
    rng: np.random.Generator,
    size: int,
    x1: np.ndarray,
    x2: np.ndarray,
    x3: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if family == "quadratic_role_v8":
        x1 = rng.uniform(-2.8, -0.90, size=size) if eligible else rng.uniform(-0.60, 2.80, size=size)
    elif family == "linear_role_v8":
        x3 = rng.uniform(0.90, 2.50, size=size) if eligible else rng.uniform(-2.50, 0.60, size=size)
    elif family == "trig_role_v8":
        x1 = rng.uniform(0.90, 2.80, size=size) if eligible else rng.uniform(-2.80, 0.60, size=size)
    elif family == "interaction_role_v8":
        x2 = rng.uniform(-np.pi, -0.90, size=size) if eligible else rng.uniform(-0.60, np.pi, size=size)
    return x1, x2, x3


def _diffuse_null_x1(
    rng: np.random.Generator,
    size: int,
    *,
    high_fraction: float,
) -> np.ndarray:
    """Create diffuse x1 gate occupancy without a client-level role.

    high_fraction is deliberately restricted to 0.25--0.55, so the preregistered
    role gap of 0.50 cannot be satisfied merely by this stress construction.
    """

    count = int(round(size * high_fraction))
    positive = rng.uniform(0.90, 2.50, size=count)
    remainder = rng.uniform(-2.50, 0.60, size=size - count)
    values = np.concatenate([positive, remainder])
    rng.shuffle(values)
    return values


def generate_v8_benchmark(
    family: str,
    *,
    nominal_samples_per_client: int = 100,
    noise_ratio: float = 0.10,
    seed: int = 25001,
    num_clients: int = 4,
    balance_profile: BalanceProfile = "balanced",
    role_profile: RoleProfile = "single",
) -> V8GeneratedBenchmark:
    if family not in V8_FAMILIES:
        raise KeyError(f"unknown v8 family: {family}")
    if num_clients not in {4, 8, 16}:
        raise ValueError("v8 supports 4, 8, or 16 clients")
    if noise_ratio not in {0.10, 0.30}:
        raise ValueError("v8 noise must be 0.10 or 0.30")
    if family in {"null_role_v8", "diffuse_null_v8"} and role_profile != "none":
        raise ValueError("v8 null families require role_profile='none'")
    if family == "dual_role_v8":
        if role_profile != "quarter" or num_clients not in {8, 16}:
            raise ValueError("dual_role_v8 requires quarter profile with 8 or 16 clients")
    elif family in SINGLE_FAMILIES_V8:
        if role_profile not in {"single", "quarter"}:
            raise ValueError("single v8 families require single or quarter role profile")
        if num_clients == 4 and role_profile != "single":
            raise ValueError("v8 removes duplicate 4-client quarter geometry")

    sizes = independent_client_sizes(
        nominal_samples_per_client,
        num_clients,
        profile=balance_profile,
        seed=seed,
    )
    spec = V8_FAMILIES[family]
    deviations = TRUE_DEVIATIONS_V8[family]
    target_coefficients = tuple(spec.coefficients) + tuple(deviations)
    catalog = v8_catalog()
    rng = np.random.default_rng(seed)

    single_role = _role_indices(num_clients, role_profile) if family in SINGLE_FAMILIES_V8 else set()
    quarter = max(1, num_clients // 4)
    quad_role = set(range(num_clients - quarter, num_clients)) if family == "dual_role_v8" else set()
    linear_role = set(range(num_clients - 2 * quarter, num_clients - quarter)) if family == "dual_role_v8" else set()

    raw_x: list[np.ndarray] = []
    noiseless_targets: list[np.ndarray] = []
    for client_index, client_size in enumerate(sizes):
        phase = client_index / max(num_clients - 1, 1)
        x1, x2, x3, x4 = _base_draws(rng, client_size, phase)

        if family in SINGLE_FAMILIES_V8:
            x1, x2, x3 = _force_single_gate(
                family,
                eligible=client_index in single_role,
                rng=rng,
                size=client_size,
                x1=x1,
                x2=x2,
                x3=x3,
            )
        elif family == "dual_role_v8":
            # Distinct non-overlapping role sets for the quadratic and linear deviations.
            x1 = (
                rng.uniform(-2.8, -0.90, size=client_size)
                if client_index in quad_role
                else rng.uniform(-0.60, 2.80, size=client_size)
            )
            x3 = (
                rng.uniform(0.90, 2.50, size=client_size)
                if client_index in linear_role
                else rng.uniform(-2.50, 0.60, size=client_size)
            )
        elif family == "diffuse_null_v8":
            fraction = 0.25 + 0.30 * phase
            x1 = _diffuse_null_x1(rng, client_size, high_fraction=fraction)

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
    return V8GeneratedBenchmark(
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


def generate_v8_global_test_data(
    generated: V8GeneratedBenchmark,
    *,
    samples: int = 4000,
    seed: int = 98001,
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
    y = evaluate_terms(x, generated.target_coefficients, v8_catalog())
    return x, y
