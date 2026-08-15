from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from fedfalsify.basis import BasisTerm, CandidateEquation
from fedfalsify.crossfit_redesign import partition_clients
from fedfalsify.crossfit_surrogate import split_selector_probe
from fedfalsify.scsv_diagnostic import _build_packets
from fedfalsify.scsv_v8 import (
    V8RoleHypothesis,
    _conditional_test,
    _estimate_pair,
    _outside_safety,
    _pair_invariant,
    _probe_state,
    _role_hypothesis,
    scsv_spcc_v8_method,
)
from fedfalsify.scsv_v8_benchmarks import (
    INTERACTION_DEV_V8,
    LINEAR_DEV_V8,
    QUADRATIC_DEV_V8,
    TRIG_DEV_V8,
    V8_DEVIATIONS,
    V8TermCatalog,
    generate_v8_benchmark,
    v8_catalog,
)
from fedfalsify.scsv_v8_study import SMOKE_SEED, _scientific_conditions, _validate_seeds


def _packets_for(generated, terms):
    catalog = v8_catalog()
    partitions = partition_clients(generated.clients, seed=SMOKE_SEED, validation_fraction=0.30)
    selectors, probes = split_selector_probe(partitions, seed=SMOKE_SEED)
    fit, selector, probe, _ = _build_packets(
        partitions, selectors, probes, catalog, tuple(terms)
    )
    return fit, selector, probe


def test_v8_catalog_has_new_source_linked_deviations():
    catalog = v8_catalog()
    expected = {
        QUADRATIC_DEV_V8: "x1^2",
        LINEAR_DEV_V8: "x3",
        TRIG_DEV_V8: "cos(x1)",
        INTERACTION_DEV_V8: "x1*x2",
    }
    assert tuple(expected) == V8_DEVIATIONS
    for term, source in expected.items():
        metadata = catalog.get(term)
        assert metadata.kind == "exception"
        assert metadata.source_term == source


def test_engineering_seed_firewall():
    _validate_seeds((SMOKE_SEED,), smoke=True)
    with pytest.raises(ValueError):
        _validate_seeds((SMOKE_SEED + 1,), smoke=True)
    with pytest.raises(ValueError):
        _validate_seeds((SMOKE_SEED,), smoke=False)


def test_preregistered_matrix_has_540_nonredundant_conditions_without_generating_them():
    dummy_seeds = (1, 2, 3, 4, 5)
    conditions = list(_scientific_conditions(dummy_seeds))
    assert len(conditions) == 540
    keys = set(conditions)
    assert len(keys) == 540
    assert not any(
        clients == 4 and role_profile == "quarter"
        for _, clients, _, role_profile, _, _ in conditions
    )


def test_single_role_is_response_free_nonvacuous_and_pair_is_isolated():
    generated = generate_v8_benchmark(
        "quadratic_role_v8",
        seed=SMOKE_SEED,
        num_clients=4,
        balance_profile="balanced",
        role_profile="single",
        noise_ratio=0.10,
    )
    terms = ("1", "x1^2", "sin(x3)", "x2", QUADRATIC_DEV_V8)
    fit, selector, probe = _packets_for(generated, terms)
    role = _role_hypothesis(fit, terms, QUADRATIC_DEV_V8)
    assert role.admissible
    assert len(role.role_indices) == 1
    assert len(role.outside_indices) == 3
    assert role.separation_gap >= 0.50
    assert role.role_mean_occupancy >= 0.75
    assert role.outside_mean_occupancy <= 0.25

    anchor = CandidateEquation(
        ("1", "x1^2", "sin(x3)", "x2"),
        (0.0, 0.85, 0.75, 0.55),
        "engineering-anchor",
    )
    full, reduced, beta_source, delta = _estimate_pair(
        anchor,
        "x1^2",
        QUADRATIC_DEV_V8,
        fit,
        terms,
        role,
        v8_catalog(),
    )
    assert np.isfinite(beta_source)
    assert np.isfinite(delta)
    assert _pair_invariant(full, reduced, QUADRATIC_DEV_V8)
    mapping_full = dict(zip(full.active_terms, full.coefficients))
    mapping_reduced = dict(zip(reduced.active_terms, reduced.coefficients))
    for term in full.active_terms:
        if term == QUADRATIC_DEV_V8:
            assert mapping_reduced[term] == 0.0
        else:
            assert mapping_full[term] == mapping_reduced[term]

    _, _, _, selector_delta, _ = _conditional_test(
        full, reduced, selector, terms, role.role_indices
    )
    _, probe_full, probe_reduced, probe_delta, _ = _conditional_test(
        full, reduced, probe, terms, role.role_indices
    )
    assert selector_delta is not None and np.isfinite(selector_delta)
    assert probe_delta is not None and np.isfinite(probe_delta)
    assert _probe_state(probe_full, probe_reduced, probe_delta) in {
        "SUPPORTED",
        "INCONCLUSIVE-DIRECTIONAL",
        "CONTRADICTED",
    }
    selector_out = _outside_safety(
        full, reduced, selector, terms, role.outside_indices
    )
    probe_out = _outside_safety(full, reduced, probe, terms, role.outside_indices)
    # Outside clients have zero support for the true gated term in this engineering case.
    assert selector_out[2]
    assert probe_out[2]


def test_null_and_diffuse_null_do_not_form_client_level_roles():
    terms = (
        "1",
        "x1^2",
        "x3",
        "cos(x1)",
        "x1*x2",
        *V8_DEVIATIONS,
    )
    for family in ("null_role_v8", "diffuse_null_v8"):
        generated = generate_v8_benchmark(
            family,
            seed=SMOKE_SEED,
            num_clients=8,
            balance_profile="balanced",
            role_profile="none",
            noise_ratio=0.10,
        )
        fit, _, _ = _packets_for(generated, terms)
        roles = [_role_hypothesis(fit, terms, term) for term in V8_DEVIATIONS]
        assert all(not role.admissible for role in roles), (family, roles)
        assert all(len(role.role_indices) == 0 for role in roles)


def test_three_state_probe_rule_is_exact():
    assert _probe_state(90.0, 100.0, -0.01) == "SUPPORTED"
    assert _probe_state(99.0, 100.0, 0.01) == "INCONCLUSIVE-DIRECTIONAL"
    assert _probe_state(100.0, 100.0, 0.01) == "CONTRADICTED"
    assert _probe_state(101.0, 100.0, 0.01) == "CONTRADICTED"
    assert _probe_state(None, 100.0, None) == "CONTRADICTED"


def _dummy_anchor(catalog, sources, bank_terms):
    structure = ("1",) + tuple(sources)
    coefficients = (0.0,) + tuple(1.0 for _ in sources)
    return SimpleNamespace(
        selector_structure=structure,
        selector_profile=SimpleNamespace(terms=structure, coefficients=coefficients),
        bank=SimpleNamespace(candidate_terms=tuple(bank_terms)),
        candidate=CandidateEquation(structure, coefficients, "dummy-anchor-final"),
        communication_bytes=1,
        runtime_seconds=0.01,
        stop_reason="dummy-anchor",
    )


def _positive_role(term):
    return V8RoleHypothesis(
        term=term,
        admissible=True,
        role_indices=(0,),
        outside_indices=(1,),
        role_client_ids=("client-1",),
        outside_client_ids=("client-2",),
        occupancies=(1.0, 0.0),
        separation_gap=1.0,
        role_mean_occupancy=1.0,
        outside_mean_occupancy=0.0,
        reason="forced engineering path",
    )


def _patch_positive_certificate(monkeypatch, module, anchor):
    monkeypatch.setattr(module, "scsv_cert_method", lambda *args, **kwargs: anchor)
    monkeypatch.setattr(module, "partition_clients", lambda *args, **kwargs: (object(), object()))
    monkeypatch.setattr(module, "split_selector_probe", lambda *args, **kwargs: ((), ()))
    monkeypatch.setattr(module, "_build_packets", lambda *args, **kwargs: ((), (), (), 0))
    monkeypatch.setattr(module, "_role_hypothesis", lambda packets, all_terms, term: _positive_role(term))

    def estimate(anchor_candidate, source, deviation, *args, **kwargs):
        full = CandidateEquation(("1", source, deviation), (0.0, 1.0, 0.5), "forced-full")
        reduced = CandidateEquation(("1", source, deviation), (0.0, 1.0, 0.0), "forced-reduced")
        return full, reduced, 1.0, 0.5

    monkeypatch.setattr(module, "_estimate_pair", estimate)
    monkeypatch.setattr(module, "_conditional_test", lambda *args, **kwargs: (20, 9.0, 10.0, -0.1, True))
    monkeypatch.setattr(module, "_outside_safety", lambda *args, **kwargs: (9.0, 10.0, True))


def test_global_more_than_two_positive_guard_restores_anchor(monkeypatch):
    import fedfalsify.scsv_v8 as module

    catalog = v8_catalog()
    bank = (QUADRATIC_DEV_V8, LINEAR_DEV_V8, TRIG_DEV_V8)
    anchor = _dummy_anchor(catalog, ("x1^2", "x3", "cos(x1)"), bank)
    _patch_positive_certificate(monkeypatch, module, anchor)
    output = scsv_spcc_v8_method((object(), object()), catalog, seed=SMOKE_SEED)
    assert output.global_ambiguity
    assert output.accepted_deviations == ()
    assert output.final_structure == anchor.selector_structure


def test_same_source_ambiguity_blocks_only_that_source(monkeypatch):
    import fedfalsify.scsv_v8 as module

    catalog = V8TermCatalog()
    second = "I(x1<-1.25)*x1^2"
    catalog._terms[second] = BasisTerm(
        second,
        lambda x: np.where(x[:, 0] < -1.25, x[:, 0] ** 2, 0.0),
        4,
        "𝟙[x₁<-1.25]·x₁²",
        kind="exception",
        validity="x1 < -1.25",
        source_term="x1^2",
    )
    bank = (QUADRATIC_DEV_V8, second)
    anchor = _dummy_anchor(catalog, ("x1^2",), bank)
    _patch_positive_certificate(monkeypatch, module, anchor)
    output = scsv_spcc_v8_method((object(), object()), catalog, seed=SMOKE_SEED)
    assert output.source_ambiguity
    assert not output.global_ambiguity
    assert output.accepted_deviations == ()
    assert output.final_structure == anchor.selector_structure
