import ast
import json
from pathlib import Path


def test_auto_colab_notebook_is_valid_and_compilable() -> None:
    path = Path("colab/FedFalsify_v06_Confirmatory_Colab_Auto.ipynb")
    notebook = json.loads(path.read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    assert len(notebook["cells"]) >= 8

    combined = []
    for cell in notebook["cells"]:
        source = "".join(cell.get("source", []))
        combined.append(source)
        if cell.get("cell_type") == "code":
            ast.parse(source)

    text = "\n".join(combined)
    assert 'MODE = "dry_run"' in text
    assert "run_all_and_merge" in text
    assert "fedfalsify-colab-audit" in text
    assert "GITHUB_TOKEN" in text
    assert "/content/drive/MyDrive/FedFalsify/results" in text
    assert "9001-9020" in text
    assert "2400" in text
    assert "VERIFIED.json" in text
