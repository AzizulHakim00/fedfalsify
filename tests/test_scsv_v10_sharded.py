from dataclasses import asdict

from fedfalsify.scsv_v10_sharded import SPENT_SEEDS, _row_from_csv
from fedfalsify.scsv_v10_study import DEVELOPMENT_SEEDS, METHODS, SMOKE_SEED, V10StudyRow, _scientific_conditions


def test_each_v10_fresh_seed_defines_exactly_120_conditions_and_720_method_rows():
    all_conditions = []
    for seed in DEVELOPMENT_SEEDS:
        conditions = tuple(_scientific_conditions((seed,)))
        assert len(conditions) == 120
        assert len(set(conditions)) == 120
        assert {item[-1] for item in conditions} == {seed}
        assert len(conditions) * len(METHODS) == 720
        all_conditions.extend(conditions)
    assert len(all_conditions) == 600
    assert len(set(all_conditions)) == 600


def test_v10_fresh_namespace_is_disjoint_from_smoke_and_registered_spent_seeds():
    assert SMOKE_SEED not in set(DEVELOPMENT_SEEDS)
    assert not (set(DEVELOPMENT_SEEDS) & SPENT_SEEDS)
    assert {26101, 26102, 26103, 26104, 26105}.issubset(SPENT_SEEDS)
    assert {27101, 27102, 27103, 27104, 27105}.issubset(SPENT_SEEDS)


def test_v10_csv_roundtrip_parser_preserves_row_types():
    row = V10StudyRow(
        family="quadratic_role_v10", noise_ratio=0.1, samples_per_client=100, num_clients=4,
        balance_profile="balanced", role_profile="single", seed=28101, method="scsv-aqcc-v10-full",
        exact_recovery=1.0, term_precision=1.0, term_recall=1.0, test_nmse=0.01, train_mse=0.02,
        deviation_tp=1, deviation_fp=0, deviation_fn=0, deviation_precision=1.0, deviation_recall=1.0,
        all_true_deviations_recovered=1.0, spurious_deviation_accepted=0.0, runtime_seconds=1.2,
        communication_bytes=123, discovered_terms="x3^2", accepted_deviations="dev",
        anchor_structure="1;x3^2", ordinary_anchor_structure="1;x3^2", quarantined_anchor_exceptions="",
        recertified_anchor_exceptions="", removed_anchor_exceptions="", final_structure="1;x3^2;dev",
        bank_terms="x3^2;dev", candidate_deviations="dev", role_proposed_candidates="dev",
        ordinary_anchor_violation_count=0, quarantine_integrity_violation_count=0,
        role_integrity_violation_count=0, source_qualification_violation_count=0,
        pair_invariant_violation_count=0, client_consensus_violation_count=0,
        diagnostics_json="[]", source_diagnostics_json="[]", expression="x", stop_reason="ok",
    )
    parsed = _row_from_csv({key: str(value) for key, value in asdict(row).items()})
    assert parsed == row
