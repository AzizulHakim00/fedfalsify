from __future__ import annotations

import json
import pickle
import zipfile
from pathlib import Path

import joblib

import fedfalsify.phase3d_runner as runner
from fedfalsify.phase3d_fixtures import build_phase3d_fixtures
from fedfalsify.scsv_v13 import Phase3DModelResult


def _fake_result(fixture, model_name, outer_fold=0):
    localized = tuple(fixture.true_localized_terms) if model_name == "v13-full" else ()
    truth = dict(fixture.truth_scopes)
    scopes = tuple((term, truth[term]) for term in localized)
    return Phase3DModelResult(
        method=model_name,
        fixture=fixture.name,
        outer_fold=int(outer_fold),
        shared_structure=tuple(fixture.true_shared_terms),
        accepted_localized=localized,
        localized_scopes=scopes,
        exact_shared=True,
        exact_localized=(set(localized) == set(fixture.true_localized_terms)),
        exact_scope=(dict(scopes) == truth),
        exact_structure=(model_name == "v13-full"),
        diagnostics=({"stage": "fake", "accepted": True},),
        communication_bytes=123,
        runtime_seconds=0.01,
        stop_reason="test fixture result",
        execution_error=None,
    )


def _one_fixture(monkeypatch):
    fixture = build_phase3d_fixtures()[0]
    monkeypatch.setattr(runner, "build_phase3d_fixtures", lambda: (fixture,))
    return fixture


def test_atomic_unit_roundtrip_and_hash_validation(tmp_path):
    key = {"fixture": "quadratic_scope_shift", "model": "v13-full", "outer_fold": 0}
    path = tmp_path / "unit.json"
    payload = runner.make_unit_payload(key, "abc123", {"method": "v13-full", "value": 7})
    runner.atomic_json_write(path, payload)

    restored = runner.verify_unit(path, key, "abc123")
    assert restored is not None
    assert restored["result"]["value"] == 7

    corrupted = json.loads(path.read_text(encoding="utf-8"))
    corrupted["result"]["value"] = 8
    path.write_text(json.dumps(corrupted), encoding="utf-8")
    assert runner.verify_unit(path, key, "abc123") is None


def test_disconnect_then_resume_skips_completed_model_fold(tmp_path, monkeypatch):
    _one_fixture(monkeypatch)
    calls: list[str] = []
    fail_once = {"enabled": True}

    def flaky(fixture, model_name, outer_fold=0):
        calls.append(model_name)
        if model_name == "v12-frozen" and fail_once["enabled"]:
            fail_once["enabled"] = False
            raise RuntimeError("simulated runtime disconnect")
        return _fake_result(fixture, model_name, outer_fold)

    monkeypatch.setattr(runner, "run_phase3d_model", flaky)

    try:
        runner.run_phase3d(tmp_path, outer_folds=(0,), live=False)
    except RuntimeError as exc:
        assert "simulated runtime disconnect" in str(exc)
    else:
        raise AssertionError("simulated disconnect should escape")

    # v11 completed before the disconnect and must already be durable.
    assert (tmp_path / "units" / "quadratic_scope_shift" / "v11-frozen" / "fold_000.json").is_file()
    checkpoint = (tmp_path / "checkpoint_index.csv").read_text(encoding="utf-8")
    assert "v11-frozen" in checkpoint

    calls.clear()
    result = runner.run_phase3d(tmp_path, outer_folds=(0,), live=False)
    assert "v11-frozen" not in calls
    assert calls == ["v12-frozen", "scope-contrast-only", "v13-full"]
    assert result["integrity"]["complete"] is True
    assert result["integrity"]["completed_units"] == 4


def test_corrupt_unit_reruns_only_that_unit(tmp_path, monkeypatch):
    _one_fixture(monkeypatch)
    calls: list[str] = []

    def fake(fixture, model_name, outer_fold=0):
        calls.append(model_name)
        return _fake_result(fixture, model_name, outer_fold)

    monkeypatch.setattr(runner, "run_phase3d_model", fake)
    runner.run_phase3d(tmp_path, outer_folds=(0,), live=False)
    assert calls == list(runner.PHASE3D_MODELS)

    corrupt = tmp_path / "units" / "quadratic_scope_shift" / "scope-contrast-only" / "fold_000.json"
    data = json.loads(corrupt.read_text(encoding="utf-8"))
    data["result"]["stop_reason"] = "tampered"
    corrupt.write_text(json.dumps(data), encoding="utf-8")

    calls.clear()
    runner.run_phase3d(tmp_path, outer_folds=(0,), live=False)
    assert calls == ["scope-contrast-only"]


def test_final_artifacts_are_reproducible_and_equivalent(tmp_path, monkeypatch):
    _one_fixture(monkeypatch)
    monkeypatch.setattr(runner, "run_phase3d_model", _fake_result)
    result = runner.run_phase3d(tmp_path, outer_folds=(0,), live=False)

    required = (
        "config/frozen_config.json",
        "config/source_provenance.json",
        "config/environment.json",
        "checkpoint_index.csv",
        "phase3d_results.csv",
        "phase3d_results.pkl",
        "phase3d_results.joblib",
        "phase3d_diagnostics.csv",
        "phase3d_scope_diagnostics.csv",
        "phase3d_summary.csv",
        "phase3d_integrity.json",
        "phase3d_manifest_sha256.txt",
        runner.ZIP_NAME,
    )
    for name in required:
        assert (tmp_path / name).is_file(), name

    with (tmp_path / "phase3d_results.pkl").open("rb") as handle:
        pkl_state = pickle.load(handle)
    joblib_state = joblib.load(tmp_path / "phase3d_results.joblib")
    assert pkl_state == joblib_state
    assert len(pkl_state) == 4

    manifest_lines = (tmp_path / "phase3d_manifest_sha256.txt").read_text(encoding="utf-8").splitlines()
    assert manifest_lines
    assert all("  " in line for line in manifest_lines)

    with zipfile.ZipFile(tmp_path / runner.ZIP_NAME, "r") as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
        assert "phase3d_results.csv" in names
        assert "phase3d_manifest_sha256.txt" in names

    assert result["integrity"]["complete"] is True
    assert result["integrity"]["duplicate_unit_keys"] == 0
    assert result["integrity"]["invalid_units"] == 0


def test_work_unit_keys_never_contain_scientific_seed_fields(tmp_path, monkeypatch):
    _one_fixture(monkeypatch)
    monkeypatch.setattr(runner, "run_phase3d_model", _fake_result)
    runner.run_phase3d(tmp_path, outer_folds=(0,), live=False)

    checkpoint = runner.pd.read_csv(tmp_path / "checkpoint_index.csv")
    assert set(checkpoint.columns) >= {"fixture", "model", "outer_fold"}
    assert "seed" not in checkpoint.columns
    assert set(checkpoint["outer_fold"]) == {0}
