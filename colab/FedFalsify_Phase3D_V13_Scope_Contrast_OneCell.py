# FedFalsify Phase-3D / v13 SCSV-SCC — deterministic zero-new-seed fixture proof
# One cell only. Resume boundary: per-fixture × model × fold.
# Completed, hash-valid units on Google Drive are skipped automatically.

from google.colab import drive

drive.mount("/content/drive", force_remount=False)

from pathlib import Path
import os
import shutil
import subprocess
import sys

REPO_URL = 'https://github.com/AzizulHakim00/fedfalsify.git'
PHASE3D_EXECUTION_SOURCE = 'd0e2907b1a3fe2e02096ec65ce4883da03ae34f8'
FROZEN_PHASE3C_SCIENTIFIC_SOURCE = 'b67a07371bcf244728536028593373ca7d1990b1'
OUTPUT_ROOT = Path('/content/drive/MyDrive/FedFalsify_Q1/PHASE3D_V13_SCOPE_CONTRAST_FIXTURES')
CHECKOUT_ROOT = Path('/content/fedfalsify_phase3d_v13')
FROZEN_SCIENTIFIC_FILES = ('src/fedfalsify/scsv_v11.py', 'src/fedfalsify/scsv_v11_study.py', 'src/fedfalsify/scsv_v10_benchmarks.py', 'src/fedfalsify/scsv_v12.py', 'src/fedfalsify/shared_recertification.py', 'src/fedfalsify/role_localization_v12.py', 'src/fedfalsify/localized_certification.py', 'src/fedfalsify/nested_tests.py', 'src/fedfalsify/multiple_testing.py', 'src/fedfalsify/sufficient_stats.py', 'src/fedfalsify/linear_algebra.py', 'src/fedfalsify/legacy_v11_adapter.py')


def banner(text):
    print("\n" + "=" * 88)
    print(text)
    print("=" * 88, flush=True)


def run(cmd, *, cwd=None):
    print("[CMD] " + " ".join(map(str, cmd)), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=cwd, check=True)


banner("FedFalsify Phase-3D — v13 SCOPE-CONTRAST FIXTURE PROOF")
print(f"[DRIVE] mounted: /content/drive")
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
print(f"[OUTPUT] {OUTPUT_ROOT}")
print("[PERSISTENCE] atomic fixture × model × fold units; restart skips verified units")

# Use a clean ephemeral source tree each session; results remain on Drive.
if CHECKOUT_ROOT.exists():
    shutil.rmtree(CHECKOUT_ROOT)
run(["git", "clone", "--filter=blob:none", REPO_URL, str(CHECKOUT_ROOT)])
run(["git", "checkout", "--detach", PHASE3D_EXECUTION_SOURCE], cwd=CHECKOUT_ROOT)

head = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=CHECKOUT_ROOT, text=True
).strip()
if head != PHASE3D_EXECUTION_SOURCE:
    raise RuntimeError(f"Execution-source mismatch: expected {PHASE3D_EXECUTION_SOURCE}, got {head}")
print(f"[BASE SOURCE] verified: {head}")

# Frozen-science integrity gate (equivalent shell form: git diff --exit-code <frozen> -- <files>)
run(
    ["git", "diff", "--exit-code", FROZEN_PHASE3C_SCIENTIFIC_SOURCE, "--", *FROZEN_SCIENTIFIC_FILES],
    cwd=CHECKOUT_ROOT,
)
print(f"[FROZEN SCIENCE] verified against {FROZEN_PHASE3C_SCIENTIFIC_SOURCE}")

# Install the exact checked-out package and test dependencies.
run([sys.executable, "-m", "pip", "install", "-q", "-e", ".[dev,study]"], cwd=CHECKOUT_ROOT)

banner("VERIFICATION GATE")
run(
    [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests/test_phase3d_scope_contrast.py",
        "tests/test_phase3d_runner.py",
    ],
    cwd=CHECKOUT_ROOT,
)
# Full-suite verification is intentionally retained in the runnable notebook.
run([sys.executable, "-m", "pytest", "-q"], cwd=CHECKOUT_ROOT)
print("[TEST GATE] PASS")

# Import only after the exact source and tests are verified.
sys.path.insert(0, str(CHECKOUT_ROOT / "src"))
from fedfalsify.phase3d_runner import run_phase3d

banner("RUN / RESUME PHASE-3D")
summary = run_phase3d(
    output_dir=OUTPUT_ROOT,
    outer_folds=(0,),
    live=True,
)

banner("PHASE-3D COMPLETE")
print(f"[OUTPUT] {OUTPUT_ROOT}")
for key, value in sorted(summary.items()):
    print(f"[{key}] {value}")
