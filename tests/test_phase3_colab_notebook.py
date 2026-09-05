import json
from pathlib import Path
import re


NOTEBOOK = Path("colab/FedFalsify_Phase3_NCSC_OneCell.ipynb")
BUILDER = Path("tools/build_phase3_engineering_colab.py")
DRIVE_ROOT = "/content/drive/MyDrive/FedFalsify_Q1/SCSV_NCSC_PHASE3_ENGINEERING/"


def _single_code_source() -> str:
    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    code = [cell for cell in nb["cells"] if cell["cell_type"] == "code"]
    assert len(code) == 1
    source = code[0]["source"]
    return "".join(source) if isinstance(source, list) else str(source)


def test_phase3_colab_has_exactly_one_code_cell():
    source = _single_code_source()
    assert source.strip()


def test_phase3_colab_pins_source_protocol_drive_and_test_gate():
    source = _single_code_source()
    commit = re.search(r'PINNED_SOURCE_COMMIT\s*=\s*["\']([0-9a-f]{40})["\']', source)
    protocol = re.search(r'EXPECTED_PROTOCOL_SHA256\s*=\s*["\']([0-9a-f]{64})["\']', source)
    assert commit is not None
    assert protocol is not None
    assert DRIVE_ROOT in source
    assert "drive.mount('/content/drive')" in source
    assert source.index("drive.mount('/content/drive')") < source.index("pip", source.index("drive.mount('/content/drive')"))
    assert "FROZEN_PHASE3_ENGINEERING_PROTOCOL.md" in source
    assert "hashlib.sha256" in source
    assert "pytest" in source
    assert 'FEDFALSIFY_PHASE3_TEST_GATE' in source
    assert 'FEDFALSIFY_PINNED_SOURCE_COMMIT' in source
    assert "run_engineering" in source

    literal_spec = (
        "fedfalsify[dev,study] @ git+https://github.com/AzizulHakim00/"
        f"fedfalsify.git@{commit.group(1)}"
    )
    assert literal_spec in source
    assert f"/{commit.group(1)}/research/FROZEN_PHASE3_ENGINEERING_PROTOCOL.md" in source


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


def test_phase3_colab_builder_reads_head_and_protocol_sha():
    text = BUILDER.read_text(encoding="utf-8")
    assert 'subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()' in text
    assert 'Path("research/FROZEN_PHASE3_ENGINEERING_PROTOCOL.md").read_bytes()' in text
    assert "hashlib.sha256(protocol_bytes).hexdigest()" in text
