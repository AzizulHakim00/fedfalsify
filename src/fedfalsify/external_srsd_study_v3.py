"""Admissible SRSD v3 runner with unique truth terms and scale-aware metrics."""

from __future__ import annotations

import numpy as np

from . import external_srsd_study_fixed as _fixed
from .basis import BasisTerm
from .external_common import FlexibleTermCatalog


PROBLEMS = _fixed.PROBLEMS


def build_catalog(spec, feature_count: int, scaling, *, include_truth: bool) -> FlexibleTermCatalog:
    """Build a catalog with exactly one representation of supported truth.

    Algebraically identical primitive terms are excluded in both conditions.
    The supported condition adds the single named truth term; the misspecified
    condition omits it. This implements the frozen protocol literally and makes
    strict recovery identifiable rather than dependent on an arbitrary alias.
    """

    means = np.asarray(scaling.x_mean, dtype=float)
    scales = np.asarray(scaling.x_scale, dtype=float)

    def physical(x: np.ndarray) -> np.ndarray:
        return np.asarray(x, dtype=float) * scales + means

    terms: list[BasisTerm] = [BasisTerm("1", lambda x: np.ones(len(x)), 1, "1")]
    if include_truth:
        terms.append(BasisTerm(
            spec.truth_name,
            lambda x, problem=spec: problem.truth_values(physical(x)),
            3,
            spec.truth_display,
        ))

    exact_square_problem = spec.problem == "feynman-ii.27.18"
    for index in range(feature_count):
        prefix = "dummy" if index >= spec.true_variables else "x"
        name = f"{prefix}{index}"
        terms.append(BasisTerm(name, lambda x, i=index: physical(x)[:, i], 1, name))
        if not (exact_square_problem and index == 0):
            terms.append(BasisTerm(
                f"{name}^2",
                lambda x, i=index: physical(x)[:, i] ** 2,
                2,
                f"{name}²",
            ))
        terms.extend([
            BasisTerm(
                f"sin({name})",
                lambda x, i=index: np.sin(physical(x)[:, i]),
                2,
                f"sin({name})",
            ),
            BasisTerm(
                f"cos({name})",
                lambda x, i=index: np.cos(physical(x)[:, i]),
                2,
                f"cos({name})",
            ),
        ])

    exact_product_problems = {"feynman-i.12.1", "feynman-i.14.3"}
    for left in range(feature_count):
        for right in range(left + 1, feature_count):
            if (
                spec.problem in exact_product_problems
                and left == 0
                and right == 1
            ):
                continue
            name = f"v{left}*v{right}"
            terms.append(BasisTerm(
                name,
                lambda x, a=left, b=right: physical(x)[:, a] * physical(x)[:, b],
                2,
                name,
            ))
    return FlexibleTermCatalog(terms)


def main() -> None:
    # The v2 runner owns download, hashing, fitting, and output serialization.
    # Replacing only its catalog constructor keeps the repair scope explicit.
    _fixed.build_catalog = build_catalog
    _fixed.main()


if __name__ == "__main__":
    main()
