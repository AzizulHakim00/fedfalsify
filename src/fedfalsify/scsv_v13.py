"""FedFalsify Phase-3D / v13 deterministic scope-contrast fixture methods.

This module is intentionally additive: frozen v11/v12 files are not modified.
Phase-3D is a zero-new-scientific-seed architectural proof.  Its deterministic
fixtures ask whether a shared source and a client-scope coefficient shift of
that same source can coexist and be independently certified.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Iterable, Sequence

import numpy as np

from .linear_algebra import fit_from_sufficient_stats
from .multiple_testing import holm_adjust
from .nested_tests import partial_nested_f
from .phase3d_fixtures import Phase3DFixture, split_fixture_clients
from .scope_contrast_v13 import (
    FrozenScopeHypothesis,
    ScopeContrastRejection,
    discover_scope_contrast,
    scope_contrast_test,
)
from .scsv_v10_benchmarks import v10_catalog
from .scsv_v11 import scsv_elrc_v11_method
from .scsv_v12 import run_scsv_v12_branches
from .sufficient_stats import SufficientStatsPacket, aggregate_packets, sse_from_packet

PHASE3D_MODELS = (
    "v11-frozen",
    "v12-frozen",
    "scope-contrast-only",
    "v13-full",
)

SHARED_ALPHA = 0.05
PROBE_ALPHA = 0.05
MAX_NONINTERCEPT_SHARED = 5
MAX_LOCALIZED = 2
MAX_FINAL_TERMS = 10

# Frozen comparators require an integer partition seed.  Phase-3D does not use
# a scientific benchmark seed: its fixture inputs are deterministic.  The
# outer-fold identifier is used only as a reproducible technical split seed
# when invoking predecessor code that requires one.
TECHNICAL_PARTITION_SEED_BASE = 0


@dataclass(frozen=True)
class Phase3DModelResult:
    method: str
    fixture: str
    outer_fold: int
    shared_structure: tuple[str, ...]
    accepted_localized: tuple[str, ...]
    localized_scopes: tuple[tuple[str, tuple[str, ...]], ...]
    exact_shared: bool
    exact_localized: bool
    exact_scope: bool
    exact_structure: bool
    diagnostics: tuple[dict[str, object], ...]
    communication_bytes: int
    runtime_seconds: float
    stop_reason: str
    execution_error: str | None = None

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["shared_structure"] = list(self.shared_structure)
        payload["accepted_localized"] = list(self.accepted_localized)
        payload["localized_scopes"] = [
            [term, list(client_ids)] for term, client_ids in self.localized_scopes
        ]
        payload["diagnostics"] = [dict(item) for item in self.diagnostics]
        return payload


def _truth_scope_map(fixture: Phase3DFixture) -> dict[str, tuple[str, ...]]:
    return {term: tuple(client_ids) for term, client_ids in fixture.truth_scopes}


def _evaluate_exactness(
    fixture: Phase3DFixture,
    shared_structure: Sequence[str],
    accepted_localized: Sequence[str],
    localized_scopes: Sequence[tuple[str, tuple[str, ...]]],
) -> tuple[bool, bool, bool, bool]:
    shared_ok = set(shared_structure) == set(fixture.true_shared_terms)
    localized_ok = set(accepted_localized) == set(fixture.true_localized_terms)
    predicted_scope = {term: tuple(ids) for term, ids in localized_scopes}
    truth_scope = _truth_scope_map(fixture)
    scope_ok = predicted_scope == truth_scope
    return shared_ok, localized_ok, scope_ok, bool(shared_ok and localized_ok and scope_ok)


def _ordered_localized(
    fixture: Phase3DFixture,
    terms: Iterable[str],
) -> tuple[str, ...]:
    selected = set(terms)
    return tuple(term for term in fixture.localized_candidates if term in selected)


def _ordered_shared(fixture: Phase3DFixture, terms: Iterable[str]) -> tuple[str, ...]:
    selected = set(terms)
    ordered = tuple(term for term in fixture.candidate_shared_terms if term in selected)
    if "1" not in ordered:
        ordered = ("1",) + ordered
    return ordered


def _scope_rows(
    hypotheses: Sequence[FrozenScopeHypothesis],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple(
        (hypothesis.localized_term, tuple(hypothesis.role_client_ids))
        for hypothesis in hypotheses
    )


def _discovery_hypotheses(
    fixture: Phase3DFixture,
    discovery_clients: Sequence[object],
    shared_terms: tuple[str, ...],
) -> tuple[tuple[FrozenScopeHypothesis, ...], tuple[dict[str, object], ...]]:
    catalog = v10_catalog()
    hypotheses: list[FrozenScopeHypothesis] = []
    diagnostics: list[dict[str, object]] = []
    for localized_term in fixture.localized_candidates:
        source = catalog.get(localized_term).source_term
        if source is None or source not in set(shared_terms):
            diagnostics.append(
                {
                    "stage": "discovery",
                    "localized_term": localized_term,
                    "source_term": source,
                    "accepted": False,
                    "reason": "SOURCE-NOT-PROTECTED",
                }
            )
            continue
        result = discover_scope_contrast(
            fixture,
            discovery_clients,
            catalog,
            shared_terms=shared_terms,
            localized_term=localized_term,
            source_term=source,
        )
        if isinstance(result, FrozenScopeHypothesis):
            hypotheses.append(result)
            diagnostics.append(
                {
                    "stage": "discovery",
                    "localized_term": localized_term,
                    "source_term": source,
                    "accepted": True,
                    "reason": "DISCOVERY-SCOPE-FROZEN",
                    "role_client_ids": list(result.role_client_ids),
                    "outside_client_ids": list(result.outside_client_ids),
                    "discovery_sign": int(result.discovery_sign),
                    "p_value": float(result.discovery_result.p_value),
                    "bh_adjusted_value": float(result.bh_adjusted_value),
                    "full_sse": float(result.discovery_result.full_sse),
                    "tested_scope_count": int(result.tested_scope_count),
                }
            )
        else:
            assert isinstance(result, ScopeContrastRejection)
            diagnostics.append(
                {
                    "stage": "discovery",
                    "localized_term": localized_term,
                    "source_term": source,
                    "accepted": False,
                    "reason": result.reason,
                    "tested_scope_count": int(result.tested_scope_count),
                }
            )
    return tuple(hypotheses), tuple(diagnostics)


def _independent_scope_screen(
    clients: Sequence[object],
    shared_terms: tuple[str, ...],
    hypotheses: Sequence[FrozenScopeHypothesis],
    *,
    stage: str,
    alpha: float,
) -> tuple[tuple[FrozenScopeHypothesis, ...], tuple[dict[str, object], ...]]:
    """Screen frozen scope identities without creating or changing a role."""
    catalog = v10_catalog()
    hypotheses = tuple(hypotheses)
    if not hypotheses:
        return (), ()

    results = [
        scope_contrast_test(
            clients,
            catalog,
            shared_terms=shared_terms,
            source_term=hypothesis.source_term,
            role_indices=hypothesis.role_indices,
        )
        for hypothesis in hypotheses
    ]
    names = tuple(hypothesis.localized_term for hypothesis in hypotheses)
    p_values = tuple(
        float(result.p_value) if result.admissible and result.p_value is not None else 1.0
        for result in results
    )
    holm = holm_adjust(names, p_values, alpha=alpha)
    adjusted = dict(zip(holm.names, holm.adjusted_values))
    rejected = set(holm.rejected)

    survivors: list[FrozenScopeHypothesis] = []
    diagnostics: list[dict[str, object]] = []
    for hypothesis, result in zip(hypotheses, results):
        sign_ok = bool(result.candidate_sign == hypothesis.discovery_sign != 0)
        accepted = bool(
            result.admissible
            and hypothesis.localized_term in rejected
            and sign_ok
            and result.raw_gain > 0.0
        )
        if accepted:
            survivors.append(hypothesis)
        diagnostics.append(
            {
                "stage": stage,
                "localized_term": hypothesis.localized_term,
                "source_term": hypothesis.source_term,
                "role_client_ids": list(hypothesis.role_client_ids),
                "admissible": bool(result.admissible),
                "reason": result.reason,
                "raw_p_value": None if result.p_value is None else float(result.p_value),
                "holm_adjusted_p_value": float(adjusted[hypothesis.localized_term]),
                "holm_rejected": bool(hypothesis.localized_term in rejected),
                "candidate_sign": int(result.candidate_sign),
                "sign_matches_discovery": sign_ok,
                "raw_gain": float(result.raw_gain),
                "accepted": accepted,
            }
        )
    return tuple(survivors), tuple(diagnostics)


def _scope_candidate_name(hypothesis: FrozenScopeHypothesis) -> str:
    return str(hypothesis.discovery_result.candidate_term)


def _joint_packet(
    dataset,
    catalog,
    shared_terms: tuple[str, ...],
    hypotheses: Sequence[FrozenScopeHypothesis],
) -> SufficientStatsPacket:
    shared_terms = tuple(shared_terms)
    hypotheses = tuple(hypotheses)
    columns = [np.asarray(catalog.get(term).evaluate(dataset.x), dtype=float) for term in shared_terms]
    names = list(shared_terms)
    for hypothesis in hypotheses:
        source = np.asarray(catalog.get(hypothesis.source_term).evaluate(dataset.x), dtype=float)
        in_role = str(dataset.client_id) in set(hypothesis.role_client_ids)
        columns.append(source if in_role else np.zeros_like(source))
        names.append(_scope_candidate_name(hypothesis))
    design = np.column_stack(columns)
    response = np.asarray(dataset.y, dtype=float)
    return SufficientStatsPacket(
        client_id=str(dataset.client_id),
        support=int(len(response)),
        terms=tuple(names),
        gram=np.asarray(design.T @ design, dtype=float),
        target=np.asarray(design.T @ response, dtype=float),
        target_energy=float(response @ response),
        observed_support=tuple(
            int(np.count_nonzero(np.abs(design[:, index]) > 1e-12))
            for index in range(design.shape[1])
        ),
    )


def _outside_safety_for_scope(
    packets: Sequence[SufficientStatsPacket],
    pooled: SufficientStatsPacket,
    full_terms: tuple[str, ...],
    candidate_term: str,
    outside_client_ids: tuple[str, ...],
) -> tuple[bool, float, float]:
    outside_set = set(outside_client_ids)
    selected = tuple(packet for packet in packets if packet.client_id in outside_set)
    if not selected:
        return False, float("nan"), float("nan")
    outside = aggregate_packets(selected)
    reduced_terms = tuple(term for term in full_terms if term != candidate_term)
    full_fit = fit_from_sufficient_stats(pooled, full_terms)
    reduced_fit = fit_from_sufficient_stats(pooled, reduced_terms)
    full_sse = sse_from_packet(outside, full_terms, full_fit.coefficients)
    reduced_sse = sse_from_packet(outside, reduced_terms, reduced_fit.coefficients)
    safe = bool(full_sse <= reduced_sse + 1e-10)
    return safe, float(full_sse), float(reduced_sse)


def _joint_certify(
    clients: Sequence[object],
    shared_family: tuple[str, ...],
    hypotheses: Sequence[FrozenScopeHypothesis],
    *,
    stage: str,
    alpha: float,
) -> tuple[
    tuple[str, ...],
    tuple[FrozenScopeHypothesis, ...],
    tuple[dict[str, object], ...],
]:
    """Jointly delete-test ordinary and frozen scope terms on one evidence split."""
    catalog = v10_catalog()
    hypotheses = tuple(hypotheses)
    packets = tuple(_joint_packet(client, catalog, shared_family, hypotheses) for client in clients)
    pooled = aggregate_packets(packets)
    scope_by_name = {_scope_candidate_name(item): item for item in hypotheses}
    full_family = tuple(pooled.terms)
    tested = tuple(term for term in full_family if term != "1")

    raw_values: list[float] = []
    nested_results = []
    safety: dict[str, tuple[bool, float, float]] = {}
    for term in tested:
        reduced = tuple(item for item in full_family if item != term)
        result = partial_nested_f(pooled, reduced, full_family, candidate_term=term)
        nested_results.append(result)
        raw_values.append(
            float(result.p_value) if result.admissible and result.p_value is not None else 1.0
        )
        if term in scope_by_name:
            hypothesis = scope_by_name[term]
            safety[term] = _outside_safety_for_scope(
                packets,
                pooled,
                full_family,
                term,
                hypothesis.outside_client_ids,
            )

    holm = holm_adjust(tested, raw_values, alpha=alpha)
    adjusted = dict(zip(holm.names, holm.adjusted_values))
    rejected = set(holm.rejected)

    shared_supported: list[str] = []
    localized_supported: list[FrozenScopeHypothesis] = []
    diagnostics: list[dict[str, object]] = []
    for term, raw_p, nested in zip(tested, raw_values, nested_results):
        is_scope = term in scope_by_name
        outside_safe, outside_full, outside_reduced = safety.get(term, (True, float("nan"), float("nan")))
        hypothesis = scope_by_name.get(term)
        sign_ok = bool(
            not is_scope
            or (
                hypothesis is not None
                and nested.candidate_sign == hypothesis.discovery_sign != 0
            )
        )
        accepted = bool(
            nested.admissible
            and term in rejected
            and sign_ok
            and (outside_safe if is_scope else True)
            and nested.raw_gain > 0.0
        )
        if accepted:
            if is_scope:
                localized_supported.append(scope_by_name[term])
            else:
                shared_supported.append(term)
        diagnostics.append(
            {
                "stage": stage,
                "term": term,
                "kind": "localized-scope" if is_scope else "shared",
                "localized_term": None if hypothesis is None else hypothesis.localized_term,
                "source_term": None if hypothesis is None else hypothesis.source_term,
                "role_client_ids": [] if hypothesis is None else list(hypothesis.role_client_ids),
                "admissible": bool(nested.admissible),
                "reason": nested.reason,
                "reduced_rank": int(nested.reduced_rank),
                "full_rank": int(nested.full_rank),
                "residual_df": int(nested.residual_df),
                "raw_p_value": float(raw_p),
                "holm_adjusted_p_value": float(adjusted[term]),
                "holm_rejected": bool(term in rejected),
                "candidate_sign": int(nested.candidate_sign),
                "sign_matches_discovery": sign_ok,
                "raw_gain": float(nested.raw_gain),
                "outside_safe": bool(outside_safe),
                "outside_full_sse": outside_full,
                "outside_reduced_sse": outside_reduced,
                "accepted": accepted,
            }
        )

    # Intercept is structural and never deletion-tested.
    shared = ("1",) + tuple(shared_supported)
    if len(shared) - 1 > MAX_NONINTERCEPT_SHARED:
        ranked = sorted(
            shared_supported,
            key=lambda term: (float(adjusted[term]), shared_family.index(term)),
        )
        shared = ("1",) + tuple(ranked[:MAX_NONINTERCEPT_SHARED])

    # Weak heredity: a localized shift is operational only if its shared source
    # remains operational in the same joint certification stage.
    shared_set = set(shared)
    localized_supported = [
        hypothesis
        for hypothesis in localized_supported
        if hypothesis.source_term in shared_set
    ]
    if len(localized_supported) > MAX_LOCALIZED:
        # More than two accepted localized mechanisms is an ambiguity state,
        # not an invitation to rank outcomes after seeing evidence.
        localized_supported = []

    return shared, tuple(localized_supported), tuple(diagnostics)


def _result(
    fixture: Phase3DFixture,
    method: str,
    outer_fold: int,
    shared_structure: Sequence[str],
    accepted_localized: Sequence[str],
    localized_scopes: Sequence[tuple[str, tuple[str, ...]]],
    diagnostics: Sequence[dict[str, object]],
    *,
    start: float,
    communication_bytes: int = 0,
    stop_reason: str,
    execution_error: str | None = None,
) -> Phase3DModelResult:
    shared = tuple(shared_structure)
    localized = _ordered_localized(fixture, accepted_localized)
    scope_lookup = {term: tuple(ids) for term, ids in localized_scopes}
    scopes = tuple((term, scope_lookup[term]) for term in localized if term in scope_lookup)
    exact_shared, exact_localized, exact_scope, exact_structure = _evaluate_exactness(
        fixture, shared, localized, scopes
    )
    return Phase3DModelResult(
        method=method,
        fixture=fixture.name,
        outer_fold=int(outer_fold),
        shared_structure=shared,
        accepted_localized=localized,
        localized_scopes=scopes,
        exact_shared=exact_shared,
        exact_localized=exact_localized,
        exact_scope=exact_scope,
        exact_structure=exact_structure,
        diagnostics=tuple(dict(item) for item in diagnostics),
        communication_bytes=int(communication_bytes),
        runtime_seconds=float(perf_counter() - start),
        stop_reason=stop_reason,
        execution_error=execution_error,
    )


def _run_scope_contrast_only(fixture: Phase3DFixture, outer_fold: int) -> Phase3DModelResult:
    start = perf_counter()
    discovery, selector, probe = split_fixture_clients(fixture, outer_fold=outer_fold)
    # This is deliberately an oracle/protected-shared ablation: it isolates
    # whether scope contrast itself solves v12's local rank Catch-22.
    protected_shared = tuple(fixture.true_shared_terms)
    hypotheses, discovery_diag = _discovery_hypotheses(fixture, discovery, protected_shared)
    selector_survivors, selector_diag = _independent_scope_screen(
        selector,
        protected_shared,
        hypotheses,
        stage="selector",
        alpha=SHARED_ALPHA,
    )
    probe_survivors, probe_diag = _independent_scope_screen(
        probe,
        protected_shared,
        selector_survivors,
        stage="probe",
        alpha=PROBE_ALPHA,
    )
    accepted = tuple(item.localized_term for item in probe_survivors)
    scopes = _scope_rows(probe_survivors)
    return _result(
        fixture,
        "scope-contrast-only",
        outer_fold,
        protected_shared,
        accepted,
        scopes,
        discovery_diag + selector_diag + probe_diag,
        start=start,
        stop_reason=(
            "Phase-3D localization-only ablation; shared structure protected by fixture truth; "
            "roles discovered on Discovery and independently Holm-confirmed on Selector/Probe"
        ),
    )


def _run_v13_full(fixture: Phase3DFixture, outer_fold: int) -> Phase3DModelResult:
    start = perf_counter()
    discovery, selector, probe = split_fixture_clients(fixture, outer_fold=outer_fold)
    provisional_shared = tuple(fixture.candidate_shared_terms)
    hypotheses, discovery_diag = _discovery_hypotheses(
        fixture,
        discovery,
        provisional_shared,
    )

    selector_shared, selector_localized, selector_diag = _joint_certify(
        selector,
        provisional_shared,
        hypotheses,
        stage="selector-joint",
        alpha=SHARED_ALPHA,
    )

    # Probe sees only frozen Selector survivors.  It cannot create a new shared
    # term, localized term, role identity, sign, or source relationship.
    probe_shared, probe_localized, probe_diag = _joint_certify(
        probe,
        selector_shared,
        selector_localized,
        stage="probe-joint",
        alpha=PROBE_ALPHA,
    )
    accepted = tuple(item.localized_term for item in probe_localized)
    scopes = _scope_rows(probe_localized)
    if len(probe_shared) + len(accepted) > MAX_FINAL_TERMS:
        raise RuntimeError("Phase-3D v13 exceeded final ten-term structural cap")

    return _result(
        fixture,
        "v13-full",
        outer_fold,
        probe_shared,
        accepted,
        scopes,
        discovery_diag + selector_diag + probe_diag,
        start=start,
        stop_reason=(
            "SCSV-SCC v13; deterministic Discovery scope contrast; joint Selector shared/localized "
            "delete-tests; frozen independent Probe; Holm=0.05; outside-scope nondegradation"
        ),
    )


def _scope_map_from_v11(output) -> tuple[tuple[str, tuple[str, ...]], ...]:
    accepted = set(getattr(output, "accepted_deviations", ()))
    rows = []
    for diagnostic in getattr(output, "diagnostics", ()):
        term = getattr(diagnostic, "term", None)
        if term in accepted:
            rows.append((str(term), tuple(getattr(diagnostic, "role_client_ids", ()))))
    return tuple(rows)


def _scope_map_from_v12(output) -> tuple[tuple[str, tuple[str, ...]], ...]:
    accepted = set(getattr(output, "accepted_deviations", ()))
    rows = []
    for diagnostic in getattr(getattr(output, "ledger", None), "discovery_localized_diagnostics", ()):
        term = getattr(diagnostic, "term", getattr(diagnostic, "localized_term", None))
        if term in accepted and hasattr(diagnostic, "role_client_ids"):
            rows.append((str(term), tuple(getattr(diagnostic, "role_client_ids"))))
    return tuple(rows)


def _run_v11_frozen(fixture: Phase3DFixture, outer_fold: int) -> Phase3DModelResult:
    start = perf_counter()
    catalog = v10_catalog()
    technical_seed = TECHNICAL_PARTITION_SEED_BASE + int(outer_fold)
    try:
        output = scsv_elrc_v11_method(
            fixture.clients,
            catalog,
            seed=technical_seed,
            target_mse=1e-10,
        )
        shared = tuple(
            term for term in output.final_structure if catalog.get(term).kind != "exception"
        )
        accepted = tuple(output.accepted_deviations)
        scopes = _scope_map_from_v11(output)
        diagnostics = (
            {
                "stage": "frozen-comparator",
                "technical_partition_seed": technical_seed,
                "scientific_fixture_seed": None,
                "stop_reason": output.stop_reason,
            },
        )
        return _result(
            fixture,
            "v11-frozen",
            outer_fold,
            shared,
            accepted,
            scopes,
            diagnostics,
            start=start,
            communication_bytes=int(output.communication_bytes),
            stop_reason="Frozen v11 comparator on deterministic Phase-3D fixture",
        )
    except Exception as exc:  # Comparator failure is recorded, never hidden.
        return _result(
            fixture,
            "v11-frozen",
            outer_fold,
            (),
            (),
            (),
            ({"stage": "frozen-comparator", "error": f"{type(exc).__name__}: {exc}"},),
            start=start,
            stop_reason="Frozen v11 comparator execution failed; recorded without altering v11",
            execution_error=f"{type(exc).__name__}: {exc}",
        )


def _run_v12_frozen(fixture: Phase3DFixture, outer_fold: int) -> Phase3DModelResult:
    start = perf_counter()
    catalog = v10_catalog()
    technical_seed = TECHNICAL_PARTITION_SEED_BASE + int(outer_fold)
    try:
        branches = run_scsv_v12_branches(
            fixture.clients,
            catalog,
            seed=technical_seed,
            target_mse=1e-10,
        )
        output = next(item for item in branches if getattr(item, "method", "") == "scsv-ncsc")
        shared = tuple(output.shared_structure)
        accepted = tuple(output.accepted_deviations)
        scopes = _scope_map_from_v12(output)
        diagnostics = (
            {
                "stage": "frozen-comparator",
                "technical_partition_seed": technical_seed,
                "scientific_fixture_seed": None,
                "stop_reason": output.stop_reason,
            },
        )
        return _result(
            fixture,
            "v12-frozen",
            outer_fold,
            shared,
            accepted,
            scopes,
            diagnostics,
            start=start,
            communication_bytes=int(output.communication_bytes),
            stop_reason="Frozen v12/SCSV-NCSC comparator on deterministic Phase-3D fixture",
        )
    except Exception as exc:
        return _result(
            fixture,
            "v12-frozen",
            outer_fold,
            (),
            (),
            (),
            ({"stage": "frozen-comparator", "error": f"{type(exc).__name__}: {exc}"},),
            start=start,
            stop_reason="Frozen v12 comparator execution failed; recorded without altering v12",
            execution_error=f"{type(exc).__name__}: {exc}",
        )


def run_phase3d_model(
    fixture: Phase3DFixture,
    model_name: str,
    *,
    outer_fold: int = 0,
) -> Phase3DModelResult:
    """Run exactly one atomic Phase-3D fixture × model × fold work unit."""
    if model_name not in PHASE3D_MODELS:
        raise ValueError(f"unknown Phase-3D model: {model_name}")
    if int(outer_fold) < 0:
        raise ValueError("outer_fold must be non-negative")
    if model_name == "v11-frozen":
        return _run_v11_frozen(fixture, int(outer_fold))
    if model_name == "v12-frozen":
        return _run_v12_frozen(fixture, int(outer_fold))
    if model_name == "scope-contrast-only":
        return _run_scope_contrast_only(fixture, int(outer_fold))
    return _run_v13_full(fixture, int(outer_fold))
