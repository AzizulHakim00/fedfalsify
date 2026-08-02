import argparse
import json
from pathlib import Path

from fedfalsify.colab_pipeline import (
    merge_chunks,
    parse_int_spec,
    split_seed_chunks,
)
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


def test_parse_integer_ranges_and_balanced_chunks() -> None:
    seeds = parse_int_spec("9001-9005,9010")
    assert seeds == (9001, 9002, 9003, 9004, 9005, 9010)
    assert split_seed_chunks(seeds, 4) == (
        (9001, 9002),
        (9003, 9004),
        (9005,),
        (9010,),
    )


def test_merge_validates_chunks_and_mirrors_to_drive(tmp_path: Path) -> None:
    output_root = tmp_path / "repo-results"
    drive_root = tmp_path / "drive-results"
    run_root = output_root / "example-run"

    for index, seed in enumerate((9001, 9002), start=1):
        directory = run_root / "chunks" / f"chunk-{index:02d}-of-02"
        directory.mkdir(parents=True)
        write_csv(
            [_row(seed, "fedfalsify-v05"), _row(seed, "centralized-tree-gp")],
            directory / "rows.csv",
        )
        (directory / "manifest.json").write_text(
            json.dumps({"status": "completed", "git_commit": "abc"}),
            encoding="utf-8",
        )

    final = merge_chunks(
        argparse.Namespace(
            run_id="example-run",
            output_root=str(output_root),
            drive_root=str(drive_root),
            expected_chunks=2,
            expected_rows=4,
            bootstrap_resamples=100,
        )
    )

    assert (final / "v06_confirmatory.csv").exists()
    assert (final / "v06_confirmatory_holm.json").exists()
    assert (run_root / "COMPLETE").exists()
    assert (drive_root / "example-run" / "final" / "v06_confirmatory.csv").exists()
