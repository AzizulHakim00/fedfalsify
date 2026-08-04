"""Theory-aligned cross-fitted certificate redesign.

This module is intentionally separate from the frozen legacy implementation.
It uses aggregate-only messages, deterministic local sample separation, and a
validation-governed continuation rule. Existing confirmatory and external
artifacts therefore remain reproducible.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from time import perf_counter
from typing import Iterable, Sequence

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .baselines import fit_federated, score_only_federated
from .client import FederatedFalsifierClient
from .external_common import ExternalClientData
from .server import DiscoveryResult, FedFalsifyDiscovery


@dataclass(frozen=True)
class PartitionedClient:
    """Disjoint local partitions used by the redesign."""

    client_id: str
    fold_a: ExternalClientData
    fold_b: ExternalClientData
    validation: ExternalClientData
    full: ExternalClientData

    @property
    def discovery(self) -> ExternalClientData:
        return ExternalClientData(
            self.client_id,
            np.concatenate([self.fold_a.x, self.fold_b.x], axis=0),
            np.concatenate([self.fold_a.y, self.fold_b.y], axis=0),
        )


class SplitFederatedFalsifierClient:
    """Fit on one local partition and certify on a disjoint partition."""

    def __init__(
        self,
        fit_dataset: ExternalClientData,
        certificate_dataset: ExternalClientData,
        catalog: TermCatalog,
    ) -> None:
        if fit_dataset.client_id != certificate_dataset.client_id:
            raise ValueError("fit and certificate partitions must share a client id")
        self._fit = FederatedFalsifierClient(fit_dataset, catalog)
        self._certificate = FederatedFalsifierClient(certificate_dataset, catalog)

    @property
    def client_id(self) -> str:
        return self._fit.client_id

    @property
    def sample_count(self) -> int:
        return self._fit.sample_count

    def fit_summary(self, active_terms: tuple[str, ...]):
        return self._fit.fit_summary(active_terms)

    def falsify(self, candidate: CandidateEquation):
        return self._certificate.falsify(candidate)


@dataclass(frozen=True)
class ValidationProfile:
    source: str
    weighted_mse: float
    worst_client_mse: float
    information_score: float
    complexity: int
    support: int
    client_mse: tuple[tuple[str, float], ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RedesignOutput:
    method: str
    candidate: CandidateEquation
    direction_a_terms: tuple[str, ...]
    direction_b_terms: tuple[str, ...]
    consensus_terms: tuple[str, ...]
    selected_source: str
    fallback_selected: bool
    validation_profile: ValidationProfile
    validation_profiles: tuple[ValidationProfile, ...]
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _stable_client_seed(seed: int, client_id: str) -> int:
    digest = hashlib.sha256(f"{seed}:{client_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def partition_clients(
    datasets: Sequence[object],
    *,
    seed: int,
    validation_fraction: float = 0.20,
) -> tuple[PartitionedClient, ...]:
    """Create deterministic 40/40/20 local partitions.

    The returned partitions are disjoint and exhaustive. This helper is for the
    i.i.d. synthetic development matrix; natural temporal datasets must keep
    their chronological partitions.
    """

    if not 0.10 <= validation_fraction <= 0.40:
        raise ValueError("validation_fraction must be between 0.10 and 0.40")
    materialized = tuple(datasets)
    if len(materialized) < 2:
        raise ValueError("cross-fitting requires at least two clients")

    output: list[PartitionedClient] = []
    for dataset in materialized:
        client_id = str(dataset.client_id)
        x = np.asarray(dataset.x, dtype=float)
        y = np.asarray(dataset.y, dtype=float)
        if x.ndim != 2 or y.ndim != 1 or len(x) != len(y):
            raise ValueError("client arrays have incompatible shapes")
        if len(y) < 50:
            raise ValueError("cross-fit development clients need at least 50 rows")

        rng = np.random.default_rng(_stable_client_seed(seed, client_id))
        order = rng.permutation(len(y))
        validation_count = max(10, int(round(validation_fraction * len(y))))
        discovery_count = len(y) - validation_count
        fold_a_count = discovery_count // 2
        fold_b_count = discovery_count - fold_a_count
        if min(validation_count, fold_a_count, fold_b_count) < 10:
            raise ValueError("every local partition needs at least 10 observations")

        validation_indices = order[:validation_count]
        fold_a_indices = order[validation_count : validation_count + fold_a_count]
        fold_b_indices = order[validation_count + fold_a_count :]

        def subset(indices: np.ndarray) -> ExternalClientData:
            return ExternalClientData(client_id, x[indices], y[indices])

        output.append(
            PartitionedClient(
                client_id=client_id,
                fold_a=subset(fold_a_indices),
                fold_b=subset(fold_b_indices),
                validation=subset(validation_indices),
                full=ExternalClientData(client_id, x, y),
            )
        )
    return tuple(output)


def _payload_bytes(value: object) -> int:
    if hasattr(value, "to_dict"):
        payload = value.to_dict()
    else:
        payload = asdict(value)  # type: ignore[arg-type]
    return len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))


def _discovery_communication(
    result: DiscoveryResult,
    clients: Sequence[SplitFederatedFalsifierClient],
) -> int:
    total = 0
    for record in result.history:
        for client in clients:
            total += _payload_bytes(client.fit_summary(record.candidate.active_terms))
            total += _payload_bytes(client.falsify(record.candidate))
    return total


def _run_direction(
    clients: list[SplitFederatedFalsifierClient],
    catalog: TermCatalog,
    *,
    max_terms: int,
    target_mse: float,
    min_repair_score: float,
) -> tuple[DiscoveryResult, int]:
    result = FedFalsifyDiscovery(
        clients,  # type: ignore[arg-type]
        catalog,
        max_rounds=max_terms + 2,
        max_terms=max_terms,
        target_mse=target_mse,
        min_repair_score=min_repair_score,
        use_coefficient_heterogeneity=True,
    ).discover()
    return result, _discovery_communication(result, clients)


def _nonzero_terms(
    candidate: CandidateEquation, *, threshold: float = 1e-3
) -> set[str]:
    return {
        term
        for term, coefficient in zip(candidate.active_terms, candidate.coefficients)
        if term != "1" and abs(float(coefficient)) >= threshold
    }


def _ordered_terms(catalog: TermCatalog, selected: Iterable[str]) -> tuple[str, ...]:
    selected_set = set(selected)
    return ("1",) + tuple(
        name for name in catalog.names() if name != "1" and name in selected_set
    )


def _federated_clients(
    partitions: Sequence[PartitionedClient],
    catalog: TermCatalog,
    *,
    include_validation: bool,
) -> list[FederatedFalsifierClient]:
    datasets = [
        partition.full if include_validation else partition.discovery
        for partition in partitions
    ]
    return [FederatedFalsifierClient(dataset, catalog) for dataset in datasets]


def _prune_candidate(
    candidate: CandidateEquation, *, threshold: float = 1e-3
) -> CandidateEquation:
    kept = [
        (term, float(coefficient))
        for term, coefficient in zip(candidate.active_terms, candidate.coefficients)
        if term == "1" or abs(float(coefficient)) >= threshold
    ]
    return CandidateEquation(
        tuple(term for term, _ in kept),
        tuple(coefficient for _, coefficient in kept),
        candidate.candidate_id,
    )


def _refit(
    partitions: Sequence[PartitionedClient],
    catalog: TermCatalog,
    terms: tuple[str, ...],
    *,
    include_validation: bool,
    candidate_id: str,
) -> tuple[CandidateEquation, int]:
    clients = _federated_clients(
        partitions, catalog, include_validation=include_validation
    )
    candidate, communication = fit_federated(clients, terms)
    return (
        _prune_candidate(
            CandidateEquation(
                candidate.active_terms,
                candidate.coefficients,
                candidate_id,
            )
        ),
        communication,
    )


def _validation_profile(
    source: str,
    candidate: CandidateEquation,
    partitions: Sequence[PartitionedClient],
    catalog: TermCatalog,
) -> tuple[ValidationProfile, int]:
    client_mse: list[tuple[str, float]] = []
    weighted_error = 0.0
    support = 0
    communication = 0
    for partition in partitions:
        prediction = candidate.predict(partition.validation.x, catalog)
        residual = partition.validation.y - prediction
        squared_error = float(residual @ residual)
        mse = squared_error / len(residual)
        client_mse.append((partition.client_id, mse))
        weighted_error += squared_error
        support += len(residual)
        communication += len(
            json.dumps(
                {
                    "client_id": partition.client_id,
                    "support": len(residual),
                    "squared_error": squared_error,
                },
                separators=(",", ":"),
            ).encode("utf-8")
        )
    weighted_mse = weighted_error / support
    complexity = int(catalog.complexity(candidate.active_terms))
    information_score = float(
        np.log(max(weighted_mse, 1e-15))
        + complexity * np.log(max(support, 2)) / support
    )
    return (
        ValidationProfile(
            source=source,
            weighted_mse=float(weighted_mse),
            worst_client_mse=float(max(value for _, value in client_mse)),
            information_score=information_score,
            complexity=complexity,
            support=support,
            client_mse=tuple(client_mse),
        ),
        communication,
    )


def _validation_term_support(
    primary: CandidateEquation,
    added_terms: set[str],
    partitions: Sequence[PartitionedClient],
    catalog: TermCatalog,
    *,
    correlation_threshold: float = 0.05,
    minimum_support_fraction: float = 0.50,
    minimum_sign_agreement: float = 0.50,
) -> tuple[bool, int, dict[str, dict[str, float]]]:
    if not added_terms:
        return True, 0, {}

    certificates = []
    communication = 0
    for partition in partitions:
        certificate = FederatedFalsifierClient(
            partition.validation, catalog
        ).falsify(primary)
        certificates.append(certificate)
        communication += _payload_bytes(certificate)

    diagnostics: dict[str, dict[str, float]] = {}
    all_supported = True
    for term in sorted(added_terms):
        correlations: list[float] = []
        weights: list[float] = []
        for certificate in certificates:
            item = next(
                (evidence for evidence in certificate.term_evidence if evidence.term == term),
                None,
            )
            if item is None:
                continue
            minimum_observed = max(10, int(round(0.10 * certificate.support)))
            if item.observed_support < minimum_observed or item.term_energy <= 1e-12:
                continue
            correlations.append(float(item.residual_correlation))
            weights.append(float(certificate.support))

        observable = len(correlations)
        if observable == 0:
            diagnostics[term] = {
                "observable_clients": 0.0,
                "support_fraction": 0.0,
                "sign_agreement": 0.0,
            }
            all_supported = False
            continue

        values = np.asarray(correlations, dtype=float)
        weight_array = np.asarray(weights, dtype=float)
        support_mask = np.abs(values) >= correlation_threshold
        support_fraction = float(np.mean(support_mask))
        if np.any(support_mask):
            sign_agreement = abs(
                float(
                    np.average(
                        np.sign(values[support_mask]),
                        weights=weight_array[support_mask],
                    )
                )
            )
        else:
            sign_agreement = 0.0
        diagnostics[term] = {
            "observable_clients": float(observable),
            "support_fraction": support_fraction,
            "sign_agreement": sign_agreement,
        }
        if (
            support_fraction < minimum_support_fraction
            or sign_agreement < minimum_sign_agreement
        ):
            all_supported = False
    return all_supported, communication, diagnostics


def _profile_map(profile: ValidationProfile) -> dict[str, float]:
    return {client_id: mse for client_id, mse in profile.client_mse}


def _admissible_fallback(
    primary_candidate: CandidateEquation,
    primary_profile: ValidationProfile,
    candidate: CandidateEquation,
    profile: ValidationProfile,
    partitions: Sequence[PartitionedClient],
    catalog: TermCatalog,
    *,
    minimum_relative_gain: float = 0.01,
    worst_client_tolerance: float = 0.05,
    nondegradation_tolerance: float = 0.02,
    minimum_nondegradation_fraction: float = 0.60,
) -> tuple[bool, int, str]:
    if candidate.active_terms == primary_candidate.active_terms:
        return False, 0, "duplicate term set"
    relative_gain = (
        primary_profile.weighted_mse - profile.weighted_mse
    ) / max(primary_profile.weighted_mse, 1e-15)
    if relative_gain < minimum_relative_gain:
        return False, 0, "insufficient validation-MSE gain"
    if profile.information_score >= primary_profile.information_score:
        return False, 0, "complexity-adjusted validation score did not improve"
    if profile.worst_client_mse > (
        1.0 + worst_client_tolerance
    ) * primary_profile.worst_client_mse:
        return False, 0, "worst-client validation safeguard failed"

    primary_by_client = _profile_map(primary_profile)
    candidate_by_client = _profile_map(profile)
    nondegraded = np.mean(
        [
            candidate_by_client[client_id]
            <= (1.0 + nondegradation_tolerance) * primary_mse
            for client_id, primary_mse in primary_by_client.items()
        ]
    )
    if float(nondegraded) < minimum_nondegradation_fraction:
        return False, 0, "client non-degradation safeguard failed"

    primary_terms = set(primary_candidate.active_terms)
    added_terms = set(candidate.active_terms) - primary_terms - {"1"}
    supported, communication, diagnostics = _validation_term_support(
        primary_candidate,
        added_terms,
        partitions,
        catalog,
    )
    if not supported:
        return (
            False,
            communication,
            "new-term cross-client support failed: "
            + json.dumps(diagnostics, sort_keys=True),
        )
    return True, communication, "all governed continuation gates passed"


def crossfit_fedfalsify_method(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    seed: int,
    max_terms: int = 6,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
    allow_fallback: bool = True,
) -> RedesignOutput:
    """Run two-way cross-fitted discovery and governed continuation."""

    start = perf_counter()
    partitions = partition_clients(datasets, seed=seed)

    direction_a_clients = [
        SplitFederatedFalsifierClient(
            partition.fold_a, partition.fold_b, catalog
        )
        for partition in partitions
    ]
    direction_b_clients = [
        SplitFederatedFalsifierClient(
            partition.fold_b, partition.fold_a, catalog
        )
        for partition in partitions
    ]
    direction_a, communication_a = _run_direction(
        direction_a_clients,
        catalog,
        max_terms=max_terms,
        target_mse=target_mse,
        min_repair_score=min_repair_score,
    )
    direction_b, communication_b = _run_direction(
        direction_b_clients,
        catalog,
        max_terms=max_terms,
        target_mse=target_mse,
        min_repair_score=min_repair_score,
    )

    terms_a = _nonzero_terms(direction_a.candidate)
    terms_b = _nonzero_terms(direction_b.candidate)
    consensus_terms = _ordered_terms(catalog, terms_a & terms_b)
    union_terms = _ordered_terms(catalog, terms_a | terms_b)
    direction_a_terms = _ordered_terms(catalog, terms_a)
    direction_b_terms = _ordered_terms(catalog, terms_b)

    discovery_clients = _federated_clients(
        partitions, catalog, include_validation=False
    )
    score_only = score_only_federated(
        discovery_clients,
        catalog,
        max_terms=max_terms,
        min_improvement=1e-5,
    )
    score_terms = _ordered_terms(catalog, _nonzero_terms(score_only.candidate))

    source_terms = (
        ("crossfit-intersection", consensus_terms),
        ("crossfit-union", union_terms),
        ("direction-a", direction_a_terms),
        ("direction-b", direction_b_terms),
        ("score-only", score_terms),
    )

    candidates: list[tuple[str, CandidateEquation]] = []
    seen: set[tuple[str, ...]] = set()
    communication = communication_a + communication_b + score_only.communication_bytes
    for source, terms in source_terms:
        if terms in seen:
            continue
        seen.add(terms)
        candidate, fit_bytes = _refit(
            partitions,
            catalog,
            terms,
            include_validation=False,
            candidate_id=source,
        )
        candidates.append((source, candidate))
        communication += fit_bytes

    candidate_by_source = {source: candidate for source, candidate in candidates}
    primary_candidate = candidate_by_source["crossfit-intersection"]

    profiles: list[ValidationProfile] = []
    profile_by_source: dict[str, ValidationProfile] = {}
    for source, candidate in candidates:
        profile, profile_bytes = _validation_profile(
            source, candidate, partitions, catalog
        )
        profiles.append(profile)
        profile_by_source[source] = profile
        communication += profile_bytes
    primary_profile = profile_by_source["crossfit-intersection"]

    selected_source = "crossfit-intersection"
    selected_candidate = primary_candidate
    decisions: list[str] = []
    if allow_fallback:
        admissible: list[tuple[ValidationProfile, CandidateEquation]] = []
        for source, candidate in candidates:
            if source == "crossfit-intersection":
                continue
            allowed, support_bytes, reason = _admissible_fallback(
                primary_candidate,
                primary_profile,
                candidate,
                profile_by_source[source],
                partitions,
                catalog,
            )
            communication += support_bytes
            decisions.append(f"{source}: {reason}")
            if allowed:
                admissible.append((profile_by_source[source], candidate))
        if admissible:
            best_profile, best_candidate = min(
                admissible,
                key=lambda item: (
                    item[0].information_score,
                    item[0].complexity,
                    item[0].source,
                ),
            )
            selected_source = best_profile.source
            selected_candidate = best_candidate

    final_candidate, final_fit_bytes = _refit(
        partitions,
        catalog,
        selected_candidate.active_terms,
        include_validation=True,
        candidate_id="crossfit-governed-final" if allow_fallback else "crossfit-final",
    )
    communication += final_fit_bytes
    selected_profile = profile_by_source[selected_source]
    method = "crossfit-governed" if allow_fallback else "crossfit-intersection"
    stop_reason = (
        f"direction A: {direction_a.stop_reason}; "
        f"direction B: {direction_b.stop_reason}; "
        f"selected={selected_source}"
    )
    if decisions:
        stop_reason += "; " + " | ".join(decisions)

    return RedesignOutput(
        method=method,
        candidate=final_candidate,
        direction_a_terms=direction_a_terms,
        direction_b_terms=direction_b_terms,
        consensus_terms=consensus_terms,
        selected_source=selected_source,
        fallback_selected=selected_source != "crossfit-intersection",
        validation_profile=selected_profile,
        validation_profiles=tuple(profiles),
        communication_bytes=communication,
        runtime_seconds=perf_counter() - start,
        stop_reason=stop_reason,
    )
