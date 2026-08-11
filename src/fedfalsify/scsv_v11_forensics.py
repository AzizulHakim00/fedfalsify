"""Post-hoc spent-v10 failure taxonomy for motivating SCSV-ELRC v11.

This module only reads sealed v10 rows. It never regenerates data, reruns v10,
or converts spent evidence into v11 validation.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
import json
from pathlib import Path
from typing import Iterable

from .scsv_v10_benchmarks import TRUE_DEVIATIONS_V10

SPENT_V10_SEEDS = {28101, 28102, 28103, 28104, 28105}
V10_METHOD = "scsv-aqcc-v10-full"

REASON_MAP = {
    "ROLE-NOT-IDENTIFIED": "OCCUPANCY-ROLE-FAILURE",
    "SOURCE-NOT-QUALIFIED": "SOURCE-QUALIFICATION-FAILURE",
    "PAIR-INVARIANT-FAIL": "PAIR-INVARIANT-FAILURE",
    "OUTSIDE-INVARIANT-FAIL": "OUTSIDE-NONDEGRADATION-FAILURE",
    "HELDOUT-SPLIT-CONTRADICTION": "HELDOUT-SPLIT-FAILURE",
    "POOLED-NOT-SUPPORTED": "POOLED-EVIDENCE-FAILURE",
    "CLIENT-MEDIAN-CONTRADICTED": "CLIENT-CONSENSUS-FAILURE",
    "EVIDENCE-NOT-SUPPORTED": "OTHER-EVIDENCE-FAILURE",
}


def _terms(value: str) -> set[str]:
    return {item for item in (value or "").split(";") if item}


def _diagnostics(value: str) -> dict[str, dict]:
    if not value:
        return {}
    payload = json.loads(value)
    return {str(item["term"]): item for item in payload}


def classify_true_deviation(row: dict[str, str], term: str) -> str:
    accepted = _terms(row.get("accepted_deviations", ""))
    if term in accepted:
        return "RECOVERED"
    candidates = _terms(row.get("candidate_deviations", ""))
    if term not in candidates:
        return "PROPOSAL-FAILURE"
    item = _diagnostics(row.get("diagnostics_json", "")).get(term)
    if item is None:
        return "DIAGNOSTIC-MISSING"
    reason = str(item.get("rejection_reason", "UNKNOWN"))
    return REASON_MAP.get(reason, f"OTHER:{reason}")


def audit_rows(rows: Iterable[dict[str, str]]) -> dict:
    counts: Counter[str] = Counter()
    family_counts: dict[str, Counter[str]] = {}
    evaluated = 0
    recovered = 0
    for row in rows:
        if row.get("method") != V10_METHOD:
            continue
        seed = int(row["seed"])
        if seed not in SPENT_V10_SEEDS:
            raise ValueError(f"forensic input contains non-spent v10 seed {seed}")
        family = row["family"]
        true_terms = tuple(term for term, _ in TRUE_DEVIATIONS_V10[family])
        for term in true_terms:
            label = classify_true_deviation(row, term)
            counts[label] += 1
            family_counts.setdefault(family, Counter())[label] += 1
            evaluated += 1
            recovered += int(label == "RECOVERED")

    return {
        "schema_version": 1,
        "status": "SPENT-V10-POST-HOC-MECHANISM-DIAGNOSTIC",
        "scientific_boundary": (
            "This taxonomy is descriptive post-hoc evidence from permanently spent "
            "28101--28105. It is not v11 development, validation, or confirmation."
        ),
        "true_deviations_evaluated": evaluated,
        "recovered": recovered,
        "missed": evaluated - recovered,
        "counts": dict(sorted(counts.items())),
        "family_counts": {
            family: dict(sorted(counter.items()))
            for family, counter in sorted(family_counts.items())
        },
    }


def audit_file(rows_csv: Path) -> dict:
    with rows_csv.open(newline="", encoding="utf-8") as handle:
        return audit_rows(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rows",
        type=Path,
        default=Path("results/scsv_v10/rows.csv"),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_file(args.rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
