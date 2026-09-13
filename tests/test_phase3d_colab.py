from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_phase3d_colab.py"
NOTEBOOK = ROOT / "colab" / "FedFalsify_Phase3D_V13_Scope_Contrast_OneCell.ipynb"


def _load_builder():
    spec = importlib.util.spec_from_file_location("phase3d_builder", BUILDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase3d_builder_has_exact_nonplaceholder_source_pin():
    assert BUILDER.exists()
    builder = _load_builder()
    assert builder.PHASE3D_EXECUTION_SOURCE == "d0e2907b1a3fe2e02096ec65ce4883da03ae34f8"
    assert builder.FROZEN_PHASE3C_SCIENTIFIC_SOURCE == "b67a07371bcf244728536028593373ca7d1990b1"
    assert len(builder.PHASE3D_EXECUTION_SOURCE) == 40
    assert "UNPINNED" not in builder.PHASE3D_EXECUTION_SOURCE


def test_generated_phase3d_notebook_is_one_cell_drive_first_and_resume_safe():
    builder = _load_builder()
    builder.build()
    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code_cells = [cell for cell in payload["cells"] if cell.get("cell_type") == "code"]
    assert len(code_cells) == 1
    cell = "".join(code_cells[0]["source"])

    assert "/content/drive/MyDrive/FedFalsify_Q1/PHASE3D_V13_SCOPE_CONTRAST_FIXTURES" in cell
    assert "outer_folds=(0,)" in cell
    assert "phase3d_runner import run_phase3d" in cell
    assert "per-fixture × model × fold" in cell or "fixture × model × fold" in cell

    drive_pos = cell.index('drive.mount("/content/drive"')
    clone_pos = cell.index('"git", "clone"')
    run_pos = cell.index("run_phase3d(")
    assert drive_pos < clone_pos < run_pos


def test_phase3d_notebook_verifies_source_frozen_science_and_tests_before_run():
    builder = _load_builder()
    builder.build()
    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cell = "".join(payload["cells"][0]["source"])

    assert builder.PHASE3D_EXECUTION_SOURCE in cell
    assert builder.FROZEN_PHASE3C_SCIENTIFIC_SOURCE in cell
    assert "git diff --exit-code" in cell
    assert "tests/test_phase3d_scope_contrast.py" in cell
    assert "tests/test_phase3d_runner.py" in cell
    assert "pytest" in cell

    checkout_pos = cell.index(builder.PHASE3D_EXECUTION_SOURCE)
    pytest_pos = cell.index("pytest")
    run_pos = cell.index("run_phase3d(")
    assert checkout_pos < pytest_pos < run_pos


def test_phase3d_notebook_has_no_scientific_seed_configuration_and_no_inline_algorithms():
    builder = _load_builder()
    builder.build()
    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cell = "".join(payload["cells"][0]["source"])

    # This zero-seed architectural proof must not configure any spent/final
    # scientific seed block in the executable wrapper.
    for token in ("29300", "29301", "29310", "11001", "11999"):
        assert token not in cell

    assert "from fedfalsify.phase3d_runner import run_phase3d" in cell
    assert "def scope_contrast_test" not in cell
    assert "def discover_scope_contrast" not in cell
    assert "def _joint_certify" not in cell
    assert "def run_phase3d_model" not in cell


def test_generated_phase3d_notebook_is_checked_in_and_matches_builder_output():
    builder = _load_builder()
    builder.build()
    first = NOTEBOOK.read_bytes()
    builder.build()
    second = NOTEBOOK.read_bytes()
    assert first == second
    payload = json.loads(first.decode("utf-8"))
    assert payload["nbformat"] == 4
