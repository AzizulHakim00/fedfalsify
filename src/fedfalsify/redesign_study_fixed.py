"""Auditable wrapper for the frozen cross-fit redesign study."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Sequence

import numpy as np

from . import redesign_study as core


def _mean(rows: Sequence[core.RedesignRow], field: str) -> float:
    return float(mean(float(getattr(row, field)) for row in rows))


def summarize(rows: Sequence[core.RedesignRow]) -> dict[str, object]:
    by_method: dict[str, list[core.RedesignRow]] = {}
    for row in rows:
        by_method.setdefault(row.method, []).append(row)
    missing = set(core.METHODS) - set(by_method)
    if missing:
        raise ValueError(f"missing frozen redesign methods: {sorted(missing)}")

    methods: dict[str, object] = {}
    for method, selected in sorted(by_method.items()):
        validation_pairs = [
            (float(row.validation_mse), row.test_nmse)
            for row in selected
            if row.validation_mse is not None
        ]
        correlation: float | None = None
        if len(validation_pairs) >= 2:
            validation_values = np.asarray([pair[0] for pair in validation_pairs])
            test_values = np.asarray([pair[1] for pair in validation_pairs])
            value = float(np.corrcoef(validation_values, test_values)[0, 1])
            correlation = value if np.isfinite(value) else None
        methods[method] = {
            "runs": len(selected),
            "exact_recovery": _mean(selected, "exact_recovery"),
            "term_precision": _mean(selected, "term_precision"),
            "term_recall": _mean(selected, "term_recall"),
            "test_nmse": _mean(selected, "test_nmse"),
            "spurious_accepted": _mean(selected, "spurious_accepted"),
            "exception_recovered": _mean(selected, "exception_recovered"),
            "fallback_selected": _mean(selected, "fallback_selected"),
            "runtime_seconds": _mean(selected, "runtime_seconds"),
            "communication_bytes": _mean(selected, "communication_bytes"),
            "validation_test_correlation": correlation,
        }

    condition_keys = {
        (
            row.benchmark,
            row.scenario,
            row.noise_ratio,
            row.samples_per_client,
            row.num_clients,
            row.seed,
        )
        for row in rows
    }
    legacy = by_method["legacy-certificate"]
    proposed = by_method["crossfit-governed"]
    high_noise_legacy = [
        row
        for row in legacy
        if row.noise_ratio == 0.20 and row.benchmark in {"poly3", "interaction"}
    ]
    high_noise_proposed = [
        row
        for row in proposed
        if row.noise_ratio == 0.20 and row.benchmark in {"poly3", "interaction"}
    ]
    proposed_spurious = [row for row in proposed if row.scenario == "spurious"]
    proposed_complementary = [
        row for row in proposed if row.scenario == "complementary"
    ]
    gate_evaluated = bool(
        len(condition_keys) == 450
        and high_noise_legacy
        and high_noise_proposed
        and proposed_spurious
        and proposed_complementary
    )
    criterion_names = (
        "overall_exact_noninferiority",
        "mean_test_nmse_improves",
        "spurious_acceptance_controlled",
        "high_noise_poly_interaction_exact_gain",
        "fallback_not_disproportionate_on_spurious",
    )
    if gate_evaluated:
        criteria: dict[str, bool | None] = {
            "overall_exact_noninferiority": _mean(proposed, "exact_recovery")
            >= _mean(legacy, "exact_recovery") - 0.02,
            "mean_test_nmse_improves": _mean(proposed, "test_nmse")
            < _mean(legacy, "test_nmse"),
            "spurious_acceptance_controlled": _mean(proposed, "spurious_accepted")
            <= _mean(legacy, "spurious_accepted") + 0.01,
            "high_noise_poly_interaction_exact_gain": _mean(
                high_noise_proposed, "exact_recovery"
            )
            >= _mean(high_noise_legacy, "exact_recovery") + 0.05,
            "fallback_not_disproportionate_on_spurious": _mean(
                proposed_spurious, "fallback_selected"
            )
            <= _mean(proposed_complementary, "fallback_selected") + 0.10,
        }
        passed: bool | None = bool(all(value is True for value in criteria.values()))
    else:
        criteria = {name: None for name in criterion_names}
        passed = None

    return {
        "schema_version": 2,
        "status": "development-redesign",
        "rows": len(rows),
        "conditions": len(condition_keys),
        "methods": methods,
        "development_gate": {
            "evaluated": gate_evaluated,
            "criteria": criteria,
            "passed": passed,
            "high_noise_definition": "noise_ratio == 0.20 and benchmark in {poly3, interaction}",
            "fallback_selectivity_definition": "spurious fallback rate <= complementary fallback rate + 0.10",
            "scientific_boundary": "Passing permits later independent confirmation only; it is not confirmatory evidence.",
        },
    }


def main() -> None:
    args = core.build_parser().parse_args()
    if args.smoke:
        settings = {
            "benchmarks": ("base", "interaction"),
            "scenarios": ("complementary", "spurious"),
            "noise_ratios": (0.10,),
            "samples_per_client": (80,),
            "seeds": (13001,),
            "methods": core.METHODS,
            "max_terms": min(args.max_terms, 5),
        }
    else:
        settings = {
            "benchmarks": core._parse_strings(args.benchmarks),
            "scenarios": core._parse_strings(args.scenarios),
            "noise_ratios": core._parse_floats(args.noise),
            "samples_per_client": core._parse_ints(args.samples),
            "seeds": core._parse_ints(args.seeds),
            "methods": core._parse_strings(args.methods),
            "max_terms": args.max_terms,
        }
    rows = core.run_study(**settings)
    core.write_csv(rows, args.output)
    summary = summarize(rows)
    Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
    Path(args.summary).write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    print(
        f"Wrote {len(rows)} redesign rows; "
        f"development_gate={summary['development_gate']['passed']}"
    )


if __name__ == "__main__":
    main()
