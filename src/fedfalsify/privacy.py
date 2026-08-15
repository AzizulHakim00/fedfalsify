"""Certificate leakage probes and noise-budgeted ablations.

These utilities do not claim differential privacy. They quantify leave-one-out
certificate sensitivity and test whether controlled Gaussian perturbation
breaks mechanism recovery. Fit summaries remain unperturbed in the current
ablation, so the wrapper must never be described as an end-to-end private FL
protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from types import SimpleNamespace

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .certificate import (
    CoefficientEvidence,
    FailureRegion,
    FalsificationCertificate,
    TermEvidence,
)
from .client import FederatedFalsifierClient


@dataclass(frozen=True)
class SensitivityProbe:
    sampled_records: int
    median_l2_change: float
    maximum_l2_change: float
    mean_l2_change: float


def certificate_vector(certificate: FalsificationCertificate) -> np.ndarray:
    """Flatten public numeric certificate fields in a deterministic order."""

    values: list[float] = [
        float(certificate.mse),
        float(certificate.mean_residual),
        float(certificate.residual_energy / max(certificate.support, 1)),
    ]
    for item in sorted(certificate.term_evidence, key=lambda value: value.term):
        values.extend(
            [
                float(item.residual_correlation),
                float(item.local_slope),
                float(item.term_energy / max(certificate.support, 1)),
            ]
        )
    for item in sorted(
        certificate.coefficient_evidence, key=lambda value: value.term
    ):
        values.extend(
            [
                float(item.local_adjustment),
                float(min(item.standard_error, 1e6)),
                float(item.z_score),
                float(item.effective_energy / max(certificate.support, 1)),
            ]
        )
    if certificate.worst_region is None:
        values.extend([0.0, 0.0])
    else:
        values.extend(
            [
                float(certificate.worst_region.mean_residual),
                float(certificate.worst_region.support / max(certificate.support, 1)),
            ]
        )
    return np.asarray(values, dtype=float)


def leave_one_out_sensitivity(
    dataset: object,
    catalog: TermCatalog,
    candidate: CandidateEquation,
    *,
    max_records: int = 32,
    seed: int = 2026,
) -> SensitivityProbe:
    """Measure certificate change after removing one private observation."""

    x = np.asarray(dataset.x, dtype=float)
    y = np.asarray(dataset.y, dtype=float)
    if x.shape[0] < 3:
        raise ValueError("at least three records are required")
    count = min(max_records, x.shape[0])
    rng = np.random.default_rng(seed)
    indices = rng.choice(x.shape[0], size=count, replace=False)
    full_client = FederatedFalsifierClient(dataset, catalog)
    full = certificate_vector(full_client.falsify(candidate))
    changes: list[float] = []
    for index in indices:
        keep = np.ones(x.shape[0], dtype=bool)
        keep[index] = False
        view = SimpleNamespace(
            client_id=f"{dataset.client_id}-loo-{index}",
            x=x[keep],
            y=y[keep],
        )
        reduced = certificate_vector(
            FederatedFalsifierClient(view, catalog).falsify(candidate)
        )
        if reduced.shape != full.shape:
            raise RuntimeError("certificate shape changed under leave-one-out probe")
        changes.append(float(np.linalg.norm(full - reduced)))
    array = np.asarray(changes, dtype=float)
    return SensitivityProbe(
        sampled_records=count,
        median_l2_change=float(np.median(array)),
        maximum_l2_change=float(np.max(array)),
        mean_l2_change=float(np.mean(array)),
    )


def _stable_seed(base_seed: int, client_id: str, candidate_id: str) -> int:
    payload = f"{base_seed}:{client_id}:{candidate_id}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big") % (2**32)


class NoisyCertificateClient:
    """Delegate fit summaries and perturb only falsification certificates."""

    def __init__(
        self,
        client: FederatedFalsifierClient,
        *,
        noise_multiplier: float,
        clip_value: float = 10.0,
        seed: int = 2026,
    ) -> None:
        if noise_multiplier < 0:
            raise ValueError("noise_multiplier cannot be negative")
        if clip_value <= 0:
            raise ValueError("clip_value must be positive")
        self._client = client
        self.noise_multiplier = float(noise_multiplier)
        self.clip_value = float(clip_value)
        self.seed = int(seed)

    @property
    def client_id(self) -> str:
        return self._client.client_id

    def fit_summary(self, active_terms):
        return self._client.fit_summary(active_terms)

    def _noise(self, rng: np.random.Generator, scale: float = 1.0) -> float:
        return float(rng.normal(0.0, self.noise_multiplier * scale))

    def _bounded(self, value: float, *, symmetric: bool = True) -> float:
        if symmetric:
            return float(np.clip(value, -self.clip_value, self.clip_value))
        return float(np.clip(value, 0.0, self.clip_value))

    def falsify(self, candidate: CandidateEquation) -> FalsificationCertificate:
        original = self._client.falsify(candidate)
        if self.noise_multiplier == 0:
            return original
        rng = np.random.default_rng(
            _stable_seed(self.seed, original.client_id, original.candidate_id)
        )
        support_scale = 1.0 / np.sqrt(max(original.support, 1))
        term_evidence = tuple(
            TermEvidence(
                term=item.term,
                residual_inner_product=self._bounded(
                    item.residual_inner_product / max(original.support, 1)
                    + self._noise(rng, support_scale)
                )
                * original.support,
                term_energy=max(
                    0.0,
                    self._bounded(
                        item.term_energy / max(original.support, 1)
                        + self._noise(rng, support_scale),
                        symmetric=False,
                    )
                    * original.support,
                ),
                residual_correlation=float(
                    np.clip(
                        item.residual_correlation + self._noise(rng, support_scale),
                        -1.0,
                        1.0,
                    )
                ),
                local_slope=self._bounded(
                    item.local_slope + self._noise(rng, support_scale)
                ),
                observed_support=item.observed_support,
            )
            for item in original.term_evidence
        )
        coefficient_evidence = tuple(
            CoefficientEvidence(
                term=item.term,
                local_adjustment=self._bounded(
                    item.local_adjustment + self._noise(rng, support_scale)
                ),
                standard_error=max(
                    1e-12,
                    self._bounded(
                        min(item.standard_error, self.clip_value)
                        + abs(self._noise(rng, support_scale)),
                        symmetric=False,
                    ),
                ),
                z_score=self._bounded(item.z_score + self._noise(rng, support_scale)),
                effective_energy=max(
                    0.0,
                    self._bounded(
                        item.effective_energy / max(original.support, 1)
                        + self._noise(rng, support_scale),
                        symmetric=False,
                    )
                    * original.support,
                ),
                observed_support=item.observed_support,
                estimable=item.estimable,
            )
            for item in original.coefficient_evidence
        )
        worst_region = original.worst_region
        if worst_region is not None:
            worst_region = FailureRegion(
                feature=worst_region.feature,
                bin_index=worst_region.bin_index,
                lower=worst_region.lower,
                upper=worst_region.upper,
                mean_residual=self._bounded(
                    worst_region.mean_residual + self._noise(rng, support_scale)
                ),
                support=worst_region.support,
            )
        return FalsificationCertificate(
            client_id=original.client_id,
            candidate_id=original.candidate_id,
            support=original.support,
            mse=max(
                0.0,
                self._bounded(
                    original.mse + self._noise(rng, support_scale),
                    symmetric=False,
                ),
            ),
            mean_residual=self._bounded(
                original.mean_residual + self._noise(rng, support_scale)
            ),
            residual_energy=max(
                0.0,
                self._bounded(
                    original.residual_energy / max(original.support, 1)
                    + self._noise(rng, support_scale),
                    symmetric=False,
                )
                * original.support,
            ),
            term_evidence=term_evidence,
            coefficient_evidence=coefficient_evidence,
            worst_region=worst_region,
        )
