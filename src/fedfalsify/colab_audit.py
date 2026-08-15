"""Scientific-integrity audit for resumable Colab confirmatory runs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable

from .colab_pipeline import (
    chunk_name,
    read_rows,
    row_identity,
    sha256_file,
    sync_to_drive,
)

_PROTOCOL_KEYS = (
    "benchmarks",
    "scenarios",
    "noise_ratios",
    "samples_per_client",
    "client_counts",
    "all_seeds",
    "total_chunks",
    "methods",
    "max_terms",
    "population_size",
    "generations",
    "max_genes",
    "bootstrap_resamples",
)

_REQUIRED_SOURCE_FILES = (
    "pyproject.toml",
    "research/V0_6_CONFIRMATORY_PROTOCOL.md",
    "colab/FedFalsify_v06_Confirmatory_Colab_Auto.ipynb",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _canonical_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _inventory(directory: Path, *, exclude: Iterable[str] = ()) -> dict[str, dict[str, object]]:
    excluded = set(exclude)
    result: dict[str, dict[str, object]] = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name not in excluded:
            relative = path.relative_to(directory).as_posix()
            result[relative] = {
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
    return result


def _verify_inventory(directory: Path, expected: dict[str, object]) -> None:
    actual = _inventory(directory, exclude={"manifest.json"})
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        unexpected = sorted(set(actual) - set(expected))
        changed = sorted(
            key for key in set(actual) & set(expected) if actual[key] != expected[key]
        )
        raise RuntimeError(
            "result inventory mismatch: "
            f"missing={missing}, unexpected={unexpected}, changed={changed}"
        )


def source_inventory(repo_root: Path) -> dict[str, dict[str, object]]:
    repo_root = repo_root.resolve()
    paths = sorted((repo_root / "src" / "fedfalsify").rglob("*.py"))
    for relative in _REQUIRED_SOURCE_FILES:
        path = repo_root / relative
        if not path.exists():
            raise RuntimeError(f"required source file is missing: {relative}")
        paths.append(path)
    unique_paths = sorted(set(paths))
    if not unique_paths:
        raise RuntimeError("no source files found for fingerprinting")
    return {
        path.relative_to(repo_root).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in unique_paths
    }


def source_fingerprint(repo_root: Path) -> tuple[str, dict[str, dict[str, object]]]:
    inventory = source_inventory(repo_root)
    return _canonical_digest(inventory), inventory


def protocol_payload(manifest: dict[str, object]) -> dict[str, object]:
    config = manifest.get("config")
    if not isinstance(config, dict):
        raise RuntimeError("manifest config is missing or invalid")
    missing = [key for key in _PROTOCOL_KEYS if key not in config]
    if missing:
        raise RuntimeError(f"manifest protocol config is missing keys: {missing}")
    return {key: config[key] for key in _PROTOCOL_KEYS}


def seal_chunk(args: argparse.Namespace) -> Path:
    repo_root = Path(args.repo_root).resolve()
    output_root = Path(args.output_root).resolve()
    run_root = output_root / args.run_id
    directory = run_root / "chunks" / chunk_name(args.chunk_index, args.total_chunks)
    manifest_path = directory / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(f"chunk manifest does not exist: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "completed":
        raise RuntimeError(f"chunk is not completed: {directory}")
    expected_inventory = manifest.get("files")
    if not isinstance(expected_inventory, dict):
        raise RuntimeError("chunk manifest has no result-file inventory")
    _verify_inventory(directory, expected_inventory)

    fingerprint, sources = source_fingerprint(repo_root)
    existing = manifest.get("source_fingerprint_sha256")
    if existing is not None and existing != fingerprint:
        raise RuntimeError(
            "completed chunk was produced with a different source fingerprint; "
            "do not overwrite confirmatory evidence"
        )
    protocol = protocol_payload(manifest)
    protocol_digest = _canonical_digest(protocol)
    existing_protocol = manifest.get("protocol_config_fingerprint_sha256")
    if existing_protocol is not None and existing_protocol != protocol_digest:
        raise RuntimeError("completed chunk protocol fingerprint changed")

    manifest.update(
        {
            "sealed_at_utc": utc_now(),
            "source_fingerprint_sha256": fingerprint,
            "source_file_count": len(sources),
            "source_files": sources,
            "protocol_config_fingerprint_sha256": protocol_digest,
        }
    )
    _write_json(manifest_path, manifest)
    sync_to_drive(run_root, Path(args.drive_root).resolve() if args.drive_root else None)
    print(f"Sealed {directory.name}: {fingerprint[:12]}")
    return directory


def verify_run(args: argparse.Namespace) -> Path:
    output_root = Path(args.output_root).resolve()
    run_root = output_root / args.run_id
    expected_names = {
        chunk_name(index, args.expected_chunks) for index in range(args.expected_chunks)
    }
    chunk_directories = {
        path.name: path for path in (run_root / "chunks").glob("chunk-*-of-*")
    }
    if set(chunk_directories) != expected_names:
        raise RuntimeError(
            "chunk directory set mismatch: "
            f"expected={sorted(expected_names)}, found={sorted(chunk_directories)}"
        )

    manifests: list[dict[str, object]] = []
    all_rows = []
    source_fingerprints: set[str] = set()
    protocol_fingerprints: set[str] = set()
    selected_seeds: list[int] = []
    expected_all_seeds: tuple[int, ...] | None = None

    for index in range(args.expected_chunks):
        directory = chunk_directories[chunk_name(index, args.expected_chunks)]
        manifest_path = directory / "manifest.json"
        rows_path = directory / "rows.csv"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "completed":
            raise RuntimeError(f"chunk is not completed: {directory}")
        if "source_fingerprint_sha256" not in manifest:
            raise RuntimeError(f"chunk is not scientifically sealed: {directory}")
        expected_inventory = manifest.get("files")
        if not isinstance(expected_inventory, dict):
            raise RuntimeError(f"chunk inventory is missing: {directory}")
        _verify_inventory(directory, expected_inventory)

        rows = read_rows(rows_path)
        if int(manifest.get("row_count", -1)) != len(rows):
            raise RuntimeError(f"chunk row count mismatch: {directory}")
        if int(manifest.get("expected_row_count", -1)) != len(rows):
            raise RuntimeError(f"chunk expected-row count mismatch: {directory}")

        config = manifest["config"]
        if int(config["chunk_index_zero_based"]) != index:
            raise RuntimeError(f"chunk index mismatch: {directory}")
        if int(config["total_chunks"]) != args.expected_chunks:
            raise RuntimeError(f"total chunk count mismatch: {directory}")
        chunk_seeds = tuple(int(value) for value in config["selected_seeds"])
        all_seed_tuple = tuple(int(value) for value in config["all_seeds"])
        if expected_all_seeds is None:
            expected_all_seeds = all_seed_tuple
        elif all_seed_tuple != expected_all_seeds:
            raise RuntimeError("all-seed specification differs across chunks")

        selected_seeds.extend(chunk_seeds)
        source_fingerprints.add(str(manifest["source_fingerprint_sha256"]))
        protocol_fingerprints.add(str(manifest["protocol_config_fingerprint_sha256"]))
        manifests.append(manifest)
        all_rows.extend(rows)

    if len(source_fingerprints) != 1:
        raise RuntimeError("source-code fingerprint differs across chunks")
    if len(protocol_fingerprints) != 1:
        raise RuntimeError("protocol configuration differs across chunks")
    if len(selected_seeds) != len(set(selected_seeds)):
        raise RuntimeError("seed overlap exists across chunks")
    if expected_all_seeds is None or tuple(sorted(selected_seeds)) != tuple(sorted(expected_all_seeds)):
        raise RuntimeError("chunk seeds do not exactly cover the frozen seed list")

    identities = [row_identity(row) for row in all_rows]
    if len(identities) != len(set(identities)):
        raise RuntimeError("duplicate method-condition rows found before merge")
    if args.expected_rows is not None and len(all_rows) != args.expected_rows:
        raise RuntimeError(
            f"expected {args.expected_rows} rows before merge but found {len(all_rows)}"
        )

    audit = {
        "schema_version": 1,
        "status": "verified",
        "verified_at_utc": utc_now(),
        "run_id": args.run_id,
        "chunk_count": len(manifests),
        "row_count": len(all_rows),
        "selected_seeds": sorted(selected_seeds),
        "source_fingerprint_sha256": next(iter(source_fingerprints)),
        "protocol_config_fingerprint_sha256": next(iter(protocol_fingerprints)),
        "chunk_manifests": {
            path.name: sha256_file(path / "manifest.json")
            for path in chunk_directories.values()
        },
    }
    audit_path = run_root / "audit_premerge.json"
    _write_json(audit_path, audit)
    sync_to_drive(run_root, Path(args.drive_root).resolve() if args.drive_root else None)
    print(f"Verified {len(all_rows)} unique rows across {len(manifests)} chunks")
    return audit_path


def seal_final(args: argparse.Namespace) -> Path:
    output_root = Path(args.output_root).resolve()
    run_root = output_root / args.run_id
    audit_path = run_root / "audit_premerge.json"
    final_directory = run_root / "final"
    final_manifest_path = final_directory / "manifest.json"
    complete_path = run_root / "COMPLETE"
    if not audit_path.exists() or not final_manifest_path.exists() or not complete_path.exists():
        raise RuntimeError("pre-merge audit, final manifest, and COMPLETE marker are required")

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("status") != "verified":
        raise RuntimeError("pre-merge audit is not verified")
    rows_path = final_directory / "v06_confirmatory.csv"
    rows = read_rows(rows_path)
    identities = [row_identity(row) for row in rows]
    if len(identities) != len(set(identities)):
        raise RuntimeError("duplicate rows found in final CSV")
    if args.expected_rows is not None and len(rows) != args.expected_rows:
        raise RuntimeError(
            f"expected {args.expected_rows} final rows but found {len(rows)}"
        )

    manifest = json.loads(final_manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "scientifically_verified_at_utc": utc_now(),
            "source_fingerprint_sha256": audit["source_fingerprint_sha256"],
            "protocol_config_fingerprint_sha256": audit[
                "protocol_config_fingerprint_sha256"
            ],
            "premerge_audit_sha256": sha256_file(audit_path),
            "verified_row_count": len(rows),
            "verified_files": _inventory(final_directory, exclude={"manifest.json"}),
        }
    )
    _write_json(final_manifest_path, manifest)
    verified_payload = {
        "status": "verified",
        "verified_at_utc": utc_now(),
        "run_id": args.run_id,
        "row_count": len(rows),
        "final_manifest_sha256": sha256_file(final_manifest_path),
        "premerge_audit_sha256": sha256_file(audit_path),
    }
    verified_path = run_root / "VERIFIED.json"
    _write_json(verified_path, verified_payload)
    sync_to_drive(run_root, Path(args.drive_root).resolve() if args.drive_root else None)
    print(f"Final result sealed and verified: {verified_path}")
    return verified_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit FedFalsify Colab results.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seal = subparsers.add_parser("seal-chunk")
    seal.add_argument("--repo-root", default=".")
    seal.add_argument("--run-id", default="v06-primary-confirmatory")
    seal.add_argument("--output-root", default="results/colab")
    seal.add_argument("--drive-root")
    seal.add_argument("--chunk-index", type=int, required=True)
    seal.add_argument("--total-chunks", type=int, default=4)
    seal.set_defaults(handler=seal_chunk)

    verify = subparsers.add_parser("verify-run")
    verify.add_argument("--run-id", default="v06-primary-confirmatory")
    verify.add_argument("--output-root", default="results/colab")
    verify.add_argument("--drive-root")
    verify.add_argument("--expected-chunks", type=int, default=4)
    verify.add_argument("--expected-rows", type=int, default=2400)
    verify.set_defaults(handler=verify_run)

    final = subparsers.add_parser("seal-final")
    final.add_argument("--run-id", default="v06-primary-confirmatory")
    final.add_argument("--output-root", default="results/colab")
    final.add_argument("--drive-root")
    final.add_argument("--expected-rows", type=int, default=2400)
    final.set_defaults(handler=seal_final)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
