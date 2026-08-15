"""Final SRSD external runner with training-only normalized basis columns.

V4 retains the five preregistered problems, client partitions, methods, seeds,
and PySR budget.  It repairs only a unit-sensitivity defect: finite-catalog
selection previously compared physical basis columns whose magnitudes differed
by many orders, so ridge regularization and score thresholds were not invariant
to scientific units.  Every non-constant basis column is now centered and
scaled from training clients only, while term names preserve structural identity.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from . import external_srsd_study as _core
from . import external_srsd_study_fixed as _fixed
from . import external_srsd_study_v3 as _v3
from .basis import BasisTerm
from .baselines import centralized_forward, fedfalsify_method, score_only_federated
from .client import FederatedFalsifierClient
from .external_common import (
    ExternalClientData,
    FlexibleTermCatalog,
    fit_standardization,
    regression_metrics,
    standardized_clients,
)
from .pysr_adapter import run_pysr


PROBLEMS = _v3.PROBLEMS


def normalize_catalog(
    catalog: FlexibleTermCatalog,
    training_clients: list[ExternalClientData],
) -> tuple[FlexibleTermCatalog, dict[str, dict[str, float]]]:
    """Standardize finite-catalog columns using training clients only."""

    normalized: list[BasisTerm] = []
    metadata: dict[str, dict[str, float]] = {}
    for name in catalog.names():
        term = catalog.get(name)
        if name == "1":
            normalized.append(term)
            metadata[name] = {"mean": 0.0, "scale": 1.0}
            continue
        values = [np.asarray(term.evaluate(client.x), dtype=float) for client in training_clients]
        total = sum(len(value) for value in values)
        mean = sum(float(value.sum()) for value in values) / total
        squared_deviation = sum(
            float(((value - mean) ** 2).sum()) for value in values
        )
        scale = float(np.sqrt(max(squared_deviation / total, 0.0)))
        if scale == 0.0:
            scale = 1.0
        normalized.append(BasisTerm(
            name,
            lambda x, raw=term, center=mean, spread=scale: (
                np.asarray(raw.evaluate(x), dtype=float) - center
            ) / spread,
            term.complexity,
            f"z({term.display})",
        ))
        metadata[name] = {"mean": float(mean), "scale": scale}
    return FlexibleTermCatalog(normalized), metadata


def _run_finite_condition(
    *,
    spec,
    condition: str,
    include_truth: bool,
    x_train: np.ndarray,
    x_test: np.ndarray,
    y_test: np.ndarray,
    scaling,
    training_clients: list[ExternalClientData],
):
    raw_catalog = _v3.build_catalog(
        spec, x_train.shape[1], scaling, include_truth=include_truth
    )
    catalog, term_scaling = normalize_catalog(raw_catalog, training_clients)
    federated = [FederatedFalsifierClient(client, catalog) for client in training_clients]
    rows = []

    fed = fedfalsify_method(
        federated,
        catalog,
        max_terms=5,
        target_mse=1e-8,
        min_repair_score=0.02,
    )
    rows.append(_core._row_from_candidate(
        spec=spec,
        method="fedfalsify",
        condition=condition,
        candidate=fed.candidate,
        catalog=catalog,
        train_clients=training_clients,
        x_test=x_test,
        y_test=y_test,
        scaling=scaling,
        runtime=fed.runtime_seconds,
        communication=fed.communication_bytes,
        raw_data_pooled=False,
        note=f"{fed.stop_reason}; training-only basis normalization",
    ))

    central = centralized_forward(
        training_clients, catalog, max_terms=5, min_improvement=1e-8
    )
    rows.append(_core._row_from_candidate(
        spec=spec,
        method="centralized-forward",
        condition=condition,
        candidate=central.candidate,
        catalog=catalog,
        train_clients=training_clients,
        x_test=x_test,
        y_test=y_test,
        scaling=scaling,
        runtime=central.runtime_seconds,
        communication=0,
        raw_data_pooled=True,
        note=f"{central.stop_reason}; training-only basis normalization",
    ))

    score = score_only_federated(
        federated, catalog, max_terms=5, min_improvement=1e-8
    )
    rows.append(_core._row_from_candidate(
        spec=spec,
        method="score-only-federated",
        condition=condition,
        candidate=score.candidate,
        catalog=catalog,
        train_clients=training_clients,
        x_test=x_test,
        y_test=y_test,
        scaling=scaling,
        runtime=score.runtime_seconds,
        communication=score.communication_bytes,
        raw_data_pooled=False,
        note=f"{score.stop_reason}; training-only basis normalization",
    ))
    return rows, term_scaling


def run_problem(cache_dir: Path, spec, *, pysr_iterations: int = 30):
    files = _core.ensure_problem_files(cache_dir, spec)
    x_train, y_train = _core._load(files["train"], spec.true_variables)
    x_test, y_test = _core._load(files["test"], spec.true_variables)
    x_train = _core._with_dummies(
        x_train, seed=12001 + sum(map(ord, spec.problem))
    )
    x_test = _core._with_dummies(
        x_test, seed=12031 + sum(map(ord, spec.problem))
    )
    raw_clients = _core._clients(x_train, y_train)
    scaling = fit_standardization(raw_clients)
    training_clients = standardized_clients(raw_clients, scaling)
    rows = []
    term_scaling_by_condition = {}

    for condition, include_truth in (
        ("truth-supported", True),
        ("catalog-misspecified", False),
    ):
        condition_rows, term_scaling = _run_finite_condition(
            spec=spec,
            condition=condition,
            include_truth=include_truth,
            x_train=x_train,
            x_test=x_test,
            y_test=y_test,
            scaling=scaling,
            training_clients=training_clients,
        )
        rows.extend(condition_rows)
        term_scaling_by_condition[condition] = term_scaling

    pysr = run_pysr(
        training_clients,
        scaling.transform_x(x_test),
        seed=12021 + sum(map(ord, spec.problem)),
        niterations=pysr_iterations,
        populations=4,
        population_size=30,
        maxsize=20,
    )
    if not pysr.available:
        raise RuntimeError(pysr.note)
    metrics = regression_metrics(y_test, scaling.inverse_y(pysr.predictions))
    dummy_names = [
        f"x{index + 1}"
        for index in range(spec.true_variables, x_train.shape[1])
    ]
    rows.append(_core.SRSDResultRow(
        spec.problem,
        "official-pysr",
        "adaptive-search",
        4,
        len(y_train),
        len(y_test),
        float("nan"),
        float(metrics["nmse"] <= 1e-6),
        float(metrics["nmse"] <= 1e-4),
        metrics["nmse"],
        metrics["rmse"],
        pysr.equation,
        len(pysr.equation),
        sum(name in pysr.equation for name in dummy_names),
        pysr.runtime_seconds,
        0,
        True,
        pysr.note,
    ))

    manifest = {
        "problem": spec.problem,
        "dataset_repository": _core.DATASET_REPOSITORY,
        "files": {
            split: {"path": str(path), "sha256": _core._sha256(path)}
            for split, path in files.items()
        },
        "true_variables": spec.true_variables,
        "appended_dummy_variables": 3,
        "client_definition": (
            "quartiles of the first physical input on official training data"
        ),
        "official_split_retained": True,
        "input_target_scaling": (
            "two-pass training-client aggregate standardization without "
            "absolute magnitude floors"
        ),
        "basis_scaling": (
            "every nonconstant finite-catalog term centered and scaled from "
            "training clients only"
        ),
        "fixed_physical_constants": (
            "absorbed into the fitted scalar coefficient"
        ),
        "misspecification_rule": (
            "remove the named truth term and algebraically identical aliases"
        ),
        "term_scaling": term_scaling_by_condition,
    }
    return rows, manifest


def main() -> None:
    args = _core.build_parser().parse_args()
    rows = []
    manifests = []
    for spec in PROBLEMS:
        problem_rows, manifest = run_problem(
            args.cache_dir, spec, pysr_iterations=args.pysr_iterations
        )
        rows.extend(problem_rows)
        manifests.append(manifest)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].to_dict()))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)

    summary = {
        "schema_version": 4,
        "status": "external-validation",
        "dataset": "SRSD-Feynman Easy",
        "license": "CC BY 4.0",
        "problems": [spec.problem for spec in PROBLEMS],
        "rows": len(rows),
        "methods": _core.summarize(rows),
        "manifests": manifests,
        "scientific_boundary": [
            "The supported finite catalog contains exactly one named truth term.",
            "The misspecified condition removes that term and identical aliases.",
            "Input, target, and finite basis scaling use training clients only.",
            "Term scaling changes numerical conditioning but not term identity.",
            "Fixed physical constants are learned through fitted coefficients.",
            "PySR searches adaptively over standardized primitive inputs.",
            "Dummy variables are deterministic augmentations, not original columns.",
        ],
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"Wrote {len(rows)} unit-invariant SRSD result rows")


if __name__ == "__main__":
    main()
