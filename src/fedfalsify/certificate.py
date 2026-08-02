"""Serializable aggregate protocol messages."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TermEvidence:
    """Conditional residual evidence for one inactive symbolic term."""

    term: str
    residual_inner_product: float
    term_energy: float
    residual_correlation: float
    local_slope: float
    observed_support: int


@dataclass(frozen=True)
class CoefficientEvidence:
    """Local coefficient adjustment after conditioning on the candidate model."""

    term: str
    local_adjustment: float
    standard_error: float
    z_score: float
    effective_energy: float
    observed_support: int
    estimable: bool


@dataclass(frozen=True)
class FailureRegion:
    feature: str
    bin_index: int
    lower: float
    upper: float
    mean_residual: float
    support: int


@dataclass(frozen=True)
class FalsificationCertificate:
    """Aggregated evidence; it deliberately contains no observation rows."""

    client_id: str
    candidate_id: str
    support: int
    mse: float
    mean_residual: float
    residual_energy: float
    term_evidence: tuple[TermEvidence, ...]
    coefficient_evidence: tuple[CoefficientEvidence, ...]
    worst_region: FailureRegion | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FitSummary:
    """Local normal-equation summary for fitting the current hypothesis."""

    client_id: str
    active_terms: tuple[str, ...]
    support: int
    gram: tuple[tuple[float, ...], ...]
    target: tuple[float, ...]
