"""Spent-seed independent diagnostic for Frozen-Core Role Residual Augmentation."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path
from statistics import mean
from typing import Sequence

from . import redesign_study as common
from . import scsv_v6_independent_study as independent
from .benchmarks import benchmark_catalog
from .fcrra_diagnostic import FCRRAOutput, fcrra_diagnostic_method

SMOKE_SEED = 22001
SPENT_DIAGNOSTIC_SEEDS = (20101, 20102, 20103, 20104, 20105)
METHOD = "fcrra-spent-diagnostic"
EXCEPTION_TERM = "I(x3>1)*x3^2"


@dataclass(frozen=True)
class FCRRAStudyRow(independent.IndependentValidationRow):
    frozen_v6_anchor_structure: str = ""
    fcrra_final_structure: str = ""
    anchor_discovery_coefficients: str = ""
    fcrra_final_coefficients: str = ""
    exception_term: str = ""
    exception_in_bank: float = 0.0
    exception_in_anchor: float = 0.0
    fcrra_attempted: float = 0.0
    eligible_discovery_clients: str = ""
    eligible_discovery_support: int = 0
    eligible_selector_clients: str = ""
    eligible_selector_support: int = 0
    residual_numerator: float | None = None
    residual_denominator: float | None = None
    exception_coefficient: float | None = None
    anchor_role_information_score: float | None = None
    augmented_role_information_score: float | None = None
    outside_selector_sse_max_difference: float | None = None
    outside_selector_prediction_max_difference: float | None = None
    augmentation_accepted: float = 0.0


def _validate_seeds(seeds: Sequence[int], *, smoke: bool) -> None:
    allowed = {SMOKE_SEED} if smoke else set(SPENT_DIAGNOSTIC_SEEDS)
    if set(seeds) - allowed:
        if smoke:
            raise ValueError("FCRRA engineering smoke may use only seed 22001")
        raise ValueError("FCRRA spent diagnostic may use only seeds 20101--20105")
    if not smoke and SMOKE_SEED in set(seeds):
        raise ValueError("FCRRA engineering smoke seed cannot enter spent diagnostic")


def _evaluate_condition(
    generated,
    *,
    panel: str,
    requested_noise: float,
    nominal_samples: int,
    balance_profile: str,
    seed: int,
) -> FCRRAStudyRow:
    catalog = benchmark_catalog(scenario=generated.scenario)
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    output: FCRRAOutput = fcrra_diagnostic_method(
        generated.clients,
        catalog,
        seed=seed,
        max_terms=6,
        target_mse=target_mse,
        min_repair_score=0.05,
    )
    base = common._evaluate_candidate(
        generated,
        output.candidate,
        method=METHOD,
        seed=seed,
        runtime_seconds=output.runtime_seconds,
        communication_bytes=output.communication_bytes,
        stop_reason=output.stop_reason,
        fallback_selected=False,
        selected_source=(
            "fcrra-frozen-core-role-residual"
            if output.augmentation_accepted
            else "frozen-v6-anchor"
        ),
        validation_mse=output.anchor.selector_profile.weighted_mse,
        worst_validation_mse=output.anchor.selector_profile.worst_client_mse,
    )

    truth = set(generated.target_terms)
    bank = set(output.anchor.bank.candidate_terms)
    extras = {
        "candidate_bank_target_recall": (
            len(bank & truth) / len(truth) if truth else 1.0
        ),
        "candidate_bank_contains_all_truth": float(truth.issubset(bank)),
        "candidate_bank_size": len(bank),
        "candidate_bank_nuisance_count": len(bank - truth),
        "probe_certified": float(output.probe_certified),
        "candidate_sets_evaluated": output.anchor.candidate_sets_evaluated,
        "necessity_failures": sum(
            not item.necessity_passed for item in output.term_diagnostics
        ),
        "swap_failures": sum(not item.swap_passed for item in output.term_diagnostics),
        "exception_eligible_diagnostics": sum(
            item.kind == "exception" and bool(item.eligible_clients)
            for item in output.term_diagnostics
        ),
        "selector_structure": ";".join(output.final_structure),
    }
    wrapped = independent._row(
        base,
        panel=panel,
        requested_noise=requested_noise,
        nominal_samples=nominal_samples,
        balance_profile=balance_profile,
        generated=generated,
        extras=extras,
    )
    payload = asdict(wrapped)
    payload.update(
        {
            "frozen_v6_anchor_structure": ";".join(output.anchor_structure),
            "fcrra_final_structure": ";".join(output.final_structure),
            "anchor_discovery_coefficients": json.dumps(
                list(output.anchor_discovery_coefficients), separators=(",", ":")
            ),
            "fcrra_final_coefficients": json.dumps(
                list(output.final_coefficients), separators=(",", ":")
            ),
            "exception_term": output.exception_term or "",
            "exception_in_bank": float(output.exception_in_bank),
            "exception_in_anchor": float(output.exception_in_anchor),
            "fcrra_attempted": float(output.attempted),
            "eligible_discovery_clients": ";".join(
                output.eligible_discovery_clients
            ),
            "eligible_discovery_support": int(output.eligible_discovery_support),
            "eligible_selector_clients": ";".join(output.eligible_selector_clients),
            "eligible_selector_support": int(output.eligible_selector_support),
            "residual_numerator": output.residual_numerator,
            "residual_denominator": output.residual_denominator,
            "exception_coefficient": output.exception_coefficient,
            "anchor_role_information_score": output.anchor_role_information_score,
            "augmented_role_information_score": output.augmented_role_information_score,
            "outside_selector_sse_max_difference": (
                output.outside_selector_sse_max_difference
            ),
            "outside_selector_prediction_max_difference": (
                output.outside_selector_prediction_max_difference
            ),
            "augmentation_accepted": float(output.augmentation_accepted),
        }
    )
    allowed = {item.name for item in fields(FCRRAStudyRow)}
    return FCRRAStudyRow(
        **{key: value for key, value in payload.items() if key in allowed}
    )


def _condition(
    benchmark: str,
    scenario: str,
    noise: float,
    nominal: int,
    client_count: int,
    profile: str,
    seed: int,
):
    return independent._condition(
        benchmark, scenario, noise, nominal, client_count, profile, seed
    )


def run_study(
    *,
    seeds: Sequence[int] = SPENT_DIAGNOSTIC_SEEDS,
    smoke: bool = False,
) -> list[FCRRAStudyRow]:
    _validate_seeds(seeds, smoke=smoke)
    rows: list[FCRRAStudyRow] = []

    if smoke:
        settings = (
            ("cubic_cross", "complementary", 0.20, 100, 4, "balanced"),
            ("trig_cross", "exception", 0.20, 100, 4, "balanced"),
            ("cubic_cross", "exception", 0.20, 100, 4, "imbalanced"),
        )
        for benchmark, scenario, noise, nominal, clients, profile in settings:
            generated = _condition(
                benchmark, scenario, noise, nominal, clients, profile, SMOKE_SEED
            )
            rows.append(
                _evaluate_condition(
                    generated,
                    panel="SMOKE",
                    requested_noise=noise,
                    nominal_samples=nominal,
                    balance_profile=profile,
                    seed=SMOKE_SEED,
                )
            )
        return rows

    for benchmark in independent.PANEL_G_BENCHMARKS:
        for scenario in ("complementary", "spurious", "exception"):
            for noise in (0.10, 0.20):
                for nominal in (100, 250):
                    for seed in seeds:
                        generated = _condition(
                            benchmark, scenario, noise, nominal, 4, "balanced", seed
                        )
                        rows.append(
                            _evaluate_condition(
                                generated,
                                panel="G",
                                requested_noise=noise,
                                nominal_samples=nominal,
                                balance_profile="balanced",
                                seed=seed,
                            )
                        )

    for benchmark in independent.PANEL_S_BENCHMARKS:
        for scenario in ("complementary", "spurious", "exception"):
            for client_count in (4, 8, 16):
                for profile in ("balanced", "imbalanced"):
                    for seed in seeds:
                        generated = _condition(
                            benchmark,
                            scenario,
                            0.20,
                            100,
                            client_count,
                            profile,
                            seed,
                        )
                        rows.append(
                            _evaluate_condition(
                                generated,
                                panel="S",
                                requested_noise=0.20,
                                nominal_samples=100,
                                balance_profile=profile,
                                seed=seed,
                            )
                        )

    for scenario in ("complementary", "exception"):
        for profile in ("balanced", "imbalanced"):
            for seed in seeds:
                generated = _condition(
                    "multi_quadratic", scenario, 0.20, 100, 32, profile, seed
                )
                rows.append(
                    _evaluate_condition(
                        generated,
                        panel="S32",
                        requested_noise=0.20,
                        nominal_samples=100,
                        balance_profile=profile,
                        seed=seed,
                    )
                )
    return rows


def _key_from_row(row) -> tuple[object, ...]:
    return (
        row.panel,
        row.benchmark,
        row.scenario,
        f"{float(row.noise_ratio):.12g}",
        int(row.nominal_samples_per_client),
        int(row.num_clients),
        row.balance_profile,
        int(row.seed),
    )


def _key_from_reference(row: dict[str, str]) -> tuple[object, ...]:
    return (
        row["panel"],
        row["benchmark"],
        row["scenario"],
        f"{float(row['noise_ratio']):.12g}",
        int(row["nominal_samples_per_client"]),
        int(row["num_clients"]),
        row["balance_profile"],
        int(row["seed"]),
    )


def _load_reference(path: Path) -> dict[tuple[object, ...], dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["method"] == "scsv-v6-full"
        ]
    if len(rows) != 590:
        raise RuntimeError(f"expected 590 frozen v6 reference rows, found {len(rows)}")
    return {_key_from_reference(row): row for row in rows}


def _structure(value: str) -> tuple[str, ...]:
    return tuple(item for item in value.split(";") if item)


def _extract_bank(stop_reason: str) -> tuple[str, ...]:
    marker = "bank="
    start = stop_reason.find(marker)
    if start < 0:
        return ()
    start += len(marker)
    end = stop_reason.find("; selector=", start)
    if end < 0:
        return ()
    return tuple(item for item in stop_reason[start:end].split(",") if item)


def summarize(
    rows: Sequence[FCRRAStudyRow],
    *,
    evaluate_signal: bool,
    reference_path: Path = Path("results/scsv_v6_independent/rows.csv"),
) -> dict[str, object]:
    result: dict[str, object] = {
        "schema_version": 1,
        "status": (
            "fcrra-spent-seed-diagnostic"
            if evaluate_signal
            else "fcrra-engineering-smoke"
        ),
        "rows": len(rows),
        "conditions": len(rows),
        "seeds": sorted({row.seed for row in rows}),
        "scientific_boundary": (
            "Post-independent spent-seed mechanism diagnostic only; never "
            "independent confirmation or external authorization."
        ),
    }
    if not evaluate_signal:
        result["mechanism_signal"] = {"evaluated": False, "passed": None}
        return result

    if len(rows) != 590:
        raise RuntimeError(f"expected 590 FCRRA diagnostic rows, found {len(rows)}")
    reference = _load_reference(reference_path)
    observed = {_key_from_row(row): row for row in rows}
    if set(observed) != set(reference):
        raise RuntimeError("FCRRA/reference condition keys do not match exactly")

    comparisons = []
    for key in sorted(observed):
        row = observed[key]
        ref = reference[key]
        ref_anchor = _structure(ref["selector_structure"])
        final = _structure(row.fcrra_final_structure)
        ref_bank_has_exception = EXCEPTION_TERM in _extract_bank(ref["stop_reason"])
        comparisons.append((row, ref, ref_anchor, final, ref_bank_has_exception))

    bank_match = all(
        bool(row.exception_in_bank) == ref_bank
        for row, _, _, _, ref_bank in comparisons
    )
    non_exception_identical = all(
        final == ref_anchor
        for row, _, ref_anchor, final, _ in comparisons
        if row.scenario != "exception"
    )
    already_selected_unchanged = all(
        final == ref_anchor
        for row, _, ref_anchor, final, _ in comparisons
        if row.scenario == "exception" and EXCEPTION_TERM in ref_anchor
    )

    attempted = [row for row in rows if bool(row.fcrra_attempted)]
    outside_identical = all(
        float(row.outside_selector_sse_max_difference or 0.0) <= 1e-10
        and float(row.outside_selector_prediction_max_difference or 0.0) <= 1e-10
        for row in attempted
    )

    def subset(*, panel=None, scenario=None, clients=None, benchmark=None, profile=None):
        return [
            row
            for row in rows
            if (panel is None or row.panel == panel)
            and (scenario is None or row.scenario == scenario)
            and (clients is None or row.num_clients == clients)
            and (benchmark is None or row.benchmark == benchmark)
            and (profile is None or row.balance_profile == profile)
        ]

    def avg(selected, field):
        if not selected:
            raise ValueError(f"empty FCRRA subset for {field}")
        return float(mean(float(getattr(row, field)) for row in selected))

    panel_s_exception = {
        clients: avg(
            subset(panel="S", scenario="exception", clients=clients),
            "exception_recovered",
        )
        for clients in (4, 8, 16)
    }
    s32_exception = avg(
        subset(panel="S32", scenario="exception"), "exception_recovered"
    )
    fcrra_exact = avg(rows, "exact_recovery")
    ref_exact = float(mean(float(ref["exact_recovery"]) for ref in reference.values()))

    exact_harms = sum(
        float(ref["exact_recovery"]) == 1.0 and float(row.exact_recovery) == 0.0
        for row, ref, _, _, _ in comparisons
    )
    spurious_worse = sum(
        row.scenario != "exception"
        and float(row.spurious_accepted) > float(ref["spurious_accepted"])
        for row, ref, _, _, _ in comparisons
    )

    frozen_misses = [
        (row, ref, ref_anchor)
        for row, ref, ref_anchor, _, _ in comparisons
        if row.scenario == "exception"
        and EXCEPTION_TERM not in ref_anchor
        and float(ref["exception_recovered"]) == 0.0
    ]
    rescued = sum(float(row.exception_recovered) == 1.0 for row, _, _ in frozen_misses)
    hard_cubic_rescues = sum(
        float(row.exception_recovered) == 1.0
        for row, _, _ in frozen_misses
        if row.panel == "S"
        and row.benchmark == "cubic_cross"
        and row.num_clients == 4
        and row.balance_profile == "imbalanced"
    )

    criteria = {
        "A_candidate_bank_identity": bank_match,
        "B_non_exception_structures_identical": non_exception_identical,
        "C_existing_exception_structures_unchanged": already_selected_unchanged,
        "D_outside_role_predictions_identical": outside_identical,
        "E_panel_s_4_exception_ge_090": panel_s_exception[4] >= 0.90,
        "F_panel_s_8_exception_ge_090": panel_s_exception[8] >= 0.90,
        "G_panel_s_16_exception_ge_09333": panel_s_exception[16] >= (28 / 30),
        "H_panel_s32_exception_remains_one": s32_exception == 1.0,
        "I_overall_exact_noninferior_001": fcrra_exact >= ref_exact - 0.01,
        "J_zero_exact_harms": exact_harms == 0,
        "K_no_spurious_worsening_non_exception": spurious_worse == 0,
        "L_rescue_at_least_7_of_13": len(frozen_misses) == 13 and rescued >= 7,
        "M_rescue_hard_cubic_4client_imbalanced": hard_cubic_rescues >= 1,
    }
    result["mechanism_signal"] = {
        "evaluated": True,
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
        "panel_s_exception_recovery": {
            str(key): value for key, value in panel_s_exception.items()
        },
        "panel_s32_exception_recovery": s32_exception,
        "fcrra_exact_recovery": fcrra_exact,
        "frozen_v6_exact_recovery": ref_exact,
        "exact_harms": exact_harms,
        "spurious_worse_non_exception": spurious_worse,
        "frozen_exception_misses": len(frozen_misses),
        "rescued_exception_misses": rescued,
        "hard_cubic_4client_imbalanced_rescues": hard_cubic_rescues,
        "augmentation_attempts": int(sum(row.fcrra_attempted for row in rows)),
        "augmentation_accepts": int(sum(row.augmentation_accepted for row in rows)),
        "outside_identity_max_sse": max(
            [float(row.outside_selector_sse_max_difference or 0.0) for row in attempted]
            or [0.0]
        ),
        "outside_identity_max_prediction": max(
            [float(row.outside_selector_prediction_max_difference or 0.0) for row in attempted]
            or [0.0]
        ),
    }
    return result


def write_csv(rows: Sequence[FCRRAStudyRow], output: Path) -> None:
    if not rows:
        raise ValueError("cannot write empty FCRRA diagnostic")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/fcrra_spent_diagnostic/rows.csv"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/fcrra_spent_diagnostic/summary.json"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = run_study(
        seeds=(SMOKE_SEED,) if args.smoke else SPENT_DIAGNOSTIC_SEEDS,
        smoke=args.smoke,
    )
    write_csv(rows, args.output)
    summary = summarize(rows, evaluate_signal=not args.smoke)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    print(
        f"Wrote {len(rows)} FCRRA rows; "
        f"signal_evaluated={summary['mechanism_signal']['evaluated']}; "
        f"signal={summary['mechanism_signal']['passed']}"
    )


if __name__ == "__main__":
    main()
