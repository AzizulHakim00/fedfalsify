"""Extended Transactions ablation entry point with a pooled-equivalent
federated catalog comparator.

This wrapper preserves the archived development runner while extending future
validation matrices with ``federated-information-catalog``.  The comparator
uses aggregate sufficient statistics and the same information criterion as the
pooled centralized catalog baseline.
"""

from __future__ import annotations

from . import transactions_ablation as _core
from . import transactions_ablation_fixed as _fixed
from .federated_catalog import federated_information_forward


EXTENDED_VARIANTS = (
    "fedfalsify-full",
    "fedfalsify-no-heterogeneity",
    "fedfalsify-no-replacement",
    "fedfalsify-no-nondegradation",
    "score-only-federated",
    "centralized-catalog",
    "federated-information-catalog",
    "local-consensus",
    "fedfalsify-no-exception-module",
)

_original_baseline_variant = _core._run_baseline_variant


def _run_baseline_variant(
    generated,
    *,
    method: str,
    max_terms: int,
    seed: int,
):
    if method != "federated-information-catalog":
        return _original_baseline_variant(
            generated,
            method=method,
            max_terms=max_terms,
            seed=seed,
        )

    catalog = _core.benchmark_catalog(scenario=generated.scenario)
    clients = _core._clients(generated, catalog)
    output = federated_information_forward(
        clients,
        catalog,
        max_terms=max_terms,
    )
    return _core._evaluate_candidate(
        generated,
        candidate=output.candidate,
        catalog=catalog,
        method=method,
        seed=seed,
        runtime_seconds=output.runtime_seconds,
        communication_bytes=output.communication_bytes,
        search_evaluations=output.rounds,
        stop_reason=output.stop_reason,
    )


# Apply both audited extensions before delegating to the original matrix code.
_core._run_fedfalsify_variant = _fixed._run_fedfalsify_variant
_core._run_baseline_variant = _run_baseline_variant
_core.DEFAULT_VARIANTS = EXTENDED_VARIANTS

run_ablation_study = _core.run_ablation_study
validate_development_seeds = _core.validate_development_seeds


def main() -> None:
    _core.main()


if __name__ == "__main__":
    main()
