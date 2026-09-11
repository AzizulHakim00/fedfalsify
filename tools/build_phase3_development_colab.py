"""Build the fail-closed one-cell Colab wrapper for Phase-3C fresh development."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

NOTEBOOK_PATH = Path("colab/FedFalsify_Phase3_Fresh_Development_OneCell.ipynb")
FROZEN_DEVELOPMENT_HARNESS_SOURCE = "c82f33cc4052b2fa266e66f488df0310edbc5737"
FROZEN_SCIENTIFIC_SOURCE = "b67a07371bcf244728536028593373ca7d1990b1"
FROZEN_PROTOCOL_SHA256 = "de2543ba67f337b0386ccf3972862e95234d6dd84ce7f12ccf4ed1fdc2068477"
PHASE3A_SEAL = "78d0ab7ca7afb1edfa4725a45dfd20ce2db39659"

_CELL_TEMPLATE = r'''# ============================================================================================
# FedFalsify Phase-3C / SCSV-NCSC — FRESH DEVELOPMENT
# SELF-CONTAINED ONE-CELL COLAB WRAPPER
#
# IMPORTANT:
#   - This notebook does NOT reimplement the scientific algorithm.
#   - It clones the exact governed development harness, verifies the frozen
#     v11/v12 science and protocol, creates an isolated environment, and runs
#     the full test gate before ANY development seed can execute.
#   - It defaults to NOT AUTHORIZED. Keep the flag False while checking setup.
#   - Setting the flag True and running the cell starts/resumes the entire
#     29301-29310 block. The block is then scientifically SPENT.
#
# FROZEN:
#   development harness : __HARNESS_COMMIT__
#   scientific source   : __SCIENCE_COMMIT__
#   protocol SHA256     : __PROTOCOL_SHA__
#   engineering seed    : 29300 BLOCKED
#   development seeds   : 29301-29310 (single governed block)
#   final seeds         : 11001-11999 BLOCKED
# ============================================================================================

# --------------------------------------------------------------------------------------------
# USER CONTROL — LEAVE FALSE UNTIL YOU INTEND TO SPEND THE FRESH DEVELOPMENT BLOCK.
# --------------------------------------------------------------------------------------------
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
PINNED_HARNESS_COMMIT = "__HARNESS_COMMIT__"
PINNED_SCIENTIFIC_COMMIT = "__SCIENCE_COMMIT__"
EXPECTED_PROTOCOL_SHA256 = "__PROTOCOL_SHA__"
PHASE3A_SEAL = "__PHASE3A_SEAL__"

SOURCE_DIR = Path("/content/fedfalsify_phase3c_pinned")
VENV_DIR = Path("/content/fedfalsify_phase3c_cleanenv")
OUTPUT_DIR = Path("/content/drive/MyDrive/FedFalsify_Q1/SCSV_NCSC_PHASE3_DEVELOPMENT")
PROTOCOL_NAME = "FROZEN_PHASE3C_DEVELOPMENT_PROTOCOL.md"
ZIP_NAME = "FedFalsify_PHASE3C_FRESH_DEVELOPMENT_RESULTS.zip"
AUTH_TOKEN = "AUTHORIZE_PHASE3C_FRESH_DEVELOPMENT"


def banner(title):
    print("\n" + "=" * 96, flush=True)
    print(title, flush=True)
    print("=" * 96, flush=True)


def run_live(cmd, *, cwd=None, env=None, label=None):
    if label:
        print(f"[RUN] {label}", flush=True)
    proc = subprocess.Popen(
        [str(x) for x in cmd],
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    if proc.stdout is not None:
        for line in proc.stdout:
            print(line, end="", flush=True)
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(
            f"Command failed with exit code {rc}:\n" + " ".join(str(x) for x in cmd)
        )
    return rc


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


banner("FedFalsify Phase-3C — FRESH DEVELOPMENT ONE-CELL WRAPPER")
print(f"[HARNESS COMMIT] {PINNED_HARNESS_COMMIT}", flush=True)
print(f"[SCIENTIFIC SOURCE] {PINNED_SCIENTIFIC_COMMIT}", flush=True)
print(f"[PROTOCOL SHA256] {EXPECTED_PROTOCOL_SHA256}", flush=True)
print("[FIREWALL] 29300 BLOCKED", flush=True)
print("[FIREWALL] development block = 29301-29310", flush=True)
print("[FIREWALL] 11001-11999 BLOCKED", flush=True)
print(f"[AUTHORIZATION FLAG] {AUTHORIZE_FRESH_DEVELOPMENT}", flush=True)

# ============================================================================================
# STAGE 1/9 — GOOGLE DRIVE FIRST
# ============================================================================================
banner("[STAGE 1/9] Google Drive persistence — FIRST")
drive.mount("/content/drive", force_remount=False)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
print(f"[DRIVE] {OUTPUT_DIR}", flush=True)

# ============================================================================================
# STAGE 2/9 — CLONE EXACT GOVERNED HARNESS
# ============================================================================================
banner("[STAGE 2/9] Clone + checkout exact development harness")
if SOURCE_DIR.exists():
    shutil.rmtree(SOURCE_DIR)
run_live(["git", "clone", "--no-tags", REPO_URL, str(SOURCE_DIR)], label="clone repository")
run_live(
    ["git", "-C", str(SOURCE_DIR), "checkout", "--detach", PINNED_HARNESS_COMMIT],
    label="checkout frozen development harness",
)
actual_commit = subprocess.check_output(
    ["git", "-C", str(SOURCE_DIR), "rev-parse", "HEAD"], text=True
).strip()
if actual_commit != PINNED_HARNESS_COMMIT:
    raise RuntimeError(f"HARNESS SOURCE MISMATCH: expected {PINNED_HARNESS_COMMIT}, got {actual_commit}")
if subprocess.check_output(
    ["git", "-C", str(SOURCE_DIR), "status", "--porcelain"], text=True
).strip():
    raise RuntimeError("Pinned development harness checkout is not clean.")
print(f"[HARNESS] verified {actual_commit}", flush=True)

# ============================================================================================
# STAGE 3/9 — VERIFY PROTOCOL + FROZEN SCIENCE
# ============================================================================================
banner("[STAGE 3/9] Verify frozen protocol, comparator, and v12 scientific files")
protocol = SOURCE_DIR / "research" / PROTOCOL_NAME
if not protocol.exists():
    raise RuntimeError(f"Frozen protocol missing: {protocol}")
actual_protocol_sha = sha256_file(protocol)
if actual_protocol_sha != EXPECTED_PROTOCOL_SHA256:
    raise RuntimeError(
        "FROZEN PROTOCOL SHA256 MISMATCH\n"
        f"Expected: {EXPECTED_PROTOCOL_SHA256}\nActual:   {actual_protocol_sha}"
    )

# Preserve provenance on Drive. Never overwrite a conflicting existing protocol.
drive_protocol = OUTPUT_DIR / PROTOCOL_NAME
if drive_protocol.exists() and sha256_file(drive_protocol) != EXPECTED_PROTOCOL_SHA256:
    raise RuntimeError("Existing Drive protocol conflicts with the frozen Phase-3C protocol.")
if not drive_protocol.exists():
    tmp = drive_protocol.with_name(drive_protocol.name + ".tmp")
    shutil.copyfile(protocol, tmp)
    os.replace(tmp, drive_protocol)
print(f"[PROTOCOL] verified SHA256={actual_protocol_sha}", flush=True)

print("[VERIFY] git diff --exit-code frozen v11/V10 comparator files", flush=True)
run_live(
    [
        "git", "-C", str(SOURCE_DIR), "diff", "--exit-code", PHASE3A_SEAL, "--",
        "src/fedfalsify/scsv_v11.py",
        "src/fedfalsify/scsv_v11_study.py",
        "src/fedfalsify/scsv_v10_benchmarks.py",
    ],
    label="frozen comparator diff",
)

print("[VERIFY] git diff --exit-code frozen v12 scientific files", flush=True)
run_live(
    [
        "git", "-C", str(SOURCE_DIR), "diff", "--exit-code", PINNED_SCIENTIFIC_COMMIT, "--",
        "src/fedfalsify/scsv_v12.py",
        "src/fedfalsify/shared_recertification.py",
        "src/fedfalsify/role_localization_v12.py",
        "src/fedfalsify/localized_certification.py",
        "src/fedfalsify/nested_tests.py",
        "src/fedfalsify/multiple_testing.py",
        "src/fedfalsify/sufficient_stats.py",
        "src/fedfalsify/linear_algebra.py",
        "src/fedfalsify/legacy_v11_adapter.py",
    ],
    label="frozen Phase-3 science diff",
)

# Verify the runner literal points to the same frozen protocol and science.
runner_probe = subprocess.check_output(
    [
        sys.executable,
        "-c",
        (
            "from pathlib import Path;"
            "p=Path(r'" + str(SOURCE_DIR / "src/fedfalsify/phase3_development_runner.py") + "');"
            "t=p.read_text();"
            "assert '" + EXPECTED_PROTOCOL_SHA256 + "' in t;"
            "assert '" + PINNED_SCIENTIFIC_COMMIT + "' in t;"
            "print('runner pins verified')"
        ),
    ],
    text=True,
).strip()
print(f"[RUNNER] {runner_probe}", flush=True)

# ============================================================================================
# STAGE 4/9 — CLEAN ISOLATED ENVIRONMENT
# ============================================================================================
banner("[STAGE 4/9] Build clean isolated Python environment")
if VENV_DIR.exists():
    shutil.rmtree(VENV_DIR)
venv_create = subprocess.run(
    [sys.executable, "-m", "venv", str(VENV_DIR)],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
if venv_create.returncode != 0:
    run_live([sys.executable, "-m", "pip", "install", "-q", "virtualenv"], label="install virtualenv fallback")
    run_live([sys.executable, "-m", "virtualenv", str(VENV_DIR)], label="create isolated environment")
VENV_PY = VENV_DIR / "bin" / "python"
if not VENV_PY.exists():
    raise RuntimeError("Isolated Python environment was not created.")
print(f"[VENV] {VENV_PY}", flush=True)

# ============================================================================================
# STAGE 5/9 — PINNED DEPENDENCIES
# ============================================================================================
banner("[STAGE 5/9] Install pinned dependencies + exact source")
run_live(
    [str(VENV_PY), "-m", "pip", "install", "-q", "--upgrade", "pip", "setuptools", "wheel"],
    label="prepare pip/build tooling",
)
run_live(
    [
        str(VENV_PY), "-m", "pip", "install", "-q",
        "numpy==2.1.3", "scipy==1.16.3", "pandas==2.2.3",
        "joblib==1.5.3", "pytest==8.4.2",
    ],
    label="install pinned numerical/test dependencies",
)
run_live(
    [
        str(VENV_PY), "-m", "pip", "install", "-q", "--no-deps", "--no-build-isolation",
        "-e", str(SOURCE_DIR),
    ],
    label="install pinned fedfalsify source",
)
probe = subprocess.check_output(
    [
        str(VENV_PY), "-c",
        (
            "import sys,numpy,scipy,pandas,joblib,pytest;"
            "print(sys.version.split()[0], numpy.__version__, scipy.__version__, "
            "pandas.__version__, joblib.__version__, pytest.__version__)"
        ),
    ],
    text=True,
).strip()
print(f"[ENV] {probe}", flush=True)

# ============================================================================================
# STAGE 6/9 — COMPLETE TEST GATE BEFORE ANY DEVELOPMENT SEED
# ============================================================================================
banner("[STAGE 6/9] Complete pinned-source pytest gate")
test_env = os.environ.copy()
test_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
test_env["PYTHONUNBUFFERED"] = "1"
started = time.time()
try:
    run_live(
        [str(VENV_PY), "-m", "pytest", "-q"],
        cwd=SOURCE_DIR,
        env=test_env,
        label="run complete pinned-source pytest suite",
    )
except Exception:
    print("[TEST GATE] FAIL", flush=True)
    print("[FIREWALL] 29301-29310 HAVE NOT been authorized or executed.", flush=True)
    raise
print(f"[TEST GATE] PASS in {time.time() - started:.1f}s", flush=True)

# The test-gate variable is deliberately created only after the complete pytest pass.
run_env = os.environ.copy()
run_env["PYTHONUNBUFFERED"] = "1"
run_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
run_env["FEDFALSIFY_PHASE3_TEST_GATE"] = "PASS"
run_env["FEDFALSIFY_PHASE3C_HARNESS_COMMIT"] = PINNED_HARNESS_COMMIT

# ============================================================================================
# STAGE 7/9 — EXPLICIT AUTHORIZATION FIREWALL
# ============================================================================================
banner("[STAGE 7/9] Fresh-development authorization firewall")
print("[MATRIX] 120 conditions/seed × 10 seeds = 1200 conditions", flush=True)
print("[METHODS] 4 methods/condition = 4800 primary rows", flush=True)
print("[SEEDS] 29301-29310", flush=True)
print("[BLOCKED] 29300 BLOCKED; 11001-11999 BLOCKED", flush=True)
print(f"[OUTPUT] {OUTPUT_DIR}", flush=True)

if not AUTHORIZE_FRESH_DEVELOPMENT:
    banner("READY BUT NOT AUTHORIZED — NO FRESH DEVELOPMENT SEED EXECUTED")
    print(
        "All source/protocol/diff/test checks passed.\n"
        "To spend the fresh development block, change ONLY:\n\n"
        "    AUTHORIZE_FRESH_DEVELOPMENT = True\n\n"
        "then run this same cell again. Do not change thresholds, methods, seeds, or the matrix.",
        flush=True,
    )
else:
    # ========================================================================================
    # STAGE 8/9 — RUN / RESUME THE ENTIRE FROZEN DEVELOPMENT BLOCK
    # ========================================================================================
    banner("[STAGE 8/9] RUN / RESUME FROZEN 29301-29310 DEVELOPMENT BLOCK")
    print(
        "[SCIENTIFIC CONSEQUENCE] The entire 29301-29310 block is now considered spent.",
        flush=True,
    )

    runner_code = r"""from pathlib import Path
from fedfalsify.phase3_development_runner import AUTHORIZATION_TOKEN, run_development
import os

result = run_development(
    Path(os.environ["FEDFALSIFY_PHASE3C_OUTPUT_DIR"]),
    authorization_token=AUTHORIZATION_TOKEN,
    live=True,
)
print("__PHASE3C_RESULT__")
print(result["decision"])
print(result["zip_path"])
print(result["zip_sha256"])
"""
    run_env["FEDFALSIFY_PHASE3C_OUTPUT_DIR"] = str(OUTPUT_DIR)
    run_live(
        [str(VENV_PY), "-u", "-c", runner_code],
        cwd=SOURCE_DIR,
        env=run_env,
        label="execute/resume all 1200 governed development conditions",
    )

    # ========================================================================================
    # STAGE 9/9 — INDEPENDENT HANDOFF CHECKS AND FINAL DISPLAY
    # ========================================================================================
    banner("[STAGE 9/9] Final artifacts + handoff")
    zip_path = OUTPUT_DIR / ZIP_NAME
    if not zip_path.is_file():
        raise RuntimeError(f"Expected final ZIP is missing: {zip_path}")
    with zipfile.ZipFile(zip_path, "r") as archive:
        bad = archive.testzip()
    if bad is not None:
        raise RuntimeError(f"ZIP integrity failure at member: {bad}")

    decision_path = OUTPUT_DIR / "phase3_development_decision.json"
    integrity_path = OUTPUT_DIR / "phase3_development_integrity.json"
    report_path = OUTPUT_DIR / "phase3_development_report.txt"
    manifest_path = OUTPUT_DIR / "phase3_development_sha256.txt"

    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    print("\n[DECISION]", flush=True)
    print(json.dumps(decision, indent=2, sort_keys=True), flush=True)
    print("\n[INTEGRITY]", flush=True)
    print(json.dumps(integrity, indent=2, sort_keys=True), flush=True)
    print("\n[REPORT]", flush=True)
    print(report_path.read_text(encoding="utf-8"), flush=True)
    print("\n[SHA256 MANIFEST]", flush=True)
    print(manifest_path.read_text(encoding="utf-8"), flush=True)
    print(f"[ZIP] {zip_path}", flush=True)
    print(f"[ZIP SHA256] {sha256_file(zip_path)}", flush=True)
    print("[HANDOFF] Upload the final ZIP for independent byte-level audit.", flush=True)
'''


def render_cell() -> str:
    return (
        _CELL_TEMPLATE
        .replace("__HARNESS_COMMIT__", FROZEN_DEVELOPMENT_HARNESS_SOURCE)
        .replace("__SCIENCE_COMMIT__", FROZEN_SCIENTIFIC_SOURCE)
        .replace("__PROTOCOL_SHA__", FROZEN_PROTOCOL_SHA256)
        .replace("__PHASE3A_SEAL__", PHASE3A_SEAL)
    )


def build() -> Path:
    protocol = Path("research/FROZEN_PHASE3C_DEVELOPMENT_PROTOCOL.md")
    actual_protocol_sha = hashlib.sha256(protocol.read_bytes()).hexdigest()
    if actual_protocol_sha != FROZEN_PROTOCOL_SHA256:
        raise RuntimeError(
            "frozen Phase-3C protocol drifted: "
            f"expected {FROZEN_PROTOCOL_SHA256}, got {actual_protocol_sha}"
        )
    for name, value, length in (
        ("harness", FROZEN_DEVELOPMENT_HARNESS_SOURCE, 40),
        ("science", FROZEN_SCIENTIFIC_SOURCE, 40),
        ("protocol", FROZEN_PROTOCOL_SHA256, 64),
    ):
        if len(value) != length or any(ch not in "0123456789abcdef" for ch in value):
            raise RuntimeError(f"invalid frozen {name} identifier")

    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": render_cell().splitlines(keepends=True),
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
    return NOTEBOOK_PATH


if __name__ == "__main__":
    print(build())
