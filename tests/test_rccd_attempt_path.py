from __future__ import annotations

from types import SimpleNamespace

import numpy as np

import fedfalsify.rccd_diagnostic as rccd
from fedfalsify.basis import CandidateEquation
from fedfalsify.benchmarks import benchmark_catalog
from fedfalsify.rccd_spent_study import SMOKE_SEED
from fedfalsify.scsv_v6 import scsv_cert_method
from fedfalsify.scsv_v6_independent import generate_independent_benchmark

EXCEPTION = "I(x3>1)*x3^2"
SOURCE = "x3^2"


def _strip_exception(candidate: CandidateEquation) -> CandidateEquation:
    kept = [
        (term, float(value))
        for term, value in zip(candidate.active_terms, candidate.coefficients)
        if term != EXCEPTION
    ]
    return CandidateEquation(
        tuple(term for term, _ in kept),
        tuple(value for _, value in kept),
        "rccd-forced-missing-exception-anchor",
    )


def test_rccd_end_to_end_attempt_branch_with_forced_missing_banked_exception(
    monkeypatch,
) -> None:
    generated = generate_independent_benchmark(
        "cubic_cross",
        scenario="exception",
        nominal_samples_per_client=100,
        noise_ratio=0.20,
        seed=SMOKE_SEED,
        num_clients=4,
        balance_profile="imbalanced",
    )
    catalog = benchmark_catalog(scenario="exception")
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    original = scsv_cert_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        max_terms=6,
        target_mse=target_mse,
        min_repair_score=0.05,
        use_score_proposer=True,
    )

    # The engineering seed happens to select the exception already. Remove only
    # that term from a test double of the frozen anchor so the RCCD attempt path
    # is exercised without changing the production algorithm or scientific data.
    assert EXCEPTION in original.selector_structure
    assert SOURCE in original.selector_structure
    assert EXCEPTION in original.bank.candidate_terms

    selector_map = dict(
        zip(original.selector_profile.terms, original.selector_profile.coefficients)
    )
    anchor_terms = tuple(
        term for term in original.selector_structure if term != EXCEPTION
    )
    anchor_selector_profile = SimpleNamespace(
        terms=anchor_terms,
        coefficients=tuple(float(selector_map[term]) for term in anchor_terms),
    )
    fake_anchor = SimpleNamespace(
        selector_structure=anchor_terms,
        selector_profile=anchor_selector_profile,
        bank=original.bank,
        candidate=_strip_exception(original.candidate),
        probe_certified=original.probe_certified,
        term_diagnostics=original.term_diagnostics,
        candidate_sets_evaluated=original.candidate_sets_evaluated,
        communication_bytes=original.communication_bytes,
    )

    monkeypatch.setattr(rccd, "scsv_cert_method", lambda *args, **kwargs: fake_anchor)
    output = rccd.rccd_diagnostic_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        max_terms=6,
        target_mse=target_mse,
        min_repair_score=0.05,
    )

    assert output.attempted is True
    assert output.exception_in_bank is True
    assert output.exception_in_anchor is False
    assert output.source_term == SOURCE
    assert output.source_in_anchor is True
    assert EXCEPTION in output.discovery_full_structure
    assert output.selector_eligible_clients == ("client-4",)
    assert output.probe_eligible_clients == ("client-4",)
    assert output.selector_eligible_support > 0
    assert output.probe_eligible_support > 0
    assert np.isfinite(output.exception_coefficient)
    assert np.isfinite(output.selector_delta)
    assert np.isfinite(output.probe_delta)
    assert np.isfinite(output.selector_outside_anchor_sse)
    assert np.isfinite(output.selector_outside_full_sse)
    assert np.isfinite(output.probe_outside_anchor_sse)
    assert np.isfinite(output.probe_outside_full_sse)
    assert set(anchor_terms).issubset(set(output.final_structure))
    if output.accepted:
        assert output.selector_passed is True
        assert output.probe_passed is True
        assert output.selector_delta < 0.0
        assert output.probe_delta < 0.0
        assert output.selector_outside_safe is True
        assert output.probe_outside_safe is True
        assert EXCEPTION in output.final_structure
    else:
        assert output.final_structure == anchor_terms
