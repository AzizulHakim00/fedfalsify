from studies.phase3a_parity import run_parity


def test_phase3a_parity_audit_is_engineering_only_and_passes_six_smoke_conditions():
    report = run_parity()
    assert report.seed == 29001
    assert report.conditions == 6
    assert report.passed is True
    assert len(report.records) == 6
    assert all(record.seed == 29001 for record in report.records)
    assert all(record.packet_equivalent for record in report.records)
    assert all(record.aggregate_equivalent for record in report.records)
    assert all(record.least_squares_equivalent for record in report.records)
