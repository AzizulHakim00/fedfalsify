from dataclasses import replace
import inspect

import pytest

from fedfalsify import scsv_v9_study as v9s
from fedfalsify.scsv_v9_recovery import (
    FROZEN_GATE_KEYS,
    METHODS,
    RECOVERY_SEEDS,
    RECOVERY_SMOKE_SEED,
    SPENT_V9_SEEDS,
    _expected_condition_keys,
    audit_rows,
    summarize_recovery,
)


def _dummy_row(condition, method):
    family, num_clients, balance, role_profile, noise, seed = condition
    return v9s.V9StudyRow(
        family=family,
        noise_ratio=float(noise),
        samples_per_client=100,
        num_clients=int(num_clients),
        balance_profile=balance,
        role_profile=role_profile,
        seed=int(seed),
        method=method,
        exact_recovery=1.0,
        term_precision=1.0,
        term_recall=1.0,
        test_nmse=0.0,
        train_mse=0.0,
        deviation_tp=1,
        deviation_fp=0,
        deviation_fn=0,
        deviation_precision=1.0,
        deviation_recall=1.0,
        all_true_deviations_recovered=1.0,
        spurious_deviation_accepted=0.0,
        runtime_seconds=1.0,
        communication_bytes=100,
        discovered_terms="",
        accepted_deviations="",
        added_sources="",
        anchor_structure="1;x1",
        final_structure="1;x1",
        bank_terms="",
        candidate_deviations="",
        role_proposed_candidates="",
        role_hypothesis_positive=0.0,
        role_integrity_violation_count=0,
        source_qualification_violation_count=0,
        pair_invariant_violation_count=0,
        evidence_fusion_violation_count=0,
        source_ambiguity=0.0,
        global_ambiguity=0.0,
        diagnostics_json="[]",
        source_diagnostics_json="[]",
        expression="0",
        stop_reason="synthetic recovery firewall row",
    )


def _rows_for_seeds(seeds):
    return [
        _dummy_row(condition, method)
        for condition in v9s._scientific_conditions(seeds)
        for method in METHODS
    ]


def test_recovery_seed_namespace_is_new_and_disjoint():
    assert RECOVERY_SMOKE_SEED == 27001
    assert RECOVERY_SEEDS == (27101, 27102, 27103, 27104, 27105)
    assert not set(RECOVERY_SEEDS) & set(SPENT_V9_SEEDS)
    assert RECOVERY_SMOKE_SEED not in RECOVERY_SEEDS
    assert RECOVERY_SMOKE_SEED not in SPENT_V9_SEEDS


def test_each_recovery_seed_defines_exactly_120_unique_conditions():
    combined = set()
    for seed in RECOVERY_SEEDS:
        keys = _expected_condition_keys((seed,))
        assert len(keys) == 120
        assert not combined & keys
        combined |= keys
    assert len(combined) == 600


def test_single_shard_audit_requires_720_rows_and_all_six_methods():
    seed = RECOVERY_SEEDS[0]
    rows = _rows_for_seeds((seed,))
    assert len(rows) == 720
    audit_rows(rows, expected_seeds=(seed,), expected_conditions=120, expected_rows=720)

    with pytest.raises(ValueError):
        audit_rows(rows[:-1], expected_seeds=(seed,), expected_conditions=120, expected_rows=720)


def test_combined_recovery_audit_requires_3600_rows_and_600_conditions():
    rows = _rows_for_seeds(RECOVERY_SEEDS)
    assert len(rows) == 3600
    audit_rows(rows, expected_seeds=RECOVERY_SEEDS, expected_conditions=600, expected_rows=3600)


def test_spent_seed_is_rejected_from_recovery_evidence():
    seed = RECOVERY_SEEDS[0]
    rows = _rows_for_seeds((seed,))
    contaminated = list(rows)
    contaminated[0] = replace(contaminated[0], seed=SPENT_V9_SEEDS[0])
    with pytest.raises(ValueError):
        audit_rows(
            contaminated,
            expected_seeds=(seed,),
            expected_conditions=120,
            expected_rows=720,
        )


def test_recovery_gate_keys_are_exactly_the_original_v9_a_to_w_keys():
    source = inspect.getsource(v9s.summarize)
    assert len(FROZEN_GATE_KEYS) == 23
    for key in FROZEN_GATE_KEYS:
        assert f'"{key}"' in source


def test_recovery_summary_reuses_original_gate_implementation_and_restores_constants():
    rows = _rows_for_seeds(RECOVERY_SEEDS)
    old_development = v9s.DEVELOPMENT_SEEDS
    old_smoke = v9s.SMOKE_SEED
    summary = summarize_recovery(rows)
    assert tuple(summary["development_gate"]["criteria"].keys()) == FROZEN_GATE_KEYS
    assert summary["seeds"] == list(RECOVERY_SEEDS)
    assert summary["status"] == "scsv-rcef-v9-infrastructure-recovery"
    assert "27101--27105" in summary["development_gate"]["scientific_boundary"]
    assert v9s.DEVELOPMENT_SEEDS == old_development
    assert v9s.SMOKE_SEED == old_smoke
