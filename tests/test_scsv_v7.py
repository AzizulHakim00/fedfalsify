from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from fedfalsify.basis import CandidateEquation
from fedfalsify.scsv_v7 import (
    _source_linked_missing,
    _zero_one,
    scsv_rcd_v7_method,
)
from fedfalsify.scsv_v7_benchmarks import (
    INTERACTION_DEV,
    LINEAR_DEV,
    QUADRATIC_DEV,
    TRIG_DEV,
    V7_DEVIATIONS,
    generate_v7_benchmark,
    v7_catalog,
)
from fedfalsify.scsv_v7_study import (
    DEVELOPMENT_SEEDS,
    SMOKE_SEED,
    _validate_seeds,
    run_study,
    summarize,
)


def test_v7_seed_firewall() -> None:
    assert SMOKE_SEED == 24001
    assert DEVELOPMENT_SEEDS == (24101, 24102, 24103, 24104, 24105)
    _validate_seeds((SMOKE_SEED,), smoke=True)
    _validate_seeds(DEVELOPMENT_SEEDS, smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((SMOKE_SEED,), smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((24101,), smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((23001,), smoke=True)


def test_v7_catalog_exposes_four_source_linked_deviations() -> None:
    catalog = v7_catalog()
    expected = {
        QUADRATIC_DEV: "x3^2",
        LINEAR_DEV: "x1",
        TRIG_DEV: "sin(x2)",
        INTERACTION_DEV: "x1*x2",
    }
    assert set(V7_DEVIATIONS) == set(expected)
    for term, source in expected.items():
        metadata = catalog.get(term)
        assert metadata.kind == "exception"
        assert metadata.source_term == source
        assert metadata.validity is not None


def test_v7_generators_do_not_hide_distractor_grammar() -> None:
    catalog = v7_catalog()
    for family, true in (
        ("quadratic_role", {QUADRATIC_DEV}),
        ("linear_role", {LINEAR_DEV}),
        ("trig_role", {TRIG_DEV}),
        ("interaction_role", {INTERACTION_DEV}),
        ("null_role", set()),
        ("dual_role", {LINEAR_DEV, QUADRATIC_DEV}),
    ):
        generated = generate_v7_benchmark(
            family,
            seed=SMOKE_SEED,
            num_clients=8 if family == "dual_role" else 4,
            balance_profile="balanced",
            role_profile=("quarter" if family == "dual_role" else "none" if family == "null_role" else "single"),
            noise_ratio=0.10,
        )
        assert set(generated.true_deviations) == true
        assert set(V7_DEVIATIONS).issubset(set(catalog.names()))
        assert len(generated.clients) in {4, 8}


def test_v7_fixed_reduced_changes_exactly_one_coefficient() -> None:
    full = CandidateEquation(
        ("1", "x1", LINEAR_DEV, QUADRATIC_DEV),
        (0.1, 1.2, 0.7, -0.4),
        "v7-test-full",
    )
    zero = _zero_one(full, LINEAR_DEV)
    full_map = dict(zip(full.active_terms, full.coefficients))
    zero_map = dict(zip(zero.active_terms, zero.coefficients))
    assert zero_map[LINEAR_DEV] == 0.0
    for term in ("1", "x1", QUADRATIC_DEV):
        assert zero_map[term] == full_map[term]


def test_source_link_blocks_orphan_deviations() -> None:
    catalog = v7_catalog()
    fake = SimpleNamespace(
        bank=SimpleNamespace(candidate_terms=(LINEAR_DEV, QUADRATIC_DEV, TRIG_DEV)),
        selector_structure=("1", "x1", "x2^2"),
    )
    # Only LINEAR_DEV is source-linked because x1 is the sole declared source
    # present in the fake shared anchor.
    assert _source_linked_missing(fake, catalog) == (LINEAR_DEV,)


def test_v7_real_smoke_preserves_frozen_anchor() -> None:
    generated = generate_v7_benchmark(
        "linear_role",
        seed=SMOKE_SEED,
        num_clients=4,
        balance_profile="balanced",
        role_profile="single",
        noise_ratio=0.10,
    )
    output = scsv_rcd_v7_method(
        generated.clients,
        v7_catalog(),
        seed=SMOKE_SEED,
        target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
        min_repair_score=0.05,
    )
    assert set(output.anchor_structure).issubset(set(output.final_structure))
    assert len(output.accepted_deviations) <= 2
    for diagnostic in output.diagnostics:
        if diagnostic.term in set(output.accepted_deviations):
            assert diagnostic.selector_passed
            assert diagnostic.probe_passed
            assert diagnostic.selector_outside_safe
            assert diagnostic.probe_outside_safe


def test_v7_ambiguity_guard_restores_anchor(monkeypatch) -> None:
    import fedfalsify.scsv_v7 as module

    catalog = v7_catalog()
    anchor_structure = ("1", "x1", "sin(x2)", "x3^2", "x1*x2")
    anchor_candidate = CandidateEquation(
        anchor_structure,
        (0.0, 1.0, 0.8, 0.6, 0.5),
        "fake-anchor",
    )
    fake_anchor = SimpleNamespace(
        candidate=anchor_candidate,
        selector_structure=anchor_structure,
        selector_profile=SimpleNamespace(
            terms=anchor_structure,
            coefficients=anchor_candidate.coefficients,
        ),
        bank=SimpleNamespace(
            candidate_terms=("x1", "sin(x2)", "x3^2", "x1*x2", LINEAR_DEV, TRIG_DEV, QUADRATIC_DEV)
        ),
        communication_bytes=100,
        runtime_seconds=0.1,
        stop_reason="fake",
    )
    positives = (LINEAR_DEV, TRIG_DEV, QUADRATIC_DEV)

    monkeypatch.setattr(module, "scsv_cert_method", lambda *args, **kwargs: fake_anchor)
    monkeypatch.setattr(module, "_source_linked_missing", lambda *args, **kwargs: positives)
    monkeypatch.setattr(module, "partition_clients", lambda *args, **kwargs: (object(),))
    monkeypatch.setattr(module, "split_selector_probe", lambda *args, **kwargs: ((object(),), (object(),)))

    packet = SimpleNamespace(client_id="client-1", support=50, observed_support=(50,) * 8)
    monkeypatch.setattr(
        module,
        "_build_packets",
        lambda *args, **kwargs: ((packet,), (packet,), (packet,), 10),
    )
    monkeypatch.setattr(module, "_role_indices", lambda *args, **kwargs: (0,))
    monkeypatch.setattr(
        module,
        "_fit_from_packets",
        lambda packets, all_terms, selected, candidate_id: CandidateEquation(
            selected,
            tuple(0.1 + 0.01 * index for index, _ in enumerate(selected)),
            candidate_id,
        ),
    )
    monkeypatch.setattr(
        module,
        "_conditional_test",
        lambda *args, **kwargs: (50, 1.0, 2.0, -0.5, True),
    )
    monkeypatch.setattr(
        module,
        "_outside_safety",
        lambda *args, **kwargs: (1.0, 0.9, True),
    )

    output = module.scsv_rcd_v7_method(
        [object()],
        catalog,
        seed=SMOKE_SEED,
        target_mse=0.01,
    )
    assert output.ambiguity_guard is True
    assert output.accepted_deviations == ()
    assert output.final_structure == anchor_structure
    assert output.candidate.active_terms == anchor_candidate.active_terms
    assert np.allclose(output.candidate.coefficients, anchor_candidate.coefficients)


def test_v7_smoke_study_is_engineering_only() -> None:
    rows = run_study(
        seeds=(SMOKE_SEED,),
        methods=("scsv-rcd-v7-full",),
        smoke=True,
    )
    assert len(rows) == 6
    assert {row.seed for row in rows} == {SMOKE_SEED}
    assert {row.method for row in rows} == {"scsv-rcd-v7-full"}
    summary = summarize(rows, evaluate_gate=False)
    assert summary["conditions"] == 6
    assert summary["development_gate"]["evaluated"] is False
    assert summary["development_gate"]["passed"] is None
