"""Serialization-safe and exception-aware adaptive Transactions entry point."""

from __future__ import annotations

from dataclasses import asdict

# Import first so the core adaptive runner resolves the corrected exception
# observability semantics through the patched certificate module globals.
from . import certificate_tree_fixed as _certificate_tree_fixed  # noqa: F401
from . import transactions_adaptive_tree as _core
from .statistics import (
    mcnemar_exact as _mcnemar_exact,
    paired_bootstrap_difference as _paired_bootstrap_difference,
)


def _serializable_mcnemar(reference, comparator):
    return asdict(_mcnemar_exact(reference, comparator))


def _serializable_bootstrap(reference, comparator, **kwargs):
    return asdict(_paired_bootstrap_difference(reference, comparator, **kwargs))


_core.mcnemar_exact = _serializable_mcnemar
_core.paired_bootstrap_difference = _serializable_bootstrap

AdaptiveTreeRow = _core.AdaptiveTreeRow
METHODS = _core.METHODS
run_study = _core.run_study
summarize = _core.summarize
validate_fresh_seeds = _core.validate_fresh_seeds
write_csv = _core.write_csv


def main() -> None:
    _core.main()


if __name__ == "__main__":
    main()
