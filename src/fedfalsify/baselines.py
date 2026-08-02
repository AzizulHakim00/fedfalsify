"""Controlled baselines sharing FedFalsify's finite grammar and term budget."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import random
from time import perf_counter

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .client import FederatedFalsifierClient
from .server import FedFalsifyDiscovery


@dataclass(frozen=True)
class MethodOutput:
    method: str
    candidates: tuple[CandidateEquation, ...]
    rounds: int
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str

    @property
    def candidate(self) -> CandidateEquation:
        return self.candidates[0]


def _solve(gram: np.ndarray, target: np.ndarray, ridge: float = 1e-8) -> np.ndarray:
    regularizer = ridge * np.eye(gram.shape[0])
    regularizer[0, 0] = 0.0
    try:
        return np.linalg.solve(gram + regularizer, target)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(gram + regularizer) @ target


def fit_pooled(datasets, catalog: TermCatalog, terms: tuple[str, ...]) -> CandidateEquation:
    x = np.concatenate([dataset.x for dataset in datasets], axis=0)
    y = np.concatenate([dataset.y for dataset in datasets], axis=0)
    design = catalog.matrix(x, terms)
    coefficients = _solve(design.T @ design, design.T @ y)
    return CandidateEquation(terms, tuple(float(value) for value in coefficients))


def fit_federated(
    clients: list[FederatedFalsifierClient], terms: tuple[str, ...]
) -> tuple[CandidateEquation, int]:
    summaries = [client.fit_summary(terms) for client in clients]
    size = len(terms)
    gram = np.zeros((size, size), dtype=float)
    target = np.zeros(size, dtype=float)
    bytes_sent = 0
    for summary in summaries:
        gram += np.asarray(summary.gram, dtype=float)
        target += np.asarray(summary.target, dtype=float)
        bytes_sent += len(
            json.dumps(asdict(summary), separators=(",", ":")).encode("utf-8")
        )
    coefficients = _solve(gram, target)
    return CandidateEquation(terms, tuple(float(value) for value in coefficients)), bytes_sent


def pooled_mse(candidate: CandidateEquation, datasets, catalog: TermCatalog) -> float:
    squared_error = 0.0
    support = 0
    for dataset in datasets:
        residual = dataset.y - candidate.predict(dataset.x, catalog)
        squared_error += float(residual @ residual)
        support += dataset.y.size
    return squared_error / support


def federated_mse(
    candidate: CandidateEquation, clients: list[FederatedFalsifierClient]
) -> tuple[float, int]:
    certificates = [client.falsify(candidate) for client in clients]
    total = sum(certificate.support for certificate in certificates)
    mse = sum(
        certificate.mse * certificate.support for certificate in certificates
    ) / total
    payload_bytes = sum(
        len(json.dumps(certificate.to_dict(), separators=(",", ":")).encode("utf-8"))
        for certificate in certificates
    )
    return mse, payload_bytes


def _information_score(mse: float, complexity: int, support: int) -> float:
    return float(
        np.log(max(mse, 1e-15))
        + complexity * np.log(max(support, 2)) / support
    )


def _prune(candidate: CandidateEquation, threshold: float = 1e-3) -> CandidateEquation:
    kept = [
        (term, coefficient)
        for term, coefficient in zip(candidate.active_terms, candidate.coefficients)
        if term == "1" or abs(coefficient) >= threshold
    ]
    return CandidateEquation(
        tuple(term for term, _ in kept),
        tuple(float(coefficient) for _, coefficient in kept),
        candidate.candidate_id,
    )


def centralized_forward(
    datasets,
    catalog: TermCatalog,
    *,
    max_terms: int = 6,
    min_improvement: float = 1e-5,
) -> MethodOutput:
    start = perf_counter()
    active = ("1",)
    current = fit_pooled(datasets, catalog, active)
    support = sum(dataset.y.size for dataset in datasets)
    current_score = _information_score(
        pooled_mse(current, datasets, catalog), catalog.complexity(active), support
    )
    rounds = 0
    while len(active) < max_terms:
        best_candidate: CandidateEquation | None = None
        best_score = current_score
        for term in catalog.names():
            if term in active:
                continue
            proposed = active + (term,)
            candidate = fit_pooled(datasets, catalog, proposed)
            score = _information_score(
                pooled_mse(candidate, datasets, catalog),
                catalog.complexity(proposed),
                support,
            )
            if score < best_score:
                best_candidate, best_score = candidate, score
        if best_candidate is None or current_score - best_score < min_improvement:
            break
        current = best_candidate
        active = current.active_terms
        current_score = best_score
        rounds += 1
    return MethodOutput(
        "centralized-forward",
        (_prune(current),),
        rounds,
        0,
        perf_counter() - start,
        "information criterion stopped",
    )


def local_forward(datasets, catalog: TermCatalog, *, max_terms: int = 6) -> MethodOutput:
    start = perf_counter()
    candidates: list[CandidateEquation] = []
    rounds = 0
    for dataset in datasets:
        output = centralized_forward((dataset,), catalog, max_terms=max_terms)
        candidates.append(
            CandidateEquation(
                output.candidate.active_terms,
                output.candidate.coefficients,
                dataset.client_id,
            )
        )
        rounds += output.rounds
    return MethodOutput(
        "local-only-forward",
        tuple(candidates),
        rounds,
        0,
        perf_counter() - start,
        "independent local searches",
    )


def score_only_federated(
    clients: list[FederatedFalsifierClient],
    catalog: TermCatalog,
    *,
    max_terms: int = 6,
    min_improvement: float = 1e-5,
) -> MethodOutput:
    start = perf_counter()
    active = ("1",)
    current, communication = fit_federated(clients, active)
    current_mse, payload = federated_mse(current, clients)
    communication += payload
    rounds = 0
    while len(active) < max_terms:
        best: tuple[CandidateEquation, float] | None = None
        for term in catalog.names():
            if term in active:
                continue
            candidate, fit_bytes = fit_federated(clients, active + (term,))
            mse, eval_bytes = federated_mse(candidate, clients)
            communication += fit_bytes + eval_bytes
            if best is None or mse < best[1]:
                best = (candidate, mse)
        if best is None or current_mse - best[1] < min_improvement:
            break
        current, current_mse = best
        active = current.active_terms
        rounds += 1
    return MethodOutput(
        "score-only-federated",
        (_prune(current),),
        rounds,
        communication,
        perf_counter() - start,
        "greedy aggregate-MSE search",
    )


def random_repair(
    clients: list[FederatedFalsifierClient],
    catalog: TermCatalog,
    *,
    max_terms: int = 6,
    seed: int = 0,
) -> MethodOutput:
    start = perf_counter()
    rng = random.Random(seed)
    active = ["1"]
    rounds = 0
    while len(active) < max_terms:
        inactive = [term for term in catalog.names() if term not in active]
        if not inactive:
            break
        active.append(rng.choice(inactive))
        rounds += 1
    candidate, fit_bytes = fit_federated(clients, tuple(active))
    _, eval_bytes = federated_mse(candidate, clients)
    return MethodOutput(
        "random-repair",
        (_prune(candidate),),
        rounds,
        fit_bytes + eval_bytes,
        perf_counter() - start,
        "fixed random term budget",
    )


def fedfalsify_method(
    clients: list[FederatedFalsifierClient],
    catalog: TermCatalog,
    *,
    max_terms: int = 6,
    target_mse: float = 0.003,
    min_repair_score: float = 0.05,
    use_coefficient_heterogeneity: bool = True,
) -> MethodOutput:
    start = perf_counter()
    result = FedFalsifyDiscovery(
        clients,
        catalog,
        max_rounds=max_terms + 2,
        max_terms=max_terms,
        target_mse=target_mse,
        min_repair_score=min_repair_score,
        use_coefficient_heterogeneity=use_coefficient_heterogeneity,
    ).discover()
    communication = 0
    for record in result.history:
        for client in clients:
            summary = client.fit_summary(record.candidate.active_terms)
            communication += len(
                json.dumps(asdict(summary), separators=(",", ":")).encode("utf-8")
            )
            certificate = client.falsify(record.candidate)
            communication += len(
                json.dumps(certificate.to_dict(), separators=(",", ":")).encode("utf-8")
            )
    method = (
        "fedfalsify"
        if use_coefficient_heterogeneity
        else "fedfalsify-no-heterogeneity"
    )
    return MethodOutput(
        method,
        (result.candidate,),
        len(result.history),
        communication,
        perf_counter() - start,
        result.stop_reason,
    )
