"""Server-side counterexample-guided discovery with heterogeneity certificates."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .basis import CandidateEquation, TermCatalog, TermKind
from .certificate import CoefficientEvidence, FalsificationCertificate, TermEvidence
from .client import FederatedFalsifierClient


@dataclass(frozen=True)
class RepairDecision:
    term: str | None
    score: float
    kind: TermKind | None
    observable_clients: int
    supporting_clients: int
    sign_agreement: float
    heterogeneity_score: float = 0.0
    coefficient_contrast: float = 0.0
    heterogeneity_z: float = 0.0


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
    heterogeneity_score: float = 0.0
    coefficient_contrast: float = 0.0
    heterogeneity_z: float = 0.0


@dataclass(frozen=True)
class DiscoveryResult:
    candidate: CandidateEquation
    history: tuple[RoundRecord, ...]
    certificates: tuple[FalsificationCertificate, ...]
    converged: bool
    stop_reason: str


class FedFalsifyDiscovery:
    """Counterexample-guided federated basis discovery.

    Version 0.4 adds a coefficient-shift certificate. For a gated exception,
    clients that observe the gate are compared with clients outside it using
    local conditional coefficient adjustments. A statistically strong contrast
    can prioritize the gated term over globally correlated surrogate terms.
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
        coefficient_prune_z: float = 2.5,
        use_coefficient_heterogeneity: bool = True,
        min_exception_heterogeneity_score: float = 0.20,
        heterogeneity_boost: float = 1.75,
        exception_priority_ratio: float = 0.90,
        search_slack_terms: int = 1,
    ) -> None:
        if len(clients) < 2:
            raise ValueError("Federated discovery requires at least two clients")
        if not 0 < min_core_support_fraction <= 1:
            raise ValueError("min_core_support_fraction must be in (0, 1]")
        if not 0 < min_exception_support_fraction <= 1:
            raise ValueError("min_exception_support_fraction must be in (0, 1]")
        if coefficient_prune_z < 0:
            raise ValueError("coefficient_prune_z cannot be negative")
        if search_slack_terms < 0:
            raise ValueError("search_slack_terms cannot be negative")
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
        self.coefficient_prune_z = coefficient_prune_z
        self.use_coefficient_heterogeneity = use_coefficient_heterogeneity
        self.min_exception_heterogeneity_score = min_exception_heterogeneity_score
        self.heterogeneity_boost = heterogeneity_boost
        self.exception_priority_ratio = exception_priority_ratio
        self.search_slack_terms = search_slack_terms

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

            if len(active_terms) >= self.max_terms + self.search_slack_terms:
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
                    decision.heterogeneity_score,
                    decision.coefficient_contrast,
                    decision.heterogeneity_z,
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
        final_certificates = tuple(client.falsify(final_candidate) for client in self.clients)
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
        candidate = CandidateEquation(
            active_terms,
            tuple(float(value) for value in coefficients),
            "pre-prune",
        )
        certificates = tuple(client.falsify(candidate) for client in self.clients)
        summaries = [client.fit_summary(active_terms) for client in self.clients]
        gram = sum(
            (np.asarray(summary.gram, dtype=float) for summary in summaries),
            start=np.zeros((len(active_terms), len(active_terms)), dtype=float),
        )
        total_support = sum(certificate.support for certificate in certificates)
        residual_energy = sum(certificate.residual_energy for certificate in certificates)
        variance = residual_energy / max(total_support - len(active_terms), 1)
        covariance = variance * np.linalg.pinv(
            gram + self.ridge * np.eye(len(active_terms))
        )
        standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))

        kept = tuple(
            name
            for name, coefficient, standard_error in zip(
                active_terms, coefficients, standard_errors
            )
            if name == "1"
            or (
                abs(float(coefficient)) >= self.coefficient_prune_threshold
                and abs(float(coefficient)) / max(float(standard_error), 1e-12)
                >= self.coefficient_prune_z
            )
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

        decisions = [self._score_term(term, certificates) for term in inactive]
        decisions = [decision for decision in decisions if decision.term is not None]
        if not decisions:
            return RepairDecision(None, 0.0, None, 0, 0, 0.0)

        best_core = max(
            (decision for decision in decisions if decision.kind == "core"),
            key=lambda item: item.score,
            default=None,
        )
        best_exception = max(
            (
                decision
                for decision in decisions
                if decision.kind == "exception"
                and (
                    not self.use_coefficient_heterogeneity
                    or decision.heterogeneity_score >= self.min_exception_heterogeneity_score
                )
            ),
            key=lambda item: item.score,
            default=None,
        )
        if best_exception is not None and (
            best_core is None
            or best_exception.score >= self.exception_priority_ratio * best_core.score
        ):
            return best_exception
        if best_core is not None:
            return best_core
        if best_exception is not None:
            return best_exception
        return RepairDecision(None, 0.0, None, 0, 0, 0.0)

    def _score_term(
        self,
        term: str,
        certificates: tuple[FalsificationCertificate, ...],
    ) -> RepairDecision:
        catalog_term = self.catalog.get(term)
        items = [self._term_item(certificate, term) for certificate in certificates]
        observable = [
            (certificate, item)
            for certificate, item in zip(certificates, items)
            if item.observed_support >= self.min_observed_support
            and item.term_energy > 1e-12
        ]
        if not observable:
            return RepairDecision(None, 0.0, None, 0, 0, 0.0)

        correlations = np.asarray(
            [item.residual_correlation for _, item in observable], dtype=float
        )
        weights = np.asarray(
            [float(certificate.support) for certificate, _ in observable], dtype=float
        )
        evidence_threshold = max(0.05, self.min_repair_score / 2)
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
            return RepairDecision(None, 0.0, None, 0, 0, 0.0)
        if catalog_term.kind == "core" and observable_clients < min(2, len(certificates)):
            return RepairDecision(None, 0.0, None, 0, 0, 0.0)

        supported_correlations = correlations[support_mask]
        supported_weights = weights[support_mask]
        sign_agreement = abs(
            float(np.average(np.sign(supported_correlations), weights=supported_weights))
        )
        if sign_agreement < 0.5:
            return RepairDecision(None, 0.0, None, 0, 0, 0.0)

        robust_strength = float(np.median(np.abs(supported_correlations)))
        weighted_strength = float(
            np.average(np.abs(supported_correlations), weights=supported_weights)
        )
        strength = 0.6 * robust_strength + 0.4 * weighted_strength
        complexity_penalty = 1.0 / np.sqrt(catalog_term.complexity)
        if catalog_term.kind == "core":
            observability_factor = np.sqrt(observable_clients / len(certificates))
        else:
            observability_factor = 0.75 + 0.25 * np.sqrt(
                observable_clients / len(certificates)
            )
        score = (
            strength
            * (0.5 + 0.5 * sign_agreement)
            * np.sqrt(support_fraction)
            * observability_factor
            * complexity_penalty
        )

        heterogeneity_score = 0.0
        contrast = 0.0
        heterogeneity_z = 0.0
        if (
            catalog_term.kind == "exception"
            and self.use_coefficient_heterogeneity
            and catalog_term.source_term is not None
        ):
            heterogeneity_score, contrast, heterogeneity_z = self._exception_heterogeneity(
                term, catalog_term.source_term, certificates
            )
            if heterogeneity_score < self.min_exception_heterogeneity_score:
                return RepairDecision(None, 0.0, None, 0, 0, 0.0)
            score = (
                score * (1.0 + self.heterogeneity_boost * heterogeneity_score)
                + 0.15 * heterogeneity_score
            )

        return RepairDecision(
            term,
            float(score),
            catalog_term.kind,
            observable_clients,
            supporting_clients,
            sign_agreement,
            heterogeneity_score,
            contrast,
            heterogeneity_z,
        )

    def _exception_heterogeneity(
        self,
        exception_term: str,
        source_term: str,
        certificates: tuple[FalsificationCertificate, ...],
    ) -> tuple[float, float, float]:
        gate: list[CoefficientEvidence] = []
        outside: list[CoefficientEvidence] = []
        for certificate in certificates:
            gate_item = self._coefficient_item(certificate, exception_term)
            source_item = self._coefficient_item(certificate, source_term)
            if not source_item.estimable:
                continue
            if gate_item.observed_support >= self.min_observed_support:
                gate.append(source_item)
            else:
                outside.append(source_item)
        if not gate or not outside:
            return 0.0, 0.0, 0.0

        gate_values = np.asarray([item.local_adjustment for item in gate], dtype=float)
        outside_values = np.asarray([item.local_adjustment for item in outside], dtype=float)
        gate_center = float(np.median(gate_values))
        outside_center = float(np.median(outside_values))
        contrast = gate_center - outside_center

        outside_mad = 1.4826 * float(
            np.median(np.abs(outside_values - outside_center))
        )
        gate_error = float(np.median([item.standard_error for item in gate]))
        outside_error = float(np.median([item.standard_error for item in outside]))
        uncertainty = np.sqrt(
            max(gate_error**2 + outside_error**2 + outside_mad**2, 1e-24)
        )
        heterogeneity_z = abs(contrast) / uncertainty
        sign_agreement = abs(float(np.mean(np.sign(gate_values - outside_center))))
        relative_effect = abs(contrast) / max(
            abs(outside_center) + outside_mad + outside_error, 1e-12
        )
        z_saturation = 1.0 - np.exp(-heterogeneity_z / 3.0)
        effect_saturation = 1.0 - np.exp(-relative_effect / 2.0)
        gate_coverage = 0.75 + 0.25 * np.sqrt(len(gate) / max(len(certificates), 1))
        score = z_saturation * effect_saturation * sign_agreement * gate_coverage
        return float(score), float(contrast), float(heterogeneity_z)

    @staticmethod
    def _term_item(certificate: FalsificationCertificate, term: str) -> TermEvidence:
        return next(item for item in certificate.term_evidence if item.term == term)

    @staticmethod
    def _coefficient_item(
        certificate: FalsificationCertificate, term: str
    ) -> CoefficientEvidence:
        return next(item for item in certificate.coefficient_evidence if item.term == term)
