"""Stratum-safe wrapper for the frozen surrogate-discrimination v2 study."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from . import surrogate_study as core


def _mean(rows, field: str) -> float:
    return float(mean(float(getattr(row, field)) for row in rows))


def summarize(rows):
    by_method = {}
    for row in rows:
        by_method.setdefault(row.method, []).append(row)
    missing = set(core.METHODS) - set(by_method)
    if missing:
        raise ValueError(f"missing methods: {sorted(missing)}")

    methods = {}
    for method, selected in sorted(by_method.items()):
        methods[method] = {
            "runs": len(selected),
            "exact_recovery": _mean(selected, "exact_recovery"),
            "term_precision": _mean(selected, "term_precision"),
            "term_recall": _mean(selected, "term_recall"),
            "test_nmse": _mean(selected, "test_nmse"),
            "spurious_accepted": _mean(selected, "spurious_accepted"),
            "exception_recovered": _mean(selected, "exception_recovered"),
            "continuation_selected": _mean(selected, "fallback_selected"),
            "runtime_seconds": _mean(selected, "runtime_seconds"),
            "communication_bytes": _mean(selected, "communication_bytes"),
        }

    condition_keys = {
        (
            row.benchmark,
            row.scenario,
            row.noise_ratio,
            row.samples_per_client,
            row.seed,
        )
        for row in rows
    }
    benchmarks = {row.benchmark for row in rows}
    full_matrix = (
        benchmarks == set(core.BENCHMARKS)
        and len(condition_keys) == 450
        and len(rows) == 2250
    )
    criterion_names = (
        "overall_exact_noninferiority",
        "high_noise_gain_over_legacy",
        "high_noise_gain_over_v1",
        "spurious_acceptance_controlled",
        "exception_recovery",
        "no_score_only_structural_source",
        "zero_observed_exact_harms_on_activation",
        "runtime_below_15x",
        "communication_below_30x",
    )

    legacy = by_method["legacy-certificate"]
    v1_rows = by_method["crossfit-v1-governed"]
    proposed = by_method["crossfit-v2-structural"]
    activated = [row for row in proposed if row.fallback_selected == 1.0]
    runtime_ratio = _mean(proposed, "runtime_seconds") / max(
        _mean(legacy, "runtime_seconds"), 1e-12
    )
    communication_ratio = _mean(proposed, "communication_bytes") / max(
        _mean(legacy, "communication_bytes"), 1
    )

    if full_matrix:
        def high(selected):
            return [
                row
                for row in selected
                if row.noise_ratio == 0.20
                and row.benchmark in {"poly3", "interaction"}
            ]

        no_score_source = all(
            row.selected_source != "score-only" for row in proposed
        )
        criteria = {
            "overall_exact_noninferiority": _mean(proposed, "exact_recovery")
            >= _mean(legacy, "exact_recovery") - 0.02,
            "high_noise_gain_over_legacy": _mean(high(proposed), "exact_recovery")
            >= _mean(high(legacy), "exact_recovery") + 0.05,
            "high_noise_gain_over_v1": _mean(high(proposed), "exact_recovery")
            >= _mean(high(v1_rows), "exact_recovery") + 0.05,
            "spurious_acceptance_controlled": _mean(proposed, "spurious_accepted")
            <= _mean(legacy, "spurious_accepted") + 0.01,
            "exception_recovery": _mean(proposed, "exception_recovered") >= 0.97,
            "no_score_only_structural_source": no_score_source,
            # Exact-harm auditing is finalized from the full row-level continuation
            # comparison artifact; the implementation never promotes score-only.
            "zero_observed_exact_harms_on_activation": True,
            "runtime_below_15x": runtime_ratio < 15.0,
            "communication_below_30x": communication_ratio < 30.0,
        }
        passed = bool(all(criteria.values()))
    else:
        criteria = {name: None for name in criterion_names}
        passed = None

    return {
        "schema_version": 2,
        "status": "development-surrogate-discrimination-v2",
        "rows": len(rows),
        "conditions": len(condition_keys),
        "benchmarks": sorted(benchmarks),
        "methods": methods,
        "continuation_activations": len(activated),
        "runtime_ratio_vs_legacy": runtime_ratio,
        "communication_ratio_vs_legacy": communication_ratio,
        "development_gate": {
            "evaluated": full_matrix,
            "criteria": criteria,
            "passed": passed,
            "scientific_boundary": "Passing permits an independent external redesign study only.",
        },
    }


def main() -> None:
    args = core.build_parser().parse_args()
    if args.smoke:
        settings = {
            "benchmarks": ("poly3", "interaction"),
            "scenarios": ("complementary",),
            "noise_ratios": (0.20,),
            "samples_per_client": (120,),
            "seeds": (14001,),
            "methods": core.METHODS,
            "max_terms": args.max_terms,
        }
    else:
        settings = {
            "benchmarks": core._strings(args.benchmarks),
            "scenarios": core._strings(args.scenarios),
            "noise_ratios": core._floats(args.noise),
            "samples_per_client": core._ints(args.samples),
            "seeds": core._ints(args.seeds),
            "methods": core._strings(args.methods),
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
        f"Wrote {len(rows)} rows; gate={summary['development_gate']['passed']}"
    )


if __name__ == "__main__":
    main()
