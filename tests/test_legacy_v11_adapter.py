from fedfalsify.scsv_v10_benchmarks import generate_v10_benchmark, v10_catalog
from fedfalsify.scsv_v11 import _core_anchor_candidate, scsv_elrc_v11_method
from fedfalsify.scsv_v11_study import SMOKE_SEED
from fedfalsify.legacy_v11_adapter import certify_v11_localized_from_core


def _diagnostic_projection(diagnostics):
    return tuple(
        (
            item.term,
            item.role_client_ids,
            item.outside_client_ids,
            item.rejection_reason,
        )
        for item in diagnostics
    )


def test_legacy_adapter_matches_frozen_v11_when_given_original_core():
    generated = generate_v10_benchmark(
        "quadratic_role_v10",
        seed=SMOKE_SEED,
        num_clients=4,
        balance_profile="balanced",
        role_profile="single",
        noise_ratio=0.10,
    )
    catalog = v10_catalog()
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    frozen = scsv_elrc_v11_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        target_mse=target_mse,
    )
    core = _core_anchor_candidate(frozen.anchor, catalog)

    adapted = certify_v11_localized_from_core(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        anchor=frozen.anchor,
        core_candidate=core,
    )

    assert adapted.candidate_deviations == frozen.candidate_deviations
    assert adapted.accepted_deviations == frozen.accepted_deviations
    assert adapted.final_structure == frozen.final_structure
    assert adapted.source_ambiguity == frozen.source_ambiguity
    assert adapted.global_ambiguity == frozen.global_ambiguity
    assert _diagnostic_projection(adapted.diagnostics) == _diagnostic_projection(frozen.diagnostics)


def test_legacy_adapter_rejects_exception_terms_in_supplied_core():
    generated = generate_v10_benchmark(
        "quadratic_role_v10",
        seed=SMOKE_SEED,
        num_clients=4,
        balance_profile="balanced",
        role_profile="single",
        noise_ratio=0.10,
    )
    catalog = v10_catalog()
    frozen = scsv_elrc_v11_method(
        generated.clients,
        catalog,
        seed=SMOKE_SEED,
        target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
    )
    exception = next(name for name in catalog.names() if catalog.get(name).kind == "exception")
    from fedfalsify.basis import CandidateEquation

    bad_core = CandidateEquation(("1", exception), (0.0, 0.1), "bad-core")
    import pytest

    with pytest.raises(ValueError):
        certify_v11_localized_from_core(
            generated.clients,
            catalog,
            seed=SMOKE_SEED,
            anchor=frozen.anchor,
            core_candidate=bad_core,
        )
