"""Client-side aggregate fitting and falsification logic."""

from __future__ import annotations

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .certificate import (
    CoefficientEvidence,
    FailureRegion,
    FalsificationCertificate,
    FitSummary,
    TermEvidence,
)
from .data import ClientDataset


class FederatedFalsifierClient:
    """Simulated institution exposing only aggregate protocol messages."""

    def __init__(self, dataset: ClientDataset, catalog: TermCatalog) -> None:
        self._dataset = dataset
        self._catalog = catalog

    @property
    def client_id(self) -> str:
        return self._dataset.client_id

    @property
    def sample_count(self) -> int:
        """Return client support metadata already carried by fit summaries."""

        return int(self._dataset.x.shape[0])

    def fit_summary(self, active_terms: tuple[str, ...]) -> FitSummary:
        design = self._catalog.matrix(self._dataset.x, active_terms)
        gram = design.T @ design
        target = design.T @ self._dataset.y
        return FitSummary(
            client_id=self.client_id,
            active_terms=active_terms,
            support=self._dataset.x.shape[0],
            gram=tuple(tuple(float(value) for value in row) for row in gram),
            target=tuple(float(value) for value in target),
        )

    def falsify(self, candidate: CandidateEquation) -> FalsificationCertificate:
        prediction = candidate.predict(self._dataset.x, self._catalog)
        residual = self._dataset.y - prediction
        residual_energy = float(residual @ residual)
        inactive = {
            name for name in self._catalog.names() if name not in candidate.active_terms
        }

        term_evidence: list[TermEvidence] = []
        coefficient_evidence: list[CoefficientEvidence] = []
        for name in self._catalog.names():
            if name == "1":
                continue
            evidence, residualized = self._coefficient_evidence(candidate, residual, name)
            coefficient_evidence.append(evidence)
            if name not in inactive:
                continue
            centered_residual = residual - residual.mean()
            centered_term = residualized - residualized.mean()
            term_energy = float(centered_term @ centered_term)
            numerator = float(centered_term @ centered_residual)
            denominator = np.sqrt(
                max(term_energy * float(centered_residual @ centered_residual), 1e-24)
            )
            term_evidence.append(
                TermEvidence(
                    term=name,
                    residual_inner_product=numerator,
                    term_energy=term_energy,
                    residual_correlation=float(numerator / denominator),
                    local_slope=evidence.local_adjustment,
                    observed_support=evidence.observed_support,
                )
            )

        return FalsificationCertificate(
            client_id=self.client_id,
            candidate_id=candidate.candidate_id,
            support=self._dataset.x.shape[0],
            mse=float(np.mean(residual**2)),
            mean_residual=float(np.mean(residual)),
            residual_energy=residual_energy,
            term_evidence=tuple(term_evidence),
            coefficient_evidence=tuple(coefficient_evidence),
            worst_region=self._find_worst_region(residual),
        )

    def _coefficient_evidence(
        self,
        candidate: CandidateEquation,
        residual: np.ndarray,
        term_name: str,
    ) -> tuple[CoefficientEvidence, np.ndarray]:
        values = self._catalog.get(term_name).evaluate(self._dataset.x)
        observed_support = int(np.count_nonzero(np.abs(values) > 1e-12))
        nuisance_terms = tuple(name for name in candidate.active_terms if name != term_name)
        nuisance = self._catalog.matrix(self._dataset.x, nuisance_terms)
        gram = nuisance.T @ nuisance
        ridge = 1e-10 * np.eye(gram.shape[0])
        projection = np.linalg.pinv(gram + ridge) @ (nuisance.T @ values)
        residualized = values - nuisance @ projection
        energy = float(residualized @ residualized)
        estimable = bool(observed_support > 0 and energy > 1e-12)
        if not estimable:
            return (
                CoefficientEvidence(
                    term=term_name,
                    local_adjustment=0.0,
                    standard_error=float("inf"),
                    z_score=0.0,
                    effective_energy=energy,
                    observed_support=observed_support,
                    estimable=False,
                ),
                residualized,
            )

        adjustment = float((residualized @ residual) / energy)
        corrected_residual = residual - adjustment * residualized
        degrees_of_freedom = max(self._dataset.x.shape[0] - nuisance.shape[1] - 1, 1)
        residual_variance = float((corrected_residual @ corrected_residual) / degrees_of_freedom)
        standard_error = float(np.sqrt(max(residual_variance / max(energy, 1e-24), 0.0)))
        z_score = adjustment / max(standard_error, 1e-12)
        return (
            CoefficientEvidence(
                term=term_name,
                local_adjustment=adjustment,
                standard_error=standard_error,
                z_score=float(z_score),
                effective_energy=energy,
                observed_support=observed_support,
                estimable=True,
            ),
            residualized,
        )

    def _find_worst_region(self, residual: np.ndarray) -> FailureRegion | None:
        best: FailureRegion | None = None
        for feature_index in range(self._dataset.x.shape[1]):
            values = self._dataset.x[:, feature_index]
            edges = np.quantile(values, [0.0, 1 / 3, 2 / 3, 1.0])
            for bin_index in range(3):
                lower = float(edges[bin_index])
                upper = float(edges[bin_index + 1])
                if bin_index == 2:
                    mask = (values >= lower) & (values <= upper)
                else:
                    mask = (values >= lower) & (values < upper)
                support = int(mask.sum())
                if support == 0:
                    continue
                region = FailureRegion(
                    feature=f"x{feature_index + 1}",
                    bin_index=bin_index,
                    lower=lower,
                    upper=upper,
                    mean_residual=float(np.mean(residual[mask])),
                    support=support,
                )
                if best is None or abs(region.mean_residual) > abs(best.mean_residual):
                    best = region
        return best
