"""Certificate-guided federated expression-tree search.

This is a Transactions-development prototype that removes the requirement for
a pre-enumerated named-term catalog. Candidate structures come from the same
auditable expression-tree grammar used by the controlled GP baselines. Unlike a
pure aggregate-fitness search, every candidate is additionally evaluated using
client-level coefficient support, sign agreement, and observability evidence.

The implementation is research code. Its finite-sample statistical guarantees
are not yet proved, and it does not provide differential privacy.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from time import perf_counter
from typing import Iterable, Sequence

import numpy as np

from .expression_baselines import (
    TreeModel,
    _client_mses,
    _crossover,
    _fit_federated,
    _mutate,
    _normalize_genes,
    _objective,
    _solve,
)
from .expression_tree import Expr, expression_library, expression_matrix, recognized_term

Array = np.ndarray


@dataclass(frozen=True)
class GeneCertificate:
    gene: str
    recognized_term: str
    kind: str
    observable_clients: int
    supporting_clients: int
    support_fraction: float
    sign_agreement: float
    median_absolute_z: float
    median_absolute_coefficient: float
    penalty: float


@dataclass(frozen=True)
class CertificateTreeOutput:
    method: str
    model: TreeModel
    certificates: tuple[GeneCertificate, ...]
    generations: int
    evaluations: int
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str
    objective: float
    global_mse: float
    worst_client_mse: float


@dataclass(frozen=True)
class _LocalGeneEvidence:
    coefficient: float
    standard_error: float
    z_score: float
    effective_energy: float
    support: int
    observable: bool


@dataclass(frozen=True)
class _CertifiedEvaluated:
    genes: tuple[Expr, ...]
    model: TreeModel
    certificates: tuple[GeneCertificate, ...]
    objective: float
    global_mse: float
    worst_client_mse: float
    communication_bytes: int


def _contains_gate(expression: Expr) -> bool:
    return expression.op == "gate_x3_gt1" or any(
        _contains_gate(child) for child in expression.args
    )


def _local_evidence(dataset: object, genes: tuple[Expr, ...]) -> tuple[_LocalGeneEvidence, ...]:
    x = np.asarray(dataset.x, dtype=float)
    y = np.asarray(dataset.y, dtype=float)
    design = expression_matrix(x, genes)
    gram = design.T @ design
    target = design.T @ y
    coefficients = _solve(gram, target)
    residual = y - design @ coefficients
    degrees_of_freedom = max(len(y) - design.shape[1], 1)
    residual_variance = float((residual @ residual) / degrees_of_freedom)
    ridge = 1e-8 * np.eye(gram.shape[0])
    ridge[0, 0] = 0.0
    covariance_shape = np.linalg.pinv(gram + ridge)

    result: list[_LocalGeneEvidence] = []
    for index, gene in enumerate(genes, start=1):
        values = gene.evaluate(x)
        centered = values - float(np.mean(values))
        energy = float(centered @ centered)
        observed_support = int(np.count_nonzero(np.abs(values) > 1e-12))
        observable = bool(observed_support > 0 and energy > 1e-12)
        coefficient = float(coefficients[index])
        variance = max(
            residual_variance * float(covariance_shape[index, index]),
            0.0,
        )
        standard_error = float(math.sqrt(variance))
        z_score = (
            coefficient / max(standard_error, 1e-12)
            if observable
            else 0.0
        )
        result.append(
            _LocalGeneEvidence(
                coefficient=coefficient,
                standard_error=standard_error,
                z_score=float(z_score),
                effective_energy=energy,
                support=len(y),
                observable=observable,
            )
        )
    return tuple(result)


def _aggregate_gene_certificate(
    gene: Expr,
    evidence: Sequence[_LocalGeneEvidence],
    *,
    total_clients: int,
    core_support_threshold: float,
    exception_support_threshold: float,
    sign_agreement_threshold: float,
    z_threshold: float,
    penalty_scale: float,
) -> GeneCertificate:
    observable = [item for item in evidence if item.observable]
    kind = "exception" if _contains_gate(gene) else "core"
    required_support = (
        exception_support_threshold if kind == "exception" else core_support_threshold
    )
    min_observable = min(2, total_clients)
    supporting = [item for item in observable if abs(item.z_score) >= z_threshold]
    support_fraction = len(supporting) / len(observable) if observable else 0.0
    if supporting:
        weights = np.asarray(
            [max(item.effective_energy, 1e-12) for item in supporting],
            dtype=float,
        )
        signs = np.sign([item.coefficient for item in supporting])
        sign_agreement = float(abs(np.average(signs, weights=weights)))
        median_z = float(np.median([abs(item.z_score) for item in supporting]))
        median_coefficient = float(
            np.median([abs(item.coefficient) for item in supporting])
        )
    else:
        sign_agreement = 0.0
        median_z = 0.0
        median_coefficient = 0.0

    observability_deficit = max(0, min_observable - len(observable)) / max(
        min_observable, 1
    )
    support_deficit = max(0.0, required_support - support_fraction)
    sign_deficit = max(0.0, sign_agreement_threshold - sign_agreement)
    penalty = penalty_scale * (
        2.0 * observability_deficit
        + 3.0 * support_deficit
        + 2.0 * sign_deficit
    )
    return GeneCertificate(
        gene=gene.canonical(),
        recognized_term=recognized_term(gene) or "",
        kind=kind,
        observable_clients=len(observable),
        supporting_clients=len(supporting),
        support_fraction=float(support_fraction),
        sign_agreement=sign_agreement,
        median_absolute_z=median_z,
        median_absolute_coefficient=median_coefficient,
        penalty=float(penalty),
    )


def candidate_certificates(
    datasets: Sequence[object],
    genes: tuple[Expr, ...],
    *,
    core_support_threshold: float = 0.60,
    exception_support_threshold: float = 0.80,
    sign_agreement_threshold: float = 0.50,
    z_threshold: float = 1.96,
    penalty_scale: float = 4.0,
) -> tuple[tuple[GeneCertificate, ...], int]:
    """Build coefficient certificates and serialized-byte accounting."""

    per_client = [_local_evidence(dataset, genes) for dataset in datasets]
    certificates: list[GeneCertificate] = []
    for gene_index, gene in enumerate(genes):
        certificates.append(
            _aggregate_gene_certificate(
                gene,
                [items[gene_index] for items in per_client],
                total_clients=len(datasets),
                core_support_threshold=core_support_threshold,
                exception_support_threshold=exception_support_threshold,
                sign_agreement_threshold=sign_agreement_threshold,
                z_threshold=z_threshold,
                penalty_scale=penalty_scale,
            )
        )
    # Per client: support, residual diagnostic, and for each gene coefficient,
    # standard error, z score, effective energy and observability flag.
    communication = sum(
        8 * (2 + 5 * len(genes))
        for _ in datasets
    )
    return tuple(certificates), communication


def _evaluate_candidate(
    datasets: Sequence[object],
    genes: tuple[Expr, ...],
    *,
    complexity_weight: float,
    worst_client_weight: float,
    core_support_threshold: float,
    exception_support_threshold: float,
    sign_agreement_threshold: float,
    z_threshold: float,
    penalty_scale: float,
) -> _CertifiedEvaluated:
    model, fit_bytes = _fit_federated(datasets, genes)
    base_objective, global_mse, worst_client_mse = _objective(
        model,
        datasets,
        complexity_weight=complexity_weight,
        worst_client_weight=worst_client_weight,
    )
    certificates, certificate_bytes = candidate_certificates(
        datasets,
        genes,
        core_support_threshold=core_support_threshold,
        exception_support_threshold=exception_support_threshold,
        sign_agreement_threshold=sign_agreement_threshold,
        z_threshold=z_threshold,
        penalty_scale=penalty_scale,
    )
    objective = base_objective + sum(item.penalty for item in certificates)
    return _CertifiedEvaluated(
        genes=genes,
        model=model,
        certificates=certificates,
        objective=float(objective),
        global_mse=global_mse,
        worst_client_mse=worst_client_mse,
        communication_bytes=fit_bytes + certificate_bytes,
    )


def _single_gene_screen(
    datasets: Sequence[object],
    library: tuple[Expr, ...],
    **evaluation_kwargs: float,
) -> tuple[list[_CertifiedEvaluated], int, int]:
    evaluated: list[_CertifiedEvaluated] = []
    communication = 0
    for gene in library:
        item = _evaluate_candidate(datasets, (gene,), **evaluation_kwargs)
        evaluated.append(item)
        communication += item.communication_bytes
    evaluated.sort(key=lambda item: item.objective)
    return evaluated, len(evaluated), communication


def _initial_population(
    screened: Sequence[_CertifiedEvaluated],
    library: tuple[Expr, ...],
    *,
    population_size: int,
    max_genes: int,
    rng: random.Random,
) -> list[tuple[Expr, ...]]:
    population: list[tuple[Expr, ...]] = []
    top_single = max(8, population_size // 3)
    population.extend(item.genes for item in screened[:top_single])
    promising = [item.genes[0] for item in screened[: min(80, len(screened))]]
    while len(population) < population_size:
        size = rng.randint(1, max_genes)
        pool = promising if rng.random() < 0.8 else list(library)
        genes = _normalize_genes(
            rng.sample(pool, k=min(size, len(pool))),
            max_genes,
        )
        if genes:
            population.append(genes)
    return population


def run_certificate_tree_search(
    datasets: Sequence[object],
    *,
    seed: int,
    population_size: int = 48,
    generations: int = 12,
    max_genes: int = 4,
    max_complexity: int = 7,
    elite_fraction: float = 0.20,
    complexity_weight: float = 0.015,
    worst_client_weight: float = 0.35,
    core_support_threshold: float = 0.60,
    exception_support_threshold: float = 0.80,
    sign_agreement_threshold: float = 0.50,
    z_threshold: float = 1.96,
    penalty_scale: float = 4.0,
    early_stop_mse: float = 1e-8,
) -> CertificateTreeOutput:
    """Run certificate-guided federated adaptive expression search."""

    if not datasets:
        raise ValueError("at least one client dataset is required")
    if population_size < 8 or generations < 1 or max_genes < 1:
        raise ValueError("invalid adaptive search budget")
    if not 0 < elite_fraction < 1:
        raise ValueError("elite_fraction must lie in (0, 1)")

    start = perf_counter()
    rng = random.Random(seed)
    n_features = int(np.asarray(datasets[0].x).shape[1])
    library = expression_library(
        n_features=n_features,
        max_complexity=max_complexity,
    )
    evaluation_kwargs = {
        "complexity_weight": complexity_weight,
        "worst_client_weight": worst_client_weight,
        "core_support_threshold": core_support_threshold,
        "exception_support_threshold": exception_support_threshold,
        "sign_agreement_threshold": sign_agreement_threshold,
        "z_threshold": z_threshold,
        "penalty_scale": penalty_scale,
    }
    screened, evaluations, communication = _single_gene_screen(
        datasets,
        library,
        **evaluation_kwargs,
    )
    population = _initial_population(
        screened,
        library,
        population_size=population_size,
        max_genes=max_genes,
        rng=rng,
    )
    best = screened[0]
    completed = 0
    stop_reason = "generation budget reached"

    for generation in range(1, generations + 1):
        completed = generation
        cache: dict[tuple[str, ...], _CertifiedEvaluated] = {}
        evaluated: list[_CertifiedEvaluated] = []
        for genes in population:
            key = tuple(gene.canonical() for gene in genes)
            if key not in cache:
                cache[key] = _evaluate_candidate(
                    datasets,
                    genes,
                    **evaluation_kwargs,
                )
                evaluations += 1
                communication += cache[key].communication_bytes
            evaluated.append(cache[key])
        evaluated.sort(key=lambda item: item.objective)
        if evaluated[0].objective < best.objective:
            best = evaluated[0]
        if best.global_mse <= early_stop_mse and all(
            certificate.penalty == 0.0 for certificate in best.certificates
        ):
            stop_reason = "target MSE reached with all certificates satisfied"
            break

        elite_count = max(2, int(math.ceil(elite_fraction * population_size)))
        elites = [item.genes for item in evaluated[:elite_count]]
        next_population = list(elites)
        while len(next_population) < population_size:
            if rng.random() < 0.45:
                child = _mutate(
                    rng.choice(elites),
                    library,
                    max_genes=max_genes,
                    rng=rng,
                )
            else:
                child = _crossover(
                    rng.choice(elites),
                    rng.choice(elites),
                    max_genes=max_genes,
                    rng=rng,
                )
                if rng.random() < 0.35:
                    child = _mutate(
                        child,
                        library,
                        max_genes=max_genes,
                        rng=rng,
                    )
            next_population.append(child)
        population = next_population

    final_model, final_fit_bytes = _fit_federated(datasets, best.genes)
    final_certificates, final_certificate_bytes = candidate_certificates(
        datasets,
        best.genes,
        core_support_threshold=core_support_threshold,
        exception_support_threshold=exception_support_threshold,
        sign_agreement_threshold=sign_agreement_threshold,
        z_threshold=z_threshold,
        penalty_scale=penalty_scale,
    )
    communication += final_fit_bytes + final_certificate_bytes
    local_mses = _client_mses(final_model, datasets)
    supports = np.asarray([len(dataset.y) for dataset in datasets], dtype=float)
    global_mse = float(np.average(local_mses, weights=supports))
    worst_client_mse = float(np.max(local_mses))
    base_objective, _, _ = _objective(
        final_model,
        datasets,
        complexity_weight=complexity_weight,
        worst_client_weight=worst_client_weight,
    )
    final_objective = base_objective + sum(
        certificate.penalty for certificate in final_certificates
    )
    return CertificateTreeOutput(
        method="certificate-guided-federated-tree",
        model=final_model,
        certificates=final_certificates,
        generations=completed,
        evaluations=evaluations,
        communication_bytes=communication,
        runtime_seconds=perf_counter() - start,
        stop_reason=stop_reason,
        objective=float(final_objective),
        global_mse=global_mse,
        worst_client_mse=worst_client_mse,
    )
