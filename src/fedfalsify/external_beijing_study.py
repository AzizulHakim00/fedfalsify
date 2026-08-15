"""End-to-end external validation on UCI Beijing multi-site air quality.

The primary task is contemporaneous PM2.5 association. One monitoring station
is one client. All preprocessing is fitted from chronological training periods,
and every compared method receives the same deterministic training rows.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from .basis import BasisTerm, CandidateEquation
from .baselines import (
    centralized_forward,
    fedfalsify_method,
    fit_pooled,
    local_forward,
    score_only_federated,
)
from .client import FederatedFalsifierClient
from .external_beijing_fixed import build_manifest, download_archive, prepare_archive
from .external_common import (
    ExternalClientData,
    FlexibleTermCatalog,
    cluster_bootstrap_mean,
    fit_standardization,
    regression_metrics,
    standardized_clients,
    systematic_sample,
)
from .pysr_adapter import run_pysr


SELECTED_FEATURES = (
    "pm10", "so2", "no2", "co", "o3", "temp", "pres", "dewp", "rain",
    "wspm", "hour_sin", "hour_cos", "month_sin", "month_cos",
)


@dataclass(frozen=True)
class BeijingResultRow:
    station: str
    method: str
    split: str
    rows: int
    mae: float
    rmse: float
    nmse: float
    expression: str
    complexity: int
    runtime_seconds: float
    communication_bytes: int
    raw_data_pooled: bool
    note: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _term(name: str, index: int, complexity: int = 1) -> BasisTerm:
    return BasisTerm(name, lambda x, i=index: x[:, i], complexity, name)


def build_catalog(feature_names: tuple[str, ...]) -> FlexibleTermCatalog:
    index = {name: feature_names.index(name) for name in feature_names}
    terms: list[BasisTerm] = [BasisTerm("1", lambda x: np.ones(len(x)), 1, "1")]
    for name in feature_names:
        terms.append(_term(name, index[name]))
    for name in ("pm10", "so2", "no2", "co", "o3", "temp", "dewp", "wspm"):
        i = index[name]
        terms.append(BasisTerm(f"{name}^2", lambda x, j=i: x[:, j] ** 2, 2, f"{name}²"))
    for left, right in (
        ("pm10", "co"), ("pm10", "no2"), ("pm10", "wspm"),
        ("no2", "o3"), ("temp", "dewp"), ("rain", "wspm"),
    ):
        i, j = index[left], index[right]
        terms.append(BasisTerm(
            f"{left}*{right}",
            lambda x, a=i, b=j: x[:, a] * x[:, b],
            2,
            f"{left}·{right}",
        ))
    return FlexibleTermCatalog(terms)


def _select(client, split: str, feature_indices: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray]:
    partition = getattr(client, split)
    return partition.x[:, feature_indices], partition.y


def _candidate_metrics(candidate, catalog, x, y, scaling) -> dict[str, float]:
    predicted = scaling.inverse_y(candidate.predict(scaling.transform_x(x), catalog))
    return regression_metrics(y, predicted)


def _summary(rows: list[BeijingResultRow]) -> dict[str, object]:
    methods = sorted({row.method for row in rows if row.split == "test"})
    result: dict[str, object] = {}
    for method in methods:
        subset = [row for row in rows if row.method == method and row.split == "test"]
        nmse = [row.nmse for row in subset]
        result[method] = {
            "stations": len(subset),
            "mean_mae": float(np.mean([row.mae for row in subset])),
            "mean_rmse": float(np.mean([row.rmse for row in subset])),
            "mean_nmse": float(np.mean(nmse)),
            "median_nmse": float(np.median(nmse)),
            "worst_station_nmse": float(np.max(nmse)),
            "cluster_bootstrap_mean_nmse": cluster_bootstrap_mean(nmse),
            "mean_runtime_seconds": float(np.mean([row.runtime_seconds for row in subset])),
            "communication_bytes": int(max(row.communication_bytes for row in subset)),
            "raw_data_pooled": bool(any(row.raw_data_pooled for row in subset)),
        }
    local = {row.station: row.nmse for row in rows if row.method == "local-only-forward" and row.split == "test"}
    for method in methods:
        if method == "local-only-forward" or not local:
            continue
        subset = [row for row in rows if row.method == method and row.split == "test"]
        result[method]["station_non_degradation_vs_local"] = float(np.mean([
            row.nmse <= local[row.station] for row in subset if row.station in local
        ]))
    loso = [row for row in rows if row.split == "loso-test"]
    if loso:
        result["leave_one_station_out"] = {
            method: {
                "stations": len([row for row in loso if row.method == method]),
                "mean_nmse": float(np.mean([row.nmse for row in loso if row.method == method])),
                "worst_station_nmse": float(np.max([row.nmse for row in loso if row.method == method])),
            }
            for method in sorted({row.method for row in loso})
        }
    return result


def run_study(
    archive: Path,
    *,
    max_train_per_station: int = 2000,
    pysr_iterations: int = 20,
    run_pysr_baseline: bool = True,
    run_loso: bool = True,
) -> tuple[list[BeijingResultRow], dict[str, object]]:
    stations = prepare_archive(archive)
    feature_indices = tuple(stations[0].feature_names.index(name) for name in SELECTED_FEATURES)
    raw_train: list[ExternalClientData] = []
    for station in stations:
        x, y = _select(station, "train", feature_indices)
        x, y = systematic_sample(x, y, max_train_per_station)
        raw_train.append(ExternalClientData(station.station, x, y))
    scaling = fit_standardization(raw_train)
    train = standardized_clients(raw_train, scaling)
    catalog = build_catalog(SELECTED_FEATURES)
    federated_clients = [FederatedFalsifierClient(client, catalog) for client in train]

    fitted: list[tuple[str, CandidateEquation, float, int, bool, str]] = []
    fed = fedfalsify_method(
        federated_clients, catalog, max_terms=6, target_mse=0.35,
        min_repair_score=0.025, use_coefficient_heterogeneity=True,
    )
    fitted.append(("fedfalsify", fed.candidate, fed.runtime_seconds, fed.communication_bytes, False, fed.stop_reason))
    pooled = centralized_forward(train, catalog, max_terms=6)
    fitted.append(("centralized-forward", pooled.candidate, pooled.runtime_seconds, 0, True, pooled.stop_reason))
    score = score_only_federated(federated_clients, catalog, max_terms=6)
    fitted.append(("score-only-federated", score.candidate, score.runtime_seconds, score.communication_bytes, False, score.stop_reason))
    linear_terms = ("1", *SELECTED_FEATURES)
    start = perf_counter()
    ridge_candidate = fit_pooled(train, catalog, linear_terms)
    fitted.append(("pooled-linear-ridge", ridge_candidate, perf_counter() - start, 0, True, "all standardized linear terms"))

    local_output = local_forward(train, catalog, max_terms=6)
    local_by_station = {candidate.candidate_id: candidate for candidate in local_output.candidates}

    rows: list[BeijingResultRow] = []
    for station in stations:
        x_test, y_test = _select(station, "test", feature_indices)
        for method, candidate, runtime, communication, pooled_raw, note in fitted:
            metrics = _candidate_metrics(candidate, catalog, x_test, y_test, scaling)
            rows.append(BeijingResultRow(
                station.station, method, "test", len(y_test), **metrics,
                expression=candidate.expression(catalog),
                complexity=catalog.complexity(candidate.active_terms),
                runtime_seconds=runtime, communication_bytes=communication,
                raw_data_pooled=pooled_raw, note=note,
            ))
        local_candidate = local_by_station[station.station]
        metrics = _candidate_metrics(local_candidate, catalog, x_test, y_test, scaling)
        rows.append(BeijingResultRow(
            station.station, "local-only-forward", "test", len(y_test), **metrics,
            expression=local_candidate.expression(catalog),
            complexity=catalog.complexity(local_candidate.active_terms),
            runtime_seconds=local_output.runtime_seconds / len(stations),
            communication_bytes=0, raw_data_pooled=False,
            note="trained only on the same station",
        ))

    if run_pysr_baseline:
        x_test_all = np.concatenate([
            scaling.transform_x(_select(station, "test", feature_indices)[0])
            for station in stations
        ])
        output = run_pysr(
            train, x_test_all, seed=12001, niterations=pysr_iterations,
            populations=4, population_size=30, maxsize=18,
        )
        if not output.available:
            raise RuntimeError(output.note)
        offset = 0
        for station in stations:
            _, y_test = _select(station, "test", feature_indices)
            count = len(y_test)
            predicted = scaling.inverse_y(output.predictions[offset:offset + count])
            offset += count
            metrics = regression_metrics(y_test, predicted)
            rows.append(BeijingResultRow(
                station.station, "official-pysr", "test", count, **metrics,
                expression=output.equation, complexity=len(output.equation),
                runtime_seconds=output.runtime_seconds, communication_bytes=0,
                raw_data_pooled=True, note=output.note,
            ))

    if run_loso:
        for held_out in stations:
            kept_raw = [client for client in raw_train if client.client_id != held_out.station]
            kept_scaling = fit_standardization(kept_raw)
            kept_train = standardized_clients(kept_raw, kept_scaling)
            kept_clients = [FederatedFalsifierClient(client, catalog) for client in kept_train]
            x_test, y_test = _select(held_out, "test", feature_indices)
            fed_loso = fedfalsify_method(
                kept_clients, catalog, max_terms=6, target_mse=0.35,
                min_repair_score=0.025,
            )
            central_loso = centralized_forward(kept_train, catalog, max_terms=6)
            for method, output in (("fedfalsify", fed_loso), ("centralized-forward", central_loso)):
                metrics = _candidate_metrics(output.candidate, catalog, x_test, y_test, kept_scaling)
                rows.append(BeijingResultRow(
                    held_out.station, method, "loso-test", len(y_test), **metrics,
                    expression=output.candidate.expression(catalog),
                    complexity=catalog.complexity(output.candidate.active_terms),
                    runtime_seconds=output.runtime_seconds,
                    communication_bytes=output.communication_bytes,
                    raw_data_pooled=method == "centralized-forward",
                    note="held station excluded from fitting",
                ))

    manifest = build_manifest(archive, stations, train_fraction=0.60, validation_fraction=0.20)
    summary = {
        "schema_version": 1,
        "status": "external-validation",
        "dataset_manifest": manifest,
        "task": "contemporaneous PM2.5 association",
        "selected_features": list(SELECTED_FEATURES),
        "training_rows": {client.client_id: len(client.y) for client in raw_train},
        "training_row_policy": f"chronological systematic sample capped at {max_train_per_station} per station",
        "scaling": asdict(scaling),
        "methods": _summary(rows),
        "scientific_boundary": [
            "Associational prediction, not causal pollution discovery.",
            "Station identity is not a predictor.",
            "All model comparisons use identical sampled training rows.",
            "Full chronological station test periods are retained.",
            "PySR and centralized methods pool training observations; FedFalsify does not.",
        ],
    }
    return rows, summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Beijing external validation")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--max-train-per-station", type=int, default=2000)
    parser.add_argument("--pysr-iterations", type=int, default=20)
    parser.add_argument("--skip-pysr", action="store_true")
    parser.add_argument("--skip-loso", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("results/external_beijing_study/rows.csv"))
    parser.add_argument("--summary", type=Path, default=Path("results/external_beijing_study/summary.json"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.download and not args.archive.exists():
        download_archive(args.archive)
    rows, summary = run_study(
        args.archive,
        max_train_per_station=args.max_train_per_station,
        pysr_iterations=args.pysr_iterations,
        run_pysr_baseline=not args.skip_pysr,
        run_loso=not args.skip_loso,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].to_dict()))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {len(rows)} Beijing result rows")


if __name__ == "__main__":
    main()
