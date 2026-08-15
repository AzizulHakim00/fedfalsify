from __future__ import annotations

import csv
import io
from pathlib import Path
import zipfile

import numpy as np

from fedfalsify.external_beijing import (
    NUMERIC_FEATURES,
    build_manifest,
    feature_names,
    prepare_archive,
)


def _station_csv(station: str, *, future_extreme: bool = False) -> str:
    output = io.StringIO()
    fieldnames = [
        "No",
        "year",
        "month",
        "day",
        "hour",
        "PM2.5",
        *NUMERIC_FEATURES,
        "wd",
        "station",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for index in range(20):
        pm10 = 10.0 + index
        if future_extreme and index >= 16:
            pm10 = 10000.0
        row = {
            "No": index + 1,
            "year": 2013,
            "month": 3,
            "day": 1,
            "hour": index,
            "PM2.5": 20.0 + index,
            "PM10": pm10,
            "SO2": "NA" if index == 3 else 2.0 + index,
            "NO2": 3.0 + index,
            "CO": 400.0 + index,
            "O3": 5.0 + index,
            "TEMP": -2.0 + index,
            "PRES": 1000.0 + index,
            "DEWP": -10.0 + index,
            "RAIN": 0.0,
            "WSPM": 1.0 + index / 10.0,
            "wd": "N" if index != 4 else "NA",
            "station": station,
        }
        writer.writerow(row)
    return output.getvalue()


def _archive(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "PRSA_Data_Alpha_20130301-20170228.csv",
            _station_csv("Alpha", future_extreme=True),
        )
        archive.writestr(
            "PRSA_Data_Beta_20130301-20170228.csv",
            _station_csv("Beta"),
        )
    return path


def test_prepare_archive_uses_natural_clients_and_chronological_splits(
    tmp_path: Path,
) -> None:
    archive = _archive(tmp_path / "beijing.zip")
    clients = prepare_archive(
        archive,
        train_fraction=0.60,
        validation_fraction=0.20,
        min_usable_rows=10,
        require_expected_station_count=False,
    )
    assert [client.station for client in clients] == ["Alpha", "Beta"]
    alpha = clients[0]
    assert len(alpha.train.y) == 12
    assert len(alpha.validation.y) == 4
    assert len(alpha.test.y) == 4
    assert alpha.train.timestamps[-1] < alpha.validation.timestamps[0]
    assert alpha.validation.timestamps[-1] < alpha.test.timestamps[0]
    assert alpha.train.x.shape[1] == len(feature_names())
    assert np.all(np.isfinite(alpha.train.x))
    assert np.all(np.isfinite(alpha.validation.x))
    assert np.all(np.isfinite(alpha.test.x))


def test_future_values_do_not_change_training_median(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "beijing.zip")
    clients = prepare_archive(
        archive,
        min_usable_rows=10,
        require_expected_station_count=False,
    )
    alpha = next(client for client in clients if client.station == "Alpha")
    beta = next(client for client in clients if client.station == "Beta")
    pm10_index = NUMERIC_FEATURES.index("PM10")
    assert alpha.training_medians[pm10_index] == beta.training_medians[pm10_index]
    assert alpha.training_medians[pm10_index] < 100.0


def test_missing_predictor_is_imputed_and_flagged(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "beijing.zip")
    client = prepare_archive(
        archive,
        min_usable_rows=10,
        require_expected_station_count=False,
    )[0]
    names = client.feature_names
    so2 = names.index("so2")
    so2_missing = names.index("so2_missing")
    assert np.isfinite(client.train.x[3, so2])
    assert client.train.x[3, so2_missing] == 1.0
    assert client.train.x[2, so2_missing] == 0.0


def test_manifest_records_client_split_and_archive_hash(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "beijing.zip")
    clients = prepare_archive(
        archive,
        min_usable_rows=10,
        require_expected_station_count=False,
    )
    manifest = build_manifest(
        archive,
        clients,
        train_fraction=0.60,
        validation_fraction=0.20,
    )
    assert manifest["station_count"] == 2
    assert len(manifest["archive_sha256"]) == 64
    assert manifest["split"]["type"] == "chronological within station"
    assert manifest["preprocessing"]["numeric_imputation"].endswith("only")
