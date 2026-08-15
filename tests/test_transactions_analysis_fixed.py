from __future__ import annotations

import numpy as np

from fedfalsify.transactions_analysis_fixed import (
    evaluate_expression,
    normalize_expression,
)


def test_unicode_blackboard_indicator_notation() -> None:
    x = np.asarray(
        [
            [0.5, 0.25, 2.0, 0.0],
            [-0.5, -0.25, 0.5, 0.0],
        ]
    )
    prediction, normalized = evaluate_expression(
        "0.75·𝟙[x₃>1]·x₃²", x
    )
    np.testing.assert_allclose(prediction, np.asarray([3.0, 0.0]))
    assert normalized == "0.75*indicator(x3)*x3**2"


def test_ascii_indicator_notation_remains_supported() -> None:
    assert (
        normalize_expression("0.75·I(x₃>1)·x₃²")
        == "0.75*indicator(x3)*x3**2"
    )
