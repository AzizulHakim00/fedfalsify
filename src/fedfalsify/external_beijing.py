"""Leakage-safe preparation of the UCI Beijing multi-site air-quality data.

The module prepares one natural federated client per monitoring station.  It
never randomizes time: each station is sorted chronologically, preprocessing is
fit on its training period only, and future rows do not influence training
medians.  This module prepares evidence; it does not claim causal air-pollution
discovery.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Iterable
from urllib.request import urlopen
import zipfile

import numpy as np


UCI_DATASET_ID = 501
UCI_ARCHIVE_URL = (
    "https://archive.ics.uci.edu/static/public/501/"
    "beijing%2Bmulti%2Bsite%2Bair%2Bquality%2Bdata.zip"
)
UCI_DOI = "10.24432/C5RK5G"
EXPECTED_STATIONS = 12
EXPECTED_RAW_ROWS = 420_768

NUMERIC_FEATURES = (
    "PM10",
    "SO2",
    "NO2",
    "CO",
    "O3",
    "TEMP",
    "PRES",
    "DEWP",
    "RAIN",
    "WSPM",
)
TARGET_NAME = "PM2.5"

_WIND_DIRECTIONS = (
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
)
_WIND_ANGLES = {
    direction: 2.0 * math.pi * index / len(_WIND_DIRECTIONS)
    for index, direction in enumerate(_WIND_DIRECTIONS)
}


@dataclass(frozen=True)
class PreparedPartition:
    x: np.ndarray
    y: np.ndarray
    timestamps: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.x.ndim != 2:
            raise ValueError("partition x must be two-dimensional")
        if self.y.ndim != 1 or len(self.y) != len(self.x):
            raise ValueError("partition y must match x rows")
        if len(self.timestamps) != len(self.y):
            raise ValueError("timestamps must match partition rows")
        if not np.all(np.isfinite(self.x)) or not np.all(np.isfinite(self.y)):
            raise ValueError("prepared partitions must be finite")


@dataclass(frozen=True)
class BeijingStationClient:
    station: str
    feature_names: tuple[str, ...]
    train: PreparedPartition
    validation: PreparedPartition
    test: PreparedPartition
    training_medians: tuple[float, ...]
    raw_rows: int
    dropped_missing_target: int

    def __post_init__(self) -> None:
        if len(self.feature_names) != self.train.x.shape[1]:
            raise ValueError("feature name count does not match x columns")
        if len(self.training_medians) != len(NUMERIC_FEATURES):
            raise ValueError("training median count is invalid")
        if min(len(self.train.y), len(self.validation.y), len(self.test.y)) < 1:
            raise ValueError("every chronological partition must contain data")


@dataclass(frozen=True)
class _RawRow:
    timestamp: datetime
    target: float
    numeric: tuple[float, ...]
    wind_direction: str | None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_archive(destination: Path, *, timeout: int = 120) -> Path:
    """Download the official UCI archive without silently replacing a file."""

    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(
            f"refusing to overwrite existing archive: {destination}"
        )
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        with urlopen(UCI_ARCHIVE_URL, timeout=timeout) as response:
            with temporary.open("wb") as handle:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    handle.write(block)
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def _parse_float(value: str | None) -> float:
    if value is None:
        return float("nan")
    text = value.strip()
    if not text or text.upper() == "NA":
        return float("nan")
    return float(text)


def _parse_timestamp(row: dict[str, str]) -> datetime:
    return datetime(
        int(row["year"]),
        int(row["month"]),
        int(row["day"]),
        int(row["hour"]),
        tzinfo=timezone.utc,
    )


def _station_from_name(name: str) -> str:
    stem = Path(name).stem
    prefix = "PRSA_Data_"
    suffix = "_20130301-20170228"
    if stem.startswith(prefix):
        stem = stem[len(prefix) :]
    if stem.endswith(suffix):
        stem = stem[: -len(suffix)]
    return stem


def _csv_members(archive: zipfile.ZipFile) -> list[str]:
    result = [
        name
        for name in archive.namelist()
        if Path(name).name.startswith("PRSA_Data_")
        and name.lower().endswith(".csv")
    ]
    return sorted(result)


def _read_station_rows(
    archive: zipfile.ZipFile,
    member: str,
) -> tuple[str, list[_RawRow], int, int]:
    station_from_file = _station_from_name(member)
    rows: list[_RawRow] = []
    raw_rows = 0
    dropped_target = 0
    with archive.open(member) as binary:
        text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(text)
        required = {
            "year",
            "month",
            "day",
            "hour",
            TARGET_NAME,
            "wd",
            *NUMERIC_FEATURES,
        }
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{member} is missing required columns: {sorted(missing)}")
        for record in reader:
            raw_rows += 1
            target = _parse_float(record.get(TARGET_NAME))
            if not np.isfinite(target):
                dropped_target += 1
                continue
            timestamp = _parse_timestamp(record)
            numeric = tuple(_parse_float(record.get(name)) for name in NUMERIC_FEATURES)
            direction_text = (record.get("wd") or "").strip().upper()
            direction = direction_text if direction_text in _WIND_ANGLES else None
            rows.append(_RawRow(timestamp, target, numeric, direction))
    rows.sort(key=lambda item: item.timestamp)
    station_values = {
        record_station
        for record_station in [station_from_file]
        if record_station
    }
    if len(station_values) != 1:
        raise ValueError(f"could not determine station for {member}")
    return station_from_file, rows, raw_rows, dropped_target


def _split_indices(
    count: int,
    *,
    train_fraction: float,
    validation_fraction: float,
) -> tuple[slice, slice, slice]:
    if count < 10:
        raise ValueError("station has fewer than 10 usable target rows")
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be in (0, 1)")
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be in (0, 1)")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train and validation fractions must leave a test period")
    train_end = max(1, int(math.floor(count * train_fraction)))
    validation_end = max(
        train_end + 1,
        int(math.floor(count * (train_fraction + validation_fraction))),
    )
    validation_end = min(validation_end, count - 1)
    return slice(0, train_end), slice(train_end, validation_end), slice(validation_end, count)


def _training_medians(rows: list[_RawRow]) -> np.ndarray:
    matrix = np.asarray([row.numeric for row in rows], dtype=float)
    medians = np.nanmedian(matrix, axis=0)
    if np.any(~np.isfinite(medians)):
        missing = [
            name
            for name, value in zip(NUMERIC_FEATURES, medians)
            if not np.isfinite(value)
        ]
        raise ValueError(
            "training period has no finite value for features: " + ", ".join(missing)
        )
    return medians


def feature_names() -> tuple[str, ...]:
    numeric = tuple(name.lower().replace(".", "_") for name in NUMERIC_FEATURES)
    missing = tuple(f"{name}_missing" for name in numeric)
    return (
        *numeric,
        *missing,
        "wind_sin",
        "wind_cos",
        "wind_missing",
        "hour_sin",
        "hour_cos",
        "month_sin",
        "month_cos",
    )


def _encode_rows(rows: list[_RawRow], medians: np.ndarray) -> PreparedPartition:
    encoded: list[list[float]] = []
    targets: list[float] = []
    timestamps: list[str] = []
    for row in rows:
        values = np.asarray(row.numeric, dtype=float)
        missing = ~np.isfinite(values)
        filled = np.where(missing, medians, values)
        if row.wind_direction is None:
            wind_sin, wind_cos, wind_missing = 0.0, 0.0, 1.0
        else:
            angle = _WIND_ANGLES[row.wind_direction]
            wind_sin, wind_cos, wind_missing = math.sin(angle), math.cos(angle), 0.0
        hour_angle = 2.0 * math.pi * row.timestamp.hour / 24.0
        month_angle = 2.0 * math.pi * (row.timestamp.month - 1) / 12.0
        encoded.append(
            [
                *filled.tolist(),
                *missing.astype(float).tolist(),
                wind_sin,
                wind_cos,
                wind_missing,
                math.sin(hour_angle),
                math.cos(hour_angle),
                math.sin(month_angle),
                math.cos(month_angle),
            ]
        )
        targets.append(row.target)
        timestamps.append(row.timestamp.isoformat())
    return PreparedPartition(
        np.asarray(encoded, dtype=float),
        np.asarray(targets, dtype=float),
        tuple(timestamps),
    )


def prepare_archive(
    archive_path: Path,
    *,
    train_fraction: float = 0.60,
    validation_fraction: float = 0.20,
    min_usable_rows: int = 1000,
    require_expected_station_count: bool = True,
) -> list[BeijingStationClient]:
    """Prepare chronological natural clients from the official archive."""

    archive_path = archive_path.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        members = _csv_members(archive)
        if require_expected_station_count and len(members) != EXPECTED_STATIONS:
            raise ValueError(
                f"expected {EXPECTED_STATIONS} station CSVs, found {len(members)}"
            )
        clients: list[BeijingStationClient] = []
        for member in members:
            station, rows, raw_rows, dropped_target = _read_station_rows(archive, member)
            if len(rows) < min_usable_rows:
                raise ValueError(
                    f"station {station} has {len(rows)} usable rows; "
                    f"minimum is {min_usable_rows}"
                )
            train_slice, validation_slice, test_slice = _split_indices(
                len(rows),
                train_fraction=train_fraction,
                validation_fraction=validation_fraction,
            )
            train_rows = rows[train_slice]
            validation_rows = rows[validation_slice]
            test_rows = rows[test_slice]
            medians = _training_medians(train_rows)
            clients.append(
                BeijingStationClient(
                    station=station,
                    feature_names=feature_names(),
                    train=_encode_rows(train_rows, medians),
                    validation=_encode_rows(validation_rows, medians),
                    test=_encode_rows(test_rows, medians),
                    training_medians=tuple(float(value) for value in medians),
                    raw_rows=raw_rows,
                    dropped_missing_target=dropped_target,
                )
            )
    stations = [client.station for client in clients]
    if len(stations) != len(set(stations)):
        raise ValueError("duplicate station names found")
    return sorted(clients, key=lambda item: item.station)


def build_manifest(
    archive_path: Path,
    clients: list[BeijingStationClient],
    *,
    train_fraction: float,
    validation_fraction: float,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "status": "prepared",
        "dataset": "UCI Beijing Multi-Site Air Quality",
        "uci_dataset_id": UCI_DATASET_ID,
        "doi": UCI_DOI,
        "archive_url": UCI_ARCHIVE_URL,
        "archive_sha256": sha256_file(archive_path),
        "license": "CC BY 4.0",
        "target": TARGET_NAME,
        "feature_names": list(feature_names()),
        "client_definition": "one nationally controlled monitoring station per client",
        "split": {
            "type": "chronological within station",
            "train_fraction": train_fraction,
            "validation_fraction": validation_fraction,
            "test_fraction": 1.0 - train_fraction - validation_fraction,
        },
        "preprocessing": {
            "numeric_imputation": "station training-period median only",
            "missingness_indicators": True,
            "wind_encoding": "16-direction sine/cosine plus missing indicator",
            "time_encoding": "cyclic hour and month",
            "target_missingness": "rows dropped before splitting",
            "scaling": "none; physical units retained",
        },
        "station_count": len(clients),
        "total_raw_rows": sum(client.raw_rows for client in clients),
        "total_dropped_missing_target": sum(
            client.dropped_missing_target for client in clients
        ),
        "total_prepared_rows": sum(
            len(client.train.y) + len(client.validation.y) + len(client.test.y)
            for client in clients
        ),
        "stations": {
            client.station: {
                "raw_rows": client.raw_rows,
                "dropped_missing_target": client.dropped_missing_target,
                "train_rows": len(client.train.y),
                "validation_rows": len(client.validation.y),
                "test_rows": len(client.test.y),
                "first_train_timestamp": client.train.timestamps[0],
                "last_train_timestamp": client.train.timestamps[-1],
                "first_validation_timestamp": client.validation.timestamps[0],
                "last_validation_timestamp": client.validation.timestamps[-1],
                "first_test_timestamp": client.test.timestamps[0],
                "last_test_timestamp": client.test.timestamps[-1],
                "training_medians": {
                    name: value
                    for name, value in zip(NUMERIC_FEATURES, client.training_medians)
                },
            }
            for client in clients
        },
        "scientific_boundary": [
            "Associational and predictive study; not a causal pollution model.",
            "Station and chronological partitions are fixed before model comparison.",
            "No future observation influences training preprocessing.",
            "External performance must be reported for every retained station."
        ],
    }


def _write_npz(output_dir: Path, clients: Iterable[BeijingStationClient]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for client in clients:
        np.savez_compressed(
            output_dir / f"{client.station}.npz",
            feature_names=np.asarray(client.feature_names),
            train_x=client.train.x,
            train_y=client.train.y,
            train_timestamps=np.asarray(client.train.timestamps),
            validation_x=client.validation.x,
            validation_y=client.validation.y,
            validation_timestamps=np.asarray(client.validation.timestamps),
            test_x=client.test.x,
            test_y=client.test.y,
            test_timestamps=np.asarray(client.test.timestamps),
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare leakage-safe station clients from UCI dataset 501."
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path("data/external/beijing_air_quality.zip"),
    )
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--train-fraction", type=float, default=0.60)
    parser.add_argument("--validation-fraction", type=float, default=0.20)
    parser.add_argument("--min-usable-rows", type=int, default=1000)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/prepared/beijing"),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/prepared/beijing/manifest.json"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.download:
        download_archive(args.archive)
    if not args.archive.exists():
        raise FileNotFoundError(
            f"archive not found: {args.archive}; use --download or provide it"
        )
    clients = prepare_archive(
        args.archive,
        train_fraction=args.train_fraction,
        validation_fraction=args.validation_fraction,
        min_usable_rows=args.min_usable_rows,
    )
    _write_npz(args.output_dir, clients)
    manifest = build_manifest(
        args.archive,
        clients,
        train_fraction=args.train_fraction,
        validation_fraction=args.validation_fraction,
    )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"Prepared {len(clients)} station clients")
    print(f"Wrote manifest to {args.manifest}")


if __name__ == "__main__":
    main()
