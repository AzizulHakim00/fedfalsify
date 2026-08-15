"""Controlled expression-tree symbolic-regression baselines.

The implementations are independent project baselines, not author-code
reproductions. They share one multi-gene expression-tree representation and
search budget so that centralized, federated aggregate-fitness, and residual-
counterexample variants can be compared without hidden grammar differences.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from time import perf_counter
from typing import Iterable, Literal, Sequence

import numpy as np

from .expression_tree import Expr, expression_library, expression_matrix, recognized_term

Array = np.ndarray
SearchMode = Literal["centralized", "federated", "counterexample"]


@dataclass(frozen=True)
class TreeModel:
    """Linear combination of evolved expression-tree genes."""

    genes: tuple[Expr, ...]
    intercept: float
    coefficients: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.genes) != len(self.coefficients):
            raise ValueError("each expression gene requires one coefficient")
        canonical = [gene.canonical() for gene in self.genes]
        if len(canonical) != len(set(canonical)):
            raise ValueError("duplicate genes are not allowed")

    def predict(self, x: Array) -> Array:
        if not self.genes:
            return np.full(x.shape[0], self.intercept, dtype=float)
        matrix = np.column_stack([gene.evaluate(x) for gene in self.genes])
        return self.intercept + matrix @ np.asarray(self.coefficients, dtype=float)

    def complexity(self) -> int:
        return 1 + sum(gene.complexity() for gene in self.genes)

    def active_terms(self, threshold: float = 1e-3) -> tuple[str, ...]:
        terms: list[str] = []
        for gene, coefficient in zip(self.genes, self.coefficients):
            if abs(coefficient) < threshold:
                continue
            terms.append(recognized_term(gene) or f"expr:{gene.canonical()}")
        return tuple(sorted(set(terms)))

    def expression(self, precision: int = 4) -> str:
        pieces = [f"{self.intercept:.{precision}g}"]
        for gene, coefficient in zip(self.genes, self.coefficients):
            if abs(coefficient) < 10 ** (-(precision + 1)):
                continue
            sign = "+" if coefficient >= 0 else "-"
            pieces.append(
                f" {sign} {abs(coefficient):.{precision}g}*{gene.display()}"
            )
        return "".join(pieces)


@dataclass(frozen=True)
class TreeSearchOutput:
    method: str
    model: TreeModel
    generations: int
    evaluations: int
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str


@dataclass(frozen=True)
class _Evaluated:
    genes: tuple[Expr, ...]
    model: TreeModel
    objective: float
    global_mse: float
    worst_client_mse: float
    communication_bytes: int


def _dataset_arrays(datasets: Sequence[object]) -> tuple[Array, Array]:
    x = np.concatenate([np.asarray(item.x, dtype=float) for item in datasets], axis=0)
    y = np.concatenate([np.asarray(item.y, dtype=float) for item in datasets], axis=0)
    return x, y


def _solve(gram: Array, target: Array, ridge: float = 1e-8) -> Array:
    regularizer = ridge * np.eye(gram.shape[0])
    regularizer[0, 0] = 0.0
    try:
        return np.linalg.solve(gram + regularizer, target)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(gram + regularizer) @ target


def _normalize_genes(genes: Iterable[Expr], max_genes: int) -> tuple[Expr, ...]:
    unique = {gene.canonical(): gene for gene in genes}
    ordered = tuple(unique[key] for key in sorted(unique))
    return ordered[:max_genes]


def _fit_centralized(
    datasets: Sequence[object],
    genes: tuple[Expr, ...],
    weights: Array | None = None,
) -> TreeModel:
    x, y = _dataset_arrays(datasets)
    design = expression_matrix(x, genes)
    if weights is None:
        gram = design.T @ design
        target = design.T @ y
    else:
        if weights.shape != y.shape:
            raise ValueError("weights must match pooled target shape")
        root = np.sqrt(np.maximum(weights, 0.0))
        weighted_design = design * root[:, None]
        weighted_target = y * root
        gram = weighted_design.T @ weighted_design
        target = weighted_design.T @ weighted_target
    coefficients = _solve(gram, target)
    return TreeModel(
        genes,
        float(coefficients[0]),
        tuple(float(value) for value in coefficients[1:]),
    )


def _fit_federated(
    datasets: Sequence[object], genes: tuple[Expr, ...]
) -> tuple[TreeModel, int]:
    width = len(genes) + 1
    gram = np.zeros((width, width), dtype=float)
    target = np.zeros(width, dtype=float)
    communication = 0
    for dataset in datasets:
        x = np.asarray(dataset.x, dtype=float)
        y = np.asarray(dataset.y, dtype=float)
        design = expression_matrix(x, genes)
        gram += design.T @ design
        target += design.T @ y
        # Gram, target, local support and one scalar diagnostic.
        communication += 8 * (width * width + width + 2)
    coefficients = _solve(gram, target)
    return (
        TreeModel(
            genes,
            float(coefficients[0]),
            tuple(float(value) for value in coefficients[1:]),
        ),
        communication,
    )


def _client_mses(model: TreeModel, datasets: Sequence[object]) -> Array:
    values = []
    for dataset in datasets:
        residual = np.asarray(dataset.y, dtype=float) - model.predict(
            np.asarray(dataset.x, dtype=float)
        )
        values.append(float(np.mean(residual**2)))
    return np.asarray(values, dtype=float)


def _objective(
    model: TreeModel,
    datasets: Sequence[object],
    *,
    complexity_weight: float,
    worst_client_weight: float,
) -> tuple[float, float, float]:
    local = _client_mses(model, datasets)
    supports = np.asarray([len(dataset.y) for dataset in datasets], dtype=float)
    global_mse = float(np.average(local, weights=supports))
    worst = float(np.max(local))
    score = (
        math.log(global_mse + 1e-12)
        + worst_client_weight * math.log(worst + 1e-12)
        + complexity_weight * model.complexity()
    )
    return float(score), global_mse, worst


def _evaluate(
    datasets: Sequence[object],
    genes: tuple[Expr, ...],
    *,
    mode: SearchMode,
    weights: Array | None,
    complexity_weight: float,
    worst_client_weight: float,
) -> _Evaluated:
    communication = 0
    if mode == "federated":
        model, communication = _fit_federated(datasets, genes)
    else:
        model = _fit_centralized(datasets, genes, weights=weights)
    objective, global_mse, worst = _objective(
        model,
        datasets,
        complexity_weight=complexity_weight,
        worst_client_weight=worst_client_weight,
    )
    return _Evaluated(
        genes,
        model,
        objective,
        global_mse,
        worst,
        communication,
    )


def _single_gene_screen(
    datasets: Sequence[object],
    library: tuple[Expr, ...],
    *,
    mode: SearchMode,
    weights: Array | None,
    complexity_weight: float,
    worst_client_weight: float,
) -> tuple[list[_Evaluated], int, int]:
    evaluated: list[_Evaluated] = []
    communication = 0
    for gene in library:
        item = _evaluate(
            datasets,
            (gene,),
            mode=mode,
            weights=weights,
            complexity_weight=complexity_weight,
            worst_client_weight=worst_client_weight,
        )
        evaluated.append(item)
        communication += item.communication_bytes
    evaluated.sort(key=lambda item: item.objective)
    return evaluated, len(evaluated), communication


def _initial_population(
    screened: Sequence[_Evaluated],
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
        genes = _normalize_genes(rng.sample(pool, k=min(size, len(pool))), max_genes)
        if genes:
            population.append(genes)
    return population


def _mutate(
    genes: tuple[Expr, ...],
    library: tuple[Expr, ...],
    *,
    max_genes: int,
    rng: random.Random,
) -> tuple[Expr, ...]:
    current = list(genes)
    choice = rng.random()
    if choice < 0.25 and len(current) > 1:
        del current[rng.randrange(len(current))]
    elif choice < 0.55 and len(current) < max_genes:
        current.append(rng.choice(library))
    else:
        if current:
            current[rng.randrange(len(current))] = rng.choice(library)
        else:
            current.append(rng.choice(library))
    return _normalize_genes(current, max_genes)


def _crossover(
    left: tuple[Expr, ...],
    right: tuple[Expr, ...],
    *,
    max_genes: int,
    rng: random.Random,
) -> tuple[Expr, ...]:
    union = list(_normalize_genes((*left, *right), max_genes * 2))
    if not union:
        return left
    size = rng.randint(1, min(max_genes, len(union)))
    return _normalize_genes(rng.sample(union, size), max_genes)


def _counterexample_weights(
    model: TreeModel,
    datasets: Sequence[object],
    previous: Array,
    *,
    fraction: float,
    boost: float,
) -> Array:
    x, y = _dataset_arrays(datasets)
    residual = np.abs(y - model.predict(x))
    count = max(1, int(math.ceil(fraction * residual.size)))
    threshold = float(np.partition(residual, residual.size - count)[residual.size - count])
    fresh = np.ones_like(residual)
    fresh[residual >= threshold] = 1.0 + boost
    updated = 0.5 * previous + 0.5 * fresh
    return updated / max(float(np.mean(updated)), 1e-12)


def run_tree_search(
    datasets: Sequence[object],
    *,
    mode: SearchMode,
    seed: int,
    population_size: int = 48,
    generations: int = 12,
    max_genes: int = 4,
    max_complexity: int = 7,
    elite_fraction: float = 0.20,
    complexity_weight: float = 0.015,
    worst_client_weight: float = 0.35,
    counterexample_fraction: float = 0.20,
    counterexample_boost: float = 4.0,
    early_stop_mse: float = 1e-8,
) -> TreeSearchOutput:
    """Run a deterministic-budget multi-gene expression-tree search."""

    if mode not in {"centralized", "federated", "counterexample"}:
        raise ValueError(f"unsupported search mode: {mode}")
    if population_size < 8 or generations < 1 or max_genes < 1:
        raise ValueError("invalid evolutionary search budget")
    if not 0 < elite_fraction < 1:
        raise ValueError("elite_fraction must lie in (0, 1)")

    start = perf_counter()
    rng = random.Random(seed)
    n_features = int(np.asarray(datasets[0].x).shape[1])
    library = expression_library(
        n_features=n_features,
        max_complexity=max_complexity,
    )
    pooled_size = sum(len(dataset.y) for dataset in datasets)
    weights = np.ones(pooled_size, dtype=float) if mode == "counterexample" else None

    screened, evaluations, communication = _single_gene_screen(
        datasets,
        library,
        mode=mode,
        weights=weights,
        complexity_weight=complexity_weight,
        worst_client_weight=worst_client_weight,
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
        cache: dict[tuple[str, ...], _Evaluated] = {}
        evaluated: list[_Evaluated] = []
        for genes in population:
            key = tuple(gene.canonical() for gene in genes)
            if key not in cache:
                cache[key] = _evaluate(
                    datasets,
                    genes,
                    mode=mode,
                    weights=weights,
                    complexity_weight=complexity_weight,
                    worst_client_weight=worst_client_weight,
                )
                evaluations += 1
                communication += cache[key].communication_bytes
            evaluated.append(cache[key])
        evaluated.sort(key=lambda item: item.objective)
        if evaluated[0].objective < best.objective:
            best = evaluated[0]
        if best.global_mse <= early_stop_mse:
            stop_reason = "target pooled MSE reached"
            break

        if mode == "counterexample":
            assert weights is not None
            weights = _counterexample_weights(
                best.model,
                datasets,
                weights,
                fraction=counterexample_fraction,
                boost=counterexample_boost,
            )

        elite_count = max(2, int(math.ceil(elite_fraction * population_size)))
        elites = [item.genes for item in evaluated[:elite_count]]
        next_population = list(elites)
        while len(next_population) < population_size:
            if rng.random() < 0.45:
                parent = rng.choice(elites)
                child = _mutate(parent, library, max_genes=max_genes, rng=rng)
            else:
                child = _crossover(
                    rng.choice(elites),
                    rng.choice(elites),
                    max_genes=max_genes,
                    rng=rng,
                )
                if rng.random() < 0.35:
                    child = _mutate(child, library, max_genes=max_genes, rng=rng)
            next_population.append(child)
        population = next_population

    # Refit the selected structure without counterexample weights for reporting.
    if mode == "federated":
        final_model, final_bytes = _fit_federated(datasets, best.genes)
        communication += final_bytes
    else:
        final_model = _fit_centralized(datasets, best.genes)

    method = {
        "centralized": "centralized-tree-gp",
        "federated": "federated-tree-gp-style",
        "counterexample": "centralized-residual-counterexample-gp",
    }[mode]
    return TreeSearchOutput(
        method=method,
        model=final_model,
        generations=completed,
        evaluations=evaluations,
        communication_bytes=communication,
        runtime_seconds=perf_counter() - start,
        stop_reason=stop_reason,
    )
