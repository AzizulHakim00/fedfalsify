"""Structure, coefficient, prediction and shortcut/exception metrics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .basis import CandidateEquation, TermCatalog
from .baselines import MethodOutput, pooled_mse
from .benchmarks import GeneratedBenchmark, generate_global_test_data


@dataclass(frozen=True)
class EvaluationRow:
    benchmark: str
    scenario: str
    noise_ratio: float
    seed: int
    method: str
    samples_per_client: int
    max_terms: int
    exact_recovery: float
    term_precision: float
    term_recall: float
    coefficient_relative_error: float
    train_mse: float
    test_nmse: float
    spurious_accepted: float
    exception_recovered: float
    rounds: int
    communication_bytes: int
    runtime_seconds: float
    discovered_terms: str
    stop_reason: str

    def to_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def _active(candidate: CandidateEquation, threshold: float = 1e-3) -> set[str]:
    return {
        term
        for term, coefficient in zip(candidate.active_terms, candidate.coefficients)
        if term != "1" and abs(coefficient) >= threshold
    }


def _candidate_metrics(
    candidate: CandidateEquation,
    generated: GeneratedBenchmark,
    catalog: TermCatalog,
    x_test: np.ndarray,
    y_test: np.ndarray,
) -> tuple[float, float, float, float, float, float, float, float, str]:
    predicted = _active(candidate)
    target = set(generated.target_terms)
    intersection = predicted & target
    precision = len(intersection) / len(predicted) if predicted else float(not target)
    recall = len(intersection) / len(target) if target else 1.0
    exact = float(predicted == target)

    predicted_coefficients = {
        term: coefficient
        for term, coefficient in zip(candidate.active_terms, candidate.coefficients)
        if term != "1"
    }
    target_coefficients = dict(generated.target_coefficients)
    union = sorted(set(predicted_coefficients) | set(target_coefficients))
    predicted_vector = np.asarray(
        [predicted_coefficients.get(term, 0.0) for term in union]
    )
    target_vector = np.asarray([target_coefficients.get(term, 0.0) for term in union])
    coefficient_error = float(
        np.linalg.norm(predicted_vector - target_vector)
        / max(np.linalg.norm(target_vector), 1e-12)
    )

    train_mse = pooled_mse(candidate, generated.clients, catalog)
    prediction = candidate.predict(x_test, catalog)
    test_nmse = float(
        np.mean((y_test - prediction) ** 2) / max(np.var(y_test), 1e-12)
    )
    spurious = float(bool({"x4", "x4^2"} & predicted))
    exception_term = "I(x3>1)*x3^2"
    exception_recovered = float(
        (exception_term in predicted)
        if generated.scenario == "exception"
        else (exception_term not in predicted)
    )
    return (
        exact,
        precision,
        recall,
        coefficient_error,
        train_mse,
        test_nmse,
        spurious,
        exception_recovered,
        ";".join(sorted(predicted)),
    )


def evaluate_output(
    output: MethodOutput,
    generated: GeneratedBenchmark,
    catalog: TermCatalog,
    *,
    noise_ratio: float,
    seed: int,
    samples_per_client: int,
    max_terms: int,
) -> EvaluationRow:
    x_test, y_test = generate_global_test_data(generated, seed=seed + 100_000)
    metrics = [
        _candidate_metrics(candidate, generated, catalog, x_test, y_test)
        for candidate in output.candidates
    ]
    numeric = np.asarray([items[:8] for items in metrics], dtype=float)
    discovered = " | ".join(items[8] for items in metrics)
    means = numeric.mean(axis=0)
    return EvaluationRow(
        benchmark=generated.spec.name,
        scenario=generated.scenario,
        noise_ratio=noise_ratio,
        seed=seed,
        method=output.method,
        samples_per_client=samples_per_client,
        max_terms=max_terms,
        exact_recovery=float(means[0]),
        term_precision=float(means[1]),
        term_recall=float(means[2]),
        coefficient_relative_error=float(means[3]),
        train_mse=float(means[4]),
        test_nmse=float(means[5]),
        spurious_accepted=float(means[6]),
        exception_recovered=float(means[7]),
        rounds=output.rounds,
        communication_bytes=output.communication_bytes,
        runtime_seconds=output.runtime_seconds,
        discovered_terms=discovered,
        stop_reason=output.stop_reason,
    )
