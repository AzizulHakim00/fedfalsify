import pytest

from fedfalsify.benchmarks import benchmark_catalog, generate_benchmark
from fedfalsify.scsv_v6 import scsv_cert_method
from fedfalsify.scsv_v6_study import _validate_seeds


def _smoke_generated(*, scenario="complementary"):
    return generate_benchmark(
        "poly3",
        scenario=scenario,
        samples_per_client=120,
        noise_ratio=0.20,
        seed=19001,
        num_clients=4,
    )


def test_v6_seed_firewall():
    _validate_seeds((19001,), allow_engineering_smoke=True)
    _validate_seeds((19101,), allow_engineering_smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((17101,), allow_engineering_smoke=False)
    with pytest.raises(ValueError):
        _validate_seeds((19001,), allow_engineering_smoke=False)


def test_v6_operational_structure_is_selector_structure():
    generated = _smoke_generated()
    output = scsv_cert_method(
        generated.clients,
        benchmark_catalog(scenario=generated.scenario),
        seed=19001,
        target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
    )
    assert output.candidate.active_terms == output.selector_structure
    assert output.candidate_sets_evaluated <= 638
    assert len(output.bank.candidate_terms) <= 10


def test_probe_is_non_destructive_even_when_forced_to_fail(monkeypatch):
    import fedfalsify.scsv_v6 as module

    generated = _smoke_generated()
    monkeypatch.setattr(module, "_validate_selector_set", lambda *args, **kwargs: (False, ()))
    output = module.scsv_cert_method(
        generated.clients,
        benchmark_catalog(scenario=generated.scenario),
        seed=19001,
        target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
    )
    assert output.probe_certified is False
    assert output.candidate.active_terms == output.selector_structure


def test_no_score_proposer_ablation_uses_same_non_destructive_rule():
    generated = _smoke_generated(scenario="exception")
    output = scsv_cert_method(
        generated.clients,
        benchmark_catalog(scenario=generated.scenario),
        seed=19001,
        target_mse=max(generated.noise_std**2 * 2.5, 1e-8),
        use_score_proposer=False,
    )
    assert output.candidate.active_terms == output.selector_structure
    assert output.candidate_sets_evaluated <= 638
