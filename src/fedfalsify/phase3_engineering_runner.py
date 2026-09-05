"""Reproducible Phase-3B engineering integration runner.

This module is an engineering harness, not a development-study gate.  It
permits only seed 29300, checkpoints complete four-method condition groups, and
archives transparent diagnostics.  Performance metrics are descriptive and are
never consulted by the engineering PASS/FAIL decision.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import pickle
import platform
import shutil
import sys
from time import perf_counter
from typing import Iterable, Sequence
import zipfile

import joblib
import numpy as np
import pandas as pd

from .scsv_v10_benchmarks import (
    V10_DEVIATIONS,
    generate_v10_benchmark,
    generate_v10_global_test_data,
    v10_catalog,
)
from .scsv_v11_study import _v11_integrity
from .scsv_v12 import PHASE3_METHODS, SCSVV12Output, run_scsv_v12_branches

ENGINEERING_SEED = 29300
ConditionKey = tuple[str, int, str, str, float, int]

ENGINEERING_CONDITIONS: tuple[ConditionKey, ...] = (
    ("quadratic_role_v10", 4, "balanced", "single", 0.10, 29300),
    ("trig_role_v10", 4, "balanced", "single", 0.30, 29300),
    ("null_role_v10", 8, "balanced", "none", 0.10, 29300),
    ("anchor_contamination_null_v10", 8, "balanced", "none", 0.30, 29300),
    ("weak_source_role_v10", 8, "balanced", "quarter", 0.10, 29300),
    ("dual_role_v10", 8, "imbalanced", "quarter", 0.30, 29300),
)

STAGE_LABELS = (
    "[STAGE 0/10] Protocol + seed firewall",
    "[STAGE 1/10] Google Drive persistence",
    "[STAGE 2/10] Exact source + dependency verification",
    "[STAGE 3/10] Scientific test gate",
    "[STAGE 4/10] Condition matrix + checkpoint validation",
    "[STAGE 5/10] Phase-3 engineering smoke",
    "[STAGE 6/10] Mechanism diagnostics",
    "[STAGE 7/10] Ablation summaries",
    "[STAGE 8/10] Reproducibility artifacts",
    "[STAGE 9/10] Integrity manifest + ZIP",
    "[STAGE 10/10] Engineering decision",
)

REQUIRED_ARTIFACTS = (
    "FROZEN_PHASE3_ENGINEERING_PROTOCOL.md",
    "phase3_engineering_checkpoint.csv",
    "phase3_engineering_rows.csv",
    "phase3_engineering_method_summary.csv",
    "phase3_engineering_shared_diagnostics.csv",
    "phase3_engineering_localized_diagnostics.csv",
    "phase3_engineering_ablation_summary.csv",
    "phase3_engineering_integrity.json",
    "phase3_engineering_environment.json",
    "phase3_engineering_decision.json",
    "phase3_engineering_state.pkl",
    "phase3_engineering_state.joblib",
    "phase3_engineering_report.txt",
    "phase3_engineering_sha256.txt",
    "FedFalsify_PHASE3_NCSC_ENGINEERING_RESULTS.zip",
)

CHECKPOINT_NAME = "phase3_engineering_checkpoint.csv"
STATE_PKL_NAME = "phase3_engineering_state.pkl"
STATE_JOBLIB_NAME = "phase3_engineering_state.joblib"
PROTOCOL_NAME = "FROZEN_PHASE3_ENGINEERING_PROTOCOL.md"
ZIP_NAME = "FedFalsify_PHASE3_NCSC_ENGINEERING_RESULTS.zip"
MANIFEST_NAME = "phase3_engineering_sha256.txt"


def _emit(live: bool, message: str) -> None:
    if live:
        print(message, flush=True)


def validate_phase3_engineering_seed(seed: int) -> None:
    if int(seed) != ENGINEERING_SEED:
        raise ValueError("Phase-3 engineering permits seed 29300 only")


def condition_key_string(condition: ConditionKey) -> str:
    family, clients, balance, role, noise, seed = condition
    return f"{family}|{int(clients)}|{balance}|{role}|{float(noise):.2f}|{int(seed)}"


def condition_key_from_row(row: dict) -> ConditionKey:
    return (
        str(row["family"]),
        int(row["num_clients"]),
        str(row["balance_profile"]),
        str(row["role_profile"]),
        float(row["noise_ratio"]),
        int(row["seed"]),
    )


def load_checkpoint(path: Path | str) -> list[dict]:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def validate_checkpoint_groups(
    rows: Sequence[dict],
) -> tuple[list[dict], set[ConditionKey]]:
    """Keep only complete, unique, authorized four-method groups."""
    authorized = set(ENGINEERING_CONDITIONS)
    grouped: dict[ConditionKey, list[dict]] = {}
    for raw in rows:
        try:
            key = condition_key_from_row(raw)
        except (KeyError, TypeError, ValueError):
            continue
        grouped.setdefault(key, []).append(dict(raw))

    cleaned: list[dict] = []
    completed: set[ConditionKey] = set()
    required_methods = set(PHASE3_METHODS)
    for condition in ENGINEERING_CONDITIONS:
        group = grouped.get(condition, [])
        methods = [str(row.get("method", "")) for row in group]
        if (
            condition in authorized
            and len(group) == len(PHASE3_METHODS)
            and set(methods) == required_methods
            and len(methods) == len(set(methods))
        ):
            by_method = {str(row["method"]): dict(row) for row in group}
            for method in PHASE3_METHODS:
                item = by_method[method]
                item["condition_key"] = condition_key_string(condition)
                cleaned.append(item)
            completed.add(condition)
    return cleaned, completed


def atomic_write_csv(df: pd.DataFrame, path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def _atomic_write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _atomic_write_json(payload: object, path: Path) -> None:
    _atomic_write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True) + "\n",
        path,
    )


def _atomic_pickle(payload: object, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as handle:
        pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, path)


def _atomic_joblib(payload: object, path: Path) -> None:
    tmp = path.with_name(path.name + ".tmp")
    joblib.dump(payload, tmp)
    os.replace(tmp, path)


def _jsonable(value):
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _json_compact(value: object) -> str:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"))


def _metric_triplet(predicted: set[str], target: set[str]) -> tuple[float, float, float, int, int, int]:
    tp = len(predicted & target)
    fp = len(predicted - target)
    fn = len(target - predicted)
    precision = tp / (tp + fp) if tp + fp else float(not target)
    recall = tp / (tp + fn) if tp + fn else 1.0
    return (
        float(predicted == target),
        float(precision),
        float(recall),
        int(tp),
        int(fp),
        int(fn),
    )


def _branch_integrity(output: object) -> int:
    if getattr(output, "method", None) == "scsv-elrc-v11-full":
        return int(_v11_integrity(output))

    if not isinstance(output, SCSVV12Output):
        return 1
    violations = 0
    final_structure = tuple(output.final_structure)
    if tuple(output.candidate.active_terms) != final_structure:
        violations += 1
    if not set(output.shared_structure).issubset(set(final_structure)):
        violations += 1
    if not set(output.accepted_deviations).issubset(set(final_structure)):
        violations += 1
    if len(output.shared_structure) > 6:
        violations += 1
    if len(output.accepted_deviations) > 2:
        violations += 1
    if len(final_structure) > 10:
        violations += 1
    ledger = output.ledger
    if tuple(ledger.final_shared_structure) != tuple(output.shared_structure):
        violations += 1
    if tuple(ledger.final_accepted_localized) != tuple(output.accepted_deviations):
        violations += 1
    if tuple(ledger.final_complete_structure) != final_structure:
        violations += 1
    return int(violations)


def _evaluate_output(generated, output: object, condition: ConditionKey) -> dict:
    family, num_clients, balance, role, noise, seed = condition
    catalog = v10_catalog()
    final_structure = tuple(getattr(output, "final_structure"))
    predicted = set(final_structure) - {"1"}
    target = set(generated.target_terms)
    exact, term_precision, term_recall, term_tp, term_fp, term_fn = _metric_triplet(
        predicted, target
    )

    deviations = set(V10_DEVIATIONS)
    true_deviations = set(generated.true_deviations)
    predicted_deviations = predicted & deviations
    _, dev_precision, dev_recall, dev_tp, dev_fp, dev_fn = _metric_triplet(
        predicted_deviations, true_deviations
    )

    true_shared = target - true_deviations
    predicted_shared = predicted - deviations
    _, shared_precision, shared_recall, shared_tp, shared_fp, shared_fn = _metric_triplet(
        predicted_shared, true_shared
    )

    x_test, y_test = generate_v10_global_test_data(generated, seed=int(seed) + 100_000)
    prediction = output.candidate.predict(x_test, catalog)
    mse = float(np.mean((np.asarray(y_test) - np.asarray(prediction)) ** 2))
    nmse = float(mse / max(float(np.var(y_test)), 1e-12))

    if isinstance(output, SCSVV12Output):
        shared_diagnostics = output.ledger.shared_diagnostics
        localized_diagnostics = {
            "localized_candidate_family": output.ledger.localized_candidate_family,
            "discovery": output.ledger.discovery_localized_diagnostics,
            "selector": output.ledger.selector_diagnostics,
            "probe": output.ledger.probe_diagnostics,
            "accepted": output.ledger.final_accepted_localized,
        }
        shared_structure = tuple(output.shared_structure)
        accepted = tuple(output.accepted_deviations)
    else:
        shared_diagnostics = ()
        localized_diagnostics = {
            "localized_candidate_family": tuple(getattr(output, "candidate_deviations", ())),
            "discovery": tuple(getattr(output, "diagnostics", ())),
            "selector": (),
            "probe": (),
            "accepted": tuple(getattr(output, "accepted_deviations", ())),
        }
        shared_structure = tuple(getattr(output, "ordinary_anchor_structure", ("1",)))
        accepted = tuple(getattr(output, "accepted_deviations", ()))

    return {
        "family": str(family),
        "noise_ratio": float(noise),
        "num_clients": int(num_clients),
        "balance_profile": str(balance),
        "role_profile": str(role),
        "seed": int(seed),
        "condition_key": condition_key_string(condition),
        "method": str(output.method),
        "exact_recovery": float(exact),
        "term_precision": float(term_precision),
        "term_recall": float(term_recall),
        "term_tp": term_tp,
        "term_fp": term_fp,
        "term_fn": term_fn,
        "shared_precision": float(shared_precision),
        "shared_recall": float(shared_recall),
        "shared_tp": shared_tp,
        "shared_fp": shared_fp,
        "shared_fn": shared_fn,
        "deviation_precision": float(dev_precision),
        "deviation_recall": float(dev_recall),
        "deviation_tp": dev_tp,
        "deviation_fp": dev_fp,
        "deviation_fn": dev_fn,
        "test_nmse": float(nmse),
        "runtime_seconds": float(output.runtime_seconds),
        "communication_bytes": int(output.communication_bytes),
        "shared_structure": ";".join(shared_structure),
        "final_structure": ";".join(final_structure),
        "accepted_deviations": ";".join(accepted),
        "integrity_violations": int(_branch_integrity(output)),
        "shared_diagnostics_json": _json_compact(shared_diagnostics),
        "localized_diagnostics_json": _json_compact(localized_diagnostics),
        "expression": output.candidate.expression(catalog),
        "stop_reason": str(output.stop_reason),
    }


def _evaluate_condition(condition: ConditionKey) -> list[dict]:
    """Scientific evaluator used only after the pre-execution test gate passes."""
    family, num_clients, balance, role, noise, seed = condition
    validate_phase3_engineering_seed(seed)
    generated = generate_v10_benchmark(
        family,
        nominal_samples_per_client=100,
        noise_ratio=float(noise),
        seed=int(seed),
        num_clients=int(num_clients),
        balance_profile=balance,
        role_profile=role,
    )
    target_mse = max(float(generated.noise_std) ** 2 * 2.5, 1e-8)
    outputs = run_scsv_v12_branches(
        generated.clients,
        v10_catalog(),
        seed=int(seed),
        target_mse=target_mse,
        min_repair_score=0.05,
    )
    if tuple(output.method for output in outputs) != PHASE3_METHODS:
        raise RuntimeError("engineering evaluator method order drifted")
    return [_evaluate_output(generated, output, condition) for output in outputs]


def _validate_new_group(condition: ConditionKey, rows: Sequence[dict]) -> list[dict]:
    if len(rows) != len(PHASE3_METHODS):
        raise RuntimeError("engineering condition did not return exactly four rows")
    methods = tuple(str(row.get("method", "")) for row in rows)
    if methods != PHASE3_METHODS or len(set(methods)) != len(PHASE3_METHODS):
        raise RuntimeError("engineering condition returned an invalid method group")
    normalized = []
    for row in rows:
        item = dict(row)
        if condition_key_from_row(item) != condition:
            raise RuntimeError("engineering evaluator changed condition identity")
        item["condition_key"] = condition_key_string(condition)
        normalized.append(item)
    return normalized


def _state_payload(rows: Sequence[dict]) -> dict:
    cleaned, completed = validate_checkpoint_groups(rows)
    return {
        "schema_version": 1,
        "engineering_seed": ENGINEERING_SEED,
        "methods": PHASE3_METHODS,
        "completed_condition_keys": [condition_key_string(item) for item in ENGINEERING_CONDITIONS if item in completed],
        "rows": list(cleaned),
    }


def _save_checkpoint_state(rows: Sequence[dict], output_dir: Path) -> None:
    frame = pd.DataFrame(list(rows))
    atomic_write_csv(frame, output_dir / CHECKPOINT_NAME)
    state = _state_payload(rows)
    _atomic_pickle(state, output_dir / STATE_PKL_NAME)
    _atomic_joblib(state, output_dir / STATE_JOBLIB_NAME)


def _repo_protocol_path() -> Path:
    return Path(__file__).resolve().parents[2] / "research" / PROTOCOL_NAME


def _ensure_protocol(output_dir: Path) -> Path:
    destination = output_dir / PROTOCOL_NAME
    if destination.exists():
        return destination
    source = _repo_protocol_path()
    if not source.exists():
        raise FileNotFoundError(
            "frozen protocol is missing; the pinned Colab wrapper must download it before execution"
        )
    tmp = destination.with_name(destination.name + ".tmp")
    shutil.copyfile(source, tmp)
    os.replace(tmp, destination)
    return destination


def _diagnostic_frames(rows: Sequence[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    shared_records: list[dict] = []
    localized_records: list[dict] = []
    meta_keys = (
        "condition_key",
        "family",
        "noise_ratio",
        "num_clients",
        "balance_profile",
        "role_profile",
        "seed",
        "method",
    )
    for row in rows:
        meta = {key: row.get(key) for key in meta_keys}
        try:
            shared = json.loads(str(row.get("shared_diagnostics_json", "[]")))
        except json.JSONDecodeError:
            shared = []
        if isinstance(shared, list) and shared:
            for item in shared:
                record = dict(meta)
                record.update(_jsonable(item) if isinstance(item, dict) else {"value": item})
                record["diagnostic_present"] = 1
                shared_records.append(record)
        else:
            shared_records.append({**meta, "diagnostic_present": 0})

        try:
            localized = json.loads(str(row.get("localized_diagnostics_json", "[]")))
        except json.JSONDecodeError:
            localized = []
        if isinstance(localized, dict):
            for stage in ("discovery", "selector", "probe"):
                items = localized.get(stage, [])
                if items:
                    for item in items:
                        record = dict(meta)
                        record["stage"] = stage
                        if isinstance(item, dict):
                            record.update(item)
                        else:
                            record["value"] = item
                        record["diagnostic_present"] = 1
                        localized_records.append(record)
                else:
                    localized_records.append({**meta, "stage": stage, "diagnostic_present": 0})
        elif isinstance(localized, list) and localized:
            for item in localized:
                record = {**meta, "stage": "legacy"}
                if isinstance(item, dict):
                    record.update(item)
                else:
                    record["value"] = item
                record["diagnostic_present"] = 1
                localized_records.append(record)
        else:
            localized_records.append({**meta, "stage": "none", "diagnostic_present": 0})

    return pd.DataFrame(shared_records), pd.DataFrame(localized_records)


def _method_summary(rows: Sequence[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(list(rows))
    metrics = [
        "exact_recovery",
        "term_precision",
        "term_recall",
        "shared_precision",
        "shared_recall",
        "deviation_precision",
        "deviation_recall",
        "test_nmse",
    ]
    records: list[dict] = []
    for method in PHASE3_METHODS:
        subset = frame[frame["method"] == method]
        record = {"method": method, "runs": int(len(subset))}
        for metric in metrics:
            record[metric] = float(pd.to_numeric(subset[metric], errors="coerce").mean())
        record["runtime_seconds_median"] = float(
            pd.to_numeric(subset["runtime_seconds"], errors="coerce").median()
        )
        record["communication_bytes_median"] = float(
            pd.to_numeric(subset["communication_bytes"], errors="coerce").median()
        )
        records.append(record)
    return pd.DataFrame(records)


def _ablation_summary(method_summary: pd.DataFrame) -> pd.DataFrame:
    indexed = method_summary.set_index("method")
    baseline = indexed.loc[PHASE3_METHODS[0]]
    records = []
    for method in PHASE3_METHODS:
        row = indexed.loc[method]
        records.append(
            {
                "method": method,
                "exact_recovery_delta_vs_v11": float(row["exact_recovery"] - baseline["exact_recovery"]),
                "shared_recall_delta_vs_v11": float(row["shared_recall"] - baseline["shared_recall"]),
                "deviation_recall_delta_vs_v11": float(row["deviation_recall"] - baseline["deviation_recall"]),
                "test_nmse_delta_vs_v11": float(row["test_nmse"] - baseline["test_nmse"]),
                "runtime_ratio_vs_v11": float(row["runtime_seconds_median"] / max(float(baseline["runtime_seconds_median"]), 1e-15)),
                "communication_ratio_vs_v11": float(row["communication_bytes_median"] / max(float(baseline["communication_bytes_median"]), 1.0)),
            }
        )
    return pd.DataFrame(records)


def _environment_payload(protocol_path: Path) -> dict:
    def version(name: str) -> str:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            return "unavailable"

    return {
        "schema_version": 1,
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": version("scipy"),
        "joblib": joblib.__version__,
        "fedfalsify": version("fedfalsify"),
        "pinned_source_commit": os.environ.get("FEDFALSIFY_PINNED_SOURCE_COMMIT", "unknown"),
        "protocol_sha256": hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        "engineering_seed": ENGINEERING_SEED,
        "blocked_development_seeds": list(range(29301, 29311)),
        "blocked_final_seed_range": "11001-11999",
    }


def _write_base_artifacts(rows: Sequence[dict], output_dir: Path, protocol_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = pd.DataFrame(list(rows))
    atomic_write_csv(frame, output_dir / "phase3_engineering_rows.csv")

    shared, localized = _diagnostic_frames(rows)
    atomic_write_csv(shared, output_dir / "phase3_engineering_shared_diagnostics.csv")
    atomic_write_csv(localized, output_dir / "phase3_engineering_localized_diagnostics.csv")

    method_summary = _method_summary(rows)
    ablation = _ablation_summary(method_summary)
    atomic_write_csv(method_summary, output_dir / "phase3_engineering_method_summary.csv")
    atomic_write_csv(ablation, output_dir / "phase3_engineering_ablation_summary.csv")

    _atomic_write_json(
        _environment_payload(protocol_path),
        output_dir / "phase3_engineering_environment.json",
    )
    state = _state_payload(rows)
    _atomic_pickle(state, output_dir / STATE_PKL_NAME)
    _atomic_joblib(state, output_dir / STATE_JOBLIB_NAME)

    report = (
        "FedFalsify Phase-3B Engineering Integration Report\n"
        "=================================================\n"
        f"Engineering seed: {ENGINEERING_SEED}\n"
        f"Complete conditions: {len(rows) // len(PHASE3_METHODS)}\n"
        f"Primary method rows: {len(rows)}\n\n"
        "DESCRIPTIVE METHOD SUMMARY (not an engineering decision gate)\n"
        + method_summary.to_string(index=False)
        + "\n\nDESCRIPTIVE ABLATION SUMMARY (not an engineering decision gate)\n"
        + ablation.to_string(index=False)
        + "\n"
    )
    _atomic_write_text(report, output_dir / "phase3_engineering_report.txt")
    return method_summary, ablation


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _base_artifacts_ok(output_dir: Path) -> bool:
    excluded = {
        "phase3_engineering_integrity.json",
        "phase3_engineering_decision.json",
        MANIFEST_NAME,
        ZIP_NAME,
    }
    for name in REQUIRED_ARTIFACTS:
        if name in excluded:
            continue
        path = output_dir / name
        if not path.exists() or not path.is_file():
            return False
        _sha256_file(path)
    return True


def engineering_decision(
    rows: Sequence[dict],
    *,
    test_gate_passed: bool,
    artifacts_ok: bool,
    zip_ok: bool,
) -> str:
    """Return an integrity-only decision; performance columns are never read."""
    cleaned, completed = validate_checkpoint_groups(rows)
    group_ok = len(completed) == len(ENGINEERING_CONDITIONS) and len(cleaned) == 24
    duplicate_free = len(rows) == len(cleaned)
    integrity_ok = all(int(float(row.get("integrity_violations", 0))) == 0 for row in cleaned)
    condition_ok = set(completed) == set(ENGINEERING_CONDITIONS)
    passed = bool(
        test_gate_passed
        and artifacts_ok
        and zip_ok
        and group_ok
        and duplicate_free
        and integrity_ok
        and condition_ok
    )
    return "PHASE3-ENGINEERING-PASS" if passed else "PHASE3-ENGINEERING-FAIL"


def _integrity_payload(
    rows: Sequence[dict],
    *,
    test_gate_passed: bool,
    artifacts_ok: bool,
    zip_verified: bool,
) -> dict:
    cleaned, completed = validate_checkpoint_groups(rows)
    return {
        "schema_version": 1,
        "test_gate_passed_before_execution": bool(test_gate_passed),
        "expected_conditions": len(ENGINEERING_CONDITIONS),
        "complete_conditions": len(completed),
        "expected_primary_rows": 24,
        "primary_rows": len(rows),
        "valid_primary_rows": len(cleaned),
        "duplicate_or_partial_rows": int(len(rows) - len(cleaned)),
        "integrity_violations": int(sum(int(float(row.get("integrity_violations", 0))) for row in cleaned)),
        "method_set": list(PHASE3_METHODS),
        "seed_set": sorted({int(condition[-1]) for condition in completed}),
        "base_artifacts_ok": bool(artifacts_ok),
        "zip_verified": bool(zip_verified),
    }


def _write_manifest(output_dir: Path) -> Path:
    lines = []
    for name in sorted(REQUIRED_ARTIFACTS):
        if name in {MANIFEST_NAME, ZIP_NAME}:
            continue
        path = output_dir / name
        if not path.exists():
            raise FileNotFoundError(f"required artifact missing before manifest: {name}")
        lines.append(f"{_sha256_file(path)}  {name}")
    manifest = output_dir / MANIFEST_NAME
    _atomic_write_text("\n".join(lines) + "\n", manifest)
    return manifest


def _write_zip(output_dir: Path) -> tuple[Path, bool]:
    archive = output_dir / ZIP_NAME
    tmp = archive.with_name(archive.name + ".tmp")
    members = [name for name in REQUIRED_ARTIFACTS if name != ZIP_NAME]
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for name in sorted(members):
            handle.write(output_dir / name, arcname=name)
    os.replace(tmp, archive)
    with zipfile.ZipFile(archive, "r") as handle:
        ok = handle.testzip() is None
    return archive, bool(ok)


def _finalize_package(
    rows: Sequence[dict],
    output_dir: Path,
    *,
    test_gate_passed: bool,
) -> tuple[str, str, bool]:
    artifacts_ok = _base_artifacts_ok(output_dir)

    # First pass establishes whether a valid archive can be built.
    _atomic_write_json(
        _integrity_payload(
            rows,
            test_gate_passed=test_gate_passed,
            artifacts_ok=artifacts_ok,
            zip_verified=False,
        ),
        output_dir / "phase3_engineering_integrity.json",
    )
    _atomic_write_json(
        {"decision": "PHASE3-ENGINEERING-FAIL", "basis": "integrity-only engineering gate"},
        output_dir / "phase3_engineering_decision.json",
    )
    _write_manifest(output_dir)
    _, first_zip_ok = _write_zip(output_dir)

    final_decision = engineering_decision(
        rows,
        test_gate_passed=test_gate_passed,
        artifacts_ok=artifacts_ok,
        zip_ok=first_zip_ok,
    )
    _atomic_write_json(
        _integrity_payload(
            rows,
            test_gate_passed=test_gate_passed,
            artifacts_ok=artifacts_ok,
            zip_verified=first_zip_ok,
        ),
        output_dir / "phase3_engineering_integrity.json",
    )
    _atomic_write_json(
        {"decision": final_decision, "basis": "integrity-only engineering gate"},
        output_dir / "phase3_engineering_decision.json",
    )
    _write_manifest(output_dir)
    archive, final_zip_ok = _write_zip(output_dir)
    if not final_zip_ok:
        final_decision = "PHASE3-ENGINEERING-FAIL"
        _atomic_write_json(
            _integrity_payload(
                rows,
                test_gate_passed=test_gate_passed,
                artifacts_ok=artifacts_ok,
                zip_verified=False,
            ),
            output_dir / "phase3_engineering_integrity.json",
        )
        _atomic_write_json(
            {"decision": final_decision, "basis": "final ZIP integrity failure"},
            output_dir / "phase3_engineering_decision.json",
        )
        _write_manifest(output_dir)
        archive, _ = _write_zip(output_dir)
    return final_decision, _sha256_file(archive), bool(final_zip_ok)


def save_reproducibility_artifacts(
    rows: Sequence[dict],
    output_dir: Path | str,
    *,
    test_gate_passed: bool,
) -> dict:
    output_dir = Path(output_dir)
    protocol_path = _ensure_protocol(output_dir)
    method_summary, ablation = _write_base_artifacts(rows, output_dir, protocol_path)
    decision, zip_sha256, zip_ok = _finalize_package(
        rows, output_dir, test_gate_passed=test_gate_passed
    )
    return {
        "decision": decision,
        "zip_sha256": zip_sha256,
        "zip_ok": zip_ok,
        "method_summary": method_summary,
        "ablation_summary": ablation,
    }


def run_engineering(
    output_dir: Path | str,
    *,
    seed: int = ENGINEERING_SEED,
    live: bool = True,
) -> dict:
    """Run or resume the exact six-condition engineering-only integration smoke."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _emit(live, STAGE_LABELS[0])
    validate_phase3_engineering_seed(seed)
    protocol_path = _ensure_protocol(output_dir)
    _emit(live, f"[PROTOCOL] {protocol_path}")
    _emit(live, "[FIREWALL] engineering=29300; development=29301-29310 BLOCKED; final=11001-11999 BLOCKED")

    _emit(live, STAGE_LABELS[1])
    _emit(live, f"[PERSISTENCE] output_dir={output_dir}")

    _emit(live, STAGE_LABELS[2])
    _emit(live, "[SOURCE] scientific package already loaded by the pinned wrapper")

    _emit(live, STAGE_LABELS[3])
    test_gate_passed = os.environ.get("FEDFALSIFY_PHASE3_TEST_GATE") == "PASS"
    if not test_gate_passed:
        raise RuntimeError("Phase-3 scientific test gate must pass before engineering execution")
    _emit(live, "[TEST GATE] PASS")

    _emit(live, STAGE_LABELS[4])
    checkpoint_path = output_dir / CHECKPOINT_NAME
    loaded = load_checkpoint(checkpoint_path)
    rows, completed = validate_checkpoint_groups(loaded)
    if len(rows) != len(loaded):
        _save_checkpoint_state(rows, output_dir)
        _emit(live, "[RESUME] discarded partial/duplicate/unauthorized checkpoint rows")
    _emit(live, f"[RESUME] valid complete groups={len(completed)}/6")

    _emit(live, STAGE_LABELS[5])
    for index, condition in enumerate(ENGINEERING_CONDITIONS, start=1):
        if condition in completed:
            _emit(live, f"[CONDITION {index}/6] resume-skip {condition_key_string(condition)}")
            continue
        started = perf_counter()
        _emit(live, f"[CONDITION {index}/6] start {condition_key_string(condition)}")
        group = _validate_new_group(condition, _evaluate_condition(condition))
        rows.extend(group)
        rows, completed = validate_checkpoint_groups(rows)
        _save_checkpoint_state(rows, output_dir)
        elapsed = perf_counter() - started
        _emit(live, f"[CHECKPOINT] condition {index}/6 saved; elapsed={elapsed:.2f}s")

    rows, completed = validate_checkpoint_groups(rows)
    if len(completed) != 6 or len(rows) != 24:
        raise RuntimeError("engineering smoke ended without six complete four-method groups")

    _emit(live, STAGE_LABELS[6])
    _emit(live, "[DIAGNOSTICS] preserving shared/localized mechanism ledgers")
    _emit(live, STAGE_LABELS[7])
    _emit(live, "[ABLATIONS] descriptive summaries only; not used for PASS/FAIL")
    _emit(live, STAGE_LABELS[8])
    artifacts = save_reproducibility_artifacts(
        rows,
        output_dir,
        test_gate_passed=test_gate_passed,
    )
    _emit(live, "[ARTIFACTS] CSV + JSON + TXT + PKL + joblib saved")
    _emit(live, STAGE_LABELS[9])
    _emit(live, f"[ZIP] verified={int(bool(artifacts['zip_ok']))}; sha256={artifacts['zip_sha256']}")
    _emit(live, STAGE_LABELS[10])
    _emit(live, f"[DECISION] {artifacts['decision']}")

    return {
        "decision": artifacts["decision"],
        "conditions_complete": len(completed),
        "primary_rows": len(rows),
        "output_dir": str(output_dir),
        "manifest": str(output_dir / MANIFEST_NAME),
        "zip_path": str(output_dir / ZIP_NAME),
        "zip_sha256": artifacts["zip_sha256"],
        "method_summary": artifacts["method_summary"],
        "ablation_summary": artifacts["ablation_summary"],
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the frozen Phase-3 engineering integration smoke")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=ENGINEERING_SEED)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)
    result = run_engineering(args.output_dir, seed=args.seed, live=not args.quiet)
    print(json.dumps({key: value for key, value in result.items() if key not in {"method_summary", "ablation_summary"}}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
