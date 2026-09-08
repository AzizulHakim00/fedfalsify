import json
from pathlib import Path
import re


NOTEBOOK = Path("colab/FedFalsify_Phase3_NCSC_OneCell.ipynb")
BUILDER = Path("tools/build_phase3_engineering_colab.py")
DRIVE_ROOT = "/content/drive/MyDrive/FedFalsify_Q1/SCSV_NCSC_PHASE3_ENGINEERING"
FROZEN_SCIENTIFIC_SOURCE = "b67a07371bcf244728536028593373ca7d1990b1"
FROZEN_PROTOCOL_SHA256 = "afcbc20da959a34b4f4e052ea0270ca98a3724fe9c8ec76edb2cc4c39b716be9"


def _single_code_source() -> str:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code = [cell for cell in nb["cells"] if cell["cell_type"] == "code"]
    assert len(code) == 1
    source = code[0]["source"]
    return "".join(source) if isinstance(source, list) else str(source)


def test_phase3_colab_has_exactly_one_code_cell():
    source = _single_code_source()
    assert source.strip()


def test_phase3_colab_pins_exact_successful_scientific_source_and_protocol():
    source = _single_code_source()
    commit = re.search(r'PINNED_SOURCE_COMMIT\s*=\s*["\']([0-9a-f]{40})["\']', source)
    protocol = re.search(r'EXPECTED_PROTOCOL_SHA256\s*=\s*\(\s*["\']([0-9a-f]{64})["\']\s*\)', source, re.S)
    assert commit is not None
    assert protocol is not None
    assert commit.group(1) == FROZEN_SCIENTIFIC_SOURCE
    assert protocol.group(1) == FROZEN_PROTOCOL_SHA256
    assert DRIVE_ROOT in source
    assert "drive.mount(\"/content/drive\", force_remount=False)" in source
    assert "FROZEN_PHASE3_ENGINEERING_PROTOCOL.md" in source
    assert "hashlib.sha256" in source
    assert "ENGINEERING_SEED = 29300" in source
    assert "29301-29310" in source
    assert "11001-11999" in source


def test_phase3_colab_is_self_contained_for_fresh_colab_runtime():
    source = _single_code_source()
    assert 'REPO_URL = "https://github.com/AzizulHakim00/fedfalsify.git"' in source
    assert 'SOURCE_DIR = Path("/content/fedfalsify_phase3_pinned")' in source
    assert 'VENV_DIR = Path("/content/fedfalsify_phase3_cleanenv")' in source
    assert '"git",\n        "clone"' in source
    assert '"checkout",\n        "--detach",\n        PINNED_SOURCE_COMMIT' in source
    assert 'actual_commit != PINNED_SOURCE_COMMIT' in source
    assert 'git_status' in source
    assert 'PYTEST_DISABLE_PLUGIN_AUTOLOAD' in source
    assert 'numpy==2.1.3' in source
    assert 'scipy==1.16.3' in source
    assert 'pandas==2.2.3' in source
    assert 'joblib==1.5.3' in source
    assert 'pytest==8.4.2' in source
    assert '/mnt/data/' not in source


def test_phase3_colab_test_gate_precedes_engineering_seed_execution():
    source = _single_code_source()
    pytest_match = re.search(
        r'run_live\(\s*\[\s*str\(VENV_PY\)\s*,\s*["\']-m["\']\s*,\s*["\']pytest["\']\s*,\s*["\']-q["\']\s*\]',
        source,
        re.S,
    )
    assert pytest_match is not None
    pytest_pos = pytest_match.start()
    gate_pos = source.index('run_env["FEDFALSIFY_PHASE3_TEST_GATE"] = "PASS"')
    engineering_pos = source.index('"fedfalsify.phase3_engineering_runner"')
    assert pytest_pos < gate_pos < engineering_pos
    assert 'Seed 29300 HAS NOT been authorized or executed.' in source


def test_phase3_colab_persists_and_independently_verifies_artifacts():
    source = _single_code_source()
    for name in (
        "phase3_engineering_rows.csv",
        "phase3_engineering_method_summary.csv",
        "phase3_engineering_shared_diagnostics.csv",
        "phase3_engineering_localized_diagnostics.csv",
        "phase3_engineering_ablation_summary.csv",
        "phase3_engineering_integrity.json",
        "phase3_engineering_decision.json",
        "phase3_engineering_state.pkl",
        "phase3_engineering_state.joblib",
        "phase3_engineering_sha256.txt",
        "FedFalsify_PHASE3_NCSC_ENGINEERING_RESULTS.zip",
    ):
        assert name in source
    assert "archive.testzip()" in source
    assert "ZIP SHA256" in source


def test_phase3_colab_does_not_embed_scientific_algorithm_copies():
    source = _single_code_source()
    forbidden = (
        "def certify_shared_core(",
        "def discover_localized_role(",
        "def screen_on_selector(",
        "def certify_on_probe(",
        "def run_scsv_v12_branches(",
    )
    assert all(token not in source for token in forbidden)


def test_phase3_colab_builder_keeps_frozen_science_pin_after_wrapper_commits():
    text = BUILDER.read_text(encoding="utf-8")
    assert f'FROZEN_SCIENTIFIC_SOURCE = "{FROZEN_SCIENTIFIC_SOURCE}"' in text
    assert 'subprocess.check_output(["git", "rev-parse", "HEAD"]' not in text
    assert 'Path("research/FROZEN_PHASE3_ENGINEERING_PROTOCOL.md").read_bytes()' in text
    assert "hashlib.sha256(protocol_bytes).hexdigest()" in text
    assert "build_notebook" in text
