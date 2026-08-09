"""Spent-seed independent diagnostic for Role-Contrast Conditional Deviation."""

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
from .rccd_diagnostic import RCCDOutput, rccd_diagnostic_method

SMOKE_SEED = 23001
SPENT_DIAGNOSTIC_SEEDS = (20101, 20102, 20103, 20104, 20105)
METHOD = "rccd-spent-diagnostic"
EXCEPTION_TERM = "I(x3>1)*x3^2"


@dataclass(frozen=True)
class RCCDStudyRow(independent.IndependentValidationRow):
    frozen_v6_anchor_structure: str = ""
    frozen_candidate_bank_terms: str = ""
    rccd_final_structure: str = ""
    discovery_full_structure: str = ""
    discovery_full_coefficients: str = ""
    exception_term: str = ""
    source_term: str = ""
    exception_in_bank: float = 0.0
    exception_in_anchor: float = 0.0
    source_in_anchor: float = 0.0
    rccd_attempted: float = 0.0
    exception_coefficient: float | None = None
    selector_eligible_clients: str = ""
    selector_eligible_support: int = 0
    selector_full_sse: float | None = None
    selector_zero_sse: float | None = None
    selector_delta: float | None = None
    selector_passed: float = 0.0
    probe_eligible_clients: str = ""
    probe_eligible_support: int = 0
    probe_full_sse: float | None = None
    probe_zero_sse: float | None = None
    probe_delta: float | None = None
    probe_passed: float = 0.0
    selector_outside_anchor_sse: float | None = None
    selector_outside_full_sse: float | None = None
    selector_outside_safe: float = 0.0
    probe_outside_anchor_sse: float | None = None
    probe_outside_full_sse: float | None = None
    probe_outside_safe: float = 0.0
    rccd_accepted: float = 0.0


def _validate_seeds(seeds: Sequence[int], *, smoke: bool) -> None:
    allowed = {SMOKE_SEED} if smoke else set(SPENT_DIAGNOSTIC_SEEDS)
    if set(seeds) - allowed:
        if smoke:
            raise ValueError("RCCD engineering smoke may use only seed 23001")
        raise ValueError("RCCD spent diagnostic may use only seeds 20101--20105")
    if not smoke and SMOKE_SEED in set(seeds):
        raise ValueError("RCCD engineering smoke seed cannot enter spent diagnostic")


def _evaluate_condition(
    generated,
    *,
    panel: str,
    requested_noise: float,
    nominal_samples: int,
    balance_profile: str,
    seed: int,
) -> RCCDStudyRow:
    catalog = benchmark_catalog(scenario=generated.scenario)
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    output: RCCDOutput = rccd_diagnostic_method(
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
            "rccd-source-linked-deviation"
            if output.accepted
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
        "probe_certified": float(output.probe_passed if output.attempted else output.anchor.probe_certified),
        "candidate_sets_evaluated": output.anchor.candidate_sets_evaluated,
        "necessity_failures": int(output.attempted and not output.selector_passed),
        "swap_failures": int(output.attempted and not output.probe_passed),
        "exception_eligible_diagnostics": int(
            bool(output.selector_eligible_clients) and bool(output.probe_eligible_clients)
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
            "frozen_candidate_bank_terms": ";".join(output.bank_terms),
            "rccd_final_structure": ";".join(output.final_structure),
            "discovery_full_structure": ";".join(output.discovery_full_structure),
            "discovery_full_coefficients": json.dumps(
                list(output.discovery_full_coefficients), separators=(",", ":")
            ),
            "exception_term": output.exception_term or "",
            "source_term": output.source_term or "",
            "exception_in_bank": float(output.exception_in_bank),
            "exception_in_anchor": float(output.exception_in_anchor),
            "source_in_anchor": float(output.source_in_anchor),
            "rccd_attempted": float(output.attempted),
            "exception_coefficient": output.exception_coefficient,
            "selector_eligible_clients": ";".join(output.selector_eligible_clients),
            "selector_eligible_support": int(output.selector_eligible_support),
            "selector_full_sse": output.selector_full_sse,
            "selector_zero_sse": output.selector_zero_sse,
            "selector_delta": output.selector_delta,
            "selector_passed": float(output.selector_passed),
            "probe_eligible_clients": ";".join(output.probe_eligible_clients),
            "probe_eligible_support": int(output.probe_eligible_support),
            "probe_full_sse": output.probe_full_sse,
            "probe_zero_sse": output.probe_zero_sse,
            "probe_delta": output.probe_delta,
            "probe_passed": float(output.probe_passed),
            "selector_outside_anchor_sse": output.selector_outside_anchor_sse,
            "selector_outside_full_sse": output.selector_outside_full_sse,
            "selector_outside_safe": float(output.selector_outside_safe),
            "probe_outside_anchor_sse": output.probe_outside_anchor_sse,
            "probe_outside_full_sse": output.probe_outside_full_sse,
            "probe_outside_safe": float(output.probe_outside_safe),
            "rccd_accepted": float(output.accepted),
        }
    )
    allowed = {item.name for item in fields(RCCDStudyRow)}
    return RCCDStudyRow(
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
) -> list[RCCDStudyRow]:
    _validate_seeds(seeds, smoke=smoke)
    rows: list[RCCDStudyRow] = []

    if smoke:
        settings = (
            ("cubic_cross", "complementary", 0.20, 100, 4, "balanced"),
            ("trig_cross", "exception", 0.20, 100, 4, "balanced"),
            ("cubic_cross", "exception", 0.20, 100, 4, "imbalanced"),
            ("multi_quadratic", "exception", 0.20, 100, 4, "balanced"),
            ("cubic_cross", "exception", 0.20, 100, 8, "balanced"),
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
    rows: Sequence[RCCDStudyRow],
    *,
    evaluate_signal: bool,
    reference_path: Path = Path("results/scsv_v6_independent/rows.csv"),
) -> dict[str, object]:
    result: dict[str, object] = {
        "schema_version": 1,
        "status": (
            "rccd-spent-seed-diagnostic"
            if evaluate_signal
            else "rccd-engineering-smoke"
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
        raise RuntimeError(f"expected 590 RCCD diagnostic rows, found {len(rows)}")
    reference = _load_reference(reference_path)
    observed = {_key_from_row(row): row for row in rows}
    if set(observed) != set(reference):
        raise RuntimeError("RCCD/reference condition keys do not match exactly")

    comparisons = []
    for key in sorted(observed):
        row = observed[key]
        ref = reference[key]
        ref_anchor = _structure(ref["selector_structure"])
        ref_bank = _extract_bank(ref["stop_reason"])
        final = _structure(row.rccd_final_structure)
        comparisons.append((row, ref, ref_anchor, ref_bank, final))

    anchor_bank_identity = all(
        _structure(row.frozen_v6_anchor_structure) == ref_anchor
        and _structure(row.frozen_candidate_bank_terms) == ref_bank
        for row, _, ref_anchor, ref_bank, _ in comparisons
    )
    non_exception_identical = all(
        final == ref_anchor
        for row, _, ref_anchor, _, final in comparisons
        if row.scenario != "exception"
    )
    already_selected_unchanged = all(
        final == ref_anchor
        for row, _, ref_anchor, _, final in comparisons
        if row.scenario == "exception" and EXCEPTION_TERM in ref_anchor
    )

    attempted = [row for row in rows if bool(row.rccd_attempted)]
    accepted = [row for row in rows if bool(row.rccd_accepted)]
    semantic_attempts = all(
        bool(row.exception_in_bank)
        and not bool(row.exception_in_anchor)
        and bool(row.source_in_anchor)
        and bool(row.source_term)
        for row in attempted
    )
    no_orphan_accept = all(bool(row.source_in_anchor) for row in accepted)
    selector_certified = all(
        bool(row.selector_passed) and float(row.selector_delta) < 0.0
        for row in accepted
    )
    probe_certified = all(
        bool(row.probe_passed) and float(row.probe_delta) < 0.0
        for row in accepted
    )
    outside_safe = all(
        bool(row.selector_outside_safe)
        and bool(row.probe_outside_safe)
        and float(row.selector_outside_full_sse)
        <= float(row.selector_outside_anchor_sse) + 1e-10
        and float(row.probe_outside_full_sse)
        <= float(row.probe_outside_anchor_sse) + 1e-10
        for row in accepted
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
            raise ValueError(f"empty RCCD subset for {field}")
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
    rccd_exact = avg(rows, "exact_recovery")
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
        "A_anchor_and_bank_identity": anchor_bank_identity,
        "B_non_exception_structures_identical": non_exception_identical,
        "C_existing_exception_structures_unchanged": already_selected_unchanged,
        "D_source_linked_attempts_only": semantic_attempts and no_orphan_accept,
        "E_accepted_selector_conditional_pass": selector_certified,
        "F_accepted_probe_conditional_pass": probe_certified,
        "G_accepted_outside_role_safe": outside_safe,
        "H_panel_s_4_exception_ge_090": panel_s_exception[4] >= 0.90,
        "I_panel_s_8_exception_ge_090": panel_s_exception[8] >= 0.90,
        "J_panel_s_16_exception_ge_09333": panel_s_exception[16] >= (28 / 30),
        "K_panel_s32_exception_remains_one": s32_exception == 1.0,
        "L_overall_exact_noninferior_001": rccd_exact >= ref_exact - 0.01,
        "M_zero_exact_harms": exact_harms == 0,
        "N_no_spurious_worsening_non_exception": spurious_worse == 0,
        "O_rescue_at_least_7_of_13": len(frozen_misses) == 13 and rescued >= 7,
        "P_rescue_hard_cubic_4client_imbalanced": hard_cubic_rescues >= 1,
    }
    result["mechanism_signal"] = {
        "evaluated": True,
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
        "panel_s_exception_recovery": {
            str(key): value for key, value in panel_s_exception.items()
        },
        "panel_s32_exception_recovery": s32_exception,
        "rccd_exact_recovery": rccd_exact,
        "frozen_v6_exact_recovery": ref_exact,
        "exact_harms": exact_harms,
        "spurious_worse_non_exception": spurious_worse,
        "frozen_exception_misses": len(frozen_misses),
        "rescued_exception_misses": rescued,
        "hard_cubic_4client_imbalanced_rescues": hard_cubic_rescues,
        "attempts": len(attempted),
        "accepts": len(accepted),
        "selector_delta_max_accepted": max(
            [float(row.selector_delta) for row in accepted] or [0.0]
        ),
        "probe_delta_max_accepted": max(
            [float(row.probe_delta) for row in accepted] or [0.0]
        ),
    }
    return result


def write_csv(rows: Sequence[RCCDStudyRow], output: Path) -> None:
    if not rows:
        raise ValueError("cannot write empty RCCD diagnostic")
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
        default=Path("results/rccd_spent_diagnostic/rows.csv"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/rccd_spent_diagnostic/summary.json"),
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
        f"Wrote {len(rows)} RCCD rows; "
        f"signal_evaluated={summary['mechanism_signal']['evaluated']}; "
        f"signal={summary['mechanism_signal']['passed']}"
    )


if __name__ == "__main__":
    main()