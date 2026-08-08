"""Frozen fresh-development study for FedFalsify SCSV-Cert v6."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from statistics import mean, median
from typing import Sequence

from . import redesign_study as common
from . import high_recall_v5_study as v5study
from .benchmarks import BENCHMARKS, benchmark_catalog, generate_benchmark
from .scsv_v6 import SCSVV6Output, scsv_cert_method

SMOKE_SEED = 19001
DEVELOPMENT_SEEDS = tuple(range(19101, 19106))
METHODS = (
    "legacy-certificate",
    "crossfit-v2-structural",
    "hr-v5-full",
    "scsv-v6-full",
    "scsv-v6-no-score-proposer",
    "centralized-forward",
    "score-only-federated",
)
V6_METHODS = {"scsv-v6-full", "scsv-v6-no-score-proposer"}


@dataclass(frozen=True)
class V6StudyRow(common.RedesignRow):
    candidate_bank_target_recall: float | None = None
    candidate_bank_contains_all_truth: float | None = None
    candidate_bank_size: int | None = None
    candidate_bank_nuisance_count: int | None = None
    probe_certified: float | None = None
    candidate_sets_evaluated: int | None = None
    necessity_failures: int | None = None
    swap_failures: int | None = None
    exception_eligible_diagnostics: int | None = None
    selector_structure: str = ""


def _validate_seeds(seeds: Sequence[int], *, allow_engineering_smoke: bool) -> None:
    allowed = set(DEVELOPMENT_SEEDS)
    if allow_engineering_smoke:
        allowed.add(SMOKE_SEED)
    if any(seed not in allowed for seed in seeds):
        raise ValueError(
            "use fresh SCSV-Cert v6 development seeds 19101--19105; "
            "19001 is engineering smoke only"
        )
    if not allow_engineering_smoke and SMOKE_SEED in set(seeds):
        raise ValueError("engineering smoke seed cannot enter v6 development evidence")


def _row(
    base: common.RedesignRow,
    requested_noise: float,
    extras: dict[str, object] | None = None,
) -> V6StudyRow:
    payload = base.to_dict()
    payload["noise_ratio"] = float(requested_noise)
    payload.update(extras or {})
    return V6StudyRow(**payload)


def _v6_extras(generated, output: SCSVV6Output) -> dict[str, object]:
    truth = set(generated.target_terms)
    bank = set(output.bank.candidate_terms)
    return {
        "candidate_bank_target_recall": len(bank & truth) / len(truth) if truth else 1.0,
        "candidate_bank_contains_all_truth": float(truth.issubset(bank)),
        "candidate_bank_size": len(bank),
        "candidate_bank_nuisance_count": len(bank - truth),
        "probe_certified": float(output.probe_certified),
        "candidate_sets_evaluated": output.candidate_sets_evaluated,
        "necessity_failures": sum(not item.necessity_passed for item in output.term_diagnostics),
        "swap_failures": sum(not item.swap_passed for item in output.term_diagnostics),
        "exception_eligible_diagnostics": sum(
            item.kind == "exception" and bool(item.eligible_clients)
            for item in output.term_diagnostics
        ),
        "selector_structure": ";".join(output.selector_structure),
    }


def _evaluate_v6(generated, output: SCSVV6Output, *, method: str, seed: int):
    return common._evaluate_candidate(
        generated,
        output.candidate,
        method=method,
        seed=seed,
        runtime_seconds=output.runtime_seconds,
        communication_bytes=output.communication_bytes,
        stop_reason=output.stop_reason,
        fallback_selected=False,
        selected_source="scsv-selector-set",
        validation_mse=output.selector_profile.weighted_mse,
        worst_validation_mse=output.selector_profile.worst_client_mse,
    )


def _evaluate_condition(
    generated,
    *,
    requested_noise: float,
    seed: int,
    methods: Sequence[str],
    max_terms: int,
) -> list[V6StudyRow]:
    requested = set(methods)
    rows: list[V6StudyRow] = []

    comparator_methods = tuple(method for method in methods if method not in V6_METHODS)
    if comparator_methods:
        comparison_rows = v5study._evaluate_condition(
            generated,
            requested_noise=requested_noise,
            seed=seed,
            methods=comparator_methods,
            max_terms=max_terms,
        )
        rows.extend(_row(item, requested_noise) for item in comparison_rows)

    catalog = benchmark_catalog(scenario=generated.scenario)
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    configs = (
        ("scsv-v6-full", True),
        ("scsv-v6-no-score-proposer", False),
    )
    for method, use_score in configs:
        if method not in requested:
            continue
        output = scsv_cert_method(
            generated.clients,
            catalog,
            seed=seed,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=0.05,
            use_score_proposer=use_score,
        )
        rows.append(
            _row(
                _evaluate_v6(generated, output, method=method, seed=seed),
                requested_noise,
                _v6_extras(generated, output),
            )
        )
    return rows


def run_study(
    *,
    benchmarks: Sequence[str] = tuple(BENCHMARKS),
    scenarios: Sequence[str] = ("complementary", "spurious", "exception"),
    noise_ratios: Sequence[float] = (0.03, 0.10, 0.20),
    samples_per_client: Sequence[int] = (120, 300),
    seeds: Sequence[int] = DEVELOPMENT_SEEDS,
    methods: Sequence[str] = METHODS,
    max_terms: int = 6,
    allow_engineering_smoke: bool = False,
) -> list[V6StudyRow]:
    _validate_seeds(seeds, allow_engineering_smoke=allow_engineering_smoke)
    unknown = set(methods) - set(METHODS)
    if unknown:
        raise ValueError(f"unknown methods: {sorted(unknown)}")
    rows: list[V6StudyRow] = []
    for benchmark in benchmarks:
        for scenario in scenarios:
            for noise in noise_ratios:
                for samples in samples_per_client:
                    for seed in seeds:
                        generated = generate_benchmark(
                            benchmark,
                            scenario=scenario,
                            samples_per_client=samples,
                            noise_ratio=noise,
                            seed=seed,
                            num_clients=4,
                        )
                        rows.extend(
                            _evaluate_condition(
                                generated,
                                requested_noise=noise,
                                seed=seed,
                                methods=methods,
                                max_terms=max_terms,
                            )
                        )
    return rows


def _mean(rows, field: str) -> float:
    return float(mean(float(getattr(row, field)) for row in rows))


def _median(rows, field: str) -> float:
    return float(median(float(getattr(row, field)) for row in rows))


def _mean_optional(rows, field: str) -> float:
    values = [getattr(row, field) for row in rows if getattr(row, field) is not None]
    if not values:
        raise ValueError(f"no values for {field}")
    return float(mean(float(value) for value in values))


def _subset(selected, *, benchmark=None, noise=None, scenario=None):
    return [
        row
        for row in selected
        if (benchmark is None or row.benchmark == benchmark)
        and (noise is None or row.noise_ratio == noise)
        and (scenario is None or row.scenario == scenario)
    ]


def summarize(rows: Sequence[V6StudyRow], *, evaluate_gate: bool = True) -> dict[str, object]:
    by_method: dict[str, list[V6StudyRow]] = {}
    for row in rows:
        by_method.setdefault(row.method, []).append(row)
    missing = set(METHODS) - set(by_method)
    if missing:
        raise ValueError(f"missing methods: {sorted(missing)}")

    methods: dict[str, object] = {}
    for method, selected in sorted(by_method.items()):
        entry = {
            "runs": len(selected),
            "exact_recovery": _mean(selected, "exact_recovery"),
            "term_precision": _mean(selected, "term_precision"),
            "term_recall": _mean(selected, "term_recall"),
            "test_nmse": _mean(selected, "test_nmse"),
            "spurious_accepted": _mean(selected, "spurious_accepted"),
            "exception_recovered_all_conditions": _mean(selected, "exception_recovered"),
            "runtime_seconds_median": _median(selected, "runtime_seconds"),
            "communication_bytes_median": _median(selected, "communication_bytes"),
        }
        if method in V6_METHODS:
            entry.update(
                {
                    "candidate_bank_target_recall": _mean_optional(selected, "candidate_bank_target_recall"),
                    "candidate_bank_contains_all_truth": _mean_optional(selected, "candidate_bank_contains_all_truth"),
                    "candidate_bank_size_median": float(
                        median(int(row.candidate_bank_size or 0) for row in selected)
                    ),
                    "probe_certification_fraction": _mean_optional(selected, "probe_certified"),
                    "candidate_sets_median": float(
                        median(int(row.candidate_sets_evaluated or 0) for row in selected)
                    ),
                    "necessity_failures": sum(int(row.necessity_failures or 0) for row in selected),
                    "swap_failures": sum(int(row.swap_failures or 0) for row in selected),
                }
            )
        methods[method] = entry

    condition_keys = {
        (row.benchmark, row.scenario, row.noise_ratio, row.samples_per_client, row.seed)
        for row in rows
    }
    result: dict[str, object] = {
        "schema_version": 1,
        "status": "scsv-v6-development" if evaluate_gate else "scsv-v6-engineering-smoke",
        "rows": len(rows),
        "conditions": len(condition_keys),
        "methods": methods,
        "seeds": sorted({row.seed for row in rows}),
    }

    if not evaluate_gate:
        result["development_gate"] = {
            "evaluated": False,
            "passed": None,
            "scientific_boundary": "Engineering smoke cannot evaluate the v6 development gate.",
        }
        return result

    full = by_method["scsv-v6-full"]
    legacy = by_method["legacy-certificate"]
    v5 = by_method["hr-v5-full"]

    full_high_poly = _subset(full, benchmark="poly3", noise=0.20)
    v5_high_poly = _subset(v5, benchmark="poly3", noise=0.20)
    full_high_interaction = _subset(full, benchmark="interaction", noise=0.20)
    legacy_high_interaction = _subset(legacy, benchmark="interaction", noise=0.20)
    full_base = _subset(full, benchmark="base")
    legacy_base = _subset(legacy, benchmark="base")
    full_nested = _subset(full, benchmark="nested_sine")
    v5_nested = _subset(v5, benchmark="nested_sine")
    full_trig = _subset(full, benchmark="trig_product")
    v5_trig = _subset(v5, benchmark="trig_product")
    full_exceptions = _subset(full, scenario="exception")

    criteria = {
        "A_overall_exact_gt_legacy_005": _mean(full, "exact_recovery") >= _mean(legacy, "exact_recovery") + 0.05,
        "B_overall_exact_gt_v5_010": _mean(full, "exact_recovery") >= _mean(v5, "exact_recovery") + 0.10,
        "C_high_noise_poly3_gt_v5_010": _mean(full_high_poly, "exact_recovery") >= _mean(v5_high_poly, "exact_recovery") + 0.10,
        "D_high_noise_interaction_noninferior_legacy": _mean(full_high_interaction, "exact_recovery") >= _mean(legacy_high_interaction, "exact_recovery") - 0.01,
        "E_base_noninferior_legacy": _mean(full_base, "exact_recovery") >= _mean(legacy_base, "exact_recovery") - 0.01,
        "F_nested_sine_preserved_v5": _mean(full_nested, "exact_recovery") >= _mean(v5_nested, "exact_recovery") - 0.02,
        "G_trig_product_preserved_v5": _mean(full_trig, "exact_recovery") >= _mean(v5_trig, "exact_recovery") - 0.02,
        "H_precision_ge_096": _mean(full, "term_precision") >= 0.96,
        "I_recall_ge_095": _mean(full, "term_recall") >= 0.95,
        "J_spurious_acceptance_controlled": _mean(full, "spurious_accepted") <= max(0.05, _mean(legacy, "spurious_accepted") + 0.01),
        "K_exception_recovery_ge_095": _mean(full_exceptions, "exception_recovered") >= 0.95,
        "L_bank_target_recall_ge_098": _mean_optional(full, "candidate_bank_target_recall") >= 0.98,
        "M_complete_bank_ge_095": _mean_optional(full, "candidate_bank_contains_all_truth") >= 0.95,
        "N_nmse_not_worse_than_legacy": _mean(full, "test_nmse") <= _mean(legacy, "test_nmse"),
        "O_probe_certification_ge_075": _mean_optional(full, "probe_certified") >= 0.75,
        "P_communication_not_worse_than_v5": _median(full, "communication_bytes") <= _median(v5, "communication_bytes"),
        "Q_runtime_le_150pct_v5": _median(full, "runtime_seconds") <= 1.50 * _median(v5, "runtime_seconds"),
    }

    result["development_gate"] = {
        "evaluated": True,
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
        "scientific_boundary": (
            "Passing permits only a separately frozen independent scalability/external-validation stage; "
            "failure freezes v6 as NO-GO."
        ),
    }
    return result


def write_csv(rows: Sequence[V6StudyRow], output: Path) -> None:
    if not rows:
        raise ValueError("cannot write an empty v6 study")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def _strings(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmarks", default=",".join(BENCHMARKS))
    parser.add_argument("--scenarios", default="complementary,spurious,exception")
    parser.add_argument("--noise", default="0.03,0.10,0.20")
    parser.add_argument("--samples", default="120,300")
    parser.add_argument("--seeds", default=",".join(map(str, DEVELOPMENT_SEEDS)))
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--max-terms", type=int, default=6)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("results/scsv_v6/rows.csv"))
    parser.add_argument("--summary", type=Path, default=Path("results/scsv_v6/summary.json"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = (
        {
            "benchmarks": ("base", "poly3"),
            "scenarios": ("complementary", "exception"),
            "noise_ratios": (0.20,),
            "samples_per_client": (120,),
            "seeds": (SMOKE_SEED,),
            "methods": METHODS,
            "max_terms": args.max_terms,
            "allow_engineering_smoke": True,
        }
        if args.smoke
        else {
            "benchmarks": _strings(args.benchmarks),
            "scenarios": _strings(args.scenarios),
            "noise_ratios": tuple(float(item) for item in _strings(args.noise)),
            "samples_per_client": tuple(int(item) for item in _strings(args.samples)),
            "seeds": tuple(int(item) for item in _strings(args.seeds)),
            "methods": _strings(args.methods),
            "max_terms": args.max_terms,
            "allow_engineering_smoke": False,
        }
    )
    rows = run_study(**settings)
    write_csv(rows, args.output)
    summary = summarize(rows, evaluate_gate=not args.smoke)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    print(
        f"Wrote {len(rows)} rows; "
        f"gate_evaluated={summary['development_gate']['evaluated']}; "
        f"gate={summary['development_gate']['passed']}"
    )


if __name__ == "__main__":
    main()