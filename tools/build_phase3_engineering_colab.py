"""Build the one-cell Google Colab wrapper for the frozen Phase-3 engineering smoke."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

NOTEBOOK_PATH = Path("colab/FedFalsify_Phase3_NCSC_OneCell.ipynb")


def render_cell(source_commit: str, protocol_sha: str) -> str:
    template = '''import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from google.colab import drive

PINNED_SOURCE_COMMIT = "__SOURCE_COMMIT__"
EXPECTED_PROTOCOL_SHA256 = "__PROTOCOL_SHA__"
DRIVE_ROOT = "/content/drive/MyDrive/FedFalsify_Q1/SCSV_NCSC_PHASE3_ENGINEERING/"
PROTOCOL_URL = "https://raw.githubusercontent.com/AzizulHakim00/fedfalsify/__SOURCE_COMMIT__/research/FROZEN_PHASE3_ENGINEERING_PROTOCOL.md"
INSTALL_SPEC = "fedfalsify[dev,study] @ git+https://github.com/AzizulHakim00/fedfalsify.git@__SOURCE_COMMIT__"
SOURCE_DIR = Path("/content/fedfalsify_phase3_pinned")

print("=" * 88, flush=True)
print("FedFalsify Phase-3B / SCSV-NCSC ENGINEERING INTEGRATION", flush=True)
print("=" * 88, flush=True)

print("[STAGE 1/10] Google Drive persistence", flush=True)
drive.mount('/content/drive')
OUTPUT_DIR = Path(DRIVE_ROOT)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
print(f"[DRIVE] {OUTPUT_DIR}", flush=True)

print("[STAGE 0/10] Protocol + seed firewall", flush=True)
print(f"[PIN] source={PINNED_SOURCE_COMMIT}", flush=True)
print(f"[PIN] protocol_sha256={EXPECTED_PROTOCOL_SHA256}", flush=True)
print("[FIREWALL] engineering=29300 ONLY", flush=True)
print("[FIREWALL] 29301-29310 BLOCKED; 11001-11999 BLOCKED", flush=True)

protocol_path = OUTPUT_DIR / "FROZEN_PHASE3_ENGINEERING_PROTOCOL.md"
protocol_tmp = OUTPUT_DIR / "FROZEN_PHASE3_ENGINEERING_PROTOCOL.md.tmp"
urllib.request.urlretrieve(PROTOCOL_URL, protocol_tmp)
actual_protocol_sha = hashlib.sha256(protocol_tmp.read_bytes()).hexdigest()
if actual_protocol_sha != EXPECTED_PROTOCOL_SHA256:
    protocol_tmp.unlink(missing_ok=True)
    raise RuntimeError(
        f"protocol SHA256 mismatch: expected {EXPECTED_PROTOCOL_SHA256}, got {actual_protocol_sha}"
    )
os.replace(protocol_tmp, protocol_path)
print(f"[PROTOCOL] verified {protocol_path}", flush=True)

print("[STAGE 2/10] Exact source + dependency verification", flush=True)
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", INSTALL_SPEC],
    check=True,
)
if SOURCE_DIR.exists():
    shutil.rmtree(SOURCE_DIR)
subprocess.run(
    ["git", "clone", "-q", "https://github.com/AzizulHakim00/fedfalsify.git", str(SOURCE_DIR)],
    check=True,
)
subprocess.run(
    ["git", "-C", str(SOURCE_DIR), "checkout", "-q", "--detach", PINNED_SOURCE_COMMIT],
    check=True,
)
checked_out = subprocess.check_output(
    ["git", "-C", str(SOURCE_DIR), "rev-parse", "HEAD"], text=True
).strip()
if checked_out != PINNED_SOURCE_COMMIT:
    raise RuntimeError(f"source checkout mismatch: {checked_out}")
print(f"[SOURCE] verified {checked_out}", flush=True)

import joblib
import numpy as np
import pandas as pd
import scipy

print(
    "[ENV] "
    f"python={sys.version.split()[0]} "
    f"numpy={np.__version__} scipy={scipy.__version__} "
    f"pandas={pd.__version__} joblib={joblib.__version__} "
    f"platform={platform.platform()}",
    flush=True,
)

print("[STAGE 3/10] Scientific test gate", flush=True)
subprocess.run(
    [sys.executable, "-m", "pytest", "-q"],
    cwd=SOURCE_DIR,
    check=True,
)
os.environ["FEDFALSIFY_PHASE3_TEST_GATE"] = "PASS"
os.environ["FEDFALSIFY_PINNED_SOURCE_COMMIT"] = PINNED_SOURCE_COMMIT
print("[TEST GATE] full pinned repository suite PASS", flush=True)

from fedfalsify.phase3_engineering_runner import run_engineering

result = run_engineering(OUTPUT_DIR, seed=29300, live=True)

print("\\n" + "=" * 88, flush=True)
print("DESCRIPTIVE METHOD SUMMARY — ENGINEERING ONLY", flush=True)
print("=" * 88, flush=True)
print(result["method_summary"].to_string(index=False), flush=True)

print("\\n" + "=" * 88, flush=True)
print("DESCRIPTIVE ABLATION SUMMARY — NOT A SCIENTIFIC GO/NO-GO GATE", flush=True)
print("=" * 88, flush=True)
print(result["ablation_summary"].to_string(index=False), flush=True)

print("\\n" + "=" * 88, flush=True)
print("FINAL ENGINEERING ARTIFACTS", flush=True)
print("=" * 88, flush=True)
print(f"decision     : {result['decision']}", flush=True)
print(f"conditions   : {result['conditions_complete']}/6", flush=True)
print(f"primary rows : {result['primary_rows']}/24", flush=True)
print(f"manifest     : {result['manifest']}", flush=True)
print(f"ZIP          : {result['zip_path']}", flush=True)
print(f"ZIP SHA256   : {result['zip_sha256']}", flush=True)
print(f"Drive folder : {OUTPUT_DIR}", flush=True)

manifest_text = Path(result["manifest"]).read_text(encoding="utf-8")
print("\\nSHA256 MANIFEST", flush=True)
print(manifest_text, flush=True)
'''
    return template.replace("__SOURCE_COMMIT__", source_commit).replace(
        "__PROTOCOL_SHA__", protocol_sha
    )


def build_notebook() -> Path:
    source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    protocol_bytes = Path("research/FROZEN_PHASE3_ENGINEERING_PROTOCOL.md").read_bytes()
    protocol_sha = hashlib.sha256(protocol_bytes).hexdigest()
    if len(source_commit) != 40:
        raise RuntimeError("expected a 40-hex source commit")
    if len(protocol_sha) != 64:
        raise RuntimeError("expected a 64-hex protocol SHA256")

    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": render_cell(source_commit, protocol_sha),
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
