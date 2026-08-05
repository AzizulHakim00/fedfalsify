"""Frozen v3 development matrix runner."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Sequence

from . import redesign_study as common
from . import surrogate_study as v2
from .benchmarks import BENCHMARKS, benchmark_catalog, generate_benchmark
from .stability_report import summarize
from .stability_superset import StabilitySupersetOutput, stability_superset_method

DEVELOPMENT_SEEDS = tuple(range(15001, 15006))
METHODS = (
    "legacy-certificate",
    "crossfit-v1-governed",
    "crossfit-v2-structural",
    "stability-superset-v3",
    "score-only-federated",
    "centralized-forward",
    "stability-v3-intersection",
)


@dataclass(frozen=True)
class StabilityStudyRow(common.RedesignRow):
    superset_target_recall: float | None = None
    superset_contains_all_truth: float | None = None
    critical_term_recalled: float | None = None
    stable_superset_size: int | None = None
    stable_superset_nuisance_count: int | None = None
    observability_floor: int | None = None


def _validate_seeds(seeds: Sequence[int]) -> None:
    if any(seed < 15001 or seed > 15999 for seed in seeds):
        raise ValueError("stability-superset seeds must be in 15001--15999")
    spent = (
        set(range(9001, 9021))
        | set(range(10501, 10506))
        | set(range(11001, 15001))
    )
    if any(seed in spent for seed in seeds):
        raise ValueError("spent or final-confirmation seeds are prohibited")


def _row(
    base: common.RedesignRow,
    requested_noise: float,
    extras: dict[str, object] | None = None,
) -> StabilityStudyRow:
    payload = base.to_dict()
    payload["noise_ratio"] = float(requested_noise)
    payload.update(extras or {})
    return StabilityStudyRow(**payload)


def _extras(generated, output: StabilitySupersetOutput) -> dict[str, object]:
    stable, target = (
        set(output.stability_profile.stable_terms),
        set(generated.target_terms),
    )
    critical = {
        "poly3": "x1^3",
        "interaction": "x1*x2",
    }.get(generated.spec.name)
    return {
        "superset_target_recall": (
            len(stable & target) / len(target) if target else 1.0
        ),
        "superset_contains_all_truth": float(target.issubset(stable)),
        "critical_term_recalled": (
            float(critical in stable) if critical is not None else None
        ),
        "stable_superset_size": len(stable),
        "stable_superset_nuisance_count": len(stable - target),
        "observability_floor": min(
            output.stability_profile.observability_floors
        ),
    }


def _v3_row(
    generated,
    output: StabilitySupersetOutput,
    *,
    method: str,
    seed: int,
) -> common.RedesignRow:
    if method == "stability-superset-v3":
        return common._evaluate_candidate(
            generated,
            output.candidate,
            method=method,
            seed=seed,
            runtime_seconds=output.runtime_seconds,
            communication_bytes=output.communication_bytes,
            stop_reason=(
                output.stop_reason
                + "; stability="
                + json.dumps(
                    output.stability_profile.to_dict(),
                    sort_keys=True,
                    separators=(",", ":"),
                )
            ),
            fallback_selected=output.continuation_selected,
            selected_source=output.selected_source,
            validation_mse=output.validation_profile.weighted_mse,
            worst_validation_mse=(
                output.validation_profile.worst_client_mse
            ),
        )
    intersection = next(
        item
        for item in output.validation_profiles
        if item.source == "stability-intersection"
    )
    return common._evaluate_candidate(
        generated,
        output.intersection_candidate,
        method=method,
        seed=seed,
        runtime_seconds=output.intersection_runtime_seconds,
        communication_bytes=output.intersection_communication_bytes,
        stop_reason="paired audit of v3 five-fold strict intersection",
        fallback_selected=False,
        selected_source="stability-intersection",
        validation_mse=intersection.weighted_mse,
        worst_validation_mse=intersection.worst_client_mse,
    )


def _evaluate_condition(
    generated,
    *,
    requested_noise: float,
    seed: int,
    methods: Sequence[str],
    max_terms: int,
) -> list[StabilityStudyRow]:
    catalog = benchmark_catalog(scenario=generated.scenario)
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    need_v3 = bool(
        {"stability-superset-v3", "stability-v3-intersection"} & set(methods)
    )
    output = (
        stability_superset_method(
            generated.clients,
            catalog,
            seed=seed,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=0.05,
        )
        if need_v3
        else None
    )
    rows = []
    for method in methods:
        if method in METHODS[:3] + METHODS[4:6]:
            rows.append(
                _row(
                    v2._evaluate(
                        generated, method, seed=seed, max_terms=max_terms
                    ),
                    requested_noise,
                )
            )
        else:
            if output is None:
                raise RuntimeError("v3 output was not generated")
            rows.append(
                _row(
                    _v3_row(
                        generated, output, method=method, seed=seed
                    ),
                    requested_noise,
                    _extras(generated, output),
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
) -> list[StabilityStudyRow]:
    _validate_seeds(seeds)
    unknown = set(methods) - set(METHODS)
    if unknown:
        raise ValueError(f"unknown methods: {sorted(unknown)}")
    rows = []
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


def write_csv(rows: Sequence[StabilityStudyRow], output: Path) -> None:
    if not rows:
        raise ValueError("cannot write an empty study")
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
    parser.add_argument(
        "--scenarios", default="complementary,spurious,exception"
    )
    parser.add_argument("--noise", default="0.03,0.10,0.20")
    parser.add_argument("--samples", default="120,300")
    parser.add_argument(
        "--seeds", default=",".join(map(str, DEVELOPMENT_SEEDS))
    )
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--max-terms", type=int, default=6)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/stability_superset_v3/rows.csv"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/stability_superset_v3/summary.json"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = (
        {
            "benchmarks": ("poly3", "interaction"),
            "scenarios": ("complementary",),
            "noise_ratios": (0.20,),
            "samples_per_client": (120,),
            "seeds": (15001,),
            "methods": METHODS,
            "max_terms": args.max_terms,
        }
        if args.smoke
        else {
            "benchmarks": _strings(args.benchmarks),
            "scenarios": _strings(args.scenarios),
            "noise_ratios": tuple(
                float(item) for item in _strings(args.noise)
            ),
            "samples_per_client": tuple(
                int(item) for item in _strings(args.samples)
            ),
            "seeds": tuple(int(item) for item in _strings(args.seeds)),
            "methods": _strings(args.methods),
            "max_terms": args.max_terms,
        }
    )
    rows = run_study(**settings)
    write_csv(rows, args.output)
    summary = summarize(rows)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    print(
        f"Wrote {len(rows)} rows; "
        f"gate={summary['development_gate']['passed']}"
    )


if __name__ == "__main__":
    main()
