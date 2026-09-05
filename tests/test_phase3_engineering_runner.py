import json
from pathlib import Path
import zipfile

import pandas as pd
import pytest

import fedfalsify.phase3_engineering_runner as runner
from fedfalsify.scsv_v12 import PHASE3_METHODS


def _row(condition, method, *, exact=0.0, integrity=0):
    family, num_clients, balance, role, noise, seed = condition
    return {
        "family": family,
        "noise_ratio": float(noise),
        "num_clients": int(num_clients),
        "balance_profile": balance,
        "role_profile": role,
        "seed": int(seed),
        "condition_key": runner.condition_key_string(condition),
        "method": method,
        "exact_recovery": float(exact),
        "term_precision": 1.0,
        "term_recall": 1.0,
        "shared_precision": 1.0,
        "shared_recall": 1.0,
        "deviation_precision": 1.0,
        "deviation_recall": 1.0,
        "test_nmse": 0.01,
        "runtime_seconds": 0.1,
        "communication_bytes": 100,
        "final_structure": "1;x1",
        "accepted_deviations": "",
        "integrity_violations": int(integrity),
        "shared_diagnostics_json": "[]",
        "localized_diagnostics_json": "[]",
        "expression": "1 + x1",
        "stop_reason": "fake",
    }


def test_engineering_matrix_is_exact_and_seed_is_29300_only():
    expected = (
        ("quadratic_role_v10", 4, "balanced", "single", 0.10, 29300),
        ("trig_role_v10", 4, "balanced", "single", 0.30, 29300),
        ("null_role_v10", 8, "balanced", "none", 0.10, 29300),
        ("anchor_contamination_null_v10", 8, "balanced", "none", 0.30, 29300),
        ("weak_source_role_v10", 8, "balanced", "quarter", 0.10, 29300),
        ("dual_role_v10", 8, "imbalanced", "quarter", 0.30, 29300),
    )
    assert runner.ENGINEERING_CONDITIONS == expected
    assert len(runner.ENGINEERING_CONDITIONS) == 6
    assert {row[-1] for row in runner.ENGINEERING_CONDITIONS} == {29300}


def test_checkpoint_resume_keeps_only_complete_four_method_groups(tmp_path):
    complete = runner.ENGINEERING_CONDITIONS[0]
    partial = runner.ENGINEERING_CONDITIONS[1]
    rows = [_row(complete, method) for method in PHASE3_METHODS]
    rows += [_row(partial, method) for method in PHASE3_METHODS[:2]]
    checkpoint = tmp_path / "checkpoint.csv"
    pd.DataFrame(rows).to_csv(checkpoint, index=False)

    loaded = runner.load_checkpoint(checkpoint)
    cleaned, completed = runner.validate_checkpoint_groups(loaded)

    assert completed == {complete}
    assert len(cleaned) == 4
    assert all(row["condition_key"] != runner.condition_key_string(partial) for row in cleaned)


def test_duplicate_method_group_is_not_resumable():
    condition = runner.ENGINEERING_CONDITIONS[0]
    rows = [_row(condition, method) for method in PHASE3_METHODS]
    rows.append(_row(condition, PHASE3_METHODS[0]))
    cleaned, completed = runner.validate_checkpoint_groups(rows)
    assert cleaned == []
    assert completed == set()


def test_atomic_write_csv_replaces_target_without_tmp_residue(tmp_path):
    path = tmp_path / "rows.csv"
    runner.atomic_write_csv(pd.DataFrame([{"a": 1}]), path)
    runner.atomic_write_csv(pd.DataFrame([{"a": 2}]), path)
    assert pd.read_csv(path).to_dict("records") == [{"a": 2}]
    assert not list(tmp_path.glob("*.tmp"))


def test_engineering_decision_uses_integrity_not_performance():
    rows = []
    for condition in runner.ENGINEERING_CONDITIONS:
        rows.extend(_row(condition, method, exact=0.0) for method in PHASE3_METHODS)
    assert runner.engineering_decision(
        rows,
        test_gate_passed=True,
        artifacts_ok=True,
        zip_ok=True,
    ) == "PHASE3-ENGINEERING-PASS"

    changed = [dict(row, exact_recovery=1.0, test_nmse=1e-12) for row in rows]
    assert runner.engineering_decision(
        changed,
        test_gate_passed=True,
        artifacts_ok=True,
        zip_ok=True,
    ) == "PHASE3-ENGINEERING-PASS"

    changed[0]["integrity_violations"] = 1
    assert runner.engineering_decision(
        changed,
        test_gate_passed=True,
        artifacts_ok=True,
        zip_ok=True,
    ) == "PHASE3-ENGINEERING-FAIL"


def test_fake_engineering_run_writes_complete_reproducibility_package(tmp_path, monkeypatch):
    monkeypatch.setenv("FEDFALSIFY_PHASE3_TEST_GATE", "PASS")

    def fake_evaluator(condition):
        return [_row(condition, method, exact=float(method == "scsv-ncsc")) for method in PHASE3_METHODS]

    monkeypatch.setattr(runner, "_evaluate_condition", fake_evaluator)
    result = runner.run_engineering(tmp_path, seed=29300, live=False)

    assert result["decision"] == "PHASE3-ENGINEERING-PASS"
    assert result["conditions_complete"] == 6
    assert result["primary_rows"] == 24
    assert set(runner.REQUIRED_ARTIFACTS).issubset({path.name for path in tmp_path.iterdir()})

    decision = json.loads((tmp_path / "phase3_engineering_decision.json").read_text())
    assert decision["decision"] == "PHASE3-ENGINEERING-PASS"

    archive = tmp_path / "FedFalsify_PHASE3_NCSC_ENGINEERING_RESULTS.zip"
    with zipfile.ZipFile(archive) as handle:
        assert handle.testzip() is None
        assert "phase3_engineering_sha256.txt" in handle.namelist()


def test_runner_rejects_missing_pre_execution_test_gate(tmp_path, monkeypatch):
    monkeypatch.delenv("FEDFALSIFY_PHASE3_TEST_GATE", raising=False)
    with pytest.raises(RuntimeError, match="test gate"):
        runner.run_engineering(tmp_path, seed=29300, live=False)
