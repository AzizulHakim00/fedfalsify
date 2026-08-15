"""Compatibility entry point for robust Transactions expression parsing.

The original frozen-analysis implementation remains unchanged for auditability.
This module installs the complete notation normalizer before delegating to that
implementation.  It supports both ASCII ``I(x3>1)`` and the Unicode expression
notation emitted by FedFalsify, ``𝟙[x₃>1]``.
"""

from __future__ import annotations

import re

from . import transactions_analysis as _core


def normalize_expression(expression: str) -> str:
    """Normalize all expression notations present in frozen v0.6 evidence."""

    text = expression.strip().translate(_core._SUBSCRIPT_TRANSLATION)
    text = text.replace("²", "**2").replace("³", "**3")
    text = re.sub(
        r"(?:I\s*\(\s*x3\s*>\s*1(?:\.0+)?\s*\)|𝟙\s*\[\s*x3\s*>\s*1(?:\.0+)?\s*\])",
        "indicator(x3)",
        text,
    )
    text = text.replace("^", "**")
    text = re.sub(r"\bx([1-9])x([1-9])\b", r"x\1*x\2", text)
    text = re.sub(
        r"\)\s*(?=(?:sin|cos|indicator)\s*\(|x[1-9]\b|\()",
        ")*",
        text,
    )
    return re.sub(r"\s+", " ", text).strip()


# Core functions resolve ``normalize_expression`` through their module globals.
# Installing the audited compatibility normalizer therefore covers every parser
# call without duplicating the semantic-analysis implementation.
_core.normalize_expression = normalize_expression

SemanticMetrics = _core.SemanticMetrics
analyze_rows = _core.analyze_rows
evaluate_expression = _core.evaluate_expression
expression_complexity = _core.expression_complexity
run_analysis = _core.run_analysis
semantic_metrics_for_row = _core.semantic_metrics_for_row


def main() -> None:
    _core.main()


if __name__ == "__main__":
    main()
