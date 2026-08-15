"""Outcome-independent five-fold stability screening for FedFalsify v3."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from math import ceil
from typing import Sequence

import numpy as np

from .basis import TermCatalog
from .crossfit_redesign import (
    PartitionedClient,
    SplitFederatedFalsifierClient,
    _discovery_communication,
    _nonzero_terms,
    _ordered_terms,
)
from .external_common import ExternalClientData
from .server import DiscoveryResult, FedFalsifyDiscovery


@dataclass(frozen=True)
class StabilityTermDiagnostic:
    term: str
    selected_fold_count: int
    best_repair_fold_count: int
    top3_repair_fold_count: int
    median_abs_residual_correlation: float
    weighted_sign_agreement: float
    coefficient_sign_stability: float
    client_coverage: float
    observable_client_folds: int
    selected: bool
    selection_rule: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class StabilitySupersetProfile:
    stable_terms: tuple[str, ...]
    diagnostics: tuple[StabilityTermDiagnostic, ...]
    fold_selected_terms: tuple[tuple[str, ...], ...]
    observability_floors: tuple[int, ...]
    maximum_size: int

    def to_dict(self) -> dict[str, object]:
        return {
            "stable_terms": self.stable_terms,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "fold_selected_terms": self.fold_selected_terms,
            "observability_floors": self.observability_floors,
            "maximum_size": self.maximum_size,
        }


@dataclass(frozen=True)
class FoldTermEvidence:
    score: float
    correlations: tuple[tuple[str, float, float], ...]
    adjustments: tuple[tuple[str, float, float], ...]


@dataclass(frozen=True)
class FoldDirection:
    result: DiscoveryResult
    selected_terms: tuple[str, ...]
    best_terms: tuple[str, ...]
    top3_terms: tuple[str, ...]
    term_evidence: dict[str, FoldTermEvidence]
    observability_floor: int
    communication_bytes: int


def _stable_seed(seed: int, client_id: str) -> int:
    digest = hashlib.sha256(
        f"{seed}:{client_id}:stability-folds".encode()
    ).digest()
    return int.from_bytes(digest[:8], "big")


def _fold_observability_floor(heldout_rows: int) -> int:
    if heldout_rows <= 0:
        raise ValueError("heldout_rows must be positive")
    return max(3, int(ceil(0.10 * heldout_rows)))


def _split_discovery_folds(
    partitions: Sequence[PartitionedClient], *, seed: int
) -> tuple[tuple[ExternalClientData, ...], ...]:
    output = []
    for partition in partitions:
        data = partition.discovery
        if len(data.y) < 40:
            raise ValueError("five discovery folds need at least 40 rows")
        rng = np.random.default_rng(_stable_seed(seed, partition.client_id))
        indices = np.array_split(rng.permutation(len(data.y)), 5)
        folds = tuple(
            ExternalClientData(
                partition.client_id, data.x[index], data.y[index]
            )
            for index in indices
        )
        if sum(len(fold.y) for fold in folds) != len(data.y):
            raise RuntimeError("fold split is not exhaustive")
        output.append(folds)
    return tuple(output)


def _join_folds(
    folds: Sequence[ExternalClientData], heldout: int
) -> ExternalClientData:
    kept = [fold for index, fold in enumerate(folds) if index != heldout]
    return ExternalClientData(
        folds[0].client_id,
        np.concatenate([fold.x for fold in kept]),
        np.concatenate([fold.y for fold in kept]),
    )


def _item(items: Sequence[object], term: str):
    return next((item for item in items if item.term == term), None)


def _record_evidence(
    engine: FedFalsifyDiscovery,
    result: DiscoveryResult,
    clients: Sequence[SplitFederatedFalsifierClient],
    catalog: TermCatalog,
    floor: int,
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, FoldTermEvidence]]:
    """Retain one maximum while-inactive score per term and fold direction."""

    best: dict[str, FoldTermEvidence] = {}
    candidates = [record.candidate for record in result.history] or [result.candidate]
    for candidate in candidates:
        certificates = tuple(client.falsify(candidate) for client in clients)
        for term in catalog.names():
            if term == "1" or term in candidate.active_terms:
                continue
            decision = engine._score_term(term, certificates)
            score = float(decision.score) if decision.term is not None else 0.0
            correlations, adjustments = [], []
            for certificate in certificates:
                evidence = _item(certificate.term_evidence, term)
                if (
                    evidence is not None
                    and evidence.observed_support >= floor
                    and evidence.term_energy > 1e-12
                ):
                    correlations.append(
                        (
                            certificate.client_id,
                            float(evidence.residual_correlation),
                            float(certificate.support),
                        )
                    )
                coefficient = _item(certificate.coefficient_evidence, term)
                if (
                    coefficient is not None
                    and coefficient.estimable
                    and coefficient.observed_support >= floor
                ):
                    adjustments.append(
                        (
                            certificate.client_id,
                            float(coefficient.local_adjustment),
                            float(certificate.support),
                        )
                    )
            current = FoldTermEvidence(
                score, tuple(correlations), tuple(adjustments)
            )
            if term not in best or current.score > best[term].score:
                best[term] = current
    for term in catalog.names():
        if term != "1":
            best.setdefault(term, FoldTermEvidence(0.0, (), ()))
    ranking = sorted(
        ((item.score, term) for term, item in best.items() if item.score > 0),
        key=lambda pair: (-pair[0], catalog.get(pair[1]).complexity, pair[1]),
    )
    return (
        tuple(term for _, term in ranking[:1]),
        tuple(term for _, term in ranking[:3]),
        best,
    )


def run_fold_directions(
    folds_by_client: Sequence[Sequence[ExternalClientData]],
    catalog: TermCatalog,
    *,
    max_terms: int,
    target_mse: float,
    min_repair_score: float,
) -> tuple[FoldDirection, ...]:
    directions = []
    for heldout in range(5):
        clients, sizes = [], []
        for folds in folds_by_client:
            certificate = folds[heldout]
            sizes.append(len(certificate.y))
            clients.append(
                SplitFederatedFalsifierClient(
                    _join_folds(folds, heldout), certificate, catalog
                )
            )
        floor = _fold_observability_floor(min(sizes))
        engine = FedFalsifyDiscovery(
            clients,  # type: ignore[arg-type]
            catalog,
            max_rounds=max_terms + 2,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=min_repair_score,
            min_observed_support=floor,
            use_coefficient_heterogeneity=True,
        )
        result = engine.discover()
        best, top3, evidence = _record_evidence(
            engine, result, clients, catalog, floor
        )
        directions.append(
            FoldDirection(
                result=result,
                selected_terms=_ordered_terms(
                    catalog, _nonzero_terms(result.candidate)
                ),
                best_terms=best,
                top3_terms=top3,
                term_evidence=evidence,
                observability_floor=floor,
                communication_bytes=_discovery_communication(result, clients),
            )
        )
    return tuple(directions)


def _sign_agreement(
    observations: Sequence[tuple[str, float, float]]
) -> float:
    values = [
        (value, weight)
        for _, value, weight in observations
        if np.isfinite(value) and value != 0 and weight > 0
    ]
    if not values:
        return 0.0
    signs = np.sign([value for value, _ in values])
    weights = [weight for _, weight in values]
    return abs(float(np.average(signs, weights=weights)))


def _passes_stability_rule(
    *,
    best_repair_fold_count: int,
    top3_repair_fold_count: int,
    weighted_sign_agreement: float,
    client_coverage: float,
) -> tuple[bool, str]:
    if best_repair_fold_count >= 2:
        return True, "best repair in at least two folds"
    if (
        top3_repair_fold_count >= 3
        and weighted_sign_agreement >= 0.60
        and client_coverage >= 0.50
    ):
        return True, "top-three stability, sign, and coverage rule"
    return False, "no frozen stability rule passed"


def build_stability_profile(
    directions: Sequence[FoldDirection],
    catalog: TermCatalog,
    *,
    client_count: int,
    maximum_size: int = 8,
) -> StabilitySupersetProfile:
    if len(directions) != 5:
        raise ValueError("v3 requires five fold directions")
    selected_sets = [set(item.selected_terms) - {"1"} for item in directions]
    diagnostics = []
    for term in catalog.names():
        if term == "1":
            continue
        correlations, adjustments = [], []
        for direction in directions:
            evidence = direction.term_evidence[term]
            correlations.extend(evidence.correlations)
            adjustments.extend(evidence.adjustments)
        observed_clients = {
            client for client, _, _ in correlations + adjustments
        }
        best_count = sum(term in item.best_terms for item in directions)
        top3_count = sum(term in item.top3_terms for item in directions)
        agreement = _sign_agreement(correlations)
        coverage = len(observed_clients) / max(client_count, 1)
        selected, rule = _passes_stability_rule(
            best_repair_fold_count=best_count,
            top3_repair_fold_count=top3_count,
            weighted_sign_agreement=agreement,
            client_coverage=coverage,
        )
        abs_correlations = [
            abs(value) for _, value, _ in correlations if np.isfinite(value)
        ]
        diagnostics.append(
            StabilityTermDiagnostic(
                term=term,
                selected_fold_count=sum(
                    term in selected_set for selected_set in selected_sets
                ),
                best_repair_fold_count=best_count,
                top3_repair_fold_count=top3_count,
                median_abs_residual_correlation=(
                    float(np.median(abs_correlations))
                    if abs_correlations
                    else 0.0
                ),
                weighted_sign_agreement=agreement,
                coefficient_sign_stability=_sign_agreement(adjustments),
                client_coverage=coverage,
                observable_client_folds=len(correlations),
                selected=selected,
                selection_rule=rule,
            )
        )
    ranked = sorted(
        (item for item in diagnostics if item.selected),
        key=lambda item: (
            -item.selected_fold_count,
            -item.best_repair_fold_count,
            -item.top3_repair_fold_count,
            -item.median_abs_residual_correlation,
            catalog.get(item.term).complexity,
            item.term,
        ),
    )
    return StabilitySupersetProfile(
        stable_terms=tuple(item.term for item in ranked[:maximum_size]),
        diagnostics=tuple(diagnostics),
        fold_selected_terms=tuple(item.selected_terms for item in directions),
        observability_floors=tuple(
            item.observability_floor for item in directions
        ),
        maximum_size=maximum_size,
    )
