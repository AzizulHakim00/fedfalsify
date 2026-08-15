"""Apply Holm correction to a FedFalsify confirmatory JSON summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .statistics import holm_adjust


def add_holm_correction(summary: dict[str, Any]) -> dict[str, Any]:
    """Return a deep JSON-compatible copy with corrected McNemar p-values."""

    copied = json.loads(json.dumps(summary))
    paired = copied.get("paired", {})
    raw = {
        label: float(details["mcnemar"]["exact_p_value"])
        for label, details in paired.items()
        if "mcnemar" in details and "exact_p_value" in details["mcnemar"]
    }
    adjusted = holm_adjust(raw)
    for label, value in adjusted.items():
        paired[label]["mcnemar"]["holm_adjusted_p_value"] = value
    copied["multiple_testing"] = {
        "method": "Holm step-down",
        "family": "primary exact-recovery comparisons against the reference method",
        "comparisons": len(adjusted),
        "alpha": 0.05,
    }
    return copied


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Add Holm-adjusted exact McNemar p-values to a summary."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = json.loads(args.input.read_text(encoding="utf-8"))
    corrected = add_holm_correction(summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(corrected, indent=2), encoding="utf-8")
    print(json.dumps(corrected.get("multiple_testing", {}), indent=2))
    print(f"Wrote corrected report to {args.output}")


if __name__ == "__main__":
    main()
