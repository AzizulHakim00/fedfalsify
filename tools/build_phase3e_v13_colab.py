"""Build the fail-closed one-cell Colab wrapper for Phase-3E v13 fresh-noisy development."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

NOTEBOOK_PATH = Path("colab/FedFalsify_Phase3E_V13_Fresh_Noisy_Development_OneCell.ipynb")
PYTHON_PATH = Path("colab/FedFalsify_Phase3E_V13_Fresh_Noisy_Development_OneCell.py")
EXECUTION_SOURCE = "b85667d02e4407b9ed913ecd5f23601921970ac2"
FROZEN_BASE_HEAD = "435a8c1af7436fac3d3b1a625e356cf6de180bb0"
PROTOCOL_SHA256 = "2eebcf892e3acd90c9a133f7945850f60cb8a89fd577f2c3ac6011f5f8fbeac7"

_CELL_TEMPLATE = r'''# ============================================================================================
# FedFalsify Phase-3E / v13 SCSV-SCC — FRESH NOISY DEVELOPMENT
# SELF-CONTAINED ONE-CELL COLAB WRAPPER
#
# IMPORTANT SCIENTIFIC FIREWALL
#   * v13 architecture is FROZEN. This cell does not redesign it.
#   * 29301-29310 are spent historical Phase-3C development seeds and are BLOCKED.
#   * 29401-29410 are the fresh Phase-3E development block.
#   * 11001-11999 are protected final-confirmation seeds and are BLOCKED.
#   * Opening/running this notebook is safe by default: authorization is False.
#   * Once AUTHORIZE_FRESH_DEVELOPMENT=True causes any 29401-29410 scientific run,
#     the whole Phase-3E block is scientifically spent and cannot be reused after tuning.
#
# PINNED VERIFIED EXECUTION SOURCE: __EXECUTION_SOURCE__
# FROZEN PRE-PHASE3E SCIENCE:       __FROZEN_BASE_HEAD__
# FROZEN PROTOCOL SHA256:           __PROTOCOL_SHA256__
# ============================================================================================

AUTHORIZE_FRESH_DEVELOPMENT = False

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from google.colab import drive

REPO_URL = "https://github.com/AzizulHakim00/fedfalsify.git"
PINNED_EXECUTION_SOURCE = "__EXECUTION_SOURCE__"
FROZEN_BASE_HEAD = "__FROZEN_BASE_HEAD__"
EXPECTED_PROTOCOL_SHA256 = "__PROTOCOL_SHA256__"
SOURCE_DIR = Path("/content/fedfalsify_phase3e_v13_pinned")
VENV_DIR = Path("/content/fedfalsify_phase3e_v13_cleanenv")
OUTPUT_DIR = Path("/content/drive/MyDrive/FedFalsify_Q1/PHASE3E_V13_FRESH_NOISY_DEVELOPMENT")
PROTOCOL_NAME = "FROZEN_PHASE3E_V13_DEVELOPMENT_PROTOCOL.md"
AUTH_TOKEN = "AUTHORIZE_PHASE3E_V13_FRESH_NOISY_DEVELOPMENT"
ZIP_NAME = "FedFalsify_PHASE3E_V13_FRESH_NOISY_RESULTS.zip"

FROZEN_SCIENCE_FILES = [
    "src/fedfalsify/scsv_v11.py",
    "src/fedfalsify/scsv_v11_study.py",
    "src/fedfalsify/scsv_v10_benchmarks.py",
    "src/fedfalsify/scsv_v12.py",
    "src/fedfalsify/scsv_v13.py",
    "src/fedfalsify/scope_contrast_v13.py",
    "src/fedfalsify/phase3d_fixtures.py",
    "src/fedfalsify/nested_tests.py",
    "src/fedfalsify/multiple_testing.py",
    "src/fedfalsify/sufficient_stats.py",
    "src/fedfalsify/linear_algebra.py",
]


def banner(title):
    print("\n" + "=" * 100, flush=True)
    print(title, flush=True)
    print("=" * 100, flush=True)


def run_live(cmd, *, cwd=None, env=None, label=None):
    if label:
        print(f"[RUN] {label}", flush=True)
    process = subprocess.Popen(
        [str(x) for x in cmd],
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    if process.stdout is not None:
        for line in process.stdout:
            print(line, end="", flush=True)
    rc = process.wait()
    if rc != 0:
        raise RuntimeError(f"Command failed ({rc}): " + " ".join(str(x) for x in cmd))
    return rc


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


banner("FedFalsify Phase-3E — v13 FRESH NOISY DEVELOPMENT")
print(f"[PINNED EXECUTION SOURCE] {PINNED_EXECUTION_SOURCE}", flush=True)
print(f"[FROZEN BASE SCIENCE] {FROZEN_BASE_HEAD}", flush=True)
print(f"[PROTOCOL SHA256] {EXPECTED_PROTOCOL_SHA256}", flush=True)
print("[BLOCKED] engineering seed 29300", flush=True)
print("[BLOCKED] spent Phase-3C seeds 29301-29310", flush=True)
print("[FRESH] Phase-3E seeds 29401-29410", flush=True)
print("[BLOCKED] final-confirmation seeds 11001-11999", flush=True)
print(f"[AUTHORIZATION] {AUTHORIZE_FRESH_DEVELOPMENT}", flush=True)

# STAGE 1 — Google Drive must be mounted before clone, tests, or science.
banner("[STAGE 1/8] Mount Google Drive FIRST")
drive.mount("/content/drive", force_remount=False)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
print(f"[PERSISTENCE] {OUTPUT_DIR}", flush=True)

# STAGE 2 — Fresh ephemeral checkout of exact verified execution source.
banner("[STAGE 2/8] Clone exact verified execution source")
if SOURCE_DIR.exists():
    shutil.rmtree(SOURCE_DIR)
run_live(["git", "clone", "--no-tags", REPO_URL, str(SOURCE_DIR)], label="clone repository")
run_live(
    ["git", "-C", str(SOURCE_DIR), "checkout", "--detach", PINNED_EXECUTION_SOURCE],
    label="checkout pinned Phase-3E runner",
)
actual_head = subprocess.check_output(
    ["git", "-C", str(SOURCE_DIR), "rev-parse", "HEAD"], text=True
).strip()
if actual_head != PINNED_EXECUTION_SOURCE:
    raise RuntimeError(f"Execution source mismatch: expected {PINNED_EXECUTION_SOURCE}, got {actual_head}")
if subprocess.check_output(
    ["git", "-C", str(SOURCE_DIR), "status", "--porcelain"], text=True
).strip():
    raise RuntimeError("Pinned checkout is not clean")
print(f"[SOURCE VERIFIED] {actual_head}", flush=True)

# STAGE 3 — Verify frozen science and protocol before installing/running anything scientific.
banner("[STAGE 3/8] Verify frozen v11/v12/v13 science + protocol")
run_live(
    ["git", "-C", str(SOURCE_DIR), "diff", "--exit-code", FROZEN_BASE_HEAD, "--", *FROZEN_SCIENCE_FILES],
    label="verify frozen scientific files unchanged",
)
protocol_path = SOURCE_DIR / "research" / PROTOCOL_NAME
if not protocol_path.is_file():
    raise RuntimeError(f"Frozen Phase-3E protocol missing: {protocol_path}")
actual_protocol_sha = sha256_file(protocol_path)
if actual_protocol_sha != EXPECTED_PROTOCOL_SHA256:
    raise RuntimeError(
        f"Frozen protocol SHA256 mismatch: expected {EXPECTED_PROTOCOL_SHA256}, got {actual_protocol_sha}"
    )

drive_protocol = OUTPUT_DIR / PROTOCOL_NAME
if drive_protocol.exists() and sha256_file(drive_protocol) != EXPECTED_PROTOCOL_SHA256:
    raise RuntimeError("Existing Drive protocol conflicts with frozen Phase-3E protocol")
if not drive_protocol.exists():
    temp_protocol = drive_protocol.with_name(drive_protocol.name + ".tmp")
    shutil.copyfile(protocol_path, temp_protocol)
    os.replace(temp_protocol, drive_protocol)
print(f"[PROTOCOL VERIFIED] {actual_protocol_sha}", flush=True)

# STAGE 4 — Isolated environment; ephemeral only. Drive results are never deleted.
banner("[STAGE 4/8] Create isolated Python environment")
if VENV_DIR.exists():
    shutil.rmtree(VENV_DIR)
venv_result = subprocess.run(
    [sys.executable, "-m", "venv", str(VENV_DIR)],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
if venv_result.returncode != 0:
    run_live([sys.executable, "-m", "pip", "install", "-q", "virtualenv"], label="install virtualenv fallback")
    run_live([sys.executable, "-m", "virtualenv", str(VENV_DIR)], label="create virtualenv fallback")
VENV_PY = VENV_DIR / "bin" / "python"
if not VENV_PY.exists():
    raise RuntimeError("Isolated Python environment was not created")
run_live([str(VENV_PY), "-m", "pip", "install", "-q", "--upgrade", "pip", "setuptools", "wheel"], label="prepare pip")
run_live([str(VENV_PY), "-m", "pip", "install", "-q", "-e", ".[dev,study]"], cwd=SOURCE_DIR, label="install exact pinned source")

# STAGE 5 — Complete test gate before any fresh scientific seed can execute.
banner("[STAGE 5/8] Run COMPLETE pinned-source test gate")
test_env = os.environ.copy()
test_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
test_env["PYTHONUNBUFFERED"] = "1"
started = time.time()
run_live(
    [str(VENV_PY), "-m", "pytest", "-q"],
    cwd=SOURCE_DIR,
    env=test_env,
    label="full repository pytest suite",
)
print(f"[TEST GATE] PASS in {time.time() - started:.1f}s", flush=True)

# Deliberately created only after the full test suite passes.
run_env = os.environ.copy()
run_env["PYTHONUNBUFFERED"] = "1"
run_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
run_env["FEDFALSIFY_PHASE3E_TEST_GATE"] = "PASS"
run_env["FEDFALSIFY_PHASE3E_OUTPUT_DIR"] = str(OUTPUT_DIR)

# STAGE 6 — Explicit user authorization. False means no 29401-29410 scientific execution.
banner("[STAGE 6/8] Authorization firewall")
print("[MATRIX] 120 conditions/seed × 10 seeds = 1200 matched conditions", flush=True)
print("[METHODS] v11-frozen + v12-frozen + scope-contrast-only + v13-full = 4800 rows", flush=True)
print("[FRESH BLOCK] 29401-29410", flush=True)
print("[SPENT/BLOCKED] 29300; 29301-29310; 11001-11999", flush=True)

if not AUTHORIZE_FRESH_DEVELOPMENT:
    banner("READY BUT NOT AUTHORIZED — NO PHASE-3E SCIENTIFIC SEED EXECUTED")
    print(
        "All source, protocol, frozen-science, installation, and test checks passed.\n"
        "Review the protocol. When you deliberately intend to spend the Phase-3E block, change ONLY:\n\n"
        "    AUTHORIZE_FRESH_DEVELOPMENT = True\n\n"
        "Then rerun this same cell. Do not change the architecture, thresholds, matrix, or seeds.",
        flush=True,
    )
else:
    # STAGE 7 — Run/resume governed study. Valid condition groups on Drive are skipped by the runner.
    banner("[STAGE 7/8] RUN / RESUME FROZEN Phase-3E 29401-29410 BLOCK")
    print("[SCIENTIFIC CONSEQUENCE] Phase-3E fresh block is now considered spent.", flush=True)
    runner_code = r'''from pathlib import Path
import os
from fedfalsify.phase3e_v13_development_runner import run_phase3e_development

result = run_phase3e_development(
    Path(os.environ["FEDFALSIFY_PHASE3E_OUTPUT_DIR"]),
    authorization_token="AUTHORIZE_PHASE3E_V13_FRESH_NOISY_DEVELOPMENT",
    live=True,
)
print("__PHASE3E_RESULT__")
print(result["decision"])
'''
    run_live(
        [str(VENV_PY), "-u", "-c", runner_code],
        cwd=SOURCE_DIR,
        env=run_env,
        label="execute/resume all governed Phase-3E conditions",
    )

    # STAGE 8 — Independent artifact checks/display.
    banner("[STAGE 8/8] Verify final handoff artifacts")
    decision_path = OUTPUT_DIR / "phase3e_v13_decision.json"
    report_path = OUTPUT_DIR / "phase3e_v13_report.txt"
    manifest_path = OUTPUT_DIR / "phase3e_v13_sha256.txt"
    zip_path = OUTPUT_DIR / ZIP_NAME
    for required in (decision_path, report_path, manifest_path, zip_path):
        if not required.is_file():
            raise RuntimeError(f"Expected final artifact missing: {required}")
    with zipfile.ZipFile(zip_path, "r") as archive:
        bad_member = archive.testzip()
    if bad_member is not None:
        raise RuntimeError(f"ZIP integrity failure at member: {bad_member}")
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    print("\n[DECISION]", flush=True)
    print(json.dumps(decision, indent=2, sort_keys=True), flush=True)
    print("\n[REPORT]", flush=True)
    print(report_path.read_text(encoding="utf-8"), flush=True)
    print("\n[SHA256 MANIFEST]", flush=True)
    print(manifest_path.read_text(encoding="utf-8"), flush=True)
    print(f"[ZIP] {zip_path}", flush=True)
    print(f"[ZIP SHA256] {sha256_file(zip_path)}", flush=True)
'''


def build_cell_source() -> str:
    return (
        _CELL_TEMPLATE
        .replace("__EXECUTION_SOURCE__", EXECUTION_SOURCE)
        .replace("__FROZEN_BASE_HEAD__", FROZEN_BASE_HEAD)
        .replace("__PROTOCOL_SHA256__", PROTOCOL_SHA256)
    )


def build() -> tuple[Path, Path]:
    protocol = Path("research/FROZEN_PHASE3E_V13_DEVELOPMENT_PROTOCOL.md")
    if not protocol.is_file():
        raise FileNotFoundError(protocol)
    actual_protocol_sha = hashlib.sha256(protocol.read_bytes()).hexdigest()
    if actual_protocol_sha != PROTOCOL_SHA256:
        raise RuntimeError(
            f"frozen Phase-3E protocol drifted: expected {PROTOCOL_SHA256}, got {actual_protocol_sha}"
        )
    for label, value, length in (
        ("execution source", EXECUTION_SOURCE, 40),
        ("base science", FROZEN_BASE_HEAD, 40),
        ("protocol", PROTOCOL_SHA256, 64),
    ):
        if len(value) != length or any(ch not in "0123456789abcdef" for ch in value):
            raise RuntimeError(f"invalid {label} identifier")

    source = build_cell_source()
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": source.splitlines(keepends=True),
            }
        ],
        "metadata": {
            "accelerator": "CPU",
            "colab": {"provenance": []},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK_PATH.write_text(
        json.dumps(notebook, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    PYTHON_PATH.write_text(source, encoding="utf-8")
    return NOTEBOOK_PATH, PYTHON_PATH


if __name__ == "__main__":
    for output in build():
        print(output)
