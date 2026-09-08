"""Build the sealed self-contained one-cell Colab wrapper for Phase-3 engineering."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

NOTEBOOK_PATH = Path("colab/FedFalsify_Phase3_NCSC_OneCell.ipynb")
FROZEN_SCIENTIFIC_SOURCE = "b67a07371bcf244728536028593373ca7d1990b1"
FROZEN_PROTOCOL_SHA256 = "afcbc20da959a34b4f4e052ea0270ca98a3724fe9c8ec76edb2cc4c39b716be9"

_CELL_TEMPLATE = r'''# ============================================================================================
# FedFalsify Phase-3B / SCSV-NCSC
# SELF-CONTAINED ONE-CELL COLAB ENGINEERING RUNNER
#
# Scientific source is NOT reimplemented in this notebook.
# This cell clones and verifies the exact frozen source commit, verifies the
# frozen Phase-3 engineering protocol, creates an isolated environment, runs
# the complete scientific test gate, and ONLY THEN authorizes seed 29300.
#
# FROZEN:
#   scientific commit : __SOURCE_COMMIT__
#   protocol SHA256   : __PROTOCOL_SHA__
#   engineering seed  : 29300 ONLY
#   development seeds : 29301-29310 BLOCKED
#   final seeds       : 11001-11999 BLOCKED
# ============================================================================================

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


# ============================================================================================
# FROZEN IDENTIFIERS
# ============================================================================================

REPO_URL = "https://github.com/AzizulHakim00/fedfalsify.git"

PINNED_SOURCE_COMMIT = "__SOURCE_COMMIT__"

EXPECTED_PROTOCOL_SHA256 = (
    "__PROTOCOL_SHA__"
)

ENGINEERING_SEED = 29300

SOURCE_DIR = Path("/content/fedfalsify_phase3_pinned")
VENV_DIR = Path("/content/fedfalsify_phase3_cleanenv")

OUTPUT_DIR = Path(
    "/content/drive/MyDrive/FedFalsify_Q1/SCSV_NCSC_PHASE3_ENGINEERING"
)

PROTOCOL_NAME = "FROZEN_PHASE3_ENGINEERING_PROTOCOL.md"
ZIP_NAME = "FedFalsify_PHASE3_NCSC_ENGINEERING_RESULTS.zip"

REQUIRED_ARTIFACTS = [
    PROTOCOL_NAME,
    "phase3_engineering_checkpoint.csv",
    "phase3_engineering_rows.csv",
    "phase3_engineering_method_summary.csv",
    "phase3_engineering_shared_diagnostics.csv",
    "phase3_engineering_localized_diagnostics.csv",
    "phase3_engineering_ablation_summary.csv",
    "phase3_engineering_integrity.json",
    "phase3_engineering_environment.json",
    "phase3_engineering_decision.json",
    "phase3_engineering_state.pkl",
    "phase3_engineering_state.joblib",
    "phase3_engineering_report.txt",
    "phase3_engineering_sha256.txt",
    ZIP_NAME,
]


# ============================================================================================
# HELPERS
# ============================================================================================

def banner(title):
    print("\n" + "=" * 92, flush=True)
    print(title, flush=True)
    print("=" * 92, flush=True)


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
            f"Command failed with exit code {rc}:\n"
            + " ".join(str(x) for x in cmd)
        )

    return rc


def sha256_file(path):
    path = Path(path)
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def print_csv_preview(path, title, max_rows=20):
    import pandas as pd

    path = Path(path)
    banner(title)

    if not path.exists():
        print(f"[MISSING] {path}", flush=True)
        return

    frame = pd.read_csv(path)

    if len(frame) <= max_rows:
        print(frame.to_string(index=False), flush=True)
    else:
        print(frame.head(max_rows).to_string(index=False), flush=True)
        print(f"\n[PREVIEW] showing first {max_rows}/{len(frame)} rows", flush=True)


# ============================================================================================
# START
# ============================================================================================

banner("FedFalsify Phase-3B / SCSV-NCSC — SELF-CONTAINED ONE-CELL COLAB RUN")

print("[FROZEN SCIENCE]", flush=True)
print(f"  source commit : {PINNED_SOURCE_COMMIT}", flush=True)
print(f"  protocol sha  : {EXPECTED_PROTOCOL_SHA256}", flush=True)
print(f"  engineering   : {ENGINEERING_SEED} ONLY", flush=True)
print("  blocked dev   : 29301-29310", flush=True)
print("  blocked final : 11001-11999", flush=True)


# ============================================================================================
# STAGE 1/10 — GOOGLE DRIVE
# ============================================================================================

banner("[STAGE 1/10] Google Drive persistence")

drive.mount("/content/drive", force_remount=False)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"[DRIVE] {OUTPUT_DIR}", flush=True)


# ============================================================================================
# STAGE 2/10 — FRESH PINNED SOURCE
# ============================================================================================

banner("[STAGE 2/10] Clone + verify exact frozen scientific source")

# /content is ephemeral. Recreate source on every fresh Colab runtime.
if SOURCE_DIR.exists():
    print(f"[SOURCE] removing stale ephemeral directory: {SOURCE_DIR}", flush=True)
    shutil.rmtree(SOURCE_DIR)

run_live(
    [
        "git",
        "clone",
        "--no-tags",
        REPO_URL,
        str(SOURCE_DIR),
    ],
    label="clone repository",
)

run_live(
    [
        "git",
        "-C",
        str(SOURCE_DIR),
        "checkout",
        "--detach",
        PINNED_SOURCE_COMMIT,
    ],
    label="checkout frozen scientific commit",
)

actual_commit = subprocess.check_output(
    ["git", "-C", str(SOURCE_DIR), "rev-parse", "HEAD"],
    text=True,
).strip()

if actual_commit != PINNED_SOURCE_COMMIT:
    raise RuntimeError(
        "SCIENTIFIC SOURCE MISMATCH\n"
        f"Expected: {PINNED_SOURCE_COMMIT}\n"
        f"Actual  : {actual_commit}"
    )

git_status = subprocess.check_output(
    ["git", "-C", str(SOURCE_DIR), "status", "--porcelain"],
    text=True,
).strip()

if git_status:
    raise RuntimeError(
        "Pinned source checkout is not clean before execution:\n" + git_status
    )

print(f"[SOURCE] verified exact commit {actual_commit}", flush=True)
print("[SOURCE] working tree clean", flush=True)


# ============================================================================================
# STAGE 3/10 — FROZEN PROTOCOL + SEED FIREWALL
# ============================================================================================

banner("[STAGE 3/10] Frozen protocol + seed firewall")

local_protocol = SOURCE_DIR / "research" / PROTOCOL_NAME

if not local_protocol.exists():
    raise RuntimeError(
        f"Frozen protocol missing from pinned source: {local_protocol}"
    )

local_protocol_sha = sha256_file(local_protocol)

if local_protocol_sha != EXPECTED_PROTOCOL_SHA256:
    raise RuntimeError(
        "LOCAL FROZEN PROTOCOL SHA256 MISMATCH\n"
        f"Expected: {EXPECTED_PROTOCOL_SHA256}\n"
        f"Actual  : {local_protocol_sha}"
    )

drive_protocol = OUTPUT_DIR / PROTOCOL_NAME

if drive_protocol.exists():
    drive_sha = sha256_file(drive_protocol)

    if drive_sha != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError(
            "EXISTING DRIVE PROTOCOL SHA256 MISMATCH\n"
            "Refusing to overwrite research provenance.\n"
            f"Expected: {EXPECTED_PROTOCOL_SHA256}\n"
            f"Actual  : {drive_sha}"
        )

    print("[PROTOCOL] existing Drive copy already verified", flush=True)

else:
    tmp_protocol = drive_protocol.with_name(drive_protocol.name + ".tmp")
    shutil.copyfile(local_protocol, tmp_protocol)
    os.replace(tmp_protocol, drive_protocol)
    print("[PROTOCOL] frozen verified copy written to Drive", flush=True)

final_drive_sha = sha256_file(drive_protocol)

if final_drive_sha != EXPECTED_PROTOCOL_SHA256:
    raise RuntimeError("Protocol verification changed during persistence.")

print(f"[PROTOCOL] verified {drive_protocol}", flush=True)
print(f"[PROTOCOL SHA256] {final_drive_sha}", flush=True)
print("[FIREWALL] engineering=29300 ONLY", flush=True)
print("[FIREWALL] 29301-29310 BLOCKED; 11001-11999 BLOCKED", flush=True)


# ============================================================================================
# STAGE 4/10 — CLEAN ISOLATED PYTHON ENVIRONMENT
# ============================================================================================

banner("[STAGE 4/10] Build clean isolated Python environment")

if VENV_DIR.exists():
    shutil.rmtree(VENV_DIR)

venv_create = subprocess.run(
    [sys.executable, "-m", "venv", str(VENV_DIR)],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

if venv_create.returncode != 0:
    print("[VENV] stdlib venv unavailable; using virtualenv fallback", flush=True)

    run_live(
        [sys.executable, "-m", "pip", "install", "-q", "virtualenv"],
        label="install virtualenv fallback",
    )

    run_live(
        [sys.executable, "-m", "virtualenv", str(VENV_DIR)],
        label="create isolated environment",
    )

VENV_PY = VENV_DIR / "bin" / "python"

if not VENV_PY.exists():
    raise RuntimeError("Isolated Python environment was not created.")

print(f"[VENV] {VENV_PY}", flush=True)


# ============================================================================================
# STAGE 5/10 — PINNED DEPENDENCIES
# ============================================================================================

banner("[STAGE 5/10] Install deterministic dependencies + pinned package")

run_live(
    [
        str(VENV_PY),
        "-m",
        "pip",
        "install",
        "-q",
        "--upgrade",
        "pip",
        "setuptools",
        "wheel",
    ],
    label="prepare pip/build tooling",
)

# These versions were reproduced successfully with the frozen source on Python 3.13.15.
run_live(
    [
        str(VENV_PY),
        "-m",
        "pip",
        "install",
        "-q",
        "numpy==2.1.3",
        "scipy==1.16.3",
        "pandas==2.2.3",
        "joblib==1.5.3",
        "pytest==8.4.2",
    ],
    label="install pinned numerical/test dependencies",
)

run_live(
    [
        str(VENV_PY),
        "-m",
        "pip",
        "install",
        "-q",
        "--no-deps",
        "--no-build-isolation",
        "-e",
        str(SOURCE_DIR),
    ],
    label="install exact local frozen fedfalsify source",
)

env_probe = subprocess.check_output(
    [
        str(VENV_PY),
        "-c",
        (
            "import sys,numpy,scipy,pandas,joblib,pytest;"
            "print(sys.version.split()[0]);"
            "print(numpy.__version__);"
            "print(scipy.__version__);"
            "print(pandas.__version__);"
            "print(joblib.__version__);"
            "print(pytest.__version__)"
        ),
    ],
    text=True,
).strip().splitlines()

if len(env_probe) != 6:
    raise RuntimeError("Could not verify isolated environment versions.")

print(
    "[ENV] "
    f"python={env_probe[0]} "
    f"numpy={env_probe[1]} "
    f"scipy={env_probe[2]} "
    f"pandas={env_probe[3]} "
    f"joblib={env_probe[4]} "
    f"pytest={env_probe[5]}",
    flush=True,
)


# ============================================================================================
# STAGE 6/10 — FULL SCIENTIFIC TEST GATE
# ============================================================================================

banner("[STAGE 6/10] Full pinned scientific test gate")

test_env = os.environ.copy()
test_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
test_env["PYTHONUNBUFFERED"] = "1"

test_start = time.time()

try:
    run_live(
        [
            str(VENV_PY),
            "-m",
            "pytest",
            "-q",
        ],
        cwd=SOURCE_DIR,
        env=test_env,
        label="run complete pinned-source pytest suite",
    )

except Exception:
    print("\n[TEST GATE] FAIL", flush=True)
    print(
        "[FIREWALL] Seed 29300 HAS NOT been authorized or executed.",
        flush=True,
    )
    raise

test_elapsed = time.time() - test_start

print(f"[TEST GATE] PASS in {test_elapsed:.1f}s", flush=True)
print("[AUTHORIZATION] 29300 may now run as engineering integration only", flush=True)


# ============================================================================================
# STAGE 7/10 — RUN / RESUME EXACT 29300 ENGINEERING SMOKE
# ============================================================================================

banner("[STAGE 7/10] Frozen 29300 engineering integration")

run_env = os.environ.copy()
run_env["PYTHONUNBUFFERED"] = "1"
run_env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
run_env["FEDFALSIFY_PHASE3_TEST_GATE"] = "PASS"
run_env["FEDFALSIFY_PINNED_SOURCE_COMMIT"] = PINNED_SOURCE_COMMIT

run_live(
    [
        str(VENV_PY),
        "-u",
        "-m",
        "fedfalsify.phase3_engineering_runner",
        "--output-dir",
        str(OUTPUT_DIR),
        "--seed",
        str(ENGINEERING_SEED),
    ],
    env=run_env,
    label="execute/resume six-condition engineering smoke",
)


# ============================================================================================
# STAGE 8/10 — INDEPENDENT ARTIFACT + ZIP VALIDATION
# ============================================================================================

banner("[STAGE 8/10] Independent artifact + ZIP validation")

missing = [
    name
    for name in REQUIRED_ARTIFACTS
    if not (OUTPUT_DIR / name).is_file()
]

if missing:
    raise RuntimeError(
        "Required engineering artifacts are missing:\n"
        + "\n".join(f" - {name}" for name in missing)
    )

print(
    f"[ARTIFACTS] {len(REQUIRED_ARTIFACTS)}/{len(REQUIRED_ARTIFACTS)} present",
    flush=True,
)

zip_path = OUTPUT_DIR / ZIP_NAME

with zipfile.ZipFile(zip_path, "r") as archive:
    bad_member = archive.testzip()

if bad_member is not None:
    raise RuntimeError(
        f"Final ZIP failed CRC/integrity validation at member: {bad_member}"
    )

print("[ZIP] CRC/integrity verification PASS", flush=True)

zip_sha256 = sha256_file(zip_path)
print(f"[ZIP SHA256] {zip_sha256}", flush=True)


# ============================================================================================
# STAGE 9/10 — DISPLAY RESULTS IN CELL
# ============================================================================================

banner("[STAGE 9/10] Organized in-cell engineering output")

decision_path = OUTPUT_DIR / "phase3_engineering_decision.json"
integrity_path = OUTPUT_DIR / "phase3_engineering_integrity.json"

decision = json.loads(decision_path.read_text(encoding="utf-8"))
integrity = json.loads(integrity_path.read_text(encoding="utf-8"))

print("\nENGINEERING DECISION (integrity-only)", flush=True)
print(json.dumps(decision, indent=2, sort_keys=True), flush=True)

print("\nENGINEERING INTEGRITY", flush=True)
print(json.dumps(integrity, indent=2, sort_keys=True), flush=True)

print_csv_preview(
    OUTPUT_DIR / "phase3_engineering_method_summary.csv",
    "DESCRIPTIVE METHOD SUMMARY — ENGINEERING ONLY",
    max_rows=20,
)

print_csv_preview(
    OUTPUT_DIR / "phase3_engineering_ablation_summary.csv",
    "DESCRIPTIVE ABLATION SUMMARY — NOT A DEVELOPMENT GO/NO-GO GATE",
    max_rows=20,
)

print_csv_preview(
    OUTPUT_DIR / "phase3_engineering_rows.csv",
    "PRIMARY 24 ENGINEERING ROWS",
    max_rows=24,
)


# ============================================================================================
# STAGE 10/10 — FINAL HANDOFF
# ============================================================================================

banner("[STAGE 10/10] COMPLETE")

manifest_path = OUTPUT_DIR / "phase3_engineering_sha256.txt"

print(f"[SOURCE COMMIT] {PINNED_SOURCE_COMMIT}", flush=True)
print(f"[PROTOCOL SHA256] {EXPECTED_PROTOCOL_SHA256}", flush=True)
print(f"[ENGINEERING SEED] {ENGINEERING_SEED}", flush=True)
print(f"[DRIVE FOLDER] {OUTPUT_DIR}", flush=True)
print(f"[MANIFEST] {manifest_path}", flush=True)
print(f"[ZIP] {zip_path}", flush=True)
print(f"[ZIP SHA256] {zip_sha256}", flush=True)

print("\nSHA256 MANIFEST", flush=True)
print("-" * 92, flush=True)
print(manifest_path.read_text(encoding="utf-8"), flush=True)

print(
    "\nNEXT HANDOFF:\n"
    "Upload this ZIP to ChatGPT:\n"
    f"{zip_path}\n\n"
    "Do not change thresholds, seeds, or scientific settings based on this "
    "engineering-only run.",
    flush=True,
)
'''


def render_cell(source_commit: str, protocol_sha: str) -> str:
    return (
        _CELL_TEMPLATE
        .replace("__SOURCE_COMMIT__", source_commit)
        .replace("__PROTOCOL_SHA__", protocol_sha)
    )


def build_notebook() -> Path:
    protocol_bytes = Path("research/FROZEN_PHASE3_ENGINEERING_PROTOCOL.md").read_bytes()
    protocol_sha = hashlib.sha256(protocol_bytes).hexdigest()
    if protocol_sha != FROZEN_PROTOCOL_SHA256:
        raise RuntimeError(
            "frozen Phase-3 engineering protocol drifted: "
            f"expected {FROZEN_PROTOCOL_SHA256}, got {protocol_sha}"
        )

    source_commit = FROZEN_SCIENTIFIC_SOURCE
    if len(source_commit) != 40 or any(ch not in "0123456789abcdef" for ch in source_commit):
        raise RuntimeError("expected a literal 40-hex frozen scientific-source commit")

    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": render_cell(source_commit, protocol_sha).splitlines(keepends=True),
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
    path = build_notebook()
    print(path)
