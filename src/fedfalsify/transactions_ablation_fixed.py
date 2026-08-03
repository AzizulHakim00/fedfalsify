"""Scientifically complete Transactions ablation entry point.

The original ablation runner remains available for audit history.  This module
ensures that the ``fedfalsify-no-heterogeneity`` condition removes coefficient
support and heterogeneity evidence from both discovery and core replacement,
not only from the discovery loop.
"""

from __future__ import annotations

from time import perf_counter

from . import transactions_ablation as _core


def coefficient_certificate_settings(
    method: str,
) -> tuple[bool, dict[str, float]]:
    """Return discovery and replacement settings for coefficient evidence."""

    if method != "fedfalsify-no-heterogeneity":
        return True, {}
    return False, {
        "min_incoming_support_fraction": 0.0,
        "min_incoming_sign_agreement": 0.0,
        "min_incoming_local_z": 0.0,
        "min_incoming_global_z": 0.0,
        "coefficient_prune_z": 0.0,
    }


def _run_fedfalsify_variant(
    generated,
    *,
    method: str,
    max_terms: int,
    seed: int,
):
    include_exception_terms = not (
        method == "fedfalsify-no-exception-module"
        and generated.scenario == "exception"
    )
    catalog = (
        _core.benchmark_catalog(scenario=generated.scenario)
        if include_exception_terms
        else _core.BenchmarkTermCatalog(include_exception_terms=False)
    )
    clients = _core._clients(generated, catalog)
    use_heterogeneity, replacement_kwargs = coefficient_certificate_settings(method)
    target_mse = max(generated.noise_std**2 * 2.5, 1e-8)
    start = perf_counter()
    base = _core.fedfalsify_method(
        clients,
        catalog,
        max_terms=max_terms,
        target_mse=target_mse,
        min_repair_score=0.05,
        use_coefficient_heterogeneity=use_heterogeneity,
    )
    candidate = base.candidate
    communication = base.communication_bytes
    evaluations = base.rounds
    stop_reason = base.stop_reason

    if method != "fedfalsify-no-replacement":
        if method == "fedfalsify-no-nondegradation":
            replacement_kwargs = {
                **replacement_kwargs,
                "min_nonworsening_client_fraction": 0.0,
                "client_worsening_tolerance": 10.0,
            }
        refined = _core.FederatedCoreReplacement(
            clients,
            catalog,
            max_rounds=3,
            max_removed_terms=2,
            **replacement_kwargs,
        ).refine(candidate)
        candidate = refined.candidate
        communication += refined.communication_bytes
        evaluations += len(refined.replacements)
        stop_reason = f"{stop_reason}; {refined.stop_reason}"

    return _core._evaluate_candidate(
        generated,
        candidate=candidate,
        catalog=catalog,
        method=method,
        seed=seed,
        runtime_seconds=perf_counter() - start,
        communication_bytes=communication,
        search_evaluations=evaluations,
        stop_reason=stop_reason,
    )


# Core matrix construction resolves this helper through module globals.
_core._run_fedfalsify_variant = _run_fedfalsify_variant

run_ablation_study = _core.run_ablation_study
validate_development_seeds = _core.validate_development_seeds


def main() -> None:
    _core.main()


if __name__ == "__main__":
    main()
