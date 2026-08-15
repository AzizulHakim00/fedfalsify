"""Structure-preserving SRSD external validation wrapper."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
import numpy as np

from . import external_srsd_study as _core
from .basis import BasisTerm
from .baselines import centralized_forward, fedfalsify_method, score_only_federated
from .client import FederatedFalsifierClient
from .external_common import FlexibleTermCatalog, fit_standardization, regression_metrics, standardized_clients
from .pysr_adapter import run_pysr


@dataclass(frozen=True)
class CorrectedProblemSpec:
    problem: str
    true_variables: int
    truth_name: str
    truth_display: str

    def truth_values(self, x: np.ndarray) -> np.ndarray:
        if self.problem in {"feynman-i.12.1", "feynman-i.14.3"}:
            return x[:, 0] * x[:, 1]
        if self.problem == "feynman-i.18.12":
            return x[:, 0] * x[:, 1] * np.sin(x[:, 2])
        if self.problem == "feynman-ii.15.4":
            return x[:, 0] * x[:, 1] * np.cos(x[:, 2])
        if self.problem == "feynman-ii.27.18":
            return x[:, 0] ** 2
        raise KeyError(self.problem)


PROBLEMS = (
    CorrectedProblemSpec("feynman-i.12.1", 2, "truth_product", "x0·x1"),
    CorrectedProblemSpec("feynman-i.14.3", 2, "truth_gravity_product", "m·z"),
    CorrectedProblemSpec("feynman-i.18.12", 3, "truth_sine_product", "r·F·sin(theta)"),
    CorrectedProblemSpec("feynman-ii.15.4", 3, "truth_cosine_product", "mu·B·cos(theta)"),
    CorrectedProblemSpec("feynman-ii.27.18", 1, "truth_square", "E²"),
)


def build_catalog(spec, feature_count: int, scaling, *, include_truth: bool) -> FlexibleTermCatalog:
    means = np.asarray(scaling.x_mean, dtype=float)
    scales = np.asarray(scaling.x_scale, dtype=float)

    def physical(x: np.ndarray) -> np.ndarray:
        return np.asarray(x, dtype=float) * scales + means

    terms: list[BasisTerm] = [BasisTerm("1", lambda x: np.ones(len(x)), 1, "1")]
    if include_truth:
        terms.append(BasisTerm(
            spec.truth_name,
            lambda x, problem=spec: problem.truth_values(physical(x)),
            3,
            spec.truth_display,
        ))
    for index in range(feature_count):
        prefix = "dummy" if index >= spec.true_variables else "x"
        name = f"{prefix}{index}"
        terms.append(BasisTerm(name, lambda x, i=index: physical(x)[:, i], 1, name))
        exact_square = (
            not include_truth
            and spec.problem == "feynman-ii.27.18"
            and index == 0
        )
        if not exact_square:
            terms.append(BasisTerm(
                f"{name}^2",
                lambda x, i=index: physical(x)[:, i] ** 2,
                2,
                f"{name}²",
            ))
        terms.extend([
            BasisTerm(f"sin({name})", lambda x, i=index: np.sin(physical(x)[:, i]), 2, f"sin({name})"),
            BasisTerm(f"cos({name})", lambda x, i=index: np.cos(physical(x)[:, i]), 2, f"cos({name})"),
        ])
    product_truth_problems = {"feynman-i.12.1", "feynman-i.14.3"}
    for left in range(feature_count):
        for right in range(left + 1, feature_count):
            exact_product = (
                not include_truth
                and spec.problem in product_truth_problems
                and left == 0
                and right == 1
            )
            if exact_product:
                continue
            name = f"v{left}*v{right}"
            terms.append(BasisTerm(
                name,
                lambda x, a=left, b=right: physical(x)[:, a] * physical(x)[:, b],
                2,
                name,
            ))
    return FlexibleTermCatalog(terms)


def run_problem(cache_dir, spec, *, pysr_iterations: int = 30):
    files = _core.ensure_problem_files(cache_dir, spec)
    x_train, y_train = _core._load(files["train"], spec.true_variables)
    x_test, y_test = _core._load(files["test"], spec.true_variables)
    x_train = _core._with_dummies(x_train, seed=12001 + sum(map(ord, spec.problem)))
    x_test = _core._with_dummies(x_test, seed=12031 + sum(map(ord, spec.problem)))
    raw_clients = _core._clients(x_train, y_train)
    scaling = fit_standardization(raw_clients)
    train_clients = standardized_clients(raw_clients, scaling)
    rows = []

    for condition, include_truth in (("truth-supported", True), ("catalog-misspecified", False)):
        catalog = build_catalog(spec, x_train.shape[1], scaling, include_truth=include_truth)
        federated = [FederatedFalsifierClient(client, catalog) for client in train_clients]
        fed = fedfalsify_method(
            federated, catalog, max_terms=5, target_mse=1e-8,
            min_repair_score=0.02,
        )
        rows.append(_core._row_from_candidate(
            spec=spec, method="fedfalsify", condition=condition,
            candidate=fed.candidate, catalog=catalog, train_clients=train_clients,
            x_test=x_test, y_test=y_test, scaling=scaling,
            runtime=fed.runtime_seconds, communication=fed.communication_bytes,
            raw_data_pooled=False, note=fed.stop_reason,
        ))
        central = centralized_forward(train_clients, catalog, max_terms=5, min_improvement=1e-8)
        rows.append(_core._row_from_candidate(
            spec=spec, method="centralized-forward", condition=condition,
            candidate=central.candidate, catalog=catalog, train_clients=train_clients,
            x_test=x_test, y_test=y_test, scaling=scaling,
            runtime=central.runtime_seconds, communication=0,
            raw_data_pooled=True, note=central.stop_reason,
        ))
        score = score_only_federated(federated, catalog, max_terms=5, min_improvement=1e-8)
        rows.append(_core._row_from_candidate(
            spec=spec, method="score-only-federated", condition=condition,
            candidate=score.candidate, catalog=catalog, train_clients=train_clients,
            x_test=x_test, y_test=y_test, scaling=scaling,
            runtime=score.runtime_seconds, communication=score.communication_bytes,
            raw_data_pooled=False, note=score.stop_reason,
        ))

    pysr = run_pysr(
        train_clients, scaling.transform_x(x_test),
        seed=12021 + sum(map(ord, spec.problem)),
        niterations=pysr_iterations, populations=4, population_size=30, maxsize=20,
    )
    if not pysr.available:
        raise RuntimeError(pysr.note)
    metrics = regression_metrics(y_test, scaling.inverse_y(pysr.predictions))
    dummy_names = [f"x{index + 1}" for index in range(spec.true_variables, x_train.shape[1])]
    rows.append(_core.SRSDResultRow(
        spec.problem, "official-pysr", "adaptive-search", 4, len(y_train), len(y_test),
        float("nan"), float(metrics["nmse"] <= 1e-6), float(metrics["nmse"] <= 1e-4),
        metrics["nmse"], metrics["rmse"], pysr.equation, len(pysr.equation),
        sum(name in pysr.equation for name in dummy_names),
        pysr.runtime_seconds, 0, True, pysr.note,
    ))
    manifest = {
        "problem": spec.problem,
        "dataset_repository": _core.DATASET_REPOSITORY,
        "files": {split: {"path": str(path), "sha256": _core._sha256(path)} for split, path in files.items()},
        "true_variables": spec.true_variables,
        "appended_dummy_variables": 3,
        "client_definition": "quartiles of the first physical input on official training data",
        "official_split_retained": True,
        "structure_preserving_scaling": "true catalog term reconstructs original physical coordinates",
        "fixed_physical_constants": "absorbed into the fitted scalar coefficient",
        "misspecification_rule": "remove the named truth term and any algebraically identical catalog duplicate",
    }
    return rows, manifest


def main() -> None:
    args = _core.build_parser().parse_args()
    rows = []
    manifests = []
    for spec in PROBLEMS:
        problem_rows, manifest = run_problem(args.cache_dir, spec, pysr_iterations=args.pysr_iterations)
        rows.extend(problem_rows)
        manifests.append(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].to_dict()))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)
    summary = {
        "schema_version": 3,
        "status": "external-validation",
        "dataset": "SRSD-Feynman Easy",
        "license": "CC BY 4.0",
        "problems": [spec.problem for spec in PROBLEMS],
        "rows": len(rows),
        "methods": _core.summarize(rows),
        "manifests": manifests,
        "scientific_boundary": [
            "The supported FedFalsify catalog contains one composite ground-truth term.",
            "The misspecified condition removes that term and algebraically identical duplicates without retuning.",
            "Fixed physical constants are learned through the fitted scalar coefficient.",
            "Physical equations are evaluated after reversing training-only input scaling.",
            "PySR searches adaptively over shared primitive operators.",
            "Dummy variables are deterministic study augmentations, not original SRSD columns.",
        ],
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {len(rows)} structure-preserving SRSD result rows")


if __name__ == "__main__":
    main()
