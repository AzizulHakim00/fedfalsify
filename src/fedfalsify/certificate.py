"""Serializable privacy-minimizing messages exchanged by FedFalsify clients."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TermEvidence:
    term: str
    residual_inner_product: float
    term_energy: float
    residual_correlation: float


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
