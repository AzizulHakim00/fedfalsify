"""Client-side fitting and falsification logic."""

from __future__ import annotations

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .certificate import FailureRegion, FalsificationCertificate, FitSummary, TermEvidence
from .data import ClientDataset


class FederatedFalsifierClient:
    """Simulated private institution exposing only aggregate protocol messages."""

    def __init__(self, dataset: ClientDataset, catalog: TermCatalog) -> None:
        self._dataset = dataset
        self._catalog = catalog

    @property
    def client_id(self) -> str:
        return self._dataset.client_id

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
        inactive = [
            name for name in self._catalog.names() if name not in candidate.active_terms
        ]

        evidence: list[TermEvidence] = []
        centered_residual = residual - residual.mean()
        centered_residual_energy = float(centered_residual @ centered_residual)
        for name in inactive:
            values = self._catalog.get(name).evaluate(self._dataset.x)
            observed_support = int(np.count_nonzero(np.abs(values) > 1e-12))
            centered_values = values - values.mean()
            term_energy = float(centered_values @ centered_values)
            numerator = float(centered_values @ centered_residual)
            denominator = np.sqrt(max(term_energy * centered_residual_energy, 1e-24))
            correlation = float(numerator / denominator)
            local_slope = float(numerator / max(term_energy, 1e-24))
            evidence.append(
                TermEvidence(
                    term=name,
                    residual_inner_product=numerator,
                    term_energy=term_energy,
                    residual_correlation=correlation,
                    local_slope=local_slope,
                    observed_support=observed_support,
                )
            )

        return FalsificationCertificate(
            client_id=self.client_id,
            candidate_id=candidate.candidate_id,
            support=self._dataset.x.shape[0],
            mse=float(np.mean(residual**2)),
            mean_residual=float(np.mean(residual)),
            residual_energy=residual_energy,
            term_evidence=tuple(evidence),
            worst_region=self._find_worst_region(residual),
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
                mean_residual = float(np.mean(residual[mask]))
                region = FailureRegion(
                    feature=f"x{feature_index + 1}",
                    bin_index=bin_index,
                    lower=lower,
                    upper=upper,
                    mean_residual=mean_residual,
                    support=support,
                )
                if best is None or abs(region.mean_residual) > abs(best.mean_residual):
                    best = region
        return best
