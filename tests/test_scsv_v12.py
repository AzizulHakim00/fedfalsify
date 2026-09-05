import pytest

from fedfalsify.scsv_v10_benchmarks import generate_v10_benchmark, v10_catalog
from fedfalsify.scsv_v11 import SCSVELRCV11Output
from fedfalsify.scsv_v11_study import SMOKE_SEED
from fedfalsify.scsv_v12 import PHASE3_METHODS, SCSVV12Output, run_scsv_v12_branches


@pytest.fixture(scope="module")
def phase3_branches():
    generated = generate_v10_benchmark(
        "quadratic_role_v10",
        seed=SMOKE_SEED,
        num_clients=4,
        balance_profile="balanced",
        role_profile="single",
        noise_ratio=0.10,
    )
    outputs = run_scsv_v12_branches(
        generated.clients,
        v10_catalog(),
        seed=SMOKE_SEED,
        target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
    )
    return outputs


def test_phase3_returns_exact_four_method_order(phase3_branches):
    assert tuple(item.method for item in phase3_branches) == PHASE3_METHODS
    assert len(phase3_branches) == 4
    assert isinstance(phase3_branches[0], SCSVELRCV11Output)
    assert all(isinstance(item, SCSVV12Output) for item in phase3_branches[1:])


def test_ablation_isolation_and_v11_remains_immutable(phase3_branches):
    v11, scr_only, ncee_only, full = phase3_branches

    assert scr_only.shared_mode == "scr"
    assert scr_only.localized_mode == "v11-adapter"
    assert ncee_only.shared_mode == "frozen-v11"
    assert ncee_only.localized_mode == "ncee"
    assert full.shared_mode == "scr"
    assert full.localized_mode == "ncee"

    assert ncee_only.shared_structure == v11.ordinary_anchor_structure
    assert scr_only.shared_structure == full.shared_structure
    assert v11.final_structure == tuple(v11.candidate.active_terms)


def test_final_refit_preserves_frozen_term_identity(phase3_branches):
    for branch in phase3_branches[1:]:
        assert tuple(branch.candidate.active_terms) == tuple(branch.final_structure)
        assert set(branch.accepted_deviations).issubset(set(branch.final_structure))
        assert set(branch.shared_structure).issubset(set(branch.final_structure))


def test_mechanism_ledger_is_complete_for_every_phase3_branch(phase3_branches):
    for branch in phase3_branches[1:]:
        ledger = branch.ledger
        assert ledger.shared_candidate_family
        assert isinstance(ledger.shared_diagnostics, tuple)
        assert isinstance(ledger.localized_candidate_family, tuple)
        assert isinstance(ledger.discovery_localized_diagnostics, tuple)
        assert isinstance(ledger.selector_diagnostics, tuple)
        assert isinstance(ledger.probe_diagnostics, tuple)
        assert ledger.final_shared_structure == branch.shared_structure
        assert ledger.final_complete_structure == branch.final_structure


def test_no_phase3_branch_uses_blocked_seed_namespace():
    assert SMOKE_SEED == 29001
    assert SMOKE_SEED not in set(range(29301, 29311))
    assert SMOKE_SEED < 11001 or SMOKE_SEED > 11999
