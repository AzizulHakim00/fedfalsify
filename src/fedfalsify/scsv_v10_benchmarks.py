"""Frozen SCSV-AQCC v10 benchmark grammar and generators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from .basis import BasisTerm
from .benchmarks import BenchmarkClientDataset, BenchmarkSpec, BenchmarkTermCatalog, evaluate_terms
from .scsv_v6_independent import BalanceProfile, independent_client_sizes

RoleProfile = Literal["single", "quarter", "none"]

QUADRATIC_DEV_V10 = "I(x3<-0.90)*x3^2"
LINEAR_DEV_V10 = "I(x1<-0.90)*x1"
TRIG_DEV_V10 = "I(x2>0.90)*cos(x2)"
INTERACTION_DEV_V10 = "I(x2>0.90)*x1*x2"
WEAK_SOURCE_DEV_V10 = "I(x4<-0.90)*x4^2"

V10_DEVIATIONS = (
    QUADRATIC_DEV_V10,
    LINEAR_DEV_V10,
    TRIG_DEV_V10,
    INTERACTION_DEV_V10,
    WEAK_SOURCE_DEV_V10,
)


class V10TermCatalog(BenchmarkTermCatalog):
    """Finite v10 grammar with rotated source-linked role deviations."""

    def __init__(self) -> None:
        super().__init__(include_exception_terms=False)
        self._terms.update(
            {
                QUADRATIC_DEV_V10: BasisTerm(
                    QUADRATIC_DEV_V10,
                    lambda x: np.where(x[:, 2] < -0.90, x[:, 2] ** 2, 0.0),
                    4,
                    "1[x3<-0.90]*x3^2",
                    kind="exception",
                    validity="x3 < -0.90",
                    source_term="x3^2",
                ),
                LINEAR_DEV_V10: BasisTerm(
                    LINEAR_DEV_V10,
                    lambda x: np.where(x[:, 0] < -0.90, x[:, 0], 0.0),
                    3,
                    "1[x1<-0.90]*x1",
                    kind="exception",
                    validity="x1 < -0.90",
                    source_term="x1",
                ),
                TRIG_DEV_V10: BasisTerm(
                    TRIG_DEV_V10,
                    lambda x: np.where(x[:, 1] > 0.90, np.cos(x[:, 1]), 0.0),
                    4,
                    "1[x2>0.90]*cos(x2)",
                    kind="exception",
                    validity="x2 > 0.90",
                    source_term="cos(x2)",
                ),
                INTERACTION_DEV_V10: BasisTerm(
                    INTERACTION_DEV_V10,
                    lambda x: np.where(x[:, 1] > 0.90, x[:, 0] * x[:, 1], 0.0),
                    5,
                    "1[x2>0.90]*x1*x2",
                    kind="exception",
                    validity="x2 > 0.90",
                    source_term="x1*x2",
                ),
                WEAK_SOURCE_DEV_V10: BasisTerm(
                    WEAK_SOURCE_DEV_V10,
                    lambda x: np.where(x[:, 3] < -0.90, x[:, 3] ** 2, 0.0),
                    4,
                    "1[x4<-0.90]*x4^2",
                    kind="exception",
                    validity="x4 < -0.90",
                    source_term="x4^2",
                ),
            }
        )


def v10_catalog() -> V10TermCatalog:
    return V10TermCatalog()


V10_FAMILIES: dict[str, BenchmarkSpec] = {
    "quadratic_role_v10": BenchmarkSpec(
        "quadratic_role_v10",
        "Quadratic x3-squared source with a negative-x3 role deviation.",
        (("x3^2", 0.86), ("sin(x2)", 0.72), ("x1", 0.56)),
    ),
    "linear_role_v10": BenchmarkSpec(
        "linear_role_v10",
        "Linear x1 source with a negative-x1 role deviation.",
        (("x1", 0.90), ("cos(x2)", 0.70), ("x4^2", 0.62)),
    ),
    "trig_role_v10": BenchmarkSpec(
        "trig_role_v10",
        "Cosine source with a positive-x2 role deviation.",
        (("cos(x2)", 0.86), ("x3^2", 0.64), ("x1", 0.58)),
    ),
    "interaction_role_v10": BenchmarkSpec(
        "interaction_role_v10",
        "Bilinear x1*x2 source with a positive-x2 role deviation.",
        (("x1*x2", 0.90), ("x3^2", 0.60), ("sin(x1)", 0.54)),
    ),
    "null_role_v10": BenchmarkSpec(
        "null_role_v10",
        "Source-rich null exposing every v10 exception distractor.",
        (("x3^2", 0.62), ("x1", 0.58), ("cos(x2)", 0.54), ("x1*x2", 0.50), ("x4^2", 0.22)),
    ),
    "anchor_contamination_null_v10": BenchmarkSpec(
        "anchor_contamination_null_v10",
        "Role-shaped x4 support but no x4-squared coefficient deviation; tests inherited exception quarantine.",
        (("x3^2", 0.62), ("x1", 0.58), ("cos(x2)", 0.54), ("x1*x2", 0.50), ("x4^2", 0.22)),
    ),
    "weak_source_role_v10": BenchmarkSpec(
        "weak_source_role_v10",
        "Weak shared x4-squared source with a stronger negative-x4 gated deviation.",
        (("x4^2", 0.25), ("sin(x2)", 0.65), ("x1", 0.55)),
    ),
    "dual_role_v10": BenchmarkSpec(
        "dual_role_v10",
        "Two non-overlapping role deviations with distinct x3-squared and x1 sources.",
        (("x3^2", 0.70), ("x1", 0.66), ("cos(x2)", 0.55)),
    ),
}

TRUE_DEVIATIONS_V10: dict[str, tuple[tuple[str, float], ...]] = {
    "quadratic_role_v10": ((QUADRATIC_DEV_V10, 0.70),),
    "linear_role_v10": ((LINEAR_DEV_V10, 0.68),),
    "trig_role_v10": ((TRIG_DEV_V10, 0.70),),
    "interaction_role_v10": ((INTERACTION_DEV_V10, 0.62),),
    "null_role_v10": (),
    "anchor_contamination_null_v10": (),
    "weak_source_role_v10": ((WEAK_SOURCE_DEV_V10, 0.75),),
    "dual_role_v10": ((QUADRATIC_DEV_V10, 0.62), (LINEAR_DEV_V10, 0.60)),
}

SINGLE_FAMILIES_V10 = (
    "quadratic_role_v10",
    "linear_role_v10",
    "trig_role_v10",
    "interaction_role_v10",
)


@dataclass(frozen=True)
class V10GeneratedBenchmark:
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
    raise ValueError(f"unknown v10 role profile: {profile}")


def _role_indices(num_clients: int, profile: RoleProfile) -> set[int]:
    count = _role_count(num_clients, profile)
    return set(range(num_clients - count, num_clients)) if count else set()


def _base_draws(rng: np.random.Generator, size: int, phase: float) -> tuple[np.ndarray, ...]:
    x1 = rng.uniform(-2.8 + 0.25 * phase, 2.7 - 0.15 * phase, size=size)
    x2 = rng.uniform(-np.pi + 0.20 * phase, np.pi - 0.15 * phase, size=size)
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
    if family == "quadratic_role_v10":
        x3 = rng.uniform(-2.6, -1.00, size=size) if eligible else rng.uniform(-0.70, 2.6, size=size)
    elif family == "linear_role_v10":
        x1 = rng.uniform(-2.8, -1.00, size=size) if eligible else rng.uniform(-0.70, 2.8, size=size)
    elif family in {"trig_role_v10", "interaction_role_v10"}:
        x2 = rng.uniform(1.00, np.pi, size=size) if eligible else rng.uniform(-np.pi, 0.70, size=size)
    return x1, x2, x3, x4


def generate_v10_benchmark(
    family: str,
    *,
    nominal_samples_per_client: int = 100,
    noise_ratio: float = 0.10,
    seed: int = 28001,
    num_clients: int = 4,
    balance_profile: BalanceProfile = "balanced",
    role_profile: RoleProfile = "single",
) -> V10GeneratedBenchmark:
    if family not in V10_FAMILIES:
        raise KeyError(f"unknown v10 family: {family}")
    if num_clients not in {4, 8, 16}:
        raise ValueError("v10 supports 4, 8, or 16 clients")
    if noise_ratio not in {0.10, 0.30}:
        raise ValueError("v10 noise must be 0.10 or 0.30")
    if family in {"null_role_v10", "anchor_contamination_null_v10"} and role_profile != "none":
        raise ValueError("v10 null families require role_profile='none'")
    if family in {"weak_source_role_v10", "dual_role_v10"}:
        if role_profile != "quarter" or num_clients not in {8, 16}:
            raise ValueError(f"{family} requires quarter role with 8 or 16 clients")
    elif family in SINGLE_FAMILIES_V10:
        if role_profile not in {"single", "quarter"}:
            raise ValueError("v10 single families require single or quarter role")
        if num_clients == 4 and role_profile != "single":
            raise ValueError("v10 removes duplicate 4-client quarter geometry")

    sizes = independent_client_sizes(
        nominal_samples_per_client,
        num_clients,
        profile=balance_profile,
        seed=seed,
    )
    spec = V10_FAMILIES[family]
    deviations = TRUE_DEVIATIONS_V10[family]
    target_coefficients = tuple(spec.coefficients) + tuple(deviations)
    catalog = v10_catalog()
    rng = np.random.default_rng(seed)

    single_role = _role_indices(num_clients, role_profile) if family in SINGLE_FAMILIES_V10 else set()
    quarter = max(1, num_clients // 4)
    last_quarter = set(range(num_clients - quarter, num_clients))
    prior_quarter = set(range(num_clients - 2 * quarter, num_clients - quarter))

    raw_x: list[np.ndarray] = []
    noiseless_targets: list[np.ndarray] = []
    for client_index, client_size in enumerate(sizes):
        phase = client_index / max(num_clients - 1, 1)
        x1, x2, x3, x4 = _base_draws(rng, client_size, phase)

        if family in SINGLE_FAMILIES_V10:
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
        elif family == "weak_source_role_v10":
            x4 = (
                rng.uniform(-2.6, -1.00, size=client_size)
                if client_index in last_quarter
                else rng.uniform(-0.70, 2.6, size=client_size)
            )
        elif family == "dual_role_v10":
            x3 = (
                rng.uniform(-2.6, -1.00, size=client_size)
                if client_index in last_quarter
                else rng.uniform(-0.70, 2.6, size=client_size)
            )
            x1 = (
                rng.uniform(-2.8, -1.00, size=client_size)
                if client_index in prior_quarter
                else rng.uniform(-0.70, 2.8, size=client_size)
            )
        elif family == "anchor_contamination_null_v10":
            x4 = (
                rng.uniform(-2.6, -1.00, size=client_size)
                if client_index in last_quarter
                else rng.uniform(-0.70, 2.6, size=client_size)
            )

        x = np.column_stack([x1, x2, x3, x4])
        noiseless = evaluate_terms(x, target_coefficients, catalog)
        raw_x.append(x)
        noiseless_targets.append(noiseless)

    pooled_scale = max(float(np.std(np.concatenate(noiseless_targets))), 1e-12)
    noise_std = noise_ratio * pooled_scale
    clients = tuple(
        BenchmarkClientDataset(
            f"client-{index + 1}",
            x,
            noiseless + rng.normal(0.0, noise_std, size=x.shape[0]),
        )
        for index, (x, noiseless) in enumerate(zip(raw_x, noiseless_targets))
    )
    return V10GeneratedBenchmark(
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


def generate_v10_global_test_data(
    generated: V10GeneratedBenchmark,
    *,
    samples: int = 4000,
    seed: int = 128001,
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
    y = evaluate_terms(x, generated.target_coefficients, v10_catalog())
    return x, y
