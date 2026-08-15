from __future__ import annotations

from types import SimpleNamespace

from fedfalsify.basis import CandidateEquation
from fedfalsify.scsv_v7_benchmarks import LINEAR_DEV, QUADRATIC_DEV, v7_catalog


def _fake_anchor(candidates):
    anchor_structure = ("1", "x1", "sin(x2)", "x3^2")
    candidate = CandidateEquation(anchor_structure, (0.0, 1.0, 0.8, 0.6), "fake-anchor")
    return SimpleNamespace(
        candidate=candidate,
        selector_structure=anchor_structure,
        selector_profile=SimpleNamespace(terms=anchor_structure, coefficients=candidate.coefficients),
        bank=SimpleNamespace(candidate_terms=("x1", "sin(x2)", "x3^2", *candidates)),
        communication_bytes=100,
        runtime_seconds=0.1,
        stop_reason="fake-anchor",
    )


def _patch_common(monkeypatch, module, candidates, *, probe_pass=True):
    anchor = _fake_anchor(candidates)
    monkeypatch.setattr(module, "scsv_cert_method", lambda *args, **kwargs: anchor)
    monkeypatch.setattr(module, "_source_linked_missing", lambda *args, **kwargs: tuple(candidates))
    monkeypatch.setattr(module, "partition_clients", lambda *args, **kwargs: (object(),))
    monkeypatch.setattr(module, "split_selector_probe", lambda *args, **kwargs: ((object(),), (object(),)))
    packet = SimpleNamespace(client_id="client-1", support=50, observed_support=(50,) * 8)
    monkeypatch.setattr(module, "_build_packets", lambda *args, **kwargs: ((packet,), (packet,), (packet,), 10))
    monkeypatch.setattr(module, "_role_indices", lambda *args, **kwargs: (0,))
    monkeypatch.setattr(
        module,
        "_fit_from_packets",
        lambda packets, all_terms, selected, candidate_id: CandidateEquation(
            selected,
            tuple(0.2 + 0.01 * index for index, _ in enumerate(selected)),
            candidate_id,
        ),
    )

    calls = {"count": 0}

    def conditional(*args, **kwargs):
        calls["count"] += 1
        # Calls alternate selector/probe for each deviation.
        is_probe = calls["count"] % 2 == 0
        passed = probe_pass if is_probe else True
        return 50, 1.0 if passed else 2.0, 2.0 if passed else 1.0, -0.5 if passed else 0.5, passed

    monkeypatch.setattr(module, "_conditional_test", conditional)
    monkeypatch.setattr(module, "_outside_safety", lambda *args, **kwargs: (1.0, 0.9, True))
    monkeypatch.setattr(
        module,
        "_refit",
        lambda partitions, catalog, terms, include_validation, candidate_id: (
            CandidateEquation(terms, tuple(0.3 + 0.01 * i for i, _ in enumerate(terms)), candidate_id),
            20,
        ),
    )
    return anchor


def test_v7_accepts_one_source_linked_deviation_without_deleting_anchor(monkeypatch) -> None:
    import fedfalsify.scsv_v7 as module

    anchor = _patch_common(monkeypatch, module, (LINEAR_DEV,), probe_pass=True)
    output = module.scsv_rcd_v7_method([object()], v7_catalog(), seed=24001, target_mse=0.01)
    assert output.ambiguity_guard is False
    assert output.accepted_deviations == (LINEAR_DEV,)
    assert LINEAR_DEV in output.final_structure
    assert set(anchor.selector_structure).issubset(set(output.final_structure))
    assert len(output.final_structure) == len(anchor.selector_structure) + 1


def test_v7_accepts_two_independently_certified_deviations(monkeypatch) -> None:
    import fedfalsify.scsv_v7 as module

    anchor = _patch_common(monkeypatch, module, (LINEAR_DEV, QUADRATIC_DEV), probe_pass=True)
    output = module.scsv_rcd_v7_method([object()], v7_catalog(), seed=24001, target_mse=0.01)
    assert output.ambiguity_guard is False
    assert set(output.accepted_deviations) == {LINEAR_DEV, QUADRATIC_DEV}
    assert set(anchor.selector_structure).issubset(set(output.final_structure))
    assert {LINEAR_DEV, QUADRATIC_DEV}.issubset(set(output.final_structure))
    assert len(output.final_structure) == len(anchor.selector_structure) + 2


def test_probe_requirement_is_operational_not_cosmetic(monkeypatch) -> None:
    import fedfalsify.scsv_v7 as module

    anchor = _patch_common(monkeypatch, module, (LINEAR_DEV,), probe_pass=False)
    full = module.scsv_rcd_v7_method(
        [object()], v7_catalog(), seed=24001, target_mse=0.01, require_probe=True
    )
    assert full.accepted_deviations == ()
    assert full.final_structure == anchor.selector_structure

    # Reset the alternating call state by rebuilding the monkeypatch fixture.
    _patch_common(monkeypatch, module, (LINEAR_DEV,), probe_pass=False)
    no_probe = module.scsv_rcd_v7_method(
        [object()], v7_catalog(), seed=24001, target_mse=0.01, require_probe=False
    )
    assert no_probe.accepted_deviations == (LINEAR_DEV,)
    assert LINEAR_DEV in no_probe.final_structure
