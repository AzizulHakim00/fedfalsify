"""Server-side counterexample-guided discovery loop."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .certificate import FalsificationCertificate
from .client import FederatedFalsifierClient


@dataclass(frozen=True)
class RoundRecord:
    round_index: int
    candidate: CandidateEquation
    weighted_mse: float
    worst_client_mse: float
    selected_repair: str | None
    repair_score: float | None


@dataclass(frozen=True)
class DiscoveryResult:
    candidate: CandidateEquation
    history: tuple[RoundRecord, ...]
    certificates: tuple[FalsificationCertificate, ...]
    converged: bool
    stop_reason: str


class FedFalsifyDiscovery:
    """Minimum viable counterexample-guided federated discovery algorithm."""

    def __init__(
        self,
        clients: list[FederatedFalsifierClient],
        catalog: TermCatalog | None = None,
        *,
        ridge: float = 1e-8,
        min_repair_score: float = 0.08,
        target_mse: float = 0.003,
        max_rounds: int = 8,
        max_terms: int = 6,
    ) -> None:
        if len(clients) < 2:
            raise ValueError("Federated discovery requires at least two clients")
        self.clients = clients
        self.catalog = catalog or TermCatalog()
        self.ridge = ridge
        self.min_repair_score = min_repair_score
        self.target_mse = target_mse
        self.max_rounds = max_rounds
        self.max_terms = max_terms

    def discover(self) -> DiscoveryResult:
        active_terms: tuple[str, ...] = ("1",)
        history: list[RoundRecord] = []
        final_certificates: tuple[FalsificationCertificate, ...] = ()
        converged = False
        stop_reason = "maximum rounds reached"

        for round_index in range(1, self.max_rounds + 1):
            coefficients = self._fit_coefficients(active_terms)
            candidate = CandidateEquation(
                active_terms=active_terms,
                coefficients=tuple(float(value) for value in coefficients),
                candidate_id=f"round-{round_index}",
            )
            certificates = tuple(client.falsify(candidate) for client in self.clients)
            final_certificates = certificates
            weighted_mse = self._weighted_mse(certificates)
            worst_client_mse = max(certificate.mse for certificate in certificates)

            if weighted_mse <= self.target_mse:
                history.append(
                    RoundRecord(
                        round_index,
                        candidate,
                        weighted_mse,
                        worst_client_mse,
                        None,
                        None,
                    )
                )
                converged = True
                stop_reason = "target federated MSE reached"
                break

            if len(active_terms) >= self.max_terms:
                history.append(
                    RoundRecord(
                        round_index,
                        candidate,
                        weighted_mse,
                        worst_client_mse,
                        None,
                        None,
                    )
                )
                stop_reason = "maximum symbolic complexity reached"
                break

            repair_term, repair_score = self._select_repair(certificates, active_terms)
            history.append(
                RoundRecord(
                    round_index,
                    candidate,
                    weighted_mse,
                    worst_client_mse,
                    repair_term,
                    repair_score,
                )
            )
            if repair_term is None or repair_score < self.min_repair_score:
                stop_reason = "no sufficiently supported counterexample repair"
                break
            active_terms = active_terms + (repair_term,)

        final_coefficients = self._fit_coefficients(active_terms)
        final_candidate = CandidateEquation(
            active_terms=active_terms,
            coefficients=tuple(float(value) for value in final_coefficients),
            candidate_id="final",
        )
        final_certificates = tuple(
            client.falsify(final_candidate) for client in self.clients
        )
        if self._weighted_mse(final_certificates) <= self.target_mse:
            converged = True
            if stop_reason == "maximum rounds reached":
                stop_reason = "target federated MSE reached after final refit"

        return DiscoveryResult(
            candidate=final_candidate,
            history=tuple(history),
            certificates=final_certificates,
            converged=converged,
            stop_reason=stop_reason,
        )

    def _fit_coefficients(self, active_terms: tuple[str, ...]) -> np.ndarray:
        summaries = [client.fit_summary(active_terms) for client in self.clients]
        size = len(active_terms)
        gram = np.zeros((size, size), dtype=float)
        target = np.zeros(size, dtype=float)
        for summary in summaries:
            if summary.active_terms != active_terms:
                raise RuntimeError("Client returned a summary for the wrong hypothesis")
            gram += np.asarray(summary.gram, dtype=float)
            target += np.asarray(summary.target, dtype=float)
        regularizer = self.ridge * np.eye(size)
        regularizer[0, 0] = 0.0
        try:
            return np.linalg.solve(gram + regularizer, target)
        except np.linalg.LinAlgError:
            return np.linalg.pinv(gram + regularizer) @ target

    @staticmethod
    def _weighted_mse(certificates: tuple[FalsificationCertificate, ...]) -> float:
        total = sum(certificate.support for certificate in certificates)
        return sum(
            certificate.mse * certificate.support for certificate in certificates
        ) / total

    def _select_repair(
        self,
        certificates: tuple[FalsificationCertificate, ...],
        active_terms: tuple[str, ...],
    ) -> tuple[str | None, float]:
        inactive = [name for name in self.catalog.names() if name not in active_terms]
        if not inactive:
            return None, 0.0

        best_term: str | None = None
        best_score = 0.0
        total_clients = len(certificates)
        for term in inactive:
            correlations: list[float] = []
            weights: list[float] = []
            for certificate in certificates:
                item = next(
                    evidence
                    for evidence in certificate.term_evidence
                    if evidence.term == term
                )
                correlations.append(item.residual_correlation)
                weights.append(float(certificate.support))

            correlations_array = np.asarray(correlations)
            weights_array = np.asarray(weights)
            weighted_abs = float(
                np.average(np.abs(correlations_array), weights=weights_array)
            )
            signed_consensus = float(
                abs(np.average(np.sign(correlations_array), weights=weights_array))
            )
            supporting_clients = int(
                np.sum(np.abs(correlations_array) >= self.min_repair_score / 2)
            )
            support_fraction = supporting_clients / total_clients
            complexity_penalty = 1.0 / np.sqrt(self.catalog.get(term).complexity)
            score = (
                weighted_abs
                * (0.5 + 0.5 * signed_consensus)
                * np.sqrt(support_fraction)
                * complexity_penalty
            )
            if score > best_score:
                best_score = score
                best_term = term
        return best_term, best_score
