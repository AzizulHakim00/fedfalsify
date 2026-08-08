"""Completed Beijing study with a strong non-symbolic context baseline."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from . import external_beijing_study as _core
from .external_beijing_fixed import download_archive, prepare_archive
from .external_common import ExternalClientData, fit_standardization, regression_metrics, systematic_sample


def run_study(
    archive: Path,
    *,
    max_train_per_station: int = 2000,
    pysr_iterations: int = 20,
    run_pysr_baseline: bool = True,
    run_loso: bool = True,
):
    rows, summary = _core.run_study(
        archive,
        max_train_per_station=max_train_per_station,
        pysr_iterations=pysr_iterations,
        run_pysr_baseline=run_pysr_baseline,
        run_loso=run_loso,
    )
    from sklearn.ensemble import HistGradientBoostingRegressor

    stations = prepare_archive(archive)
    feature_indices = tuple(stations[0].feature_names.index(name) for name in _core.SELECTED_FEATURES)
    raw_train = []
    for station in stations:
        x, y = _core._select(station, "train", feature_indices)
        x, y = systematic_sample(x, y, max_train_per_station)
        raw_train.append(ExternalClientData(station.station, x, y))
    scaling = fit_standardization(raw_train)
    x_train = np.concatenate([scaling.transform_x(client.x) for client in raw_train])
    y_train = np.concatenate([scaling.transform_y(client.y) for client in raw_train])
    model = HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=0.06,
        max_iter=250,
        max_leaf_nodes=31,
        l2_regularization=1e-3,
        random_state=12002,
    )
    start = perf_counter()
    model.fit(x_train, y_train)
    runtime = perf_counter() - start
    for station in stations:
        x_test, y_test = _core._select(station, "test", feature_indices)
        predicted = scaling.inverse_y(model.predict(scaling.transform_x(x_test)))
        metrics = regression_metrics(y_test, predicted)
        rows.append(_core.BeijingResultRow(
            station.station,
            "pooled-hist-gradient-boosting",
            "test",
            len(y_test),
            metrics["mae"],
            metrics["rmse"],
            metrics["nmse"],
            "non-symbolic HistGradientBoostingRegressor",
            -1,
            runtime,
            0,
            True,
            "predictive context baseline; not an interpretable equation",
        ))
    summary["methods"] = _core._summary(rows)
    summary["scientific_boundary"].append(
        "Histogram gradient boosting is a predictive context baseline, not a symbolic claim."
    )
    return rows, summary


def main() -> None:
    args = _core.build_parser().parse_args()
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
    print(f"Wrote {len(rows)} completed Beijing result rows")


if __name__ == "__main__":
    main()
