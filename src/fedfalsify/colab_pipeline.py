"""Resumable Google Colab orchestration for FedFalsify confirmatory runs.

The runner keeps research outputs in a Git-tracked results directory and mirrors
the same directory to a mounted Google Drive path. Git authentication and Drive
mounting intentionally remain notebook responsibilities.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import fields
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Iterable

from . import __version__
from .confirmatory import (
    METHODS,
    ConfirmatoryRow,
    run_study,
    summarize,
    write_csv,
)
from .confirmatory_report import add_holm_correction


_INT_FIELDS = {
    "samples_per_client",
    "num_clients",
    "seed",
    "communication_bytes",
    "search_evaluations",
}
_FLOAT_FIELDS = {
    "noise_ratio",
    "exact_recovery",
    "term_precision",
    "term_recall",
    "test_nmse",
    "train_mse",
    "spurious_accepted",
    "exception_recovered",
    "runtime_seconds",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_csv_list(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def parse_float_list(value: str) -> tuple[float, ...]:
    return tuple(float(item) for item in parse_csv_list(value))


def parse_int_spec(value: str) -> tuple[int, ...]:
    """Parse comma-separated integers and inclusive ranges such as 9001-9020."""

    result: list[int] = []
    for token in parse_csv_list(value):
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start, end = int(start_text), int(end_text)
            if end < start:
                raise ValueError(f"descending integer range is not allowed: {token}")
            result.extend(range(start, end + 1))
        else:
            result.append(int(token))
    if not result:
        raise ValueError("at least one integer is required")
    if len(set(result)) != len(result):
        raise ValueError("duplicate integers are not allowed")
    return tuple(result)


def split_seed_chunks(seeds: Iterable[int], total_chunks: int) -> tuple[tuple[int, ...], ...]:
    values = tuple(seeds)
    if total_chunks < 1:
        raise ValueError("total_chunks must be at least one")
    if total_chunks > len(values):
        raise ValueError("total_chunks cannot exceed the number of seeds")
    base, remainder = divmod(len(values), total_chunks)
    chunks: list[tuple[int, ...]] = []
    offset = 0
    for index in range(total_chunks):
        size = base + (1 if index < remainder else 0)
        chunks.append(values[offset : offset + size])
        offset += size
    return tuple(chunks)


def chunk_name(chunk_index: int, total_chunks: int) -> str:
    return f"chunk-{chunk_index + 1:02d}-of-{total_chunks:02d}"


def _row_from_mapping(mapping: dict[str, str]) -> ConfirmatoryRow:
    converted: dict[str, object] = {}
    allowed = {field.name for field in fields(ConfirmatoryRow)}
    missing = allowed - set(mapping)
    if missing:
        raise ValueError(f"CSV row is missing fields: {sorted(missing)}")
    for key in allowed:
        value = mapping[key]
        if key in _INT_FIELDS:
            converted[key] = int(value)
        elif key in _FLOAT_FIELDS:
            converted[key] = float(value)
        else:
            converted[key] = value
    return ConfirmatoryRow(**converted)


def read_rows(path: Path) -> list[ConfirmatoryRow]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return [_row_from_mapping(row) for row in csv.DictReader(handle)]


def row_identity(row: ConfirmatoryRow) -> tuple[object, ...]:
    return (
        row.benchmark,
        row.scenario,
        row.noise_ratio,
        row.samples_per_client,
        row.num_clients,
        row.seed,
        row.method,
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _file_inventory(directory: Path) -> dict[str, dict[str, object]]:
    inventory: dict[str, dict[str, object]] = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            relative = path.relative_to(directory).as_posix()
            inventory[relative] = {
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
    return inventory


def sync_to_drive(run_directory: Path, drive_root: Path | None) -> Path | None:
    if drive_root is None:
        return None
    drive_root.mkdir(parents=True, exist_ok=True)
    destination = drive_root / run_directory.name
    shutil.copytree(run_directory, destination, dirs_exist_ok=True)
    return destination


def _base_manifest(
    *,
    command: str,
    run_id: str,
    config: dict[str, object],
    status: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "command": command,
        "run_id": run_id,
        "status": status,
        "created_at_utc": utc_now(),
        "fedfalsify_version": __version__,
        "git_commit": git_commit(),
        "python": sys.version,
        "platform": platform.platform(),
        "config": config,
    }


def run_chunk(args: argparse.Namespace) -> Path:
    all_seeds = parse_int_spec(args.seeds)
    chunks = split_seed_chunks(all_seeds, args.total_chunks)
    if not 0 <= args.chunk_index < args.total_chunks:
        raise ValueError("chunk_index must use zero-based indexing and be in range")
    selected_seeds = chunks[args.chunk_index]

    root = Path(args.output_root).resolve() / args.run_id
    directory = root / "chunks" / chunk_name(args.chunk_index, args.total_chunks)
    manifest_path = directory / "manifest.json"
    if manifest_path.exists() and not args.force:
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        if previous.get("status") == "completed":
            print(f"Chunk already completed; leaving files unchanged: {directory}")
            sync_to_drive(root, Path(args.drive_root).resolve() if args.drive_root else None)
            return directory

    config: dict[str, object] = {
        "benchmarks": list(parse_csv_list(args.benchmarks)),
        "scenarios": list(parse_csv_list(args.scenarios)),
        "noise_ratios": list(parse_float_list(args.noise)),
        "samples_per_client": list(parse_int_spec(args.samples)),
        "client_counts": list(parse_int_spec(args.clients)),
        "all_seeds": list(all_seeds),
        "selected_seeds": list(selected_seeds),
        "chunk_index_zero_based": args.chunk_index,
        "total_chunks": args.total_chunks,
        "methods": list(parse_csv_list(args.methods)),
        "max_terms": args.max_terms,
        "population_size": args.population_size,
        "generations": args.generations,
        "max_genes": args.max_genes,
        "bootstrap_resamples": args.bootstrap_resamples,
    }
    directory.mkdir(parents=True, exist_ok=True)
    _write_json(
        manifest_path,
        _base_manifest(
            command="run-chunk",
            run_id=args.run_id,
            config=config,
            status="running",
        ),
    )

    rows = run_study(
        benchmarks=tuple(config["benchmarks"]),
        scenarios=tuple(config["scenarios"]),
        noise_ratios=tuple(config["noise_ratios"]),
        samples_per_client=tuple(config["samples_per_client"]),
        client_counts=tuple(config["client_counts"]),
        seeds=tuple(config["selected_seeds"]),
        methods=tuple(config["methods"]),
        max_terms=args.max_terms,
        population_size=args.population_size,
        generations=args.generations,
        max_genes=args.max_genes,
    )
    rows_path = directory / "rows.csv"
    raw_summary_path = directory / "summary_raw.json"
    corrected_summary_path = directory / "summary_holm.json"
    write_csv(rows, rows_path)
    raw_summary = summarize(rows, bootstrap_resamples=args.bootstrap_resamples)
    _write_json(raw_summary_path, raw_summary)
    _write_json(corrected_summary_path, add_holm_correction(raw_summary))

    expected_rows = (
        len(config["benchmarks"])
        * len(config["scenarios"])
        * len(config["noise_ratios"])
        * len(config["samples_per_client"])
        * len(config["client_counts"])
        * len(config["selected_seeds"])
        * len(config["methods"])
    )
    if len(rows) != expected_rows:
        raise RuntimeError(f"expected {expected_rows} rows but produced {len(rows)}")

    manifest = _base_manifest(
        command="run-chunk",
        run_id=args.run_id,
        config=config,
        status="completed",
    )
    manifest.update(
        {
            "completed_at_utc": utc_now(),
            "row_count": len(rows),
            "expected_row_count": expected_rows,
            "files": _file_inventory(directory),
        }
    )
    _write_json(manifest_path, manifest)

    drive_destination = sync_to_drive(
        root,
        Path(args.drive_root).resolve() if args.drive_root else None,
    )
    print(f"Completed {chunk_name(args.chunk_index, args.total_chunks)}")
    print(f"Seeds: {selected_seeds}")
    print(f"Repository output: {directory}")
    if drive_destination is not None:
        print(f"Drive mirror: {drive_destination}")
    return directory


def merge_chunks(args: argparse.Namespace) -> Path:
    root = Path(args.output_root).resolve() / args.run_id
    chunk_directories = sorted((root / "chunks").glob("chunk-*-of-*"))
    if len(chunk_directories) != args.expected_chunks:
        raise RuntimeError(
            f"expected {args.expected_chunks} chunk directories but found "
            f"{len(chunk_directories)} under {root / 'chunks'}"
        )

    all_rows: list[ConfirmatoryRow] = []
    chunk_manifests: list[dict[str, object]] = []
    for directory in chunk_directories:
        manifest_path = directory / "manifest.json"
        rows_path = directory / "rows.csv"
        if not manifest_path.exists() or not rows_path.exists():
            raise RuntimeError(f"incomplete chunk directory: {directory}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "completed":
            raise RuntimeError(f"chunk is not completed: {directory}")
        chunk_manifests.append(manifest)
        all_rows.extend(read_rows(rows_path))

    identities = [row_identity(row) for row in all_rows]
    duplicates = len(identities) - len(set(identities))
    if duplicates:
        raise RuntimeError(f"found {duplicates} duplicate method-condition rows")
    if args.expected_rows is not None and len(all_rows) != args.expected_rows:
        raise RuntimeError(
            f"expected {args.expected_rows} merged rows but found {len(all_rows)}"
        )

    final_directory = root / "final"
    final_directory.mkdir(parents=True, exist_ok=True)
    rows_path = final_directory / "v06_confirmatory.csv"
    raw_summary_path = final_directory / "v06_confirmatory_raw.json"
    corrected_summary_path = final_directory / "v06_confirmatory_holm.json"
    write_csv(all_rows, rows_path)
    raw_summary = summarize(all_rows, bootstrap_resamples=args.bootstrap_resamples)
    corrected_summary = add_holm_correction(raw_summary)
    _write_json(raw_summary_path, raw_summary)
    _write_json(corrected_summary_path, corrected_summary)

    manifest = _base_manifest(
        command="merge",
        run_id=args.run_id,
        config={
            "expected_chunks": args.expected_chunks,
            "expected_rows": args.expected_rows,
            "bootstrap_resamples": args.bootstrap_resamples,
        },
        status="completed",
    )
    manifest.update(
        {
            "completed_at_utc": utc_now(),
            "row_count": len(all_rows),
            "chunk_count": len(chunk_directories),
            "chunk_git_commits": sorted(
                {str(item.get("git_commit", "unknown")) for item in chunk_manifests}
            ),
            "files": _file_inventory(final_directory),
        }
    )
    _write_json(final_directory / "manifest.json", manifest)
    (root / "COMPLETE").write_text(
        f"completed_at_utc={utc_now()}\nrows={len(all_rows)}\n",
        encoding="utf-8",
    )

    drive_destination = sync_to_drive(
        root,
        Path(args.drive_root).resolve() if args.drive_root else None,
    )
    print(f"Merged {len(all_rows)} rows from {len(chunk_directories)} chunks")
    print(f"Repository output: {final_directory}")
    if drive_destination is not None:
        print(f"Drive mirror: {drive_destination}")
    return final_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run and merge resumable FedFalsify Colab experiments."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run-chunk", help="run one deterministic seed chunk")
    run.add_argument("--run-id", default="v06-primary-confirmatory")
    run.add_argument("--output-root", default="results/colab")
    run.add_argument("--drive-root")
    run.add_argument("--benchmarks", default="base,poly3,nested_sine,trig_product,interaction")
    run.add_argument("--scenarios", default="complementary,spurious,exception")
    run.add_argument("--noise", default="0.03,0.10")
    run.add_argument("--samples", default="300")
    run.add_argument("--clients", default="4")
    run.add_argument("--seeds", default="9001-9020")
    run.add_argument("--methods", default=",".join(METHODS))
    run.add_argument("--chunk-index", type=int, default=0)
    run.add_argument("--total-chunks", type=int, default=4)
    run.add_argument("--max-terms", type=int, default=6)
    run.add_argument("--population-size", type=int, default=48)
    run.add_argument("--generations", type=int, default=12)
    run.add_argument("--max-genes", type=int, default=4)
    run.add_argument("--bootstrap-resamples", type=int, default=4000)
    run.add_argument("--force", action="store_true")
    run.set_defaults(handler=run_chunk)

    merge = subparsers.add_parser("merge", help="validate and merge completed chunks")
    merge.add_argument("--run-id", default="v06-primary-confirmatory")
    merge.add_argument("--output-root", default="results/colab")
    merge.add_argument("--drive-root")
    merge.add_argument("--expected-chunks", type=int, default=4)
    merge.add_argument("--expected-rows", type=int, default=2400)
    merge.add_argument("--bootstrap-resamples", type=int, default=10000)
    merge.set_defaults(handler=merge_chunks)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
