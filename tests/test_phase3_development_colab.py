from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "build_phase3_development_colab.py"
NOTEBOOK = ROOT / "colab" / "FedFalsify_Phase3_Fresh_Development_OneCell.ipynb"


def _load_builder():
    spec = importlib.util.spec_from_file_location("phase3c_builder", BUILDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_phase3c_builder_has_frozen_nonplaceholder_pins():
    assert BUILDER.exists()
    builder = _load_builder()
    assert builder.FROZEN_SCIENTIFIC_SOURCE == "b67a07371bcf244728536028593373ca7d1990b1"
    assert builder.FROZEN_DEVELOPMENT_HARNESS_SOURCE == "c82f33cc4052b2fa266e66f488df0310edbc5737"
    assert len(builder.FROZEN_PROTOCOL_SHA256) == 64
    assert set(builder.FROZEN_PROTOCOL_SHA256) <= set("0123456789abcdef")
    assert "UNFROZEN" not in builder.FROZEN_PROTOCOL_SHA256


def test_generated_phase3c_notebook_is_one_cell_drive_first_and_fail_closed():
    builder = _load_builder()
    builder.build()
    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code_cells = [cell for cell in payload["cells"] if cell.get("cell_type") == "code"]
    assert len(code_cells) == 1
    cell = "".join(code_cells[0]["source"])

    assert "AUTHORIZE_FRESH_DEVELOPMENT = False" in cell
    assert "29301-29310" in cell
    assert "29300 BLOCKED" in cell
    assert "11001-11999 BLOCKED" in cell
    assert "/content/drive/MyDrive/FedFalsify_Q1/SCSV_NCSC_PHASE3_DEVELOPMENT" in cell

    drive_pos = cell.index('drive.mount("/content/drive"')
    clone_pos = cell.index('"git", "clone"')
    run_pos = cell.index("run_development(")
    assert drive_pos < clone_pos < run_pos


def test_phase3c_notebook_verifies_source_protocol_and_tests_before_authorization():
    builder = _load_builder()
    builder.build()
    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cell = "".join(payload["cells"][0]["source"])

    assert builder.FROZEN_DEVELOPMENT_HARNESS_SOURCE in cell
    assert builder.FROZEN_SCIENTIFIC_SOURCE in cell
    assert builder.FROZEN_PROTOCOL_SHA256 in cell
    assert "FROZEN_PHASE3C_DEVELOPMENT_PROTOCOL.md" in cell
    assert "git diff --exit-code" in cell
    assert "78d0ab7ca7afb1edfa4725a45dfd20ce2db39659" in cell
    assert "b67a07371bcf244728536028593373ca7d1990b1" in cell
    assert "pytest" in cell

    pytest_pos = cell.index("pytest")
    gate_pos = cell.index('FEDFALSIFY_PHASE3_TEST_GATE')
    runner_pos = cell.index("run_development(")
    assert pytest_pos < gate_pos < runner_pos
    assert "AUTHORIZE_PHASE3C_FRESH_DEVELOPMENT" in cell


def test_phase3c_notebook_does_not_copy_scientific_algorithms_inline():
    builder = _load_builder()
    builder.build()
    payload = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cell = "".join(payload["cells"][0]["source"])

    assert "from fedfalsify.phase3_development_runner import" in cell
    assert "def certify_shared_core" not in cell
    assert "def discover_localized_role" not in cell
    assert "def screen_on_selector" not in cell
    assert "def certify_on_probe" not in cell
    assert "def run_scsv_v12_branches" not in cell
