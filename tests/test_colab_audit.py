import argparse
import json
from pathlib import Path

import pytest

from fedfalsify.colab_audit import _inventory, seal_chunk, verify_run
from fedfalsify.confirmatory import ConfirmatoryRow, write_csv


def _row(seed: int, method: str) -> ConfirmatoryRow:
    return ConfirmatoryRow(
        benchmark="base",
        scenario="complementary",
        noise_ratio=0.03,
        samples_per_client=60,
        num_clients=4,
        seed=seed,
        method=method,
        exact_recovery=float(method == "fedfalsify-v05"),
        term_precision=1.0,
        term_recall=1.0,
        test_nmse=0.01,
        train_mse=0.01,
        spurious_accepted=0.0,
        exception_recovered=1.0,
        runtime_seconds=0.1,
        communication_bytes=100,
        search_evaluations=3,
        discovered_terms="x1",
        expression="2*x1",
        stop_reason="test",
    )


def _fake_repo(root: Path) -> None:
    source = root / "src" / "fedfalsify"
    source.mkdir(parents=True)
    (source / "algorithm.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    protocol = root / "research" / "V0_6_CONFIRMATORY_PROTOCOL.md"
    protocol.parent.mkdir(parents=True)
    protocol.write_text("frozen protocol\n", encoding="utf-8")
    notebook = root / "colab" / "FedFalsify_v06_Confirmatory_Colab_Auto.ipynb"
    notebook.parent.mkdir(parents=True)
    notebook.write_text('{"nbformat": 4, "cells": []}\n', encoding="utf-8")


def _config(index: int, seed: int) -> dict[str, object]:
    return {
        "benchmarks": ["base"],
        "scenarios": ["complementary"],
        "noise_ratios": [0.03],
        "samples_per_client": [60],
        "client_counts": [4],
        "all_seeds": [9001, 9002],
        "selected_seeds": [seed],
        "chunk_index_zero_based": index,
        "total_chunks": 2,
        "methods": ["fedfalsify-v05", "centralized-tree-gp"],
        "max_terms": 6,
        "population_size": 12,
        "generations": 2,
        "max_genes": 3,
        "bootstrap_resamples": 500,
    }


def _write_chunk(run_root: Path, index: int, seed: int) -> None:
    directory = run_root / "chunks" / f"chunk-{index + 1:02d}-of-02"
    directory.mkdir(parents=True)
    rows = [_row(seed, "fedfalsify-v05"), _row(seed, "centralized-tree-gp")]
    write_csv(rows, directory / "rows.csv")
    manifest = {
        "status": "completed",
        "row_count": len(rows),
        "expected_row_count": len(rows),
        "config": _config(index, seed),
        "files": _inventory(directory, exclude={"manifest.json"}),
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def test_seal_and_verify_detects_consistent_chunks(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    output_root = repo_root / "results" / "colab"
    drive_root = tmp_path / "drive"
    run_root = output_root / "example"
    _fake_repo(repo_root)
    _write_chunk(run_root, 0, 9001)
    _write_chunk(run_root, 1, 9002)

    for index in range(2):
        seal_chunk(
            argparse.Namespace(
                repo_root=str(repo_root),
                run_id="example",
                output_root=str(output_root),
                drive_root=str(drive_root),
                chunk_index=index,
                total_chunks=2,
            )
        )

    audit_path = verify_run(
        argparse.Namespace(
            run_id="example",
            output_root=str(output_root),
            drive_root=str(drive_root),
            expected_chunks=2,
            expected_rows=4,
        )
    )
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["status"] == "verified"
    assert audit["row_count"] == 4
    assert audit["selected_seeds"] == [9001, 9002]
    assert (drive_root / "example" / "audit_premerge.json").exists()


def test_sealed_chunk_rejects_changed_source(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    output_root = repo_root / "results" / "colab"
    run_root = output_root / "example"
    _fake_repo(repo_root)
    _write_chunk(run_root, 0, 9001)
    args = argparse.Namespace(
        repo_root=str(repo_root),
        run_id="example",
        output_root=str(output_root),
        drive_root=None,
        chunk_index=0,
        total_chunks=2,
    )
    seal_chunk(args)
    (repo_root / "src" / "fedfalsify" / "algorithm.py").write_text(
        "VALUE = 2\n", encoding="utf-8"
    )
    with pytest.raises(RuntimeError, match="different source fingerprint"):
        seal_chunk(args)
