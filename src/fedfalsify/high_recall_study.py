"""Frozen v5 HR-VFS development matrix and smoke runner."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Sequence

from . import redesign_study as common
from . import role_conditional_study as v4
from .benchmarks import BENCHMARKS, benchmark_catalog, generate_benchmark
from .high_recall_forward import HighRecallOutput, high_recall_forward_method
from .high_recall_report import summarize

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
COMPARATOR_METHODS = tuple(method for method in METHODS if method not in V5_METHODS)


@dataclass(frozen=True)
class HighRecallStudyRow(v4.RoleStudyRow):
    candidate_bank_contains_all_truth: float | None = None
    single_forward_accepted: int | None = None
    pair_bundles_attempted: int | None = None
    pair_bundles_accepted: int | None = None
    single_exact_harms: int | None = None
    pair_exact_harms: int | None = None


def _validate_seeds(seeds: Sequence[int], *, allow_engineering_smoke: bool) -> None:
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
    )
    if any(seed in spent for seed in seeds):
        raise ValueError("prior, validation, final, or v1-v4 seeds are prohibited")


def _exact_terms(terms, truth) -> bool:
    return (set(terms) - {"1"}) == set(truth)


def _decision_harms(output: HighRecallOutput, truth: Sequence[str]) -> tuple[int, int]:
    single = sum(
        item.accepted
        and _exact_terms(item.before_terms, truth)
        and not _exact_terms(item.after_terms, truth)
        for item in output.single_decisions
    )
    pair = sum(
        item.accepted
        and _exact_terms(item.before_terms, truth)
        and not _exact_terms(item.after_terms, truth)
        for item in output.pair_decisions
    )
    return int(single), int(pair)


def _extras(generated, output: HighRecallOutput) -> dict[str, object]:
    bank = set(output.profile.candidate_terms)
    truth = set(generated.target_terms)
    exception = "I(x3>1)*x3^2"
    single_harms, pair_harms = _decision_harms(output, generated.target_terms)
    critical = {"poly3": "x1^3", "interaction": "x1*x2"}.get(generated.spec.name)
    return {
        "candidate_pool_target_recall": len(bank & truth) / len(truth) if truth else 1.0,
        "candidate_pool_contains_all_truth": float(truth.issubset(bank)),
        "critical_term_recalled": float(critical in bank) if critical else None,
        "exception_candidate_recalled": (
            float(exception in bank) if generated.scenario == "exception" else None
        ),
        "candidate_pool_size": len(bank),
        "candidate_pool_nuisance_count": len(bank - truth),
        "forward_accepted_terms": sum(item.accepted for item in output.single_decisions),
        "backward_deleted_terms": 0,
        "candidate_bank_contains_all_truth": float(truth.issubset(bank)),
        "single_forward_accepted": sum(item.accepted for item in output.single_decisions),
        "pair_bundles_attempted": len(output.pair_decisions),
        "pair_bundles_accepted": sum(item.accepted for item in output.pair_decisions),
        "single_exact_harms": single_harms,
        "pair_exact_harms": pair_harms,
    }


def _evaluate_v5(generated, output: HighRecallOutput, method: str, seed: int):
    payload = {
        "profile": output.profile.to_dict(),
        "single_decisions": [item.to_dict() for item in output.single_decisions],
        "pair_decisions": [item.to_dict() for item in output.pair_decisions],
    }
    base = common._evaluate_candidate(
        generated,
        output.candidate,
        method=method,
        seed=seed,
        runtime_seconds=output.runtime_seconds,
        communication_bytes=output.communication_bytes,
        stop_reason=output.stop_reason + "; v5=" + json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ),
        fallback_selected=any(item.accepted for item in output.single_decisions)
        or any(item.accepted for item in output.pair_decisions),
        selected_source=method,
        validation_mse=output.validation_profile.weighted_mse,
        worst_validation_mse=output.validation_profile.worst_client_mse,
    )
    values = base.to_dict()
    values.update(_extras(generated, output))
    return HighRecallStudyRow(**values)


def _v5_output(generated, method: str, *, seed: int, max_terms: int) -> HighRecallOutput:
    catalog = benchmark_catalog(scenario=generated.scenario)
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    return high_recall_forward_method(
        generated.clients,
        catalog,
        seed=seed,
        max_terms=max_terms,
        target_mse=target_mse,
        min_repair_score=0.05,
        use_bundle_rescue=method != "hr-v5-no-bundle-rescue",
        use_score_proposer=method != "hr-v5-no-score-proposer",
        role_conditioning=method != "hr-v5-no-role-conditioning",
    )


def _coerce_comparator(row) -> HighRecallStudyRow:
    return HighRecallStudyRow(**asdict(row))


def _evaluate_condition(
    generated,
    *,
    requested_noise: float,
    seed: int,
    methods: Sequence[str],
    max_terms: int,
) -> list[HighRecallStudyRow]:
    rows: list[HighRecallStudyRow] = []
    comparator = [method for method in methods if method in COMPARATOR_METHODS]
    if comparator:
        for row in v4._evaluate_condition(
            generated,
            requested_noise=requested_noise,
            seed=seed,
            methods=comparator,
            max_terms=max_terms,
        ):
            rows.append(_coerce_comparator(row))
    for method in methods:
        if method not in V5_METHODS:
            continue
        output = _v5_output(generated, method, seed=seed, max_terms=max_terms)
        row = _evaluate_v5(generated, output, method, seed)
        values = row.to_dict()
        values["noise_ratio"] = float(requested_noise)
        rows.append(HighRecallStudyRow(**values))
    order = {method: index for index, method in enumerate(methods)}
    rows.sort(key=lambda row: order[row.method])
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
) -> list[HighRecallStudyRow]:
    _validate_seeds(seeds, allow_engineering_smoke=allow_engineering_smoke)
    unknown = set(methods) - set(METHODS)
    if unknown:
        raise ValueError(f"unknown v5 methods: {sorted(unknown)}")
    rows: list[HighRecallStudyRow] = []
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


def _write_csv(path: Path, rows: Sequence[HighRecallStudyRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("no v5 rows")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].to_dict()))
        writer.writeheader()
        writer.writerows(row.to_dict() for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("results/high_recall_v5"))
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.smoke:
        rows = run_study(
            benchmarks=("poly3",),
            scenarios=("complementary",),
            noise_ratios=(0.20,),
            samples_per_client=(120,),
            seeds=(SMOKE_SEED,),
            methods=(
                "role-v4-no-backward",
                "hr-v5-full",
                "hr-v5-no-bundle-rescue",
                "hr-v5-no-score-proposer",
                "hr-v5-no-role-conditioning",
            ),
            allow_engineering_smoke=True,
        )
        decision = {"engineering_smoke": True, "development_gate_evaluated": False}
    else:
        rows = run_study()
        decision = summarize(rows)
    args.output.mkdir(parents=True, exist_ok=True)
    _write_csv(args.output / "rows.csv", rows)
    (args.output / "summary.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
