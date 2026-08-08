"""External ground-truth validation on selected official SRSD-Feynman data.

Five physics equations are downloaded from the official Hugging Face dataset.
Clients are fixed by quartiles of the first physical variable, and deterministic
irrelevant variables are appended as a variable-selection stress test.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from time import perf_counter
from urllib.request import urlopen

import numpy as np

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


DATASET_REPOSITORY = "yoshitomo-matsubara/srsd-feynman_easy"
BASE_URL = f"https://huggingface.co/datasets/{DATASET_REPOSITORY}/resolve/main"


@dataclass(frozen=True)
class ProblemSpec:
    problem: str
    true_variables: int
    truth_name: str
    truth_display: str

    def truth_values(self, x: np.ndarray) -> np.ndarray:
        if self.problem == "feynman-i.12.1":
            return x[:, 0] * x[:, 1]
        if self.problem == "feynman-i.14.3":
            return x[:, 0] * x[:, 1] * x[:, 2]
        if self.problem == "feynman-i.18.12":
            return x[:, 0] * x[:, 1] * np.sin(x[:, 2])
        if self.problem == "feynman-ii.15.4":
            return x[:, 0] * x[:, 1] * np.cos(x[:, 2])
        if self.problem == "feynman-ii.27.18":
            return x[:, 0] * x[:, 1] ** 2
        raise KeyError(self.problem)


PROBLEMS = (
    ProblemSpec("feynman-i.12.1", 2, "truth_product", "x0·x1"),
    ProblemSpec("feynman-i.14.3", 3, "truth_triple", "x0·x1·x2"),
    ProblemSpec("feynman-i.18.12", 3, "truth_sine_product", "x0·x1·sin(x2)"),
    ProblemSpec("feynman-ii.15.4", 3, "truth_cosine_product", "x0·x1·cos(x2)"),
    ProblemSpec("feynman-ii.27.18", 2, "truth_square_product", "x0·x1²"),
)


@dataclass(frozen=True)
class SRSDResultRow:
    problem: str
    method: str
    catalog_condition: str
    clients: int
    train_rows: int
    test_rows: int
    strict_exact_recovery: float
    semantic_1e6: float
    semantic_1e4: float
    test_nmse: float
    test_rmse: float
    expression: str
    complexity: int
    dummy_terms_selected: int
    runtime_seconds: float
    communication_bytes: int
    raw_data_pooled: bool
    note: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _download(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination
    temporary = destination.with_suffix(destination.suffix + ".part")
    with urlopen(url, timeout=120) as response, temporary.open("wb") as handle:
        while True:
            block = response.read(1024 * 1024)
            if not block:
                break
            handle.write(block)
    temporary.replace(destination)
    return destination


def _sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def ensure_problem_files(cache_dir: Path, spec: ProblemSpec) -> dict[str, Path]:
    files = {}
    for split in ("train", "val", "test"):
        path = cache_dir / split / f"{spec.problem}.txt"
        files[split] = _download(f"{BASE_URL}/{split}/{spec.problem}.txt", path)
    return files


def _load(path: Path, true_variables: int) -> tuple[np.ndarray, np.ndarray]:
    matrix = np.loadtxt(path, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != true_variables + 1:
        raise ValueError(
            f"{path.name} expected {true_variables} inputs plus target, got {matrix.shape}"
        )
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"non-finite SRSD values in {path}")
    return matrix[:, :-1], matrix[:, -1]


def _with_dummies(x: np.ndarray, *, seed: int, count: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    dummy = rng.normal(0.0, 1.0, size=(len(x), count))
    return np.column_stack([x, dummy])


def _clients(x: np.ndarray, y: np.ndarray) -> list[ExternalClientData]:
    edges = np.quantile(x[:, 0], [0.0, 0.25, 0.5, 0.75, 1.0])
    clients = []
    for index in range(4):
        if index == 3:
            mask = (x[:, 0] >= edges[index]) & (x[:, 0] <= edges[index + 1])
        else:
            mask = (x[:, 0] >= edges[index]) & (x[:, 0] < edges[index + 1])
        clients.append(ExternalClientData(f"domain-q{index + 1}", x[mask], y[mask]))
    return clients


def build_catalog(spec: ProblemSpec, feature_count: int, *, include_truth: bool) -> FlexibleTermCatalog:
    terms: list[BasisTerm] = [BasisTerm("1", lambda x: np.ones(len(x)), 1, "1")]
    if include_truth:
        terms.append(BasisTerm(
            spec.truth_name,
            lambda x, problem=spec: problem.truth_values(x),
            3,
            spec.truth_display,
        ))
    for index in range(feature_count):
        prefix = "dummy" if index >= spec.true_variables else "x"
        name = f"{prefix}{index}"
        terms.extend([
            BasisTerm(name, lambda x, i=index: x[:, i], 1, name),
            BasisTerm(f"{name}^2", lambda x, i=index: x[:, i] ** 2, 2, f"{name}²"),
            BasisTerm(f"sin({name})", lambda x, i=index: np.sin(x[:, i]), 2, f"sin({name})"),
            BasisTerm(f"cos({name})", lambda x, i=index: np.cos(x[:, i]), 2, f"cos({name})"),
        ])
    for left in range(feature_count):
        for right in range(left + 1, feature_count):
            if spec.problem == "feynman-i.12.1" and left == 0 and right == 1:
                continue
            name = f"v{left}*v{right}"
            terms.append(BasisTerm(
                name,
                lambda x, a=left, b=right: x[:, a] * x[:, b],
                2,
                name,
            ))
    return FlexibleTermCatalog(terms)


def _row_from_candidate(
    *, spec: ProblemSpec, method: str, condition: str, candidate, catalog,
    train_clients, x_test, y_test, scaling, runtime: float, communication: int,
    raw_data_pooled: bool, note: str,
) -> SRSDResultRow:
    predicted = scaling.inverse_y(candidate.predict(scaling.transform_x(x_test), catalog))
    metrics = regression_metrics(y_test, predicted)
    active = {name for name, coefficient in zip(candidate.active_terms, candidate.coefficients) if name != "1" and abs(coefficient) >= 1e-3}
    strict = float(condition == "truth-supported" and active == {spec.truth_name})
    expression = candidate.expression(catalog)
    dummy = sum("dummy" in name for name in active)
    return SRSDResultRow(
        spec.problem, method, condition, len(train_clients),
        sum(len(client.y) for client in train_clients), len(y_test),
        strict, float(metrics["nmse"] <= 1e-6), float(metrics["nmse"] <= 1e-4),
        metrics["nmse"], metrics["rmse"], expression,
        catalog.complexity(candidate.active_terms), dummy, runtime, communication,
        raw_data_pooled, note,
    )


def run_problem(cache_dir: Path, spec: ProblemSpec, *, pysr_iterations: int = 30) -> tuple[list[SRSDResultRow], dict[str, object]]:
    files = ensure_problem_files(cache_dir, spec)
    x_train, y_train = _load(files["train"], spec.true_variables)
    x_test, y_test = _load(files["test"], spec.true_variables)
    x_train = _with_dummies(x_train, seed=12001 + sum(map(ord, spec.problem)))
    x_test = _with_dummies(x_test, seed=12031 + sum(map(ord, spec.problem)))
    raw_clients = _clients(x_train, y_train)
    scaling = fit_standardization(raw_clients)
    train_clients = standardized_clients(raw_clients, scaling)
    rows: list[SRSDResultRow] = []

    for condition, include_truth in (("truth-supported", True), ("catalog-misspecified", False)):
        catalog = build_catalog(spec, x_train.shape[1], include_truth=include_truth)
        federated = [FederatedFalsifierClient(client, catalog) for client in train_clients]
        fed = fedfalsify_method(
            federated, catalog, max_terms=5, target_mse=1e-8,
            min_repair_score=0.02,
        )
        rows.append(_row_from_candidate(
            spec=spec, method="fedfalsify", condition=condition,
            candidate=fed.candidate, catalog=catalog, train_clients=train_clients,
            x_test=x_test, y_test=y_test, scaling=scaling,
            runtime=fed.runtime_seconds, communication=fed.communication_bytes,
            raw_data_pooled=False, note=fed.stop_reason,
        ))
        central = centralized_forward(train_clients, catalog, max_terms=5, min_improvement=1e-8)
        rows.append(_row_from_candidate(
            spec=spec, method="centralized-forward", condition=condition,
            candidate=central.candidate, catalog=catalog, train_clients=train_clients,
            x_test=x_test, y_test=y_test, scaling=scaling,
            runtime=central.runtime_seconds, communication=0,
            raw_data_pooled=True, note=central.stop_reason,
        ))
        score = score_only_federated(federated, catalog, max_terms=5, min_improvement=1e-8)
        rows.append(_row_from_candidate(
            spec=spec, method="score-only-federated", condition=condition,
            candidate=score.candidate, catalog=catalog, train_clients=train_clients,
            x_test=x_test, y_test=y_test, scaling=scaling,
            runtime=score.runtime_seconds, communication=score.communication_bytes,
            raw_data_pooled=False, note=score.stop_reason,
        ))

    x_test_scaled = scaling.transform_x(x_test)
    pysr = run_pysr(
        train_clients, x_test_scaled, seed=12021 + sum(map(ord, spec.problem)),
        niterations=pysr_iterations, populations=4, population_size=30, maxsize=20,
    )
    if not pysr.available:
        raise RuntimeError(pysr.note)
    prediction = scaling.inverse_y(pysr.predictions)
    metrics = regression_metrics(y_test, prediction)
    dummy_names = [f"x{index + 1}" for index in range(spec.true_variables, x_train.shape[1])]
    dummy_count = sum(name in pysr.equation for name in dummy_names)
    rows.append(SRSDResultRow(
        spec.problem, "official-pysr", "adaptive-search", 4, len(y_train), len(y_test),
        float("nan"), float(metrics["nmse"] <= 1e-6), float(metrics["nmse"] <= 1e-4),
        metrics["nmse"], metrics["rmse"], pysr.equation, len(pysr.equation),
        dummy_count, pysr.runtime_seconds, 0, True, pysr.note,
    ))
    manifest = {
        "problem": spec.problem,
        "dataset_repository": DATASET_REPOSITORY,
        "files": {split: {"path": str(path), "sha256": _sha256(path)} for split, path in files.items()},
        "true_variables": spec.true_variables,
        "appended_dummy_variables": 3,
        "client_definition": "quartiles of the first physical input on official training data",
        "official_split_retained": True,
    }
    return rows, manifest


def summarize(rows: list[SRSDResultRow]) -> dict[str, object]:
    methods = sorted({row.method for row in rows})
    return {
        method: {
            "runs": len([row for row in rows if row.method == method]),
            "mean_test_nmse": float(np.mean([row.test_nmse for row in rows if row.method == method])),
            "semantic_1e6_rate": float(np.mean([row.semantic_1e6 for row in rows if row.method == method])),
            "semantic_1e4_rate": float(np.mean([row.semantic_1e4 for row in rows if row.method == method])),
            "dummy_free_rate": float(np.mean([row.dummy_terms_selected == 0 for row in rows if row.method == method])),
        }
        for method in methods
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run selected SRSD external validation")
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/srsd-feynman_easy"))
    parser.add_argument("--pysr-iterations", type=int, default=30)
    parser.add_argument("--output", type=Path, default=Path("results/external_srsd/rows.csv"))
    parser.add_argument("--summary", type=Path, default=Path("results/external_srsd/summary.json"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows: list[SRSDResultRow] = []
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
        "schema_version": 1,
        "status": "external-validation",
        "dataset": "SRSD-Feynman Easy",
        "license": "CC BY 4.0",
        "problems": [spec.problem for spec in PROBLEMS],
        "rows": len(rows),
        "methods": summarize(rows),
        "manifests": manifests,
        "scientific_boundary": [
            "The supported FedFalsify catalog contains one composite ground-truth term.",
            "The misspecified condition removes that term without retuning.",
            "PySR searches adaptively over the shared primitive operators.",
            "Dummy variables are deterministic study augmentations, not original SRSD columns.",
        ],
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {len(rows)} SRSD result rows")


if __name__ == "__main__":
    main()
