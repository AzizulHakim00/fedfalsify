from fedfalsify.confirmatory import METHODS, run_study, summarize
from fedfalsify.confirmatory_report import add_holm_correction


def test_confirmatory_smoke_produces_matched_rows_and_statistics() -> None:
    rows = run_study(
        benchmarks=("base",),
        scenarios=("complementary",),
        noise_ratios=(0.03,),
        samples_per_client=(60,),
        client_counts=(4,),
        seeds=(5001,),
        methods=METHODS,
        population_size=10,
        generations=1,
        max_genes=3,
    )
    assert len(rows) == len(METHODS)
    assert {row.method for row in rows} == set(METHODS)
    assert all(row.runtime_seconds >= 0 for row in rows)
    report = summarize(rows, bootstrap_resamples=300)
    assert set(report["methods"]) == set(METHODS)
    assert len(report["paired"]) == len(METHODS) - 1
    corrected = add_holm_correction(report)
    assert corrected["multiple_testing"]["method"] == "Holm step-down"
    for details in corrected["paired"].values():
        assert "holm_adjusted_p_value" in details["mcnemar"]
