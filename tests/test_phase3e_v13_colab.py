from __future__ import annotations

import json
from pathlib import Path

from tools.build_phase3e_v13_colab import (
    EXECUTION_SOURCE,
    NOTEBOOK_PATH,
    PROTOCOL_SHA256,
    PYTHON_PATH,
    build_cell_source,
)

EXPECTED_EXECUTION_SOURCE = "b85667d02e4407b9ed913ecd5f23601921970ac2"
EXPECTED_BASE_SCIENCE = "435a8c1af7436fac3d3b1a625e356cf6de180bb0"
EXPECTED_PROTOCOL_SHA = "2eebcf892e3acd90c9a133f7945850f60cb8a89fd577f2c3ac6011f5f8fbeac7"


def test_phase3e_wrapper_pins_verified_runner_and_frozen_protocol() -> None:
    assert EXECUTION_SOURCE == EXPECTED_EXECUTION_SOURCE
    assert PROTOCOL_SHA256 == EXPECTED_PROTOCOL_SHA
    source = build_cell_source()
    assert EXPECTED_EXECUTION_SOURCE in source
    assert EXPECTED_BASE_SCIENCE in source
    assert EXPECTED_PROTOCOL_SHA in source


def test_phase3e_wrapper_is_fail_closed_and_drive_first() -> None:
    source = build_cell_source()
    assert "AUTHORIZE_FRESH_DEVELOPMENT = False" in source
    assert "AUTHORIZE_PHASE3E_V13_FRESH_NOISY_DEVELOPMENT" in source
    assert "/content/drive/MyDrive/FedFalsify_Q1/PHASE3E_V13_FRESH_NOISY_DEVELOPMENT" in source
    assert "29401-29410" in source
    assert "29301-29310" in source
    assert "11001-11999" in source

    mount = source.index('drive.mount("/content/drive"')
    clone = source.index('"git", "clone"')
    scientific_run = source.index("run_phase3e_development(")
    assert mount < clone < scientific_run


def test_phase3e_wrapper_runs_test_gate_before_authorized_science() -> None:
    source = build_cell_source()
    pytest_call = source.index('"-m", "pytest", "-q"')
    gate_pass = source.index('run_env["FEDFALSIFY_PHASE3E_TEST_GATE"] = "PASS"')
    science = source.index("run_phase3e_development(")
    assert pytest_call < gate_pass < science
    assert 'git", "-C", str(SOURCE_DIR), "diff", "--exit-code", FROZEN_BASE_HEAD' in source
    assert "actual_protocol_sha != EXPECTED_PROTOCOL_SHA256" in source


def test_phase3e_wrapper_never_deletes_drive_output_and_only_cleans_ephemeral_checkout() -> None:
    source = build_cell_source()
    assert "shutil.rmtree(SOURCE_DIR)" in source
    assert "shutil.rmtree(OUTPUT_DIR)" not in source
    assert "OUTPUT_DIR.unlink" not in source


def test_generated_notebook_is_exactly_one_code_cell_and_matches_python_handoff() -> None:
    notebook = json.loads(Path(NOTEBOOK_PATH).read_text(encoding="utf-8"))
    assert len(notebook["cells"]) == 1
    assert notebook["cells"][0]["cell_type"] == "code"
    notebook_source = "".join(notebook["cells"][0]["source"])
    assert notebook_source == build_cell_source()
    assert Path(PYTHON_PATH).read_text(encoding="utf-8") == build_cell_source()
