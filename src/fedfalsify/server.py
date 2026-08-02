"""Server-side counterexample-guided discovery loop."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .basis import CandidateEquation, TermCatalog, TermKind
from .certificate import FalsificationCertificate, TermEvidence
from .client import FederatedFalsifierClient


@dataclass(frozen=True)
class RepairDecision:
    term: str | None
    score: float
    kind: TermKind | None
    observable_clients: int
    supporting_clients: int
    sign_agreement: float


@dataclass(frozen=True)
class RoundRecord:
    round_index: int
    candidate: CandidateEquation
    weighted_mse: float
    worst_client_mse: float
    selected_repair: str | None
    repair_score: float | None
    repair_kind: TermKind | None = None
    observable_clients: int = 0
    supporting_clients: int = 0


@dataclass(frozen=True)
class DiscoveryResult:
    candidate: CandidateEquation
    history: tuple[RoundRecord, ...]
    certificates: tuple[FalsificationCertificate, ...]
    converged: bool
    stop_reason: str


class FedFalsifyDiscovery:
    """Counterexample-guided federated basis discovery.

    Core terms require cross-client support. A domain-gated exception can be
    selected when all clients that actually observe its validity region agree,
    while clients outside that region are treated as unable to falsify it.
    """

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
        min_core_support_fraction: float = 0.6,
        min_exception_support_fraction: float = 0.8,
        min_observed_support: int = 20,
        coefficient_prune_threshold: float = 1e-3,
    ) -> None:
        if len(clients) < 2:
            raise ValueError("Federated discovery requires at least two clients")
        if not 0 < min_core_support_fraction <= 1:
            raise ValueError("min_core_support_fraction must be in (0, 1]")
        if not 0 < min_exception_support_fraction <= 1:
            raise ValueError("min_exception_support_fraction must be in (0, 1]")
        self.clients = clients
        self.catalog = catalog or TermCatalog()
        self.ridge = ridge
        self.min_repair_score = min_repair_score
        self.target_mse = target_mse
        self.max_rounds = max_rounds
        self.max_terms = max_terms
        self.min_core_support_fraction = min_core_support_fraction
        self.min_exception_support_fraction = min_exception_support_fraction
        self.min_observed_support = min_observed_support
        self.coefficient_prune_threshold = coefficient_prune_threshold

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

            decision = self._select_repair(certificates, active_terms)
            history.append(
                RoundRecord(
                    round_index,
                    candidate,
                    weighted_mse,
                    worst_client_mse,
                    decision.term,
                    decision.score,
                    decision.kind,
                    decision.observable_clients,
                    decision.supporting_clients,
                )
            )
            if decision.term is None or decision.score < self.min_repair_score:
                stop_reason = "no sufficiently supported counterexample repair"
                break
            active_terms = active_terms + (decision.term,)

        final_coefficients = self._fit_coefficients(active_terms)
        active_terms, final_coefficients = self._prune_negligible_terms(
            active_terms, final_coefficients
        )
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

    def _prune_negligible_terms(
        self, active_terms: tuple[str, ...], coefficients: np.ndarray
    ) -> tuple[tuple[str, ...], np.ndarray]:
        kept = tuple(
            name
            for name, coefficient in zip(active_terms, coefficients)
            if name == "1" or abs(float(coefficient)) >= self.coefficient_prune_threshold
        )
        if kept == active_terms:
            return active_terms, coefficients
        return kept, self._fit_coefficients(kept)

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
    ) -> RepairDecision:
        inactive = [name for name in self.catalog.names() if name not in active_terms]
        if not inactive:
            return RepairDecision(None, 0.0, None, 0, 0, 0.0)

        best = RepairDecision(None, 0.0, None, 0, 0, 0.0)
        total_clients = len(certificates)
        evidence_threshold = max(0.05, self.min_repair_score / 2)

        for term in inactive:
            catalog_term = self.catalog.get(term)
            items = [self._term_item(certificate, term) for certificate in certificates]
            observable = [
                (certificate, item)
                for certificate, item in zip(certificates, items)
                if item.observed_support >= self.min_observed_support
                and item.term_energy > 1e-12
            ]
            if not observable:
                continue

            correlations = np.asarray(
                [item.residual_correlation for _, item in observable], dtype=float
            )
            weights = np.asarray(
                [float(certificate.support) for certificate, _ in observable], dtype=float
            )
            support_mask = np.abs(correlations) >= evidence_threshold
            supporting_clients = int(np.sum(support_mask))
            observable_clients = len(observable)
            support_fraction = supporting_clients / observable_clients
            required_fraction = (
                self.min_exception_support_fraction
                if catalog_term.kind == "exception"
                else self.min_core_support_fraction
            )
            if support_fraction < required_fraction:
                continue
            if catalog_term.kind == "core" and observable_clients < min(2, total_clients):
                continue

            supported_correlations = correlations[support_mask]
            supported_weights = weights[support_mask]
            signed_mean = float(
                np.average(np.sign(supported_correlations), weights=supported_weights)
            )
            sign_agreement = abs(signed_mean)
            if sign_agreement < 0.5:
                continue

            robust_strength = float(np.median(np.abs(supported_correlations)))
            weighted_strength = float(
                np.average(np.abs(supported_correlations), weights=supported_weights)
            )
            strength = 0.6 * robust_strength + 0.4 * weighted_strength
            complexity_penalty = 1.0 / np.sqrt(catalog_term.complexity)

            if catalog_term.kind == "core":
                observability_factor = np.sqrt(observable_clients / total_clients)
            else:
                # A restricted-domain term can be provisionally discovered from
                # one observing client, but receives a confidence discount.
                observability_factor = 0.75 + 0.25 * np.sqrt(
                    observable_clients / total_clients
                )

            score = (
                strength
                * (0.5 + 0.5 * sign_agreement)
                * np.sqrt(support_fraction)
                * observability_factor
                * complexity_penalty
            )
            if score > best.score:
                best = RepairDecision(
                    term,
                    score,
                    catalog_term.kind,
                    observable_clients,
                    supporting_clients,
                    sign_agreement,
                )
        return best

    @staticmethod
    def _term_item(
        certificate: FalsificationCertificate, term: str
    ) -> TermEvidence:
        return next(item for item in certificate.term_evidence if item.term == term)
