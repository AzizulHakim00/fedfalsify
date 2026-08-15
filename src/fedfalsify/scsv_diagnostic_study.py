"""Spent-seed exploratory study for Set-Conditional Structural Verification."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from statistics import mean, median
from typing import Sequence

from . import redesign_study as common
from .benchmarks import BENCHMARKS, benchmark_catalog, generate_benchmark
from .scsv_diagnostic import SCSVOutput, scsv_diagnostic_method

SMOKE_SEED = 18001
SPENT_DIAGNOSTIC_SEEDS = tuple(range(17101, 17106))
METHODS = ("scsv-selector", "scsv-validated")


@dataclass(frozen=True)
class SCSVStudyRow(common.RedesignRow):
    bank_target_recall: float | None = None
    bank_contains_all_truth: float | None = None
    bank_size: int | None = None
    bank_nuisance_count: int | None = None
    selector_structure: str = ""
    validated_structure: str = ""
    probe_passed: float | None = None
    candidate_sets_evaluated: int | None = None
    necessity_failures: int | None = None
    swap_failures: int | None = None
    exception_eligible_diagnostics: int | None = None


def _validate_seeds(seeds: Sequence[int], *, allow_engineering_smoke: bool) -> None:
    allowed = set(SPENT_DIAGNOSTIC_SEEDS)
    if allow_engineering_smoke:
        allowed.add(SMOKE_SEED)
    if any(seed not in allowed for seed in seeds):
        raise ValueError(
            "SCSV is exploratory only: use spent v5 seeds 17101--17105 "
            "or engineering smoke seed 18001"
        )
    if not allow_engineering_smoke and SMOKE_SEED in set(seeds):
        raise ValueError("engineering smoke seed cannot enter spent-seed diagnostic")


def _row(
    base: common.RedesignRow,
    *,
    requested_noise: float,
    output: SCSVOutput,
    generated,
) -> SCSVStudyRow:
    truth = set(generated.target_terms)
    bank = set(output.bank.candidate_terms)
    exception_diags = sum(
        item.kind == "exception" and bool(item.eligible_clients)
        for item in output.term_diagnostics
    )
    payload = base.to_dict()
    payload["noise_ratio"] = float(requested_noise)
    payload.update(
        {
            "bank_target_recall": len(bank & truth) / len(truth) if truth else 1.0,
            "bank_contains_all_truth": float(truth.issubset(bank)),
            "bank_size": len(bank),
            "bank_nuisance_count": len(bank - truth),
            "selector_structure": ";".join(output.selector_structure),
            "validated_structure": ";".join(output.validated_structure),
            "probe_passed": float(output.probe_passed),
            "candidate_sets_evaluated": output.candidate_sets_evaluated,
            "necessity_failures": sum(
                not item.necessity_passed for item in output.term_diagnostics
            ),
            "swap_failures": sum(
                not item.swap_passed for item in output.term_diagnostics
            ),
            "exception_eligible_diagnostics": int(exception_diags),
        }
    )
    return SCSVStudyRow(**payload)


def _evaluate_condition(
    generated,
    *,
    requested_noise: float,
    seed: int,
    max_terms: int,
) -> list[SCSVStudyRow]:
    catalog = benchmark_catalog(scenario=generated.scenario)
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    output = scsv_diagnostic_method(
        generated.clients,
        catalog,
        seed=seed,
        max_terms=max_terms,
        target_mse=target_mse,
        min_repair_score=0.05,
    )
    diagnostics = json.dumps(
        [item.to_dict() for item in output.term_diagnostics],
        sort_keys=True,
        separators=(",", ":"),
    )

    selector = common._evaluate_candidate(
        generated,
        output.selector_candidate,
        method="scsv-selector",
        seed=seed,
        runtime_seconds=output.runtime_seconds,
        communication_bytes=output.communication_bytes,
        stop_reason=output.stop_reason,
        selected_source="scsv-selector",
        validation_mse=output.selector_profile.weighted_mse,
        worst_validation_mse=output.selector_profile.worst_client_mse,
    )
    validated = common._evaluate_candidate(
        generated,
        output.validated_candidate,
        method="scsv-validated",
        seed=seed,
        runtime_seconds=output.runtime_seconds,
        communication_bytes=output.communication_bytes,
        stop_reason=(
            output.stop_reason
            + "; operational_probe="
            + str(int(output.probe_passed))
            + "; term_diagnostics="
            + diagnostics
        ),
        fallback_selected=not output.probe_passed,
        selected_source=(
            "selector-set" if output.probe_passed else "strict-intersection-anchor"
        ),
        validation_mse=output.selector_profile.weighted_mse,
        worst_validation_mse=output.selector_profile.worst_client_mse,
    )
    return [
        _row(selector, requested_noise=requested_noise, output=output, generated=generated),
        _row(validated, requested_noise=requested_noise, output=output, generated=generated),
    ]


def run_study(
    *,
    benchmarks: Sequence[str] = tuple(BENCHMARKS),
    scenarios: Sequence[str] = ("complementary", "spurious", "exception"),
    noise_ratios: Sequence[float] = (0.03, 0.10, 0.20),
    samples_per_client: Sequence[int] = (120, 300),
    seeds: Sequence[int] = SPENT_DIAGNOSTIC_SEEDS,
    max_terms: int = 6,
    allow_engineering_smoke: bool = False,
) -> list[SCSVStudyRow]:
    _validate_seeds(seeds, allow_engineering_smoke=allow_engineering_smoke)
    rows: list[SCSVStudyRow] = []
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
                                max_terms=max_terms,
                            )
                        )
    return rows


def _metric(rows, field: str) -> float:
    return float(mean(float(getattr(row, field)) for row in rows))


def _subset(rows, *, method=None, benchmark=None):
    return [
        row
        for row in rows
        if (method is None or row.method == method)
        and (benchmark is None or row.benchmark == benchmark)
    ]


def _load_v5_reference(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if row["method"] == "hr-v5-full"
        ]


def _ref_mean(rows: Sequence[dict[str, str]], field: str, *, benchmark=None) -> float:
    selected = [
        float(row[field])
        for row in rows
        if benchmark is None or row["benchmark"] == benchmark
    ]
    if not selected:
        raise ValueError(f"missing v5 reference values for {field}")
    return float(mean(selected))


def summarize(
    rows: Sequence[SCSVStudyRow],
    *,
    evaluate_signal: bool,
    v5_reference_path: Path = Path("results/high_recall_v5/rows.csv"),
) -> dict[str, object]:
    by_method = {method: _subset(rows, method=method) for method in METHODS}
    if any(not selected for selected in by_method.values()):
        raise ValueError("both SCSV diagnostic outputs are required")

    methods: dict[str, object] = {}
    for method, selected in by_method.items():
        methods[method] = {
            "runs": len(selected),
            "exact_recovery": _metric(selected, "exact_recovery"),
            "term_precision": _metric(selected, "term_precision"),
            "term_recall": _metric(selected, "term_recall"),
            "test_nmse": _metric(selected, "test_nmse"),
            "probe_pass_fraction": _metric(selected, "probe_passed"),
            "bank_target_recall": _metric(selected, "bank_target_recall"),
            "bank_complete_truth": _metric(selected, "bank_contains_all_truth"),
            "bank_size_median": float(median(int(row.bank_size or 0) for row in selected)),
            "candidate_sets_median": float(
                median(int(row.candidate_sets_evaluated or 0) for row in selected)
            ),
            "communication_bytes_median": float(
                median(int(row.communication_bytes) for row in selected)
            ),
            "runtime_seconds_median": float(
                median(float(row.runtime_seconds) for row in selected)
            ),
        }

    result: dict[str, object] = {
        "schema_version": 1,
        "status": (
            "scsv-spent-seed-diagnostic"
            if evaluate_signal
            else "scsv-engineering-smoke"
        ),
        "rows": len(rows),
        "conditions": len(rows) // len(METHODS),
        "seeds": sorted({row.seed for row in rows}),
        "methods": methods,
        "scientific_boundary": (
            "Post-hoc spent-seed mechanism diagnostic only; never fresh v6 evidence."
        ),
    }

    if not evaluate_signal:
        result["diagnostic_signal"] = {
            "evaluated": False,
            "passed": None,
        }
        return result

    reference = _load_v5_reference(v5_reference_path)
    if len(reference) != 450:
        raise RuntimeError(
            f"expected 450 sealed hr-v5-full reference rows, found {len(reference)}"
        )
    selector = by_method["scsv-selector"]
    validated = by_method["scsv-validated"]
    v5_exact = _ref_mean(reference, "exact_recovery")
    v5_precision = _ref_mean(reference, "term_precision")
    v5_poly = _ref_mean(reference, "exact_recovery", benchmark="poly3")
    v5_nested = _ref_mean(reference, "exact_recovery", benchmark="nested_sine")
    v5_trig = _ref_mean(reference, "exact_recovery", benchmark="trig_product")
    v5_comm = float(median(float(row["communication_bytes"]) for row in reference))

    selector_exact = _metric(selector, "exact_recovery")
    validated_exact = _metric(validated, "exact_recovery")
    validated_poly = _metric(_subset(validated, benchmark="poly3"), "exact_recovery")
    validated_nested = _metric(
        _subset(validated, benchmark="nested_sine"), "exact_recovery"
    )
    validated_trig = _metric(
        _subset(validated, benchmark="trig_product"), "exact_recovery"
    )
    validated_precision = _metric(validated, "term_precision")
    validated_comm = float(median(row.communication_bytes for row in validated))

    exception_selected = [
        row
        for row in validated
        if row.scenario == "exception"
        and "I(x3>1)*x3^2" in row.selector_structure.split(";")
    ]
    exception_route_ok = bool(exception_selected) and all(
        int(row.exception_eligible_diagnostics or 0) >= 1 for row in exception_selected
    )

    criteria = {
        "A_selector_exact_signal": selector_exact >= v5_exact + 0.05,
        "B_validated_exact_improves_v5": validated_exact > v5_exact,
        "C_poly3_exact_signal": validated_poly >= v5_poly + 0.10,
        "D_nested_sine_preserved": validated_nested >= v5_nested - 0.02,
        "E_trig_product_preserved": validated_trig >= v5_trig - 0.02,
        "F_precision_not_below_v5": validated_precision >= v5_precision,
        "G_communication_below_v5": validated_comm < v5_comm,
        "H_exception_route_has_eligible_diagnostics": exception_route_ok,
    }
    result["diagnostic_signal"] = {
        "evaluated": True,
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
        "reference_v5_exact": v5_exact,
        "reference_v5_poly3_exact": v5_poly,
        "reference_v5_precision": v5_precision,
        "reference_v5_communication_median": v5_comm,
    }
    return result


def write_csv(rows: Sequence[SCSVStudyRow], output: Path) -> None:
    if not rows:
        raise ValueError("cannot write an empty SCSV diagnostic")
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
    parser.add_argument("--seeds", default=",".join(map(str, SPENT_DIAGNOSTIC_SEEDS)))
    parser.add_argument("--max-terms", type=int, default=6)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/scsv_diagnostic/rows.csv"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/scsv_diagnostic/summary.json"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.smoke:
        settings = {
            "benchmarks": ("base", "poly3"),
            "scenarios": ("complementary", "exception"),
            "noise_ratios": (0.20,),
            "samples_per_client": (120,),
            "seeds": (SMOKE_SEED,),
            "max_terms": args.max_terms,
            "allow_engineering_smoke": True,
        }
    else:
        settings = {
            "benchmarks": _strings(args.benchmarks),
            "scenarios": _strings(args.scenarios),
            "noise_ratios": tuple(float(item) for item in _strings(args.noise)),
            "samples_per_client": tuple(int(item) for item in _strings(args.samples)),
            "seeds": tuple(int(item) for item in _strings(args.seeds)),
            "max_terms": args.max_terms,
            "allow_engineering_smoke": False,
        }

    rows = run_study(**settings)
    write_csv(rows, args.output)
    summary = summarize(rows, evaluate_signal=not args.smoke)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    print(
        f"Wrote {len(rows)} rows; "
        f"signal_evaluated={summary['diagnostic_signal']['evaluated']}; "
        f"signal={summary['diagnostic_signal']['passed']}"
    )


if __name__ == "__main__":
    main()
