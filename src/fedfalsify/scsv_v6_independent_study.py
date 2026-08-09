"""Frozen independent scalability/generalization study for SCSV-Cert v6."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path
from statistics import mean, median
from typing import Iterable, Sequence

from . import high_recall_v5_study as v5study
from . import redesign_study as common
from . import scsv_v6_study as v6study
from .scsv_v6 import SCSVV6Output, scsv_cert_method
from .scsv_v6_independent import (
    INDEPENDENT_BENCHMARKS,
    generate_independent_benchmark,
)

SMOKE_SEED = 20001
INDEPENDENT_SEEDS = (20101, 20102, 20103, 20104, 20105)
METHODS = (
    "legacy-certificate",
    "hr-v5-full",
    "scsv-v6-full",
    "scsv-v6-no-score-proposer",
    "centralized-forward",
    "score-only-federated",
)
V6_METHODS = {"scsv-v6-full", "scsv-v6-no-score-proposer"}
PANEL_G_BENCHMARKS = tuple(INDEPENDENT_BENCHMARKS)
PANEL_S_BENCHMARKS = ("cubic_cross", "multi_quadratic", "trig_cross")


@dataclass(frozen=True)
class IndependentValidationRow(v6study.V6StudyRow):
    panel: str = ""
    balance_profile: str = ""
    nominal_samples_per_client: int = 0
    client_sizes: str = ""
    communication_per_client: float = 0.0


def _validate_seeds(seeds: Sequence[int], *, smoke: bool) -> None:
    allowed = {SMOKE_SEED} if smoke else set(INDEPENDENT_SEEDS)
    if set(seeds) - allowed:
        if smoke:
            raise ValueError("independent engineering smoke may use only seed 20001")
        raise ValueError("independent evidence may use only seeds 20101--20105")
    if not smoke and SMOKE_SEED in set(seeds):
        raise ValueError("engineering smoke seed cannot enter independent evidence")


def _row(
    base: common.RedesignRow,
    *,
    panel: str,
    requested_noise: float,
    nominal_samples: int,
    balance_profile: str,
    generated,
    extras: dict[str, object] | None = None,
) -> IndependentValidationRow:
    payload = base.to_dict()
    payload["noise_ratio"] = float(requested_noise)
    payload["samples_per_client"] = int(nominal_samples)
    payload.update(extras or {})
    payload.update(
        {
            "panel": panel,
            "balance_profile": balance_profile,
            "nominal_samples_per_client": int(nominal_samples),
            "client_sizes": ";".join(str(len(client.y)) for client in generated.clients),
            "communication_per_client": float(base.communication_bytes)
            / max(len(generated.clients), 1),
        }
    )
    allowed = {item.name for item in fields(IndependentValidationRow)}
    return IndependentValidationRow(**{key: value for key, value in payload.items() if key in allowed})


def _evaluate_condition(
    generated,
    *,
    panel: str,
    requested_noise: float,
    nominal_samples: int,
    balance_profile: str,
    seed: int,
    methods: Sequence[str] = METHODS,
    max_terms: int = 6,
) -> list[IndependentValidationRow]:
    requested = set(methods)
    unknown = requested - set(METHODS)
    if unknown:
        raise ValueError(f"unknown independent methods: {sorted(unknown)}")

    rows: list[IndependentValidationRow] = []
    comparator_methods = tuple(method for method in methods if method not in V6_METHODS)
    if comparator_methods:
        comparators = v5study._evaluate_condition(
            generated,
            requested_noise=requested_noise,
            seed=seed,
            methods=comparator_methods,
            max_terms=max_terms,
        )
        for item in comparators:
            rows.append(
                _row(
                    item,
                    panel=panel,
                    requested_noise=requested_noise,
                    nominal_samples=nominal_samples,
                    balance_profile=balance_profile,
                    generated=generated,
                )
            )

    catalog = v6study.benchmark_catalog(scenario=generated.scenario)
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    for method, use_score in (
        ("scsv-v6-full", True),
        ("scsv-v6-no-score-proposer", False),
    ):
        if method not in requested:
            continue
        output: SCSVV6Output = scsv_cert_method(
            generated.clients,
            catalog,
            seed=seed,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=0.05,
            use_score_proposer=use_score,
        )
        base = v6study._evaluate_v6(generated, output, method=method, seed=seed)
        rows.append(
            _row(
                base,
                panel=panel,
                requested_noise=requested_noise,
                nominal_samples=nominal_samples,
                balance_profile=balance_profile,
                generated=generated,
                extras=v6study._v6_extras(generated, output),
            )
        )
    return rows


def _condition(
    benchmark: str,
    scenario: str,
    noise: float,
    nominal_samples: int,
    client_count: int,
    balance_profile: str,
    seed: int,
):
    return generate_independent_benchmark(
        benchmark,
        scenario=scenario,
        nominal_samples_per_client=nominal_samples,
        noise_ratio=noise,
        seed=seed,
        num_clients=client_count,
        balance_profile=balance_profile,
    )


def run_independent_study(
    *,
    seeds: Sequence[int] = INDEPENDENT_SEEDS,
    methods: Sequence[str] = METHODS,
) -> list[IndependentValidationRow]:
    _validate_seeds(seeds, smoke=False)
    rows: list[IndependentValidationRow] = []

    # Panel G: five unseen combinations at four balanced clients.
    for benchmark in PANEL_G_BENCHMARKS:
        for scenario in ("complementary", "spurious", "exception"):
            for noise in (0.10, 0.20):
                for nominal in (100, 250):
                    for seed in seeds:
                        generated = _condition(
                            benchmark, scenario, noise, nominal, 4, "balanced", seed
                        )
                        rows.extend(
                            _evaluate_condition(
                                generated,
                                panel="G",
                                requested_noise=noise,
                                nominal_samples=nominal,
                                balance_profile="balanced",
                                seed=seed,
                                methods=methods,
                            )
                        )

    # Panel S: client-count and deterministic imbalance stress.
    for benchmark in PANEL_S_BENCHMARKS:
        for scenario in ("complementary", "spurious", "exception"):
            for client_count in (4, 8, 16):
                for profile in ("balanced", "imbalanced"):
                    for seed in seeds:
                        generated = _condition(
                            benchmark, scenario, 0.20, 100, client_count, profile, seed
                        )
                        rows.extend(
                            _evaluate_condition(
                                generated,
                                panel="S",
                                requested_noise=0.20,
                                nominal_samples=100,
                                balance_profile=profile,
                                seed=seed,
                                methods=methods,
                            )
                        )

    # Panel S32: targeted high-client-count stress.
    for scenario in ("complementary", "exception"):
        for profile in ("balanced", "imbalanced"):
            for seed in seeds:
                generated = _condition(
                    "multi_quadratic", scenario, 0.20, 100, 32, profile, seed
                )
                rows.extend(
                    _evaluate_condition(
                        generated,
                        panel="S32",
                        requested_noise=0.20,
                        nominal_samples=100,
                        balance_profile=profile,
                        seed=seed,
                        methods=methods,
                    )
                )
    return rows


def run_smoke() -> list[IndependentValidationRow]:
    _validate_seeds((SMOKE_SEED,), smoke=True)
    generated = _condition(
        "cubic_cross", "exception", 0.20, 100, 8, "imbalanced", SMOKE_SEED
    )
    return _evaluate_condition(
        generated,
        panel="SMOKE",
        requested_noise=0.20,
        nominal_samples=100,
        balance_profile="imbalanced",
        seed=SMOKE_SEED,
        methods=("scsv-v6-full",),
    )


def _subset(
    rows: Iterable[IndependentValidationRow],
    *,
    panel: str | None = None,
    method: str | None = None,
    scenario: str | None = None,
    client_count: int | None = None,
    profile: str | None = None,
) -> list[IndependentValidationRow]:
    return [
        row
        for row in rows
        if (panel is None or row.panel == panel)
        and (method is None or row.method == method)
        and (scenario is None or row.scenario == scenario)
        and (client_count is None or row.num_clients == client_count)
        and (profile is None or row.balance_profile == profile)
    ]


def _mean(rows: Sequence[IndependentValidationRow], field: str) -> float:
    if not rows:
        raise ValueError(f"cannot average empty subset for {field}")
    return float(mean(float(getattr(row, field)) for row in rows))


def _median(rows: Sequence[IndependentValidationRow], field: str) -> float:
    if not rows:
        raise ValueError(f"cannot take median of empty subset for {field}")
    return float(median(float(getattr(row, field)) for row in rows))


def _mean_optional(rows: Sequence[IndependentValidationRow], field: str) -> float:
    values = [getattr(row, field) for row in rows if getattr(row, field) is not None]
    if not values:
        raise ValueError(f"no values for {field}")
    return float(mean(float(value) for value in values))


def _method_summary(rows: Sequence[IndependentValidationRow]) -> dict[str, float | int]:
    summary: dict[str, float | int] = {
        "runs": len(rows),
        "exact_recovery": _mean(rows, "exact_recovery"),
        "term_precision": _mean(rows, "term_precision"),
        "term_recall": _mean(rows, "term_recall"),
        "test_nmse": _mean(rows, "test_nmse"),
        "spurious_accepted": _mean(rows, "spurious_accepted"),
        "exception_recovered": _mean(rows, "exception_recovered"),
        "runtime_seconds_median": _median(rows, "runtime_seconds"),
        "communication_bytes_median": _median(rows, "communication_bytes"),
        "communication_per_client_median": _median(rows, "communication_per_client"),
    }
    if rows[0].method in V6_METHODS:
        summary.update(
            {
                "candidate_bank_target_recall": _mean_optional(rows, "candidate_bank_target_recall"),
                "candidate_bank_contains_all_truth": _mean_optional(rows, "candidate_bank_contains_all_truth"),
                "probe_certification_fraction": _mean_optional(rows, "probe_certified"),
                "candidate_sets_median": _median(rows, "candidate_sets_evaluated"),
            }
        )
    return summary


def summarize(
    rows: Sequence[IndependentValidationRow], *, evaluate_gate: bool = True
) -> dict[str, object]:
    if not rows:
        raise ValueError("cannot summarize empty independent study")

    condition_keys = {
        (
            row.panel,
            row.benchmark,
            row.scenario,
            row.noise_ratio,
            row.nominal_samples_per_client,
            row.num_clients,
            row.balance_profile,
            row.seed,
        )
        for row in rows
    }
    result: dict[str, object] = {
        "schema_version": 1,
        "status": "scsv-v6-independent-validation" if evaluate_gate else "scsv-v6-independent-smoke",
        "rows": len(rows),
        "conditions": len(condition_keys),
        "seeds": sorted({row.seed for row in rows}),
        "methods_present": sorted({row.method for row in rows}),
        "panels": {panel: sum(row.panel == panel for row in rows) for panel in sorted({row.panel for row in rows})},
    }

    if not evaluate_gate:
        result["independent_gate"] = {
            "evaluated": False,
            "passed": None,
            "scientific_boundary": "Engineering smoke cannot evaluate independent validation gates.",
        }
        return result

    if set(row.method for row in rows) != set(METHODS):
        raise ValueError("full independent evidence must contain exactly the six frozen methods")
    if len(rows) != 3540 or len(condition_keys) != 590:
        raise ValueError("full independent evidence must contain 3,540 rows and 590 conditions")

    panel_summaries: dict[str, object] = {}
    for panel in ("G", "S", "S32"):
        panel_rows = _subset(rows, panel=panel)
        panel_summaries[panel] = {
            method: _method_summary(_subset(panel_rows, method=method))
            for method in METHODS
        }
    result["panel_methods"] = panel_summaries

    g_full = _subset(rows, panel="G", method="scsv-v6-full")
    g_legacy = _subset(rows, panel="G", method="legacy-certificate")
    g_v5 = _subset(rows, panel="G", method="hr-v5-full")
    g_central = _subset(rows, panel="G", method="centralized-forward")
    g_spurious = _subset(g_full, scenario="spurious")
    g_legacy_spurious = _subset(g_legacy, scenario="spurious")
    g_exception = _subset(g_full, scenario="exception")

    s_full = _subset(rows, panel="S", method="scsv-v6-full")
    s_legacy = _subset(rows, panel="S", method="legacy-certificate")
    s32_full = _subset(rows, panel="S32", method="scsv-v6-full")

    exact_by_clients = {
        count: _mean(_subset(s_full, client_count=count), "exact_recovery")
        for count in (4, 8, 16)
    }
    legacy_exact_by_clients = {
        count: _mean(_subset(s_legacy, client_count=count), "exact_recovery")
        for count in (4, 8, 16)
    }
    exception_by_clients = {
        count: _mean(
            _subset(s_full, scenario="exception", client_count=count),
            "exception_recovered",
        )
        for count in (4, 8, 16)
    }
    comm_per_client = {
        count: _median(
            _subset(s_full, client_count=count), "communication_per_client"
        )
        for count in (4, 16)
    }
    runtime = {
        count: _median(_subset(s_full, client_count=count), "runtime_seconds")
        for count in (4, 16)
    }
    s_balanced = _subset(s_full, profile="balanced")
    s_imbalanced = _subset(s_full, profile="imbalanced")
    s32_exception = _subset(s32_full, scenario="exception")
    all_full = [row for row in rows if row.method == "scsv-v6-full"]

    values = {
        "panel_g_v6_exact": _mean(g_full, "exact_recovery"),
        "panel_g_legacy_exact": _mean(g_legacy, "exact_recovery"),
        "panel_g_v5_exact": _mean(g_v5, "exact_recovery"),
        "panel_g_centralized_exact": _mean(g_central, "exact_recovery"),
        "panel_g_precision": _mean(g_full, "term_precision"),
        "panel_g_recall": _mean(g_full, "term_recall"),
        "panel_g_v6_nmse": _mean(g_full, "test_nmse"),
        "panel_g_legacy_nmse": _mean(g_legacy, "test_nmse"),
        "panel_g_spurious_acceptance": _mean(g_spurious, "spurious_accepted"),
        "panel_g_legacy_spurious_acceptance": _mean(g_legacy_spurious, "spurious_accepted"),
        "panel_g_exception_recovery": _mean(g_exception, "exception_recovered"),
        "panel_g_bank_target_recall": _mean_optional(g_full, "candidate_bank_target_recall"),
        "panel_g_complete_bank": _mean_optional(g_full, "candidate_bank_contains_all_truth"),
        "panel_s_exact_by_clients": exact_by_clients,
        "panel_s_legacy_exact_by_clients": legacy_exact_by_clients,
        "panel_s_exception_by_clients": exception_by_clients,
        "panel_s_balanced_exact": _mean(s_balanced, "exact_recovery"),
        "panel_s_imbalanced_exact": _mean(s_imbalanced, "exact_recovery"),
        "panel_s_comm_per_client": comm_per_client,
        "panel_s_runtime": runtime,
        "panel_s32_exact": _mean(s32_full, "exact_recovery"),
        "panel_s32_exception_recovery": _mean(s32_exception, "exception_recovered"),
        "all_probe_certification": _mean_optional(all_full, "probe_certified"),
    }

    criteria = {
        "A_panel_g_exact_gt_legacy_005": values["panel_g_v6_exact"] >= values["panel_g_legacy_exact"] + 0.05,
        "B_panel_g_exact_gt_v5_010": values["panel_g_v6_exact"] >= values["panel_g_v5_exact"] + 0.10,
        "C_panel_g_within_005_centralized": values["panel_g_v6_exact"] >= values["panel_g_centralized_exact"] - 0.05,
        "D_panel_g_precision_ge_095": values["panel_g_precision"] >= 0.95,
        "E_panel_g_recall_ge_095": values["panel_g_recall"] >= 0.95,
        "F_panel_g_nmse_not_worse_legacy": values["panel_g_v6_nmse"] <= values["panel_g_legacy_nmse"],
        "G_panel_g_spurious_controlled": values["panel_g_spurious_acceptance"] <= max(0.05, values["panel_g_legacy_spurious_acceptance"] + 0.01),
        "H_panel_g_exception_ge_090": values["panel_g_exception_recovery"] >= 0.90,
        "I_panel_g_bank_recall_ge_098": values["panel_g_bank_target_recall"] >= 0.98,
        "J_panel_g_complete_bank_ge_095": values["panel_g_complete_bank"] >= 0.95,
        "K_panel_s_each_client_count_gt_legacy_003": all(exact_by_clients[count] >= legacy_exact_by_clients[count] + 0.03 for count in (4, 8, 16)),
        "L_panel_s_16_no_collapse": exact_by_clients[16] >= exact_by_clients[4] - 0.03,
        "M_panel_s_imbalance_robust": values["panel_s_imbalanced_exact"] >= values["panel_s_balanced_exact"] - 0.05,
        "N_panel_s_exception_each_count_ge_090": all(exception_by_clients[count] >= 0.90 for count in (4, 8, 16)),
        "O_panel_s_comm_per_client_scaling": comm_per_client[16] <= 1.50 * comm_per_client[4],
        "P_panel_s_runtime_scaling": runtime[16] <= 5.0 * runtime[4],
        "Q_panel_s32_structural_and_exception": values["panel_s32_exact"] >= 0.85 and values["panel_s32_exception_recovery"] >= 0.85,
        "R_probe_certification_ge_070": values["all_probe_certification"] >= 0.70,
    }
    result["gate_values"] = values
    result["independent_gate"] = {
        "evaluated": True,
        "criteria": criteria,
        "passed": bool(all(criteria.values())),
        "scientific_boundary": (
            "GO authorizes only the separately preserved external SRSD layer; "
            "NO-GO is retained without tuning on seeds 20101--20105."
        ),
    }
    return result


def write_csv(rows: Sequence[IndependentValidationRow], output: Path) -> None:
    if not rows:
        raise ValueError("cannot write empty independent validation")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--output", type=Path, default=Path("results/scsv_v6_independent/rows.csv")
    )
    parser.add_argument(
        "--summary", type=Path, default=Path("results/scsv_v6_independent/summary.json")
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = run_smoke() if args.smoke else run_independent_study()
    summary = summarize(rows, evaluate_gate=not args.smoke)
    write_csv(rows, args.output)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
