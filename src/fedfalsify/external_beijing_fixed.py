"""Official-archive compatible Beijing external-data preparation.

UCI dataset 501 distributes the station CSV files inside an inner ZIP archive.
This module preserves direct-CSV ZIP support used by unit fixtures and adds
strict nested-ZIP discovery for the official package.
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import zipfile

from . import external_beijing as _core


def _open_station_archive(
    archive_path: Path,
) -> tuple[zipfile.ZipFile, io.BytesIO | None]:
    outer = zipfile.ZipFile(archive_path)
    if _core._csv_members(outer):
        return outer, None

    candidates: list[tuple[str, bytes]] = []
    for name in outer.namelist():
        if not name.lower().endswith(".zip"):
            continue
        payload = outer.read(name)
        with zipfile.ZipFile(io.BytesIO(payload)) as nested:
            if _core._csv_members(nested):
                candidates.append((name, payload))
    outer.close()
    if not candidates:
        raise ValueError(
            "archive contains neither station CSV files nor a nested ZIP "
            "with PRSA station CSV files"
        )
    if len(candidates) != 1:
        names = [name for name, _ in candidates]
        raise ValueError(
            "expected exactly one nested station-data ZIP, found: "
            + ", ".join(names)
        )
    buffer = io.BytesIO(candidates[0][1])
    return zipfile.ZipFile(buffer), buffer


def prepare_archive(
    archive_path: Path,
    *,
    train_fraction: float = 0.60,
    validation_fraction: float = 0.20,
    min_usable_rows: int = 1000,
    require_expected_station_count: bool = True,
):
    """Prepare station clients from direct or official nested ZIP archives."""

    archive_path = archive_path.resolve()
    archive, buffer = _open_station_archive(archive_path)
    try:
        members = _core._csv_members(archive)
        if require_expected_station_count and len(members) != _core.EXPECTED_STATIONS:
            raise ValueError(
                f"expected {_core.EXPECTED_STATIONS} station CSVs, "
                f"found {len(members)}"
            )
        clients = []
        for member in members:
            station, rows, raw_rows, dropped_target = _core._read_station_rows(
                archive, member
            )
            if len(rows) < min_usable_rows:
                raise ValueError(
                    f"station {station} has {len(rows)} usable rows; "
                    f"minimum is {min_usable_rows}"
                )
            train_slice, validation_slice, test_slice = _core._split_indices(
                len(rows),
                train_fraction=train_fraction,
                validation_fraction=validation_fraction,
            )
            train_rows = rows[train_slice]
            validation_rows = rows[validation_slice]
            test_rows = rows[test_slice]
            medians = _core._training_medians(train_rows)
            clients.append(
                _core.BeijingStationClient(
                    station=station,
                    feature_names=_core.feature_names(),
                    train=_core._encode_rows(train_rows, medians),
                    validation=_core._encode_rows(validation_rows, medians),
                    test=_core._encode_rows(test_rows, medians),
                    training_medians=tuple(float(value) for value in medians),
                    raw_rows=raw_rows,
                    dropped_missing_target=dropped_target,
                )
            )
    finally:
        archive.close()
        if buffer is not None:
            buffer.close()
    stations = [client.station for client in clients]
    if len(stations) != len(set(stations)):
        raise ValueError("duplicate station names found")
    return sorted(clients, key=lambda item: item.station)


# Re-export audited preparation utilities.
build_manifest = _core.build_manifest
download_archive = _core.download_archive
feature_names = _core.feature_names
_write_npz = _core._write_npz


def build_parser() -> argparse.ArgumentParser:
    return _core.build_parser()


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
