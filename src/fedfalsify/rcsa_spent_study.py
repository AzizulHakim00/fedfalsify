"""Spent-seed independent diagnostic for Role-Conditional Set Augmentation."""

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
from . import scsv_v6_study as v6study
from .benchmarks import benchmark_catalog
from .rcsa_diagnostic import RCSAOutput, rcsa_diagnostic_method

SMOKE_SEED = 21001
SPENT_DIAGNOSTIC_SEEDS = (20101, 20102, 20103, 20104, 20105)
METHOD = "rcsa-spent-diagnostic"
EXCEPTION_TERM = "I(x3>1)*x3^2"


@dataclass(frozen=True)
class RCSAStudyRow(independent.IndependentValidationRow):
    frozen_v6_anchor_structure: str = ""
    rcsa_final_structure: str = ""
    exception_term: str = ""
    exception_in_bank: float = 0.0
    exception_in_anchor: float = 0.0
    rcsa_attempted: float = 0.0
    eligible_selector_clients: str = ""
    eligible_selector_support: int = 0
    anchor_role_information_score: float | None = None
    augmented_role_information_score: float | None = None
    outside_selector_sse_anchor: float | None = None
    outside_selector_sse_augmented: float | None = None
    augmentation_accepted: float = 0.0


def _validate_seeds(seeds: Sequence[int], *, smoke: bool) -> None:
    allowed = {SMOKE_SEED} if smoke else set(SPENT_DIAGNOSTIC_SEEDS)
    if set(seeds) - allowed:
        if smoke:
            raise ValueError("RCSA engineering smoke may use only seed 21001")
        raise ValueError("RCSA spent diagnostic may use only seeds 20101--20105")
    if not smoke and SMOKE_SEED in set(seeds):
        raise ValueError("RCSA engineering smoke seed cannot enter spent diagnostic")


def _evaluate_condition(
    generated,
    *,
    panel: str,
    requested_noise: float,
    nominal_samples: int,
    balance_profile: str,
    seed: int,
) -> RCSAStudyRow:
    catalog = benchmark_catalog(scenario=generated.scenario)
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    output: RCSAOutput = rcsa_diagnostic_method(
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
            "rcsa-role-augmentation"
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
            "rcsa_final_structure": ";".join(output.final_structure),
            "exception_term": output.exception_term or "",
            "exception_in_bank": float(output.exception_in_bank),
            "exception_in_anchor": float(output.exception_in_anchor),
            "rcsa_attempted": float(output.attempted),
            "eligible_selector_clients": ";".join(
                output.eligible_selector_clients
            ),
            "eligible_selector_support": int(output.eligible_selector_support),
            "anchor_role_information_score": output.anchor_role_information_score,
            "augmented_role_information_score": output.augmented_role_information_score,
            "outside_selector_sse_anchor": output.outside_selector_sse_anchor,
            "outside_selector_sse_augmented": output.outside_selector_sse_augmented,
            "augmentation_accepted": float(output.augmentation_accepted),
        }
    )
    allowed = {item.name for item in fields(RCSAStudyRow)}
    return RCSAStudyRow(**{key: value for key, value in payload.items() if key in allowed})


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
) -> list[RCSAStudyRow]:
    _validate_seeds(seeds, smoke=smoke)
    rows: list[RCSAStudyRow] = []

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

    # Reuse the exact frozen 590-condition independent geometry.
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


def summarize(
    rows: Sequence[RCSAStudyRow],
    *,
    evaluate_signal: bool,
    reference_path: Path = Path("results/scsv_v6_independent/rows.csv"),
) -> dict[str, object]:
    result: dict[str, object] = {
        "schema_version": 1,
        "status": (
            "rcsa-spent-seed-diagnostic"
            if evaluate_signal
            else "rcsa-engineering-smoke"
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
        raise RuntimeError(f"expected 590 RCSA diagnostic rows, found {len(rows)}")
    reference = _load_reference(reference_path)
    observed = {_key_from_row(row): row for row in rows}
    if set(observed) != set(reference):
        raise RuntimeError("RCSA/reference condition keys do not match exactly")

    comparisons = []
    for key in sorted(observed):
        row = observed[key]
        ref = reference[key]
        ref_anchor = _structure(ref["selector_structure"])
        rcsa_final = _structure(row.rcsa_final_structure)
        ref_bank_match = EXCEPTION_TERM in _extract_bank(ref["stop_reason"])
        comparisons.append((row, ref, ref_anchor, rcsa_final, ref_bank_match))

    non_exception_identical = all(
        rcsa_final == ref_anchor
        for row, _, ref_anchor, rcsa_final, _ in comparisons
        if row.scenario != "exception"
    )
    already_selected_unchanged = all(
        rcsa_final == ref_anchor
        for row, _, ref_anchor, rcsa_final, _ in comparisons
        if row.scenario == "exception" and EXCEPTION_TERM in ref_anchor
    )
    bank_match = all(
        bool(row.exception_in_bank) == ref_bank_match
        for row, _, _, _, ref_bank_match in comparisons
    )

    def subset(*, panel=None, scenario=None, clients=None):
        return [
            row
            for row in rows
            if (panel is None or row.panel == panel)
            and (scenario is None or row.scenario == scenario)
            and (clients is None or row.num_clients == clients)
        ]

    def avg(selected, field):
        if not selected:
            raise ValueError(f"empty RCSA subset for {field}")
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
    rcsa_exact = avg(rows, "exact_recovery")
    ref_exact = float(
        mean(float(ref["exact_recovery"]) for ref in reference.values())
    )

    exact_harms = sum(
        float(ref["exact_recovery"]) == 1.0 and float(row.exact_recovery) == 0.0
        for row, ref, _, _, _ in comparisons
    )
    spurious_worse = sum(
        row.scenario != "exception"
        and float(row.spurious_accepted) > float(ref["spurious_accepted"])
        for row, ref, _, _, _ in comparisons
    )
    frozen_exception_misses = [
        (row, ref)
        for row, ref, ref_anchor, _, _
        in comparisons
        if row.scenario == "exception" and EXCEPTION_TERM not in ref_anchor
    ]
    rescued = sum(
        float(ref["exception_recovered"]) == 0.0
        and float(row.exception_recovered) == 1.0
        for row, ref in frozen_exception_misses
    )
    frozen_miss_count = sum(
        float(ref["exception_recovered"]) == 0.0
        for _, ref in frozen_exception_misses
    )

    criteria = {
        "A_candidate_bank_identity": bank_match,
        "B_non_exception_structures_identical": non_exception_identical,
        "C_existing_exception_structures_unchanged": already_selected_unchanged,
        "D_panel_s_4_exception_ge_090": panel_s_exception[4] >= 0.90,
        "E_panel_s_8_exception_ge_frozen": panel_s_exception[8] >= 0.90,
        "F_panel_s_16_exception_ge_frozen": panel_s_exception[16] >= (28 / 30),
        "G_panel_s32_exception_remains_one": s32_exception == 1.0,
        "H_overall_exact_noninferior_001": rcsa_exact >= ref_exact - 0.01,
        "I_zero_exact_harms": exact_harms == 0,
        "J_no_spurious_worsening_non_exception": spurious_worse == 0,
        "K_rescue_at_least_7_of_13": rescued >= 7 and frozen_miss_count == 13,
    }
    result["mechanism_signal"] = {
        "evaluated": True,
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
        "panel_s_exception_recovery": {
            str(key): value for key, value in panel_s_exception.items()
        },
        "panel_s32_exception_recovery": s32_exception,
        "rcsa_exact_recovery": rcsa_exact,
        "frozen_v6_exact_recovery": ref_exact,
        "exact_harms": exact_harms,
        "spurious_worse_non_exception": spurious_worse,
        "frozen_exception_misses": frozen_miss_count,
        "rescued_exception_misses": rescued,
        "augmentation_attempts": int(sum(row.rcsa_attempted for row in rows)),
        "augmentation_accepts": int(sum(row.augmentation_accepted for row in rows)),
    }
    return result


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


def write_csv(rows: Sequence[RCSAStudyRow], output: Path) -> None:
    if not rows:
        raise ValueError("cannot write empty RCSA diagnostic")
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
        default=Path("results/rcsa_spent_diagnostic/rows.csv"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/rcsa_spent_diagnostic/summary.json"),
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
        f"Wrote {len(rows)} RCSA rows; "
        f"signal_evaluated={summary['mechanism_signal']['evaluated']}; "
        f"signal={summary['mechanism_signal']['passed']}"
    )


if __name__ == "__main__":
    main()
