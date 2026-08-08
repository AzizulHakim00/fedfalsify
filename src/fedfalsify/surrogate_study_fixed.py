"""Stratum-safe, paired-audit wrapper for surrogate discrimination v2."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from . import surrogate_study as core
from .baselines import fit_federated
from .benchmarks import benchmark_catalog, generate_benchmark
from .client import FederatedFalsifierClient
from .crossfit_surrogate import structural_crossfit_method

INTERSECTION_METHOD = "crossfit-v2-intersection"
ALL_METHODS = core.METHODS + (INTERSECTION_METHOD,)


def _mean(rows, field: str) -> float:
    return float(mean(float(getattr(row, field)) for row in rows))


def _condition_key(row):
    return (
        row.benchmark,
        row.scenario,
        row.noise_ratio,
        row.samples_per_client,
        row.seed,
    )


def _intersection_rows(settings):
    rows = []
    for benchmark in settings["benchmarks"]:
        for scenario in settings["scenarios"]:
            for noise in settings["noise_ratios"]:
                for samples in settings["samples_per_client"]:
                    for seed in settings["seeds"]:
                        generated = generate_benchmark(
                            benchmark,
                            scenario=scenario,
                            samples_per_client=samples,
                            noise_ratio=noise,
                            seed=seed,
                            num_clients=4,
                        )
                        catalog = benchmark_catalog(scenario=scenario)
                        target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
                        structural = structural_crossfit_method(
                            generated.clients,
                            catalog,
                            seed=seed,
                            max_terms=settings["max_terms"],
                            target_mse=target_mse,
                            min_repair_score=0.05,
                        )
                        clients = [
                            FederatedFalsifierClient(item, catalog)
                            for item in generated.clients
                        ]
                        candidate, fit_bytes = fit_federated(
                            clients, structural.intersection_terms
                        )
                        evaluated = core.v1._evaluate_candidate(
                            generated,
                            candidate,
                            method=INTERSECTION_METHOD,
                            seed=seed,
                            runtime_seconds=structural.runtime_seconds,
                            communication_bytes=structural.communication_bytes + fit_bytes,
                            stop_reason="paired audit of v2 cross-fit intersection",
                            fallback_selected=False,
                            selected_source="crossfit-intersection",
                            validation_mse=None,
                            worst_validation_mse=None,
                        )
                        rows.append(
                            core.v1.RedesignRow(
                                **{
                                    **evaluated.to_dict(),
                                    "noise_ratio": float(noise),
                                }
                            )
                        )
    return rows


def summarize(rows):
    by_method = {}
    for row in rows:
        by_method.setdefault(row.method, []).append(row)
    missing = set(ALL_METHODS) - set(by_method)
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

    condition_keys = {_condition_key(row) for row in rows}
    benchmarks = {row.benchmark for row in rows}
    full_matrix = (
        benchmarks == set(core.BENCHMARKS)
        and len(condition_keys) == 450
        and len(rows) == 2700
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
    intersections = by_method[INTERSECTION_METHOD]
    intersection_by_key = {_condition_key(row): row for row in intersections}
    activated = [row for row in proposed if row.fallback_selected == 1.0]
    exact_gains = sum(
        row.exact_recovery > intersection_by_key[_condition_key(row)].exact_recovery
        for row in activated
    )
    exact_harms = sum(
        row.exact_recovery < intersection_by_key[_condition_key(row)].exact_recovery
        for row in activated
    )
    nmse_improvements = sum(
        row.test_nmse < intersection_by_key[_condition_key(row)].test_nmse
        for row in activated
    )
    nmse_harms = sum(
        row.test_nmse > intersection_by_key[_condition_key(row)].test_nmse
        for row in activated
    )
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
            "zero_observed_exact_harms_on_activation": exact_harms == 0,
            "runtime_below_15x": runtime_ratio < 15.0,
            "communication_below_30x": communication_ratio < 30.0,
        }
        passed = bool(all(criteria.values()))
    else:
        criteria = {name: None for name in criterion_names}
        passed = None

    return {
        "schema_version": 3,
        "status": "development-surrogate-discrimination-v2",
        "rows": len(rows),
        "conditions": len(condition_keys),
        "benchmarks": sorted(benchmarks),
        "methods": methods,
        "continuation_audit": {
            "activations": len(activated),
            "exact_gains": int(exact_gains),
            "exact_harms": int(exact_harms),
            "nmse_improvements": int(nmse_improvements),
            "nmse_harms": int(nmse_harms),
        },
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
    rows.extend(_intersection_rows(settings))
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
