"""Cross-fitted, validation-aware governance for federated symbolic discovery.

The controller separates term discovery from candidate evaluation within every
client.  Observation rows remain local: only aggregate fit summaries and scalar
validation losses are communicated.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from time import perf_counter
from typing import Sequence

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .baselines import MethodOutput, fedfalsify_method, fit_federated, score_only_federated
from .client import FederatedFalsifierClient
from .external_common import ExternalClientData


@dataclass(frozen=True)
class FoldClients:
    fold_index: int
    training: tuple[FederatedFalsifierClient, ...]
    validation: tuple[FederatedFalsifierClient, ...]
    training_rows: int
    validation_rows: int


@dataclass(frozen=True)
class CandidateValidation:
    source: str
    active_terms: tuple[str, ...]
    mean_mse: float
    worst_client_mse: float
    information_score: float
    fold_mse: tuple[float, ...]
    nondegradation_rate: float
    complexity: int


@dataclass(frozen=True)
class CrossFittedResult:
    candidate: CandidateEquation
    selected_source: str
    fallback_activated: bool
    validations: tuple[CandidateValidation, ...]
    folds: int
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


def _stable_seed(client_id: str, seed: int) -> int:
    digest = hashlib.sha256(f"{seed}:{client_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little", signed=False)


def make_crossfit_folds(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    folds: int = 2,
    seed: int = 13001,
    minimum_rows_per_partition: int = 10,
) -> tuple[FoldClients, ...]:
    """Create deterministic within-client folds without sharing raw rows."""

    if folds < 2:
        raise ValueError("cross-fitting requires at least two folds")
    materialized = tuple(datasets)
    if len(materialized) < 2:
        raise ValueError("federated cross-fitting requires at least two clients")

    assignments: list[np.ndarray] = []
    for dataset in materialized:
        count = int(len(dataset.y))
        if count < folds * minimum_rows_per_partition:
            raise ValueError(
                f"client {dataset.client_id} has too few rows for {folds}-fold cross-fitting"
            )
        rng = np.random.default_rng(_stable_seed(str(dataset.client_id), seed))
        permutation = rng.permutation(count)
        labels = np.empty(count, dtype=int)
        labels[permutation] = np.arange(count, dtype=int) % folds
        assignments.append(labels)

    output: list[FoldClients] = []
    for fold_index in range(folds):
        training_clients: list[FederatedFalsifierClient] = []
        validation_clients: list[FederatedFalsifierClient] = []
        training_rows = 0
        validation_rows = 0
        for dataset, labels in zip(materialized, assignments):
            validation_mask = labels == fold_index
            training_mask = ~validation_mask
            train = ExternalClientData(
                f"{dataset.client_id}:train-f{fold_index}",
                np.asarray(dataset.x, dtype=float)[training_mask],
                np.asarray(dataset.y, dtype=float)[training_mask],
            )
            validation = ExternalClientData(
                f"{dataset.client_id}:validation-f{fold_index}",
                np.asarray(dataset.x, dtype=float)[validation_mask],
                np.asarray(dataset.y, dtype=float)[validation_mask],
            )
            training_clients.append(FederatedFalsifierClient(train, catalog))
            validation_clients.append(FederatedFalsifierClient(validation, catalog))
            training_rows += len(train.y)
            validation_rows += len(validation.y)
        output.append(
            FoldClients(
                fold_index,
                tuple(training_clients),
                tuple(validation_clients),
                training_rows,
                validation_rows,
            )
        )
    return tuple(output)


def _validation_losses(
    candidate: CandidateEquation,
    clients: Sequence[FederatedFalsifierClient],
) -> tuple[float, float, tuple[float, ...], int]:
    losses: list[float] = []
    supports: list[int] = []
    communication = 0
    for client in clients:
        certificate = client.falsify(candidate)
        losses.append(float(certificate.mse))
        supports.append(int(certificate.support))
        communication += len(
            json.dumps(certificate.to_dict(), separators=(",", ":")).encode("utf-8")
        )
    weighted = float(np.average(losses, weights=supports))
    return weighted, max(losses), tuple(losses), communication


def _information_score(mse: float, complexity: int, support: int) -> float:
    return float(np.log(max(mse, 1e-15)) + complexity * np.log(max(support, 2)) / support)


def _evaluate_term_set(
    *,
    source: str,
    active_terms: tuple[str, ...],
    fold_clients: Sequence[FoldClients],
    catalog: TermCatalog,
    local_reference: Sequence[float] | None = None,
) -> tuple[CandidateValidation, int]:
    fold_means: list[float] = []
    all_client_losses: list[float] = []
    communication = 0
    total_validation = 0
    for fold in fold_clients:
        candidate, fit_bytes = fit_federated(list(fold.training), active_terms)
        mean_mse, _, client_losses, eval_bytes = _validation_losses(
            candidate, fold.validation
        )
        fold_means.append(mean_mse)
        all_client_losses.extend(client_losses)
        communication += fit_bytes + eval_bytes
        total_validation += fold.validation_rows

    complexity = catalog.complexity(active_terms)
    mean_mse = float(np.mean(fold_means))
    if local_reference is None:
        nondegradation_rate = 1.0
    else:
        reference = np.asarray(local_reference, dtype=float)
        observed = np.asarray(all_client_losses, dtype=float)
        if reference.shape != observed.shape:
            raise ValueError("local reference must match fold-by-client validation losses")
        nondegradation_rate = float(np.mean(observed <= reference * 1.05))
    return (
        CandidateValidation(
            source=source,
            active_terms=active_terms,
            mean_mse=mean_mse,
            worst_client_mse=float(max(all_client_losses)),
            information_score=_information_score(mean_mse, complexity, total_validation),
            fold_mse=tuple(float(value) for value in fold_means),
            nondegradation_rate=nondegradation_rate,
            complexity=complexity,
        ),
        communication,
    )


def cross_fitted_fedfalsify(
    datasets: Sequence[object],
    catalog: TermCatalog,
    *,
    folds: int = 2,
    seed: int = 13001,
    max_terms: int = 6,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
    fallback_min_relative_improvement: float = 0.02,
    fallback_worst_client_tolerance: float = 0.05,
    fallback_complexity_slack: int = 3,
) -> CrossFittedResult:
    """Select a governed candidate using held-out within-client evidence.

    Full FedFalsify and score-only federated search are run only on discovery
    partitions.  Their unique term sets are then refit and evaluated across all
    held-out folds.  The score-only fallback is activated only when it improves
    mean validation loss by a preregistered margin, respects a worst-client
    tolerance, and stays within a bounded complexity increase.
    """

    start = perf_counter()
    fold_clients = make_crossfit_folds(datasets, catalog, folds=folds, seed=seed)
    proposals: dict[tuple[str, ...], str] = {}
    communication = 0

    for fold in fold_clients:
        full = fedfalsify_method(
            list(fold.training),
            catalog,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=min_repair_score,
        )
        score = score_only_federated(
            list(fold.training), catalog, max_terms=max_terms
        )
        communication += full.communication_bytes + score.communication_bytes
        proposals.setdefault(full.candidate.active_terms, "fedfalsify")
        proposals.setdefault(score.candidate.active_terms, "score-only-federated")

    validations: list[CandidateValidation] = []
    for terms, source in proposals.items():
        validation, payload = _evaluate_term_set(
            source=source,
            active_terms=terms,
            fold_clients=fold_clients,
            catalog=catalog,
        )
        validations.append(validation)
        communication += payload

    full_candidates = [item for item in validations if item.source == "fedfalsify"]
    if not full_candidates:
        raise RuntimeError("cross-fitting produced no FedFalsify proposal")
    incumbent = min(full_candidates, key=lambda item: item.information_score)

    fallback_candidates = [
        item for item in validations if item.source == "score-only-federated"
    ]
    admissible: list[CandidateValidation] = []
    for item in fallback_candidates:
        relative_gain = (incumbent.mean_mse - item.mean_mse) / max(
            incumbent.mean_mse, 1e-15
        )
        worst_ok = item.worst_client_mse <= incumbent.worst_client_mse * (
            1.0 + fallback_worst_client_tolerance
        )
        complexity_ok = item.complexity <= incumbent.complexity + fallback_complexity_slack
        if (
            relative_gain >= fallback_min_relative_improvement
            and worst_ok
            and complexity_ok
        ):
            admissible.append(item)

    selected = (
        min(admissible, key=lambda item: item.information_score)
        if admissible
        else incumbent
    )
    all_clients = [FederatedFalsifierClient(dataset, catalog) for dataset in datasets]
    final_candidate, final_fit_bytes = fit_federated(all_clients, selected.active_terms)
    communication += final_fit_bytes
    fallback_activated = selected.source == "score-only-federated"
    reason = (
        "governed score-only fallback passed held-out improvement, worst-client, and complexity gates"
        if fallback_activated
        else "cross-fitted FedFalsify retained; no fallback proposal passed all gates"
    )
    return CrossFittedResult(
        candidate=final_candidate,
        selected_source=selected.source,
        fallback_activated=fallback_activated,
        validations=tuple(sorted(validations, key=lambda item: item.information_score)),
        folds=folds,
        communication_bytes=communication,
        runtime_seconds=perf_counter() - start,
        stop_reason=reason,
    )


def as_method_output(result: CrossFittedResult) -> MethodOutput:
    """Expose the governed result through the repository's common method API."""

    return MethodOutput(
        method="cross-fitted-fedfalsify",
        candidates=(result.candidate,),
        rounds=len(result.validations),
        communication_bytes=result.communication_bytes,
        runtime_seconds=result.runtime_seconds,
        stop_reason=result.stop_reason,
    )
