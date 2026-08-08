"""Frozen development matrix for role-conditioned dual-evidence FedFalsify v4."""

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
from .role_conditional import RoleConditionalOutput, role_conditional_method
from .role_conditional_report import summarize
from .stability_superset import StabilitySupersetOutput, stability_superset_method

SMOKE_SEED = 16001
DEVELOPMENT_SEEDS = tuple(range(16101, 16106))
METHODS = (
    "legacy-certificate",
    "crossfit-v2-structural",
    "stability-superset-v3",
    "role-v4-full",
    "role-v4-anchor",
    "role-v4-no-role-conditioning",
    "role-v4-no-path-persistence",
    "role-v4-no-backward",
    "centralized-forward",
    "score-only-federated",
)


@dataclass(frozen=True)
class RoleStudyRow(common.RedesignRow):
    candidate_pool_target_recall: float | None = None
    candidate_pool_contains_all_truth: float | None = None
    critical_term_recalled: float | None = None
    exception_candidate_recalled: float | None = None
    candidate_pool_size: int | None = None
    candidate_pool_nuisance_count: int | None = None
    forward_accepted_terms: int | None = None
    backward_deleted_terms: int | None = None


def _validate_seeds(
    seeds: Sequence[int], *, allow_engineering_smoke: bool
) -> None:
    allowed = set(DEVELOPMENT_SEEDS)
    if allow_engineering_smoke:
        allowed.add(SMOKE_SEED)
    if any(seed not in allowed for seed in seeds):
        raise ValueError(
            "use untouched v4 development seeds 16101--16105; "
            "16001 is engineering smoke only"
        )
    prohibited = (
        set(range(9001, 9021))
        | set(range(10001, 10006))
        | set(range(10501, 10506))
        | set(range(11001, 16001))
    )
    if any(seed in prohibited for seed in seeds):
        raise ValueError("prior, validation, final, or v1-v3 seeds are prohibited")


def _row(
    base: common.RedesignRow,
    requested_noise: float,
    extras: dict[str, object] | None = None,
) -> RoleStudyRow:
    payload = base.to_dict()
    payload["noise_ratio"] = float(requested_noise)
    payload.update(extras or {})
    return RoleStudyRow(**payload)


def _profile_extras(generated, output: RoleConditionalOutput) -> dict[str, object]:
    pool = set(output.candidate_profile.candidate_terms)
    truth = set(generated.target_terms)
    critical = {
        "poly3": "x1^3",
        "interaction": "x1*x2",
    }.get(generated.spec.name)
    exception = "I(x3>1)*x3^2"
    return {
        "candidate_pool_target_recall": (
            len(pool & truth) / len(truth) if truth else 1.0
        ),
        "candidate_pool_contains_all_truth": float(truth.issubset(pool)),
        "critical_term_recalled": (
            float(critical in pool) if critical is not None else None
        ),
        "exception_candidate_recalled": (
            float(exception in pool)
            if generated.scenario == "exception"
            else None
        ),
        "candidate_pool_size": len(pool),
        "candidate_pool_nuisance_count": len(pool - truth),
        "forward_accepted_terms": sum(
            item.accepted for item in output.forward_decisions
        ),
        "backward_deleted_terms": sum(
            not item.accepted for item in output.backward_decisions
        ),
    }


def _evaluate_v3(
    generated,
    output: StabilitySupersetOutput,
    *,
    seed: int,
) -> common.RedesignRow:
    profile_json = json.dumps(
        output.stability_profile.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )
    return common._evaluate_candidate(
        generated,
        output.candidate,
        method="stability-superset-v3",
        seed=seed,
        runtime_seconds=output.runtime_seconds,
        communication_bytes=output.communication_bytes,
        stop_reason=output.stop_reason + "; stability=" + profile_json,
        fallback_selected=output.continuation_selected,
        selected_source=output.selected_source,
        validation_mse=output.validation_profile.weighted_mse,
        worst_validation_mse=output.validation_profile.worst_client_mse,
    )


def _decision_payload(output: RoleConditionalOutput) -> str:
    payload = {
        "candidate_profile": output.candidate_profile.to_dict(),
        "forward": [item.to_dict() for item in output.forward_decisions],
        "backward": [item.to_dict() for item in output.backward_decisions],
        "probes": [item.to_dict() for item in output.probe_profiles],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _evaluate_role_candidate(
    generated,
    output: RoleConditionalOutput,
    *,
    method: str,
    seed: int,
    candidate_kind: str = "full",
) -> common.RedesignRow:
    if candidate_kind == "anchor":
        candidate = output.anchor_candidate
        runtime = output.anchor_runtime_seconds
        communication = output.anchor_communication_bytes
        profile = output.anchor_validation_profile
        fallback = False
        source = "v4-anchor"
    elif candidate_kind == "forward":
        candidate = output.forward_candidate
        runtime = output.forward_runtime_seconds
        communication = output.forward_communication_bytes
        profile = output.forward_validation_profile
        fallback = any(item.accepted for item in output.forward_decisions)
        source = "v4-forward-only"
    else:
        candidate = output.candidate
        runtime = output.runtime_seconds
        communication = output.communication_bytes
        profile = output.validation_profile
        fallback = any(item.accepted for item in output.forward_decisions)
        source = method
    return common._evaluate_candidate(
        generated,
        candidate,
        method=method,
        seed=seed,
        runtime_seconds=runtime,
        communication_bytes=communication,
        stop_reason=output.stop_reason + "; decisions=" + _decision_payload(output),
        fallback_selected=fallback,
        selected_source=source,
        validation_mse=profile.weighted_mse,
        worst_validation_mse=profile.worst_client_mse,
    )


def _evaluate_condition(
    generated,
    *,
    requested_noise: float,
    seed: int,
    methods: Sequence[str],
    max_terms: int,
) -> list[RoleStudyRow]:
    catalog = benchmark_catalog(scenario=generated.scenario)
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    requested = set(methods)

    v3_output = None
    if "stability-superset-v3" in requested:
        v3_output = stability_superset_method(
            generated.clients,
            catalog,
            seed=seed,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=0.05,
        )

    need_full = bool(
        {
            "role-v4-full",
            "role-v4-anchor",
            "role-v4-no-backward",
        }
        & requested
    )
    full_output = (
        role_conditional_method(
            generated.clients,
            catalog,
            seed=seed,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=0.05,
            role_conditioning=True,
            path_persistence=True,
            backward_audit=True,
        )
        if need_full
        else None
    )

    no_role_output = (
        role_conditional_method(
            generated.clients,
            catalog,
            seed=seed,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=0.05,
            role_conditioning=False,
            path_persistence=True,
            backward_audit=True,
        )
        if "role-v4-no-role-conditioning" in requested
        else None
    )
    no_path_output = (
        role_conditional_method(
            generated.clients,
            catalog,
            seed=seed,
            max_terms=max_terms,
            target_mse=target_mse,
            min_repair_score=0.05,
            role_conditioning=True,
            path_persistence=False,
            backward_audit=True,
        )
        if "role-v4-no-path-persistence" in requested
        else None
    )

    rows: list[RoleStudyRow] = []
    for method in methods:
        if method in {
            "legacy-certificate",
            "crossfit-v2-structural",
            "score-only-federated",
            "centralized-forward",
        }:
            rows.append(
                _row(
                    v2._evaluate(
                        generated, method, seed=seed, max_terms=max_terms
                    ),
                    requested_noise,
                )
            )
            continue
        if method == "stability-superset-v3":
            if v3_output is None:
                raise RuntimeError("v3 comparator was not generated")
            rows.append(
                _row(
                    _evaluate_v3(generated, v3_output, seed=seed),
                    requested_noise,
                )
            )
            continue
        if method in {"role-v4-full", "role-v4-anchor", "role-v4-no-backward"}:
            if full_output is None:
                raise RuntimeError("full v4 output was not generated")
            kind = (
                "anchor"
                if method == "role-v4-anchor"
                else "forward"
                if method == "role-v4-no-backward"
                else "full"
            )
            rows.append(
                _row(
                    _evaluate_role_candidate(
                        generated,
                        full_output,
                        method=method,
                        seed=seed,
                        candidate_kind=kind,
                    ),
                    requested_noise,
                    _profile_extras(generated, full_output),
                )
            )
            continue
        if method == "role-v4-no-role-conditioning":
            if no_role_output is None:
                raise RuntimeError("no-role v4 ablation was not generated")
            rows.append(
                _row(
                    _evaluate_role_candidate(
                        generated,
                        no_role_output,
                        method=method,
                        seed=seed,
                    ),
                    requested_noise,
                    _profile_extras(generated, no_role_output),
                )
            )
            continue
        if method == "role-v4-no-path-persistence":
            if no_path_output is None:
                raise RuntimeError("no-path v4 ablation was not generated")
            rows.append(
                _row(
                    _evaluate_role_candidate(
                        generated,
                        no_path_output,
                        method=method,
                        seed=seed,
                    ),
                    requested_noise,
                    _profile_extras(generated, no_path_output),
                )
            )
            continue
        raise KeyError(method)
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
) -> list[RoleStudyRow]:
    _validate_seeds(
        seeds, allow_engineering_smoke=allow_engineering_smoke
    )
    unknown = set(methods) - set(METHODS)
    if unknown:
        raise ValueError(f"unknown methods: {sorted(unknown)}")
    rows: list[RoleStudyRow] = []
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


def write_csv(rows: Sequence[RoleStudyRow], output: Path) -> None:
    if not rows:
        raise ValueError("cannot write an empty v4 study")
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
        default=Path("results/role_conditional_v4/rows.csv"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/role_conditional_v4/summary.json"),
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
            "samples_per_client": tuple(
                int(item) for item in _strings(args.samples)
            ),
            "seeds": tuple(int(item) for item in _strings(args.seeds)),
            "methods": _strings(args.methods),
            "max_terms": args.max_terms,
            "allow_engineering_smoke": False,
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
