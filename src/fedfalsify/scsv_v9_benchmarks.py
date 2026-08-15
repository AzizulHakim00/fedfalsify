"""Frozen SCSV-RCEF v9 benchmark grammar and generators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from .basis import BasisTerm
from .benchmarks import BenchmarkClientDataset, BenchmarkSpec, BenchmarkTermCatalog, evaluate_terms
from .scsv_v6_independent import BalanceProfile, independent_client_sizes

RoleProfile = Literal["single", "quarter", "none"]

QUADRATIC_DEV_V9 = "I(x2>0.85)*x2^2"
LINEAR_DEV_V9 = "I(x4<-0.85)*x4"
TRIG_DEV_V9 = "I(x3<-0.85)*sin(x3)"
INTERACTION_DEV_V9 = "I(x1>0.85)*x1*x3"
WEAK_SOURCE_DEV_V9 = "I(x4>0.85)*x4^2"

V9_DEVIATIONS = (
    QUADRATIC_DEV_V9,
    LINEAR_DEV_V9,
    TRIG_DEV_V9,
    INTERACTION_DEV_V9,
    WEAK_SOURCE_DEV_V9,
)


class V9TermCatalog(BenchmarkTermCatalog):
    """Finite v9 grammar with new source-linked role deviations."""

    def __init__(self) -> None:
        super().__init__(include_exception_terms=False)
        self._terms.update(
            {
                "x1*x3": BasisTerm("x1*x3", lambda x: x[:, 0] * x[:, 2], 2, "x₁x₃"),
                QUADRATIC_DEV_V9: BasisTerm(
                    QUADRATIC_DEV_V9,
                    lambda x: np.where(x[:, 1] > 0.85, x[:, 1] ** 2, 0.0),
                    4,
                    "𝟙[x₂>0.85]·x₂²",
                    kind="exception",
                    validity="x2 > 0.85",
                    source_term="x2^2",
                ),
                LINEAR_DEV_V9: BasisTerm(
                    LINEAR_DEV_V9,
                    lambda x: np.where(x[:, 3] < -0.85, x[:, 3], 0.0),
                    3,
                    "𝟙[x₄<-0.85]·x₄",
                    kind="exception",
                    validity="x4 < -0.85",
                    source_term="x4",
                ),
                TRIG_DEV_V9: BasisTerm(
                    TRIG_DEV_V9,
                    lambda x: np.where(x[:, 2] < -0.85, np.sin(x[:, 2]), 0.0),
                    4,
                    "𝟙[x₃<-0.85]·sin(x₃)",
                    kind="exception",
                    validity="x3 < -0.85",
                    source_term="sin(x3)",
                ),
                INTERACTION_DEV_V9: BasisTerm(
                    INTERACTION_DEV_V9,
                    lambda x: np.where(x[:, 0] > 0.85, x[:, 0] * x[:, 2], 0.0),
                    5,
                    "𝟙[x₁>0.85]·x₁x₃",
                    kind="exception",
                    validity="x1 > 0.85",
                    source_term="x1*x3",
                ),
                WEAK_SOURCE_DEV_V9: BasisTerm(
                    WEAK_SOURCE_DEV_V9,
                    lambda x: np.where(x[:, 3] > 0.85, x[:, 3] ** 2, 0.0),
                    4,
                    "𝟙[x₄>0.85]·x₄²",
                    kind="exception",
                    validity="x4 > 0.85",
                    source_term="x4^2",
                ),
            }
        )


def v9_catalog() -> V9TermCatalog:
    return V9TermCatalog()


V9_FAMILIES: dict[str, BenchmarkSpec] = {
    "quadratic_role_v9": BenchmarkSpec(
        "quadratic_role_v9",
        "Quadratic source with a positive-x2 role deviation.",
        (("x2^2", 0.85), ("sin(x3)", 0.75), ("x1", 0.55)),
    ),
    "linear_role_v9": BenchmarkSpec(
        "linear_role_v9",
        "Linear x4 source with a negative-x4 role deviation.",
        (("x4", 0.90), ("cos(x2)", 0.70), ("x1^2", 0.65)),
    ),
    "trig_role_v9": BenchmarkSpec(
        "trig_role_v9",
        "Trigonometric source with a negative-x3 role deviation.",
        (("sin(x3)", 0.85), ("x1^2", 0.65), ("cos(x2)", 0.60)),
    ),
    "interaction_role_v9": BenchmarkSpec(
        "interaction_role_v9",
        "Interaction source with a positive-x1 role deviation.",
        (("x1*x3", 0.90), ("x2^2", 0.60), ("cos(x1)", 0.55)),
    ),
    "null_role_v9": BenchmarkSpec(
        "null_role_v9",
        "Source-rich null exposing every v9 deviation distractor.",
        (("x2^2", 0.62), ("x4", 0.58), ("sin(x3)", 0.54), ("x1*x3", 0.50), ("x4^2", 0.22)),
    ),
    "diffuse_null_v9": BenchmarkSpec(
        "diffuse_null_v9",
        "Diffuse-gate null without a true client-level role deviation.",
        (("x2^2", 0.62), ("x4", 0.58), ("sin(x3)", 0.54), ("x1*x3", 0.50), ("x4^2", 0.22)),
    ),
    "weak_source_role_v9": BenchmarkSpec(
        "weak_source_role_v9",
        "Weak shared x4-squared source with a stronger gated deviation.",
        (("x4^2", 0.25), ("sin(x2)", 0.65), ("x1", 0.55)),
    ),
    "dual_role_v9": BenchmarkSpec(
        "dual_role_v9",
        "Two non-overlapping role deviations with distinct sources.",
        (("x2^2", 0.70), ("x4", 0.65), ("sin(x3)", 0.55)),
    ),
}

TRUE_DEVIATIONS_V9: dict[str, tuple[tuple[str, float], ...]] = {
    "quadratic_role_v9": ((QUADRATIC_DEV_V9, 0.70),),
    "linear_role_v9": ((LINEAR_DEV_V9, 0.68),),
    "trig_role_v9": ((TRIG_DEV_V9, 0.70),),
    "interaction_role_v9": ((INTERACTION_DEV_V9, 0.62),),
    "null_role_v9": (),
    "diffuse_null_v9": (),
    "weak_source_role_v9": ((WEAK_SOURCE_DEV_V9, 0.75),),
    "dual_role_v9": ((QUADRATIC_DEV_V9, 0.62), (LINEAR_DEV_V9, 0.60)),
}

SINGLE_FAMILIES_V9 = (
    "quadratic_role_v9",
    "linear_role_v9",
    "trig_role_v9",
    "interaction_role_v9",
)


@dataclass(frozen=True)
class V9GeneratedBenchmark:
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
    raise ValueError(f"unknown v9 role profile: {profile}")


def _role_indices(num_clients: int, profile: RoleProfile) -> set[int]:
    count = _role_count(num_clients, profile)
    return set(range(num_clients - count, num_clients)) if count else set()


def _base_draws(rng: np.random.Generator, size: int, phase: float) -> tuple[np.ndarray, ...]:
    x1 = rng.uniform(-2.8 + 0.30 * phase, 2.7 - 0.15 * phase, size=size)
    x2 = rng.uniform(-np.pi + 0.25 * phase, np.pi - 0.15 * phase, size=size)
    x3 = rng.uniform(-2.6 + 0.20 * phase, 2.5 - 0.10 * phase, size=size)
    x4 = rng.uniform(-2.5 + 0.15 * phase, 2.5 - 0.10 * phase, size=size)
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
    x4: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if family == "quadratic_role_v9":
        x2 = rng.uniform(0.95, np.pi, size=size) if eligible else rng.uniform(-np.pi, 0.65, size=size)
    elif family == "linear_role_v9":
        x4 = rng.uniform(-2.6, -0.95, size=size) if eligible else rng.uniform(-0.65, 2.6, size=size)
    elif family == "trig_role_v9":
        x3 = rng.uniform(-2.6, -0.95, size=size) if eligible else rng.uniform(-0.65, 2.6, size=size)
    elif family == "interaction_role_v9":
        x1 = rng.uniform(0.95, 2.8, size=size) if eligible else rng.uniform(-2.8, 0.65, size=size)
    return x1, x2, x3, x4


def _shuffle_mix(rng: np.random.Generator, active: np.ndarray, inactive: np.ndarray) -> np.ndarray:
    values = np.concatenate([active, inactive])
    rng.shuffle(values)
    return values


def _diffuse_null_draws(
    rng: np.random.Generator,
    size: int,
    phase: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    frac = 0.30 + 0.15 * phase
    count = int(round(size * frac))
    x1 = _shuffle_mix(
        rng,
        rng.uniform(0.95, 2.5, size=count),
        rng.uniform(-2.5, 0.65, size=size - count),
    )
    x2 = _shuffle_mix(
        rng,
        rng.uniform(0.95, np.pi, size=count),
        rng.uniform(-np.pi, 0.65, size=size - count),
    )
    x3 = _shuffle_mix(
        rng,
        rng.uniform(-2.5, -0.95, size=count),
        rng.uniform(-0.65, 2.5, size=size - count),
    )
    neg_count = int(round(size * 0.30))
    pos_count = int(round(size * 0.30))
    neutral_count = size - neg_count - pos_count
    x4 = np.concatenate(
        [
            rng.uniform(-2.5, -0.95, size=neg_count),
            rng.uniform(0.95, 2.5, size=pos_count),
            rng.uniform(-0.65, 0.65, size=neutral_count),
        ]
    )
    rng.shuffle(x4)
    return x1, x2, x3, x4


def generate_v9_benchmark(
    family: str,
    *,
    nominal_samples_per_client: int = 100,
    noise_ratio: float = 0.10,
    seed: int = 26001,
    num_clients: int = 4,
    balance_profile: BalanceProfile = "balanced",
    role_profile: RoleProfile = "single",
) -> V9GeneratedBenchmark:
    if family not in V9_FAMILIES:
        raise KeyError(f"unknown v9 family: {family}")
    if num_clients not in {4, 8, 16}:
        raise ValueError("v9 supports 4, 8, or 16 clients")
    if noise_ratio not in {0.10, 0.30}:
        raise ValueError("v9 noise must be 0.10 or 0.30")
    if family in {"null_role_v9", "diffuse_null_v9"} and role_profile != "none":
        raise ValueError("v9 null families require role_profile='none'")
    if family in {"weak_source_role_v9", "dual_role_v9"}:
        if role_profile != "quarter" or num_clients not in {8, 16}:
            raise ValueError(f"{family} requires quarter role with 8 or 16 clients")
    elif family in SINGLE_FAMILIES_V9:
        if role_profile not in {"single", "quarter"}:
            raise ValueError("v9 single families require single or quarter role")
        if num_clients == 4 and role_profile != "single":
            raise ValueError("v9 removes duplicate 4-client quarter geometry")

    sizes = independent_client_sizes(
        nominal_samples_per_client,
        num_clients,
        profile=balance_profile,
        seed=seed,
    )
    spec = V9_FAMILIES[family]
    deviations = TRUE_DEVIATIONS_V9[family]
    target_coefficients = tuple(spec.coefficients) + tuple(deviations)
    catalog = v9_catalog()
    rng = np.random.default_rng(seed)

    single_role = _role_indices(num_clients, role_profile) if family in SINGLE_FAMILIES_V9 else set()
    quarter = max(1, num_clients // 4)
    last_quarter = set(range(num_clients - quarter, num_clients))
    prior_quarter = set(range(num_clients - 2 * quarter, num_clients - quarter))

    raw_x: list[np.ndarray] = []
    noiseless_targets: list[np.ndarray] = []
    for client_index, client_size in enumerate(sizes):
        phase = client_index / max(num_clients - 1, 1)
        x1, x2, x3, x4 = _base_draws(rng, client_size, phase)

        if family in SINGLE_FAMILIES_V9:
            x1, x2, x3, x4 = _force_single_gate(
                family,
                eligible=client_index in single_role,
                rng=rng,
                size=client_size,
                x1=x1,
                x2=x2,
                x3=x3,
                x4=x4,
            )
        elif family == "weak_source_role_v9":
            x4 = (
                rng.uniform(0.95, 2.6, size=client_size)
                if client_index in last_quarter
                else rng.uniform(-2.6, 0.65, size=client_size)
            )
        elif family == "dual_role_v9":
            x2 = (
                rng.uniform(0.95, np.pi, size=client_size)
                if client_index in last_quarter
                else rng.uniform(-np.pi, 0.65, size=client_size)
            )
            x4 = (
                rng.uniform(-2.6, -0.95, size=client_size)
                if client_index in prior_quarter
                else rng.uniform(-0.65, 2.6, size=client_size)
            )
        elif family == "diffuse_null_v9":
            x1, x2, x3, x4 = _diffuse_null_draws(rng, client_size, phase)

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
    return V9GeneratedBenchmark(
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


def generate_v9_global_test_data(
    generated: V9GeneratedBenchmark,
    *,
    samples: int = 4000,
    seed: int = 99001,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = np.column_stack(
        [
            rng.uniform(-3.0, 3.0, size=samples),
            rng.uniform(-np.pi, np.pi, size=samples),
            rng.uniform(-2.7, 2.7, size=samples),
            rng.uniform(-2.7, 2.7, size=samples),
        ]
    )
    y = evaluate_terms(x, generated.target_coefficients, v9_catalog())
    return x, y
