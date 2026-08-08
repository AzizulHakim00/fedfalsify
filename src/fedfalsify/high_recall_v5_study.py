"""Frozen 4,500-row development study for FedFalsify HR-VFS v5."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from statistics import mean, median
from typing import Sequence

from . import redesign_study as common
from . import role_conditional_study as v4study
from .benchmarks import BENCHMARKS, benchmark_catalog, generate_benchmark
from .high_recall_v5 import HighRecallOutput, high_recall_verified_forward_method

SMOKE_SEED = 17001
DEVELOPMENT_SEEDS = tuple(range(17101, 17106))
METHODS = (
    "legacy-certificate",
    "crossfit-v2-structural",
    "stability-superset-v3",
    "role-v4-no-backward",
    "hr-v5-full",
    "hr-v5-no-bundle-rescue",
    "hr-v5-no-score-proposer",
    "hr-v5-no-role-conditioning",
    "centralized-forward",
    "score-only-federated",
)
V5_METHODS = {
    "hr-v5-full",
    "hr-v5-no-bundle-rescue",
    "hr-v5-no-score-proposer",
    "hr-v5-no-role-conditioning",
}


@dataclass(frozen=True)
class V5StudyRow(common.RedesignRow):
    # Retain v4/stability comparator diagnostics rather than dropping them.
    candidate_pool_target_recall: float | None = None
    candidate_pool_contains_all_truth: float | None = None
    critical_term_recalled: float | None = None
    exception_candidate_recalled: float | None = None
    candidate_pool_size: int | None = None
    candidate_pool_nuisance_count: int | None = None
    forward_accepted_terms: int | None = None
    backward_deleted_terms: int | None = None
    # V5-specific proposal/transition diagnostics.
    candidate_bank_target_recall: float | None = None
    candidate_bank_contains_all_truth: float | None = None
    candidate_bank_size: int | None = None
    candidate_bank_nuisance_count: int | None = None
    single_terms_attempted: int | None = None
    single_terms_accepted: int | None = None
    pair_bundles_attempted: int | None = None
    pair_bundles_accepted: int | None = None
    single_exact_harms: int | None = None
    pair_exact_harms: int | None = None


def _validate_seeds(
    seeds: Sequence[int], *, allow_engineering_smoke: bool
) -> None:
    allowed = set(DEVELOPMENT_SEEDS)
    if allow_engineering_smoke:
        allowed.add(SMOKE_SEED)
    if any(seed not in allowed for seed in seeds):
        raise ValueError(
            "use untouched v5 development seeds 17101--17105; "
            "17001 is engineering smoke only"
        )
    spent = (
        set(range(9001, 9021))
        | set(range(10001, 10006))
        | set(range(10501, 10506))
        | set(range(11001, 17001))
        | set(range(17002, 17101))
    )
    if any(seed in spent for seed in seeds):
        raise ValueError("prior development, validation, or final seeds are prohibited")


def _row(
    base: common.RedesignRow,
    requested_noise: float,
    extras: dict[str, object] | None = None,
) -> V5StudyRow:
    payload = base.to_dict()
    payload["noise_ratio"] = float(requested_noise)
    payload.update(extras or {})
    return V5StudyRow(**payload)


def _transition_harms(decisions, truth: set[str]) -> int:
    harms = 0
    for decision in decisions:
        if not decision.accepted:
            continue
        before = set(decision.before_terms) - {"1"}
        after = set(decision.after_terms) - {"1"}
        harms += int(before == truth and after != truth)
    return harms


def _v5_extras(generated, output: HighRecallOutput) -> dict[str, object]:
    truth = set(generated.target_terms)
    bank = set(output.candidate_profile.candidate_terms)
    exception = "I(x3>1)*x3^2"
    return {
        "candidate_bank_target_recall": len(bank & truth) / len(truth) if truth else 1.0,
        "candidate_bank_contains_all_truth": float(truth.issubset(bank)),
        "exception_candidate_recalled": (
            float(exception in bank) if generated.scenario == "exception" else None
        ),
        "candidate_bank_size": len(bank),
        "candidate_bank_nuisance_count": len(bank - truth),
        "single_terms_attempted": len(output.forward_decisions),
        "single_terms_accepted": sum(item.accepted for item in output.forward_decisions),
        "pair_bundles_attempted": len(output.pair_decisions),
        "pair_bundles_accepted": sum(item.accepted for item in output.pair_decisions),
        "single_exact_harms": _transition_harms(output.forward_decisions, truth),
        "pair_exact_harms": _transition_harms(output.pair_decisions, truth),
    }


def _evaluate_v5(
    generated,
    output: HighRecallOutput,
    *,
    method: str,
    seed: int,
) -> common.RedesignRow:
    audit = {
        "bank": output.candidate_profile.to_dict(),
        "role_profile": output.role_profile.to_dict(),
        "single": [item.to_dict() for item in output.forward_decisions],
        "pairs": [item.to_dict() for item in output.pair_decisions],
        "probes": [item.to_dict() for item in output.probe_profiles],
    }
    return common._evaluate_candidate(
        generated,
        output.candidate,
        method=method,
        seed=seed,
        runtime_seconds=output.runtime_seconds,
        communication_bytes=output.communication_bytes,
        stop_reason=output.stop_reason
        + "; v5audit="
        + json.dumps(audit, sort_keys=True, separators=(",", ":")),
        fallback_selected=any(item.accepted for item in output.forward_decisions)
        or any(item.accepted for item in output.pair_decisions),
        selected_source=method,
        validation_mse=output.validation_profile.weighted_mse,
        worst_validation_mse=output.validation_profile.worst_client_mse,
    )


def _evaluate_condition(
    generated,
    *,
    requested_noise: float,
    seed: int,
    methods: Sequence[str],
    max_terms: int,
) -> list[V5StudyRow]:
    requested = set(methods)
    rows: list[V5StudyRow] = []

    comparator_methods = tuple(method for method in methods if method not in V5_METHODS)
    if comparator_methods:
        comparison_rows = v4study._evaluate_condition(
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
        ("hr-v5-full", True, True, True),
        ("hr-v5-no-bundle-rescue", False, True, True),
        ("hr-v5-no-score-proposer", True, False, True),
        ("hr-v5-no-role-conditioning", True, True, False),
    )
    for method, bundles, score, role in configs:
        if method not in requested:
            continue
        output = high_recall_verified_forward_method(
            generated.clients,
            catalog,
            seed=seed,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=0.05,
            use_bundle_rescue=bundles,
            use_score_proposer=score,
            role_conditioning=role,
        )
        rows.append(
            _row(
                _evaluate_v5(generated, output, method=method, seed=seed),
                requested_noise,
                _v5_extras(generated, output),
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
) -> list[V5StudyRow]:
    _validate_seeds(seeds, allow_engineering_smoke=allow_engineering_smoke)
    unknown = set(methods) - set(METHODS)
    if unknown:
        raise ValueError(f"unknown methods: {sorted(unknown)}")
    rows: list[V5StudyRow] = []
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


def summarize(rows: Sequence[V5StudyRow], *, evaluate_gate: bool = True) -> dict[str, object]:
    by_method: dict[str, list[V5StudyRow]] = {}
    for row in rows:
        by_method.setdefault(row.method, []).append(row)
    missing = set(METHODS) - set(by_method)
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
            "exception_recovered_all_conditions": _mean(selected, "exception_recovered"),
            "runtime_seconds_mean": _mean(selected, "runtime_seconds"),
            "runtime_seconds_median": _median(selected, "runtime_seconds"),
            "communication_bytes_mean": _mean(selected, "communication_bytes"),
            "communication_bytes_median": _median(selected, "communication_bytes"),
        }
        if method in V5_METHODS:
            methods[method].update(
                {
                    "candidate_bank_target_recall": _mean_optional(
                        selected, "candidate_bank_target_recall"
                    ),
                    "candidate_bank_contains_all_truth": _mean_optional(
                        selected, "candidate_bank_contains_all_truth"
                    ),
                    "candidate_bank_size_median": float(
                        median(
                            int(row.candidate_bank_size)
                            for row in selected
                            if row.candidate_bank_size is not None
                        )
                    ),
                    "single_terms_accepted": sum(
                        int(row.single_terms_accepted or 0) for row in selected
                    ),
                    "pair_bundles_accepted": sum(
                        int(row.pair_bundles_accepted or 0) for row in selected
                    ),
                    "single_exact_harms": sum(
                        int(row.single_exact_harms or 0) for row in selected
                    ),
                    "pair_exact_harms": sum(
                        int(row.pair_exact_harms or 0) for row in selected
                    ),
                }
            )

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
    result: dict[str, object] = {
        "schema_version": 1,
        "status": "hr-v5-development" if evaluate_gate else "hr-v5-engineering-smoke",
        "rows": len(rows),
        "conditions": len(condition_keys),
        "methods": methods,
        "seeds": sorted({row.seed for row in rows}),
    }

    if not evaluate_gate:
        result["development_gate"] = {
            "evaluated": False,
            "passed": None,
            "scientific_boundary": "Engineering smoke cannot evaluate the v5 development gate.",
        }
        return result

    full = by_method["hr-v5-full"]
    legacy = by_method["legacy-certificate"]

    def subset(selected, *, benchmark=None, noise=None, scenario=None):
        return [
            row
            for row in selected
            if (benchmark is None or row.benchmark == benchmark)
            and (noise is None or row.noise_ratio == noise)
            and (scenario is None or row.scenario == scenario)
        ]

    high_poly = subset(full, benchmark="poly3", noise=0.20)
    legacy_high_poly = subset(legacy, benchmark="poly3", noise=0.20)
    high_interaction = subset(full, benchmark="interaction", noise=0.20)
    legacy_high_interaction = subset(legacy, benchmark="interaction", noise=0.20)
    base = subset(full, benchmark="base")
    legacy_base = subset(legacy, benchmark="base")
    exceptions = subset(full, scenario="exception")

    legacy_spurious = _mean(legacy, "spurious_accepted")
    runtime_ratio = _median(full, "runtime_seconds") / max(
        _median(legacy, "runtime_seconds"), 1e-12
    )
    communication_ratio = _median(full, "communication_bytes") / max(
        _median(legacy, "communication_bytes"), 1.0
    )
    criteria = {
        "A_overall_exact_noninferiority": _mean(full, "exact_recovery")
        >= _mean(legacy, "exact_recovery") - 0.01,
        "B_high_noise_poly3_gain": _mean(high_poly, "exact_recovery")
        >= _mean(legacy_high_poly, "exact_recovery") + 0.05,
        "C_high_noise_interaction_gain": _mean(high_interaction, "exact_recovery")
        >= _mean(legacy_high_interaction, "exact_recovery") + 0.05,
        "D_base_exact_noninferiority": _mean(base, "exact_recovery")
        >= _mean(legacy_base, "exact_recovery") - 0.01,
        "E_high_noise_poly3_bank_recall": _mean_optional(
            high_poly, "candidate_bank_target_recall"
        )
        >= 0.95,
        "F_high_noise_poly3_complete_bank": _mean_optional(
            high_poly, "candidate_bank_contains_all_truth"
        )
        >= 0.90,
        "G_exception_candidate_recall": _mean_optional(
            exceptions, "exception_candidate_recalled"
        )
        >= 0.95,
        "H_conditional_exception_recovery": _mean(exceptions, "exception_recovered")
        >= 0.97,
        "I_spurious_acceptance_controlled": _mean(full, "spurious_accepted")
        <= max(0.05, legacy_spurious + 0.01),
        "J_zero_single_forward_exact_harms": sum(
            int(row.single_exact_harms or 0) for row in full
        )
        == 0,
        "K_zero_pair_rescue_exact_harms": sum(
            int(row.pair_exact_harms or 0) for row in full
        )
        == 0,
        "L_nmse_noninferiority": _mean(full, "test_nmse")
        <= 1.10 * _mean(legacy, "test_nmse"),
        "M_candidate_bank_compact": float(
            median(int(row.candidate_bank_size or 0) for row in full)
        )
        <= 10.0,
        "N_runtime_below_15x": runtime_ratio < 15.0,
        "O_communication_below_30x": communication_ratio < 30.0,
    }

    result["development_gate"] = {
        "evaluated": True,
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
        "runtime_median_ratio_vs_legacy": runtime_ratio,
        "communication_median_ratio_vs_legacy": communication_ratio,
        "scientific_boundary": (
            "Passing permits a separately frozen independent validation/scalability stage only; "
            "failure freezes v5 as NO-GO."
        ),
    }
    return result


def write_csv(rows: Sequence[V5StudyRow], output: Path) -> None:
    if not rows:
        raise ValueError("cannot write an empty v5 study")
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
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/high_recall_v5/rows.csv"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/high_recall_v5/summary.json"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = (
        {
            "benchmarks": ("poly3", "interaction"),
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
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    print(
        f"Wrote {len(rows)} rows; "
        f"gate_evaluated={summary['development_gate']['evaluated']}; "
        f"gate={summary['development_gate']['passed']}"
    )


if __name__ == "__main__":
    main()
