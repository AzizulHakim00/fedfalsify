"""Federated post-search replacement of correlated core surrogates.

The v0.4 discovery loop can select a correlated basis term before the true core
term.  This module adds a conservative post-search stage that tests one-for-one
and two-for-one structural replacements using only aggregate fit summaries and
client falsification certificates.

The procedure is deliberately separated from the v0.4 search so that the older
method remains an executable ablation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
import json

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .certificate import CoefficientEvidence, FalsificationCertificate
from .client import FederatedFalsifierClient


@dataclass(frozen=True)
class ReplacementCertificate:
    """Aggregate evidence supporting one structural replacement."""

    removed_terms: tuple[str, ...]
    added_term: str
    objective_before: float
    objective_after: float
    objective_gain: float
    improved_client_fraction: float
    nonworsening_client_fraction: float
    incoming_support_fraction: float
    incoming_sign_agreement: float
    incoming_global_z: float


@dataclass(frozen=True)
class CoreReplacementResult:
    """Final refined candidate and the accepted replacement ledger."""

    candidate: CandidateEquation
    replacements: tuple[ReplacementCertificate, ...]
    communication_bytes: int
    stop_reason: str


@dataclass(frozen=True)
class _CandidateStats:
    candidate: CandidateEquation
    certificates: tuple[FalsificationCertificate, ...]
    weighted_mse: float
    worst_client_mse: float
    objective: float
    global_z: dict[str, float]


class FederatedCoreReplacement:
    """Replace active correlated surrogates with better-supported core terms.

    Every proposal removes one or two active core terms and inserts one inactive
    core term.  The server refits the proposed structure from federated normal
    equations, then requires:

    * a prespecified robust-objective improvement;
    * improvement on a declared fraction of clients;
    * no material degradation for most clients; and
    * cross-client coefficient support for the incoming term.

    No observation row is transferred, although repeated aggregate queries may
    increase privacy leakage and communication cost.  This is not a privacy
    guarantee.
    """

    def __init__(
        self,
        clients: list[FederatedFalsifierClient],
        catalog: TermCatalog,
        *,
        ridge: float = 1e-8,
        max_rounds: int = 3,
        max_removed_terms: int = 2,
        min_objective_gain: float = 0.015,
        min_improved_client_fraction: float = 0.50,
        min_nonworsening_client_fraction: float = 0.75,
        client_worsening_tolerance: float = 0.02,
        min_incoming_support_fraction: float = 0.50,
        min_incoming_sign_agreement: float = 0.50,
        min_incoming_local_z: float = 1.96,
        min_incoming_global_z: float = 2.50,
        worst_client_weight: float = 0.20,
        complexity_weight: float = 1.0,
        coefficient_prune_threshold: float = 1e-3,
        coefficient_prune_z: float = 2.50,
    ) -> None:
        if len(clients) < 2:
            raise ValueError("Core replacement requires at least two clients")
        if max_rounds < 0:
            raise ValueError("max_rounds cannot be negative")
        if max_removed_terms not in {1, 2}:
            raise ValueError("max_removed_terms must be 1 or 2")
        for value, name in (
            (min_improved_client_fraction, "min_improved_client_fraction"),
            (min_nonworsening_client_fraction, "min_nonworsening_client_fraction"),
            (min_incoming_support_fraction, "min_incoming_support_fraction"),
            (min_incoming_sign_agreement, "min_incoming_sign_agreement"),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0, 1]")
        self.clients = clients
        self.catalog = catalog
        self.ridge = ridge
        self.max_rounds = max_rounds
        self.max_removed_terms = max_removed_terms
        self.min_objective_gain = min_objective_gain
        self.min_improved_client_fraction = min_improved_client_fraction
        self.min_nonworsening_client_fraction = min_nonworsening_client_fraction
        self.client_worsening_tolerance = client_worsening_tolerance
        self.min_incoming_support_fraction = min_incoming_support_fraction
        self.min_incoming_sign_agreement = min_incoming_sign_agreement
        self.min_incoming_local_z = min_incoming_local_z
        self.min_incoming_global_z = min_incoming_global_z
        self.worst_client_weight = worst_client_weight
        self.complexity_weight = complexity_weight
        self.coefficient_prune_threshold = coefficient_prune_threshold
        self.coefficient_prune_z = coefficient_prune_z

    def refine(self, candidate: CandidateEquation) -> CoreReplacementResult:
        current, fit_bytes = self._fit_and_prune(candidate.active_terms, "replacement-start")
        communication_bytes = fit_bytes
        current_stats, stats_bytes = self._stats(current)
        communication_bytes += stats_bytes
        accepted: list[ReplacementCertificate] = []
        stop_reason = "maximum replacement rounds reached"

        for round_index in range(1, self.max_rounds + 1):
            decision: tuple[
                float,
                CandidateEquation,
                _CandidateStats,
                ReplacementCertificate,
                int,
            ] | None = None

            protected_sources = {
                self.catalog.get(name).source_term
                for name in current.active_terms
                if self.catalog.get(name).kind == "exception"
                and self.catalog.get(name).source_term is not None
            }
            removable = tuple(
                name
                for name in current.active_terms
                if name != "1"
                and self.catalog.get(name).kind == "core"
                and name not in protected_sources
            )
            inactive = tuple(
                name
                for name in self.catalog.names()
                if name not in current.active_terms
                and name != "1"
                and self.catalog.get(name).kind == "core"
            )

            if not removable or not inactive:
                stop_reason = "no eligible core replacement"
                break

            for added_term in inactive:
                support_fraction, sign_agreement = self._incoming_support(
                    current_stats.certificates, added_term
                )
                if support_fraction < self.min_incoming_support_fraction:
                    continue
                if sign_agreement < self.min_incoming_sign_agreement:
                    continue

                for remove_count in range(
                    1, min(self.max_removed_terms, len(removable)) + 1
                ):
                    for removed_terms in combinations(removable, remove_count):
                        proposed_terms = tuple(
                            name
                            for name in current.active_terms
                            if name not in removed_terms
                        ) + (added_term,)
                        proposed, proposal_fit_bytes = self._fit_and_prune(
                            proposed_terms, f"replacement-{round_index}"
                        )
                        communication_bytes += proposal_fit_bytes
                        if added_term not in proposed.active_terms:
                            continue

                        proposed_stats, proposal_stats_bytes = self._stats(proposed)
                        communication_bytes += proposal_stats_bytes
                        incoming_global_z = proposed_stats.global_z.get(added_term, 0.0)
                        if incoming_global_z < self.min_incoming_global_z:
                            continue

                        current_losses = np.asarray(
                            [item.mse for item in current_stats.certificates], dtype=float
                        )
                        proposed_losses = np.asarray(
                            [item.mse for item in proposed_stats.certificates], dtype=float
                        )
                        improved_fraction = float(
                            np.mean(proposed_losses < current_losses * 0.99)
                        )
                        nonworsening_fraction = float(
                            np.mean(
                                proposed_losses
                                <= current_losses * (1.0 + self.client_worsening_tolerance)
                            )
                        )
                        objective_gain = current_stats.objective - proposed_stats.objective
                        if objective_gain < self.min_objective_gain:
                            continue
                        if improved_fraction < self.min_improved_client_fraction:
                            continue
                        if (
                            nonworsening_fraction
                            < self.min_nonworsening_client_fraction
                        ):
                            continue

                        certificate = ReplacementCertificate(
                            removed_terms=tuple(removed_terms),
                            added_term=added_term,
                            objective_before=current_stats.objective,
                            objective_after=proposed_stats.objective,
                            objective_gain=objective_gain,
                            improved_client_fraction=improved_fraction,
                            nonworsening_client_fraction=nonworsening_fraction,
                            incoming_support_fraction=support_fraction,
                            incoming_sign_agreement=sign_agreement,
                            incoming_global_z=incoming_global_z,
                        )
                        ranking_score = (
                            objective_gain
                            + 0.05 * improved_fraction
                            + 0.02 * nonworsening_fraction
                            + 0.002 * min(incoming_global_z, 20.0)
                        )
                        if decision is None or ranking_score > decision[0]:
                            decision = (
                                ranking_score,
                                proposed,
                                proposed_stats,
                                certificate,
                                proposal_fit_bytes + proposal_stats_bytes,
                            )

            if decision is None:
                stop_reason = "no replacement passed the federated certificate"
                break
            _, current, current_stats, certificate, _ = decision
            accepted.append(certificate)
        else:
            stop_reason = "maximum replacement rounds reached"

        final, final_fit_bytes = self._fit_and_prune(
            current.active_terms, "replacement-final"
        )
        communication_bytes += final_fit_bytes
        return CoreReplacementResult(
            candidate=final,
            replacements=tuple(accepted),
            communication_bytes=communication_bytes,
            stop_reason=stop_reason,
        )

    def _fit_and_prune(
        self, active_terms: tuple[str, ...], candidate_id: str
    ) -> tuple[CandidateEquation, int]:
        candidate, gram, support, communication = self._fit(active_terms, candidate_id)
        certificates = tuple(client.falsify(candidate) for client in self.clients)
        communication += self._certificate_bytes(certificates)
        residual_energy = sum(item.residual_energy for item in certificates)
        variance = residual_energy / max(support - len(active_terms), 1)
        covariance = variance * np.linalg.pinv(
            gram + self.ridge * np.eye(len(active_terms))
        )
        standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))
        kept = tuple(
            name
            for name, coefficient, standard_error in zip(
                candidate.active_terms, candidate.coefficients, standard_errors
            )
            if name == "1"
            or (
                abs(float(coefficient)) >= self.coefficient_prune_threshold
                and abs(float(coefficient)) / max(float(standard_error), 1e-12)
                >= self.coefficient_prune_z
            )
        )
        if kept == candidate.active_terms:
            return candidate, communication
        refitted, _, _, extra = self._fit(kept, candidate_id)
        return refitted, communication + extra

    def _fit(
        self, active_terms: tuple[str, ...], candidate_id: str
    ) -> tuple[CandidateEquation, np.ndarray, int, int]:
        summaries = [client.fit_summary(active_terms) for client in self.clients]
        size = len(active_terms)
        gram = np.zeros((size, size), dtype=float)
        target = np.zeros(size, dtype=float)
        support = 0
        communication = 0
        for summary in summaries:
            gram += np.asarray(summary.gram, dtype=float)
            target += np.asarray(summary.target, dtype=float)
            support += summary.support
            communication += len(
                json.dumps(asdict(summary), separators=(",", ":")).encode("utf-8")
            )
        regularizer = self.ridge * np.eye(size)
        regularizer[0, 0] = 0.0
        try:
            coefficients = np.linalg.solve(gram + regularizer, target)
        except np.linalg.LinAlgError:
            coefficients = np.linalg.pinv(gram + regularizer) @ target
        return (
            CandidateEquation(
                active_terms,
                tuple(float(value) for value in coefficients),
                candidate_id,
            ),
            gram,
            support,
            communication,
        )

    def _stats(self, candidate: CandidateEquation) -> tuple[_CandidateStats, int]:
        certificates = tuple(client.falsify(candidate) for client in self.clients)
        total_support = sum(item.support for item in certificates)
        weighted_mse = sum(
            item.mse * item.support for item in certificates
        ) / total_support
        worst_client_mse = max(item.mse for item in certificates)
        complexity = self.catalog.complexity(candidate.active_terms)
        objective = (
            np.log(max(weighted_mse, 1e-15))
            + self.worst_client_weight * np.log(max(worst_client_mse, 1e-15))
            + self.complexity_weight
            * complexity
            * np.log(max(total_support, 2))
            / total_support
        )

        summaries = [
            client.fit_summary(candidate.active_terms) for client in self.clients
        ]
        gram = sum(
            (np.asarray(item.gram, dtype=float) for item in summaries),
            start=np.zeros(
                (len(candidate.active_terms), len(candidate.active_terms)), dtype=float
            ),
        )
        residual_energy = sum(item.residual_energy for item in certificates)
        variance = residual_energy / max(
            total_support - len(candidate.active_terms), 1
        )
        covariance = variance * np.linalg.pinv(
            gram + self.ridge * np.eye(len(candidate.active_terms))
        )
        standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0.0))
        global_z = {
            name: abs(float(coefficient)) / max(float(standard_error), 1e-12)
            for name, coefficient, standard_error in zip(
                candidate.active_terms, candidate.coefficients, standard_errors
            )
        }
        communication = self._certificate_bytes(certificates) + sum(
            len(json.dumps(asdict(item), separators=(",", ":")).encode("utf-8"))
            for item in summaries
        )
        return (
            _CandidateStats(
                candidate,
                certificates,
                float(weighted_mse),
                float(worst_client_mse),
                float(objective),
                global_z,
            ),
            communication,
        )

    def _incoming_support(
        self,
        certificates: tuple[FalsificationCertificate, ...],
        term: str,
    ) -> tuple[float, float]:
        evidence: list[CoefficientEvidence] = []
        for certificate in certificates:
            item = next(
                candidate
                for candidate in certificate.coefficient_evidence
                if candidate.term == term
            )
            if item.estimable:
                evidence.append(item)
        if not evidence:
            return 0.0, 0.0
        supported = [
            item for item in evidence if abs(item.z_score) >= self.min_incoming_local_z
        ]
        if not supported:
            return 0.0, 0.0
        support_fraction = len(supported) / len(evidence)
        sign_agreement = abs(float(np.mean(np.sign([item.z_score for item in supported]))))
        return float(support_fraction), float(sign_agreement)

    @staticmethod
    def _certificate_bytes(
        certificates: tuple[FalsificationCertificate, ...]
    ) -> int:
        return sum(
            len(json.dumps(item.to_dict(), separators=(",", ":")).encode("utf-8"))
            for item in certificates
        )
