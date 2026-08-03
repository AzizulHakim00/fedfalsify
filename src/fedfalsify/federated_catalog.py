"""Data-local catalog search equivalent to pooled information-criterion search.

Clients transmit aggregate fit summaries and residual-evaluation certificates;
raw rows are not pooled. With identical terms, ridge, and information score,
the selected candidate should numerically reproduce the controlled centralized
catalog baseline. This is a strong finite-catalog comparator, not a privacy
guarantee.
"""

from __future__ import annotations

from time import perf_counter

import numpy as np

from .baselines import (
    MethodOutput,
    _information_score,
    _prune,
    federated_mse,
    fit_federated,
)
from .basis import CandidateEquation, TermCatalog
from .client import FederatedFalsifierClient


def federated_information_forward(
    clients: list[FederatedFalsifierClient],
    catalog: TermCatalog,
    *,
    max_terms: int = 6,
    min_improvement: float = 1e-5,
) -> MethodOutput:
    """Run pooled-equivalent forward search from aggregate client summaries."""

    if not clients:
        raise ValueError("at least one client is required")
    if max_terms < 1:
        raise ValueError("max_terms must be positive")

    start = perf_counter()
    active = ("1",)
    current, communication = fit_federated(clients, active)
    current_mse, evaluation_bytes = federated_mse(current, clients)
    communication += evaluation_bytes
    # Client support is protocol metadata already present in every fit summary;
    # reading it here creates no extra simulated message.
    support = sum(client.sample_count for client in clients)
    current_score = _information_score(
        current_mse,
        catalog.complexity(active),
        support,
    )
    rounds = 0

    while len(active) < max_terms:
        best_candidate: CandidateEquation | None = None
        best_score = current_score
        for term in catalog.names():
            if term in active:
                continue
            proposed = active + (term,)
            candidate, fit_bytes = fit_federated(clients, proposed)
            mse, eval_bytes = federated_mse(candidate, clients)
            score = _information_score(
                mse,
                catalog.complexity(proposed),
                support,
            )
            # Every evaluated candidate generated aggregate protocol traffic,
            # including candidates that were not selected.
            communication += fit_bytes + eval_bytes
            if score < best_score:
                best_candidate = candidate
                best_score = score
        if best_candidate is None or current_score - best_score < min_improvement:
            break
        current = best_candidate
        active = current.active_terms
        current_score = best_score
        rounds += 1

    return MethodOutput(
        method="federated-information-catalog",
        candidates=(_prune(current),),
        rounds=rounds,
        communication_bytes=communication,
        runtime_seconds=perf_counter() - start,
        stop_reason="aggregate information criterion stopped",
    )


def candidates_numerically_equivalent(
    left: CandidateEquation,
    right: CandidateEquation,
    *,
    coefficient_tolerance: float = 1e-8,
) -> bool:
    """Check support identity and coefficient agreement for audit tests."""

    return left.active_terms == right.active_terms and bool(
        np.allclose(
            np.asarray(left.coefficients),
            np.asarray(right.coefficients),
            atol=coefficient_tolerance,
            rtol=coefficient_tolerance,
        )
    )
