import json
from pathlib import Path
import subprocess
import sys


def test_phase3a_parity_audit_is_engineering_only_and_passes_six_smoke_conditions(tmp_path):
    output = tmp_path / "phase3a_parity.json"
    completed = subprocess.run(
        [sys.executable, "studies/phase3a_parity.py", "--output", str(output)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(Path(output).read_text(encoding="utf-8"))
    assert payload["seed"] == 29001
    assert payload["conditions"] == 6
    assert payload["passed"] is True
    assert len(payload["records"]) == 6
    assert all(record["seed"] == 29001 for record in payload["records"])
    assert all(record["packet_equivalent"] for record in payload["records"])
    assert all(record["aggregate_equivalent"] for record in payload["records"])
    assert all(record["least_squares_equivalent"] for record in payload["records"])
