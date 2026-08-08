"""Post-hoc forensic decomposition of the sealed RC-DES v4 development evidence.

This module does not create new statistical evidence and must not modify the
frozen v4 gate. It classifies where truth terms were lost in the already-sealed
4,500-row matrix and compares preregistered ablations condition-by-condition.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from .benchmarks import generate_benchmark

KEY = ("benchmark", "scenario", "noise_ratio", "samples_per_client", "seed")
EXPECTED_METHODS = {
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
}
EXPECTED_SEEDS = {16101, 16102, 16103, 16104, 16105}
DECISION_MARKER = "; decisions="


def _f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def _terms(value: str) -> set[str]:
    return {item for item in value.split(";") if item}


def _parse_decisions(stop_reason: str) -> dict[str, object]:
    if DECISION_MARKER not in stop_reason:
        raise ValueError("v4 row lacks decision payload")
    return json.loads(stop_reason.split(DECISION_MARKER, 1)[1])


def _prefix_terms(stop_reason: str, name: str) -> set[str]:
    prefix = stop_reason.split(DECISION_MARKER, 1)[0]
    match = re.search(rf"(?:^|; ){re.escape(name)}=([^;]*)", prefix)
    if not match:
        return set()
    return {item for item in match.group(1).split(",") if item and item != "1"}


def _truth_terms(row: dict[str, str]) -> set[str]:
    generated = generate_benchmark(
        row["benchmark"],
        scenario=row["scenario"],
        samples_per_client=int(row["samples_per_client"]),
        noise_ratio=float(row["noise_ratio"]),
        seed=int(row["seed"]),
        num_clients=int(row["num_clients"]),
    )
    return set(generated.target_terms)


def _exact_binomial_two_sided(success_a_only: int, success_b_only: int) -> float:
    n = success_a_only + success_b_only
    if n == 0:
        return 1.0
    k = min(success_a_only, success_b_only)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def _paired(rows_by_method, a: str, b: str) -> dict[str, object]:
    a_rows = rows_by_method[a]
    b_rows = rows_by_method[b]
    wins = losses = ties = 0
    for key in sorted(a_rows):
        av = int(float(a_rows[key]["exact_recovery"]) > 0.5)
        bv = int(float(b_rows[key]["exact_recovery"]) > 0.5)
        if av > bv:
            wins += 1
        elif av < bv:
            losses += 1
        else:
            ties += 1
    return {
        "a": a,
        "b": b,
        "a_only_exact": wins,
        "b_only_exact": losses,
        "ties": ties,
        "exact_rate_delta": mean(float(r["exact_recovery"]) for r in a_rows.values())
        - mean(float(r["exact_recovery"]) for r in b_rows.values()),
        "mcnemar_exact_p_posthoc": _exact_binomial_two_sided(wins, losses),
    }


def _classify_truth_term(
    term: str,
    *,
    row: dict[str, str],
    payload: dict[str, object],
) -> str:
    profile = payload["candidate_profile"]
    pool = set(profile["candidate_terms"])
    anchor = _prefix_terms(row["stop_reason"], "anchor")
    forward_active = _prefix_terms(row["stop_reason"], "forward")
    final_active = _prefix_terms(row["stop_reason"], "final")
    discovered = _terms(row["discovered_terms"])

    if term in discovered:
        return "retained_truth"
    if term not in pool and term not in anchor:
        return "candidate_bank_miss"
    if term in anchor:
        if term not in forward_active:
            return "lost_before_forward_snapshot"
        if term not in final_active:
            return "backward_removed_anchor_truth"
        return "coefficient_threshold_loss"

    decisions = {item["term"]: item for item in payload["forward"]}
    decision = decisions.get(term)
    if decision is None:
        return "candidate_present_not_attempted"
    if not decision["selector_passed"]:
        return "selector_rejected_truth"
    if not decision["probe_passed"]:
        return "structural_probe_rejected_truth"
    if not decision["accepted"]:
        return "forward_rejected_other"
    if term not in final_active:
        return "backward_removed_forward_truth"
    return "coefficient_threshold_loss"


def analyze(rows: list[dict[str, str]]) -> dict[str, object]:
    if len(rows) != 4500:
        raise ValueError(f"expected 4500 rows, found {len(rows)}")

    rows_by_method: dict[str, dict[tuple[str, ...], dict[str, str]]] = defaultdict(dict)
    for row in rows:
        if int(row["seed"]) not in EXPECTED_SEEDS:
            raise ValueError("unexpected seed in sealed v4 evidence")
        key = tuple(row[field] for field in KEY)
        if key in rows_by_method[row["method"]]:
            raise ValueError(f"duplicate method-condition row: {row['method']} {key}")
        rows_by_method[row["method"]][key] = row

    if set(rows_by_method) != EXPECTED_METHODS:
        raise ValueError(
            f"method mismatch: missing={sorted(EXPECTED_METHODS-set(rows_by_method))}; "
            f"extra={sorted(set(rows_by_method)-EXPECTED_METHODS)}"
        )
    condition_counts = {method: len(items) for method, items in rows_by_method.items()}
    if any(count != 450 for count in condition_counts.values()):
        raise ValueError(f"expected 450 conditions/method, got {condition_counts}")

    full_rows = rows_by_method["role-v4-full"]
    failure_stage = Counter()
    term_stage = Counter()
    nuisance_count = Counter()
    benchmark_failure = Counter()
    noise_failure = Counter()
    scenario_failure = Counter()
    truth_opportunities = 0
    truth_missing = 0

    for row in full_rows.values():
        truth = _truth_terms(row)
        discovered = _terms(row["discovered_terms"])
        payload = _parse_decisions(row["stop_reason"])
        truth_opportunities += len(truth)
        missing = truth - discovered
        truth_missing += len(missing)
        for term in sorted(missing):
            stage = _classify_truth_term(term, row=row, payload=payload)
            failure_stage[stage] += 1
            term_stage[(term, stage)] += 1

        extra = discovered - truth
        if extra:
            nuisance_count["conditions_with_nuisance"] += 1
            nuisance_count["nuisance_terms"] += len(extra)

        if float(row["exact_recovery"]) < 0.5:
            benchmark_failure[row["benchmark"]] += 1
            scenario_failure[row["scenario"]] += 1
            noise_failure[row["noise_ratio"]] += 1

    full_payloads = [_parse_decisions(row["stop_reason"]) for row in full_rows.values()]
    forward = Counter()
    backward = Counter()
    rejection_reasons = Counter()
    probe_reasons = Counter()
    for payload in full_payloads:
        for item in payload["forward"]:
            forward["attempted"] += 1
            forward["selector_passed"] += int(bool(item["selector_passed"]))
            forward["probe_passed"] += int(bool(item["probe_passed"]))
            forward["accepted"] += int(bool(item["accepted"]))
            if not item["selector_passed"]:
                rejection_reasons[item["selector_reason"]] += 1
            elif not item["probe_passed"]:
                probe_reasons[item["probe_reason"]] += 1
        for item in payload["backward"]:
            backward["tested"] += 1
            backward["retained"] += int(bool(item["accepted"]))
            backward["deleted"] += int(not bool(item["accepted"]))

    methods = {}
    for method, mapping in rows_by_method.items():
        vals = list(mapping.values())
        methods[method] = {
            "exact_recovery": mean(_f(r, "exact_recovery") for r in vals),
            "term_precision": mean(_f(r, "term_precision") for r in vals),
            "term_recall": mean(_f(r, "term_recall") for r in vals),
            "test_nmse": mean(_f(r, "test_nmse") for r in vals),
            "spurious_accepted": mean(_f(r, "spurious_accepted") for r in vals),
            "exception_recovered": mean(_f(r, "exception_recovered") for r in vals),
        }

    paired = [
        _paired(rows_by_method, "role-v4-no-backward", "role-v4-full"),
        _paired(rows_by_method, "role-v4-no-backward", "legacy-certificate"),
        _paired(rows_by_method, "role-v4-no-backward", "crossfit-v2-structural"),
        _paired(rows_by_method, "role-v4-no-backward", "stability-superset-v3"),
        _paired(rows_by_method, "role-v4-full", "role-v4-no-role-conditioning"),
        _paired(rows_by_method, "role-v4-full", "role-v4-no-path-persistence"),
    ]

    by_benchmark_no_backward = {}
    nb = rows_by_method["role-v4-no-backward"]
    legacy = rows_by_method["legacy-certificate"]
    for benchmark in sorted({key[0] for key in nb}):
        keys = [key for key in nb if key[0] == benchmark]
        by_benchmark_no_backward[benchmark] = {
            "conditions": len(keys),
            "v4_no_backward_exact": mean(_f(nb[key], "exact_recovery") for key in keys),
            "legacy_exact": mean(_f(legacy[key], "exact_recovery") for key in keys),
            "v4_no_backward_nmse": mean(_f(nb[key], "test_nmse") for key in keys),
            "legacy_nmse": mean(_f(legacy[key], "test_nmse") for key in keys),
        }

    term_breakdown = {}
    for (term, stage), count in sorted(term_stage.items()):
        term_breakdown.setdefault(term, {})[stage] = count

    return {
        "analysis_status": "POST_HOC_DIAGNOSTIC_ONLY",
        "evidence_rows": len(rows),
        "conditions_per_method": condition_counts,
        "seeds": sorted(EXPECTED_SEEDS),
        "methods": methods,
        "paired_exact_comparisons": paired,
        "v4_full_failure_decomposition": {
            "truth_term_opportunities": truth_opportunities,
            "missing_truth_terms": truth_missing,
            "missing_truth_stage_counts": dict(failure_stage),
            "missing_truth_by_term_and_stage": term_breakdown,
            "conditions_with_nuisance": nuisance_count["conditions_with_nuisance"],
            "nuisance_terms_total": nuisance_count["nuisance_terms"],
            "failed_conditions_by_benchmark": dict(benchmark_failure),
            "failed_conditions_by_scenario": dict(scenario_failure),
            "failed_conditions_by_noise": dict(noise_failure),
        },
        "decision_mechanism_counts": {
            "forward": dict(forward),
            "backward": dict(backward),
            "selector_rejection_reasons": dict(rejection_reasons.most_common()),
            "probe_rejection_reasons": dict(probe_reasons.most_common()),
        },
        "v4_no_backward_by_benchmark": by_benchmark_no_backward,
        "interpretation_boundary": (
            "These statistics reuse the spent v4 development matrix and are post-hoc "
            "mechanism diagnostics. They must not be represented as preregistered "
            "confirmatory evidence or used to retune v4."
        ),
    }


def render_markdown(summary: dict[str, object]) -> str:
    methods = summary["methods"]
    decomp = summary["v4_full_failure_decomposition"]
    lines = [
        "# RC-DES v4 Post-hoc Failure Forensics",
        "",
        "> Status: **diagnostic only**. This report reuses the sealed v4 development matrix. It creates no new evidence, changes no v4 threshold, and does not reopen the v4 NO-GO decision.",
        "",
        "## Evidence integrity",
        "",
        f"- Rows: **{summary['evidence_rows']}**.",
        f"- Seeds: `{', '.join(map(str, summary['seeds']))}`.",
        "- Ten preregistered methods, 450 matched conditions per method.",
        "",
        "## Method snapshot",
        "",
        "| Method | Exact | Recall | Precision | NMSE | Exception | Spurious |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    order = [
        "centralized-forward", "legacy-certificate", "crossfit-v2-structural",
        "stability-superset-v3", "role-v4-no-backward", "role-v4-full",
        "role-v4-no-path-persistence", "role-v4-no-role-conditioning",
        "role-v4-anchor", "score-only-federated",
    ]
    for method in order:
        item = methods[method]
        lines.append(
            f"| {method} | {item['exact_recovery']:.4f} | {item['term_recall']:.4f} | "
            f"{item['term_precision']:.4f} | {item['test_nmse']:.6g} | "
            f"{item['exception_recovered']:.4f} | {item['spurious_accepted']:.4f} |"
        )

    lines += [
        "", "## Where true terms were lost", "",
        f"Across {decomp['truth_term_opportunities']} truth-term opportunities, {decomp['missing_truth_terms']} were absent from the final thresholded support.",
        "", "| Failure stage | Missing truth terms |", "|---|---:|",
    ]
    for stage, count in sorted(decomp["missing_truth_stage_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {stage} | {count} |")

    lines += ["", "## Term-specific failure map", "", "| Truth term | Stage counts |", "|---|---|"]
    for term, counts in sorted(decomp["missing_truth_by_term_and_stage"].items()):
        detail = ", ".join(f"{stage}={count}" for stage, count in sorted(counts.items()))
        lines.append(f"| `{term}` | {detail} |")

    lines += [
        "", "## Paired ablation diagnosis", "",
        "| A | B | A-only exact | B-only exact | Δ exact | post-hoc McNemar p |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for item in summary["paired_exact_comparisons"]:
        lines.append(
            f"| {item['a']} | {item['b']} | {item['a_only_exact']} | {item['b_only_exact']} | "
            f"{item['exact_rate_delta']:+.4f} | {item['mcnemar_exact_p_posthoc']:.3g} |"
        )

    lines += [
        "", "## Mechanism conclusion", "",
        "1. **Backward pruning is rejected for continuation.** The preregistered v4 gate already showed 49 exact harms and zero exact gains. The paired ablation is therefore treated as mechanistic support for a forward-only successor, not as permission to retune v4.",
        "2. **Candidate completeness remains the primary target.** A successor must expose more plausible truth terms before the independent selector/probe gates, especially correlated polynomial siblings and restricted-domain exceptions.",
        "3. **Role conditioning and path persistence are retained as hypotheses.** They are not claimed as independently confirmed contributions from this post-hoc report.",
        "4. **Score-only search may propose but never decide structure.** Its very high recall and low NMSE coexist with poor exact recovery and high spurious acceptance.",
        "5. **No final-seed work is authorized.** Any successor requires a new frozen protocol and fresh development seeds.",
        "", "## Scientific boundary", "", summary["interpretation_boundary"], "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path, default=Path("results/role_conditional_v4/rows.csv"))
    parser.add_argument("--json", type=Path, default=Path("results/role_conditional_v4/forensics.json"))
    parser.add_argument("--markdown", type=Path, default=Path("research/TRANSACTIONS_ROLE_CONDITIONAL_V4_FORENSICS.md"))
    args = parser.parse_args()

    with args.rows.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    summary = analyze(rows)

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    args.markdown.write_text(render_markdown(summary), encoding="utf-8")
    print(
        "v4 forensic analysis complete: "
        f"{summary['evidence_rows']} rows; missing_truth_terms="
        f"{summary['v4_full_failure_decomposition']['missing_truth_terms']}"
    )


if __name__ == "__main__":
    main()
