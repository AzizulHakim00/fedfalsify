"""Resume-safe Phase-3D deterministic fixture runner.

The durability boundary is exactly one ``fixture × model × outer_fold`` unit.
A unit is written to Google Drive (or any caller supplied directory) before the
next unit begins.  On restart, hash-valid complete units are skipped and only
missing/corrupt units are recomputed.
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import platform
import sys
import zipfile
from pathlib import Path
from typing import Iterable, Sequence

import joblib
import numpy as np
import pandas as pd
import scipy

from .phase3d_fixtures import build_phase3d_fixtures
from .scsv_v13 import PHASE3D_MODELS, run_phase3d_model

ZIP_NAME = "FedFalsify_PHASE3D_V13_FIXTURES.zip"
UNIT_SCHEMA = "fedfalsify-phase3d-unit-v1"
CONFIG_SCHEMA = "fedfalsify-phase3d-config-v1"
FROZEN_PHASE3C_SCIENTIFIC_SOURCE = "b67a07371bcf244728536028593373ca7d1990b1"


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_bytes(path: Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def atomic_json_write(path: Path, payload: object) -> None:
    """Atomically write deterministic UTF-8 JSON."""
    data = json.dumps(
        payload,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    _atomic_bytes(Path(path), data)


def _atomic_text(path: Path, text: str) -> None:
    _atomic_bytes(Path(path), text.encode("utf-8"))


def _atomic_dataframe(path: Path, frame: pd.DataFrame) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    frame.to_csv(temporary, index=False, lineterminator="\n")
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _atomic_pickle(path: Path, value: object) -> None:
    _atomic_bytes(Path(path), pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))


def _atomic_joblib(path: Path, value: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    joblib.dump(value, temporary, compress=0)
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def make_unit_payload(
    unit_key: dict[str, object],
    config_sha256: str,
    result: dict[str, object],
) -> dict[str, object]:
    """Create a self-hashing immutable unit payload."""
    body: dict[str, object] = {
        "schema_version": UNIT_SCHEMA,
        "unit_key": dict(unit_key),
        "config_sha256": str(config_sha256),
        "result": result,
    }
    body["payload_sha256"] = _sha256_bytes(_canonical_json_bytes(body))
    return body


def verify_unit(
    path: Path,
    expected_key: dict[str, object],
    config_sha256: str,
) -> dict[str, object] | None:
    """Return a verified unit, otherwise ``None`` without trusting partial data."""
    path = Path(path)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        stored_hash = str(payload.pop("payload_sha256"))
        computed_hash = _sha256_bytes(_canonical_json_bytes(payload))
        payload["payload_sha256"] = stored_hash
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
    if stored_hash != computed_hash:
        return None
    if payload.get("schema_version") != UNIT_SCHEMA:
        return None
    if payload.get("unit_key") != expected_key:
        return None
    if payload.get("config_sha256") != str(config_sha256):
        return None
    if not isinstance(payload.get("result"), dict):
        return None
    return payload


def _unit_key(fixture: str, model: str, outer_fold: int) -> dict[str, object]:
    return {
        "fixture": str(fixture),
        "model": str(model),
        "outer_fold": int(outer_fold),
    }


def _unit_path(output_dir: Path, key: dict[str, object]) -> Path:
    return (
        Path(output_dir)
        / "units"
        / str(key["fixture"])
        / str(key["model"])
        / f"fold_{int(key['outer_fold']):03d}.json"
    )


def _build_config(fixtures: Sequence[object], outer_folds: Sequence[int]) -> dict[str, object]:
    base: dict[str, object] = {
        "schema_version": CONFIG_SCHEMA,
        "study": "FedFalsify Phase-3D / v13 SCSV-SCC deterministic fixture proof",
        "fixtures": [str(item.name) for item in fixtures],
        "models": list(PHASE3D_MODELS),
        "outer_folds": [int(value) for value in outer_folds],
        "work_unit": "fixture×model×outer_fold",
        "scientific_fixture_rng": False,
        "scientific_seed_policy": (
            "No scientific benchmark seed is generated or consumed by Phase-3D fixtures. "
            "Frozen predecessor comparators may receive outer_fold as a technical partition seed only."
        ),
        "phase3c_development_seed_block_status": "SPENT-NOT-REUSED",
        "final_confirmation_seed_block_status": "BLOCKED-NOT-ACCESSED",
        "frozen_phase3c_scientific_source": FROZEN_PHASE3C_SCIENTIFIC_SOURCE,
        "unit_persistence": "atomic-temp-fsync-os.replace-before-next-unit",
    }
    base["config_sha256"] = _sha256_bytes(_canonical_json_bytes(base))
    return base


def _prepare_config(output_dir: Path, fixtures: Sequence[object], outer_folds: Sequence[int]) -> dict[str, object]:
    config = _build_config(fixtures, outer_folds)
    path = Path(output_dir) / "config" / "frozen_config.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("config_sha256") != config["config_sha256"]:
            raise RuntimeError(
                "Phase-3D output directory contains a different frozen configuration; "
                "use a new output directory rather than mixing studies"
            )
    else:
        atomic_json_write(path, config)
    return config


def _write_provenance(output_dir: Path, config_sha: str) -> None:
    provenance = {
        "config_sha256": config_sha,
        "phase3d_source_commit": os.environ.get("FEDFALSIFY_PHASE3D_SOURCE_COMMIT", "UNPINNED-LOCAL-SOURCE"),
        "frozen_phase3c_scientific_source": FROZEN_PHASE3C_SCIENTIFIC_SOURCE,
        "frozen_predecessors_modified": False,
    }
    environment = {
        "config_sha256": config_sha,
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "pandas": pd.__version__,
        "joblib": joblib.__version__,
    }
    atomic_json_write(Path(output_dir) / "config" / "source_provenance.json", provenance)
    atomic_json_write(Path(output_dir) / "config" / "environment.json", environment)


def _expected_units(fixtures: Sequence[object], outer_folds: Sequence[int]) -> list[tuple[object, str, int, dict[str, object], Path]]:
    rows = []
    seen: set[tuple[str, str, int]] = set()
    for fixture in fixtures:
        for model in PHASE3D_MODELS:
            for fold in outer_folds:
                identity = (str(fixture.name), str(model), int(fold))
                if identity in seen:
                    raise RuntimeError(f"duplicate Phase-3D work-unit identity: {identity}")
                seen.add(identity)
                key = _unit_key(*identity)
                rows.append((fixture, model, int(fold), key, Path()))
    return rows


def _scan_units(
    output_dir: Path,
    expected: Sequence[tuple[object, str, int, dict[str, object], Path]],
    config_sha: str,
) -> tuple[list[dict[str, object]], int]:
    valid: list[dict[str, object]] = []
    invalid = 0
    for _, _, _, key, _ in expected:
        path = _unit_path(output_dir, key)
        payload = verify_unit(path, key, config_sha)
        if payload is not None:
            valid.append(payload)
        elif path.exists():
            invalid += 1
    return valid, invalid


def _json_cell(value: object) -> object:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return value


def _result_rows(valid_payloads: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for payload in valid_payloads:
        key = dict(payload["unit_key"])
        result = dict(payload["result"])
        row = {"fixture": key["fixture"], "model": key["model"], "outer_fold": key["outer_fold"]}
        for name, value in result.items():
            if name in {"fixture", "method", "outer_fold", "diagnostics"}:
                continue
            row[name] = _json_cell(value)
        rows.append(row)
    return rows


def _diagnostic_rows(valid_payloads: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for payload in valid_payloads:
        key = dict(payload["unit_key"])
        diagnostics = dict(payload["result"]).get("diagnostics", [])
        for index, diagnostic in enumerate(diagnostics):
            row = {
                "fixture": key["fixture"],
                "model": key["model"],
                "outer_fold": key["outer_fold"],
                "diagnostic_index": index,
            }
            for name, value in dict(diagnostic).items():
                row[name] = _json_cell(value)
            rows.append(row)
    return rows


def _scope_diagnostic_rows(diagnostics: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    return [
        dict(row)
        for row in diagnostics
        if row.get("localized_term") not in (None, "", "null")
        or row.get("kind") == "localized-scope"
    ]


def _summary_frame(result_frame: pd.DataFrame) -> pd.DataFrame:
    columns = (
        "model",
        "units",
        "exact_shared_rate",
        "exact_localized_rate",
        "exact_scope_rate",
        "exact_structure_rate",
        "execution_errors",
        "mean_runtime_seconds",
        "mean_communication_bytes",
    )
    if result_frame.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for model, group in result_frame.groupby("model", sort=False):
        def mean_bool(name: str) -> float:
            return float(pd.Series(group[name]).astype(bool).mean()) if name in group else float("nan")

        error_count = int(group["execution_error"].notna().sum()) if "execution_error" in group else 0
        rows.append(
            {
                "model": model,
                "units": int(len(group)),
                "exact_shared_rate": mean_bool("exact_shared"),
                "exact_localized_rate": mean_bool("exact_localized"),
                "exact_scope_rate": mean_bool("exact_scope"),
                "exact_structure_rate": mean_bool("exact_structure"),
                "execution_errors": error_count,
                "mean_runtime_seconds": float(pd.to_numeric(group["runtime_seconds"], errors="coerce").mean()),
                "mean_communication_bytes": float(pd.to_numeric(group["communication_bytes"], errors="coerce").mean()),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _write_incremental_artifacts(
    output_dir: Path,
    expected: Sequence[tuple[object, str, int, dict[str, object], Path]],
    config_sha: str,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    valid, invalid = _scan_units(output_dir, expected, config_sha)
    order = {
        (str(key["fixture"]), str(key["model"]), int(key["outer_fold"])): index
        for index, (_, _, _, key, _) in enumerate(expected)
    }
    valid.sort(
        key=lambda item: order[
            (
                str(item["unit_key"]["fixture"]),
                str(item["unit_key"]["model"]),
                int(item["unit_key"]["outer_fold"]),
            )
        ]
    )

    checkpoint_rows = []
    for payload in valid:
        key = dict(payload["unit_key"])
        path = _unit_path(output_dir, key)
        result = dict(payload["result"])
        checkpoint_rows.append(
            {
                "fixture": key["fixture"],
                "model": key["model"],
                "outer_fold": key["outer_fold"],
                "unit_path": str(path.relative_to(output_dir)),
                "payload_sha256": payload["payload_sha256"],
                "file_sha256": _sha256_file(path),
                "exact_structure": bool(result.get("exact_structure", False)),
                "execution_error": result.get("execution_error"),
            }
        )
    checkpoint = pd.DataFrame(
        checkpoint_rows,
        columns=(
            "fixture",
            "model",
            "outer_fold",
            "unit_path",
            "payload_sha256",
            "file_sha256",
            "exact_structure",
            "execution_error",
        ),
    )
    _atomic_dataframe(Path(output_dir) / "checkpoint_index.csv", checkpoint)

    result_state = [dict(payload["result"]) for payload in valid]
    result_frame = pd.DataFrame(_result_rows(valid))
    _atomic_dataframe(Path(output_dir) / "phase3d_results.csv", result_frame)
    _atomic_pickle(Path(output_dir) / "phase3d_results.pkl", result_state)
    _atomic_joblib(Path(output_dir) / "phase3d_results.joblib", result_state)

    diagnostic_rows = _diagnostic_rows(valid)
    diagnostics = pd.DataFrame(diagnostic_rows)
    _atomic_dataframe(Path(output_dir) / "phase3d_diagnostics.csv", diagnostics)
    scope_diagnostics = pd.DataFrame(_scope_diagnostic_rows(diagnostic_rows))
    _atomic_dataframe(Path(output_dir) / "phase3d_scope_diagnostics.csv", scope_diagnostics)
    _atomic_dataframe(Path(output_dir) / "phase3d_summary.csv", _summary_frame(result_frame))

    integrity = {
        "config_sha256": config_sha,
        "expected_units": int(len(expected)),
        "completed_units": int(len(valid)),
        "remaining_units": int(len(expected) - len(valid)),
        "invalid_units": int(invalid),
        "duplicate_unit_keys": 0,
        "scientific_fixture_seed_count": 0,
        "complete": bool(len(valid) == len(expected) and invalid == 0),
        "zip_verified": False,
    }
    atomic_json_write(Path(output_dir) / "phase3d_integrity.json", integrity)
    return valid, integrity


def _manifest_files(output_dir: Path) -> list[Path]:
    output_dir = Path(output_dir)
    excluded = {ZIP_NAME, "phase3d_manifest_sha256.txt"}
    return sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file()
        and path.name not in excluded
        and not path.name.startswith(".")
    )


def _write_manifest(output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    lines = [
        f"{_sha256_file(path)}  {path.relative_to(output_dir).as_posix()}"
        for path in _manifest_files(output_dir)
    ]
    manifest = output_dir / "phase3d_manifest_sha256.txt"
    _atomic_text(manifest, "\n".join(lines) + "\n")
    return manifest


def _write_reproducible_zip(output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    zip_path = output_dir / ZIP_NAME
    temporary = zip_path.with_name(f".{zip_path.name}.tmp-{os.getpid()}")
    files = sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file()
        and path != zip_path
        and path != temporary
        and not path.name.startswith(".")
    )
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(output_dir).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    os.replace(temporary, zip_path)
    with zipfile.ZipFile(zip_path, "r") as archive:
        bad = archive.testzip()
    if bad is not None:
        raise RuntimeError(f"Phase-3D ZIP CRC failure at {bad}")
    return zip_path


def _finalize(output_dir: Path, integrity: dict[str, object]) -> tuple[Path, str]:
    if not integrity.get("complete"):
        raise RuntimeError("cannot finalize an incomplete Phase-3D fixture study")

    # Two-pass finalization keeps the integrity JSON, manifest and final ZIP
    # mutually consistent while still physically verifying the final archive.
    _write_manifest(output_dir)
    _write_reproducible_zip(output_dir)
    with zipfile.ZipFile(Path(output_dir) / ZIP_NAME, "r") as archive:
        if archive.testzip() is not None:
            raise RuntimeError("first-pass Phase-3D ZIP verification failed")

    final_integrity = dict(integrity)
    final_integrity["zip_verified"] = True
    atomic_json_write(Path(output_dir) / "phase3d_integrity.json", final_integrity)
    _write_manifest(output_dir)
    zip_path = _write_reproducible_zip(output_dir)
    with zipfile.ZipFile(zip_path, "r") as archive:
        bad = archive.testzip()
    if bad is not None:
        raise RuntimeError(f"final Phase-3D ZIP verification failed at {bad}")
    return zip_path, _sha256_file(zip_path)


def _banner(text: str) -> None:
    print("\n" + "=" * 96, flush=True)
    print(text, flush=True)
    print("=" * 96, flush=True)


def run_phase3d(
    output_dir: Path,
    *,
    outer_folds: Sequence[int] = (0,),
    live: bool = True,
) -> dict[str, object]:
    """Run/resume the deterministic Phase-3D fixture proof.

    Completed hash-valid units are never recomputed.  If execution is
    interrupted during a model/fold, that unit has no valid final JSON and only
    that unfinished unit is recomputed on restart.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    folds = tuple(int(value) for value in outer_folds)
    if not folds or len(set(folds)) != len(folds) or any(value < 0 for value in folds):
        raise ValueError("outer_folds must be a non-empty tuple of unique non-negative integers")

    fixtures = tuple(build_phase3d_fixtures())
    config = _prepare_config(output_dir, fixtures, folds)
    config_sha = str(config["config_sha256"])
    _write_provenance(output_dir, config_sha)
    expected = _expected_units(fixtures, folds)
    total = len(expected)

    if live:
        _banner("FedFalsify Phase-3D — V13 SCOPE-CONTRAST DETERMINISTIC FIXTURE PROOF")
        print(f"[OUTPUT] {output_dir}", flush=True)
        print(f"[CONFIG SHA256] {config_sha}", flush=True)
        print(f"[FIXTURES] {len(fixtures)}", flush=True)
        print(f"[MODELS] {len(PHASE3D_MODELS)} :: {', '.join(PHASE3D_MODELS)}", flush=True)
        print(f"[OUTER FOLDS] {folds}", flush=True)
        print("[SCIENTIFIC SEEDS] NONE — Phase-3C spent block not reused; final block untouched", flush=True)
        existing, invalid = _scan_units(output_dir, expected, config_sha)
        print(f"[RESUME] verified complete units={len(existing)}/{total}; invalid={invalid}", flush=True)

    for position, (fixture, model, fold, key, _) in enumerate(expected, start=1):
        path = _unit_path(output_dir, key)
        existing = verify_unit(path, key, config_sha)
        if existing is not None:
            if live:
                print(
                    f"[UNIT {position:03d}/{total:03d}] SKIP verified :: "
                    f"{fixture.name} | {model} | fold={fold}",
                    flush=True,
                )
            continue

        status = "RERUN-CORRUPT" if path.exists() else "RUN"
        if live:
            _banner(f"UNIT {position}/{total} — {status}")
            print(f"Fixture : {fixture.name}", flush=True)
            print(f"Model   : {model}", flush=True)
            print(f"Fold    : {fold}", flush=True)

        result = run_phase3d_model(fixture, model, outer_fold=fold)
        payload = make_unit_payload(key, config_sha, result.as_dict())
        atomic_json_write(path, payload)
        verified = verify_unit(path, key, config_sha)
        if verified is None:
            raise RuntimeError(f"newly written Phase-3D unit failed self-verification: {path}")

        valid, integrity = _write_incremental_artifacts(output_dir, expected, config_sha)
        if live:
            print(f"[SAVED] {path.relative_to(output_dir)}", flush=True)
            print(
                f"[CHECKPOINT] {len(valid)}/{total} verified; "
                f"remaining={integrity['remaining_units']}",
                flush=True,
            )
            print(
                f"[RESULT] exact_structure={int(bool(result.exact_structure))}; "
                f"shared={','.join(result.shared_structure)}; "
                f"localized={','.join(result.accepted_localized) or '-'}",
                flush=True,
            )

    valid, integrity = _write_incremental_artifacts(output_dir, expected, config_sha)
    if len(valid) != total or not integrity["complete"]:
        raise RuntimeError(
            f"Phase-3D ended incomplete: valid={len(valid)}/{total}, invalid={integrity['invalid_units']}"
        )

    zip_path, zip_sha = _finalize(output_dir, integrity)
    final_integrity = json.loads((output_dir / "phase3d_integrity.json").read_text(encoding="utf-8"))
    summary = pd.read_csv(output_dir / "phase3d_summary.csv")

    if live:
        _banner("PHASE-3D FIXTURE PROOF COMPLETE")
        print(summary.to_string(index=False), flush=True)
        print(f"\n[INTEGRITY] {json.dumps(final_integrity, sort_keys=True)}", flush=True)
        print(f"[ZIP] {zip_path}", flush=True)
        print(f"[ZIP SHA256] {zip_sha}", flush=True)
        print("[NOTE] This is an architectural fixture proof, not a fresh-seed superiority claim.", flush=True)

    return {
        "output_dir": str(output_dir),
        "config_sha256": config_sha,
        "integrity": final_integrity,
        "zip_path": str(zip_path),
        "zip_sha256": zip_sha,
        "completed_units": len(valid),
    }
