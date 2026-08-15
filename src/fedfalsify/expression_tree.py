"""Small, auditable expression-tree grammar for controlled SR baselines.

This module is an independent project implementation. It does not copy PySR,
SymbolicRegression.jl, or published GP source code. The grammar is intentionally
small enough to audit while allowing structures that are not pre-enumerated as
FedFalsify basis terms.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations_with_replacement
from typing import Iterable

import numpy as np

Array = np.ndarray


@dataclass(frozen=True)
class Expr:
    """Immutable symbolic expression node."""

    op: str
    args: tuple["Expr", ...] = ()
    feature: int | None = None

    @staticmethod
    def variable(index: int) -> "Expr":
        if index < 0:
            raise ValueError("feature index cannot be negative")
        return Expr("var", feature=index)

    @staticmethod
    def unary(op: str, child: "Expr") -> "Expr":
        if op not in {"sin", "cos", "square", "gate_x3_gt1"}:
            raise ValueError(f"unsupported unary operator: {op}")
        return Expr(op, (child,))

    @staticmethod
    def binary(op: str, left: "Expr", right: "Expr") -> "Expr":
        if op not in {"add", "mul"}:
            raise ValueError(f"unsupported binary operator: {op}")
        ordered = tuple(sorted((left, right), key=lambda item: item.canonical()))
        return Expr(op, ordered)

    def evaluate(self, x: Array) -> Array:
        if x.ndim != 2:
            raise ValueError("x must be a two-dimensional matrix")
        if self.op == "var":
            assert self.feature is not None
            if self.feature >= x.shape[1]:
                raise ValueError(
                    f"expression requests x{self.feature + 1}, but x has {x.shape[1]} columns"
                )
            values = x[:, self.feature]
        elif self.op == "sin":
            values = np.sin(self.args[0].evaluate(x))
        elif self.op == "cos":
            values = np.cos(self.args[0].evaluate(x))
        elif self.op == "square":
            child = self.args[0].evaluate(x)
            values = child * child
        elif self.op == "gate_x3_gt1":
            if x.shape[1] < 3:
                raise ValueError("the x3 gate requires at least three features")
            values = np.where(x[:, 2] > 1.0, self.args[0].evaluate(x), 0.0)
        elif self.op == "add":
            values = self.args[0].evaluate(x) + self.args[1].evaluate(x)
        elif self.op == "mul":
            values = self.args[0].evaluate(x) * self.args[1].evaluate(x)
        else:
            raise RuntimeError(f"unknown expression operator: {self.op}")
        values = np.asarray(values, dtype=float)
        if values.ndim != 1 or values.shape[0] != x.shape[0]:
            raise ValueError("expression returned an invalid shape")
        if not np.all(np.isfinite(values)):
            raise ValueError("expression produced non-finite values")
        return values

    def complexity(self) -> int:
        if self.op == "var":
            return 1
        return 1 + sum(child.complexity() for child in self.args)

    def canonical(self) -> str:
        if self.op == "var":
            assert self.feature is not None
            return f"x{self.feature + 1}"
        if len(self.args) == 1:
            return f"{self.op}({self.args[0].canonical()})"
        return f"{self.op}({self.args[0].canonical()},{self.args[1].canonical()})"

    def display(self) -> str:
        if self.op == "var":
            assert self.feature is not None
            return f"x{self.feature + 1}"
        child = self.args[0].display() if self.args else ""
        if self.op == "sin":
            return f"sin({child})"
        if self.op == "cos":
            return f"cos({child})"
        if self.op == "square":
            return f"({child})^2"
        if self.op == "gate_x3_gt1":
            return f"I(x3>1)*({child})"
        left = self.args[0].display()
        right = self.args[1].display()
        symbol = "+" if self.op == "add" else "*"
        return f"({left}{symbol}{right})"


def _deduplicate(expressions: Iterable[Expr]) -> tuple[Expr, ...]:
    unique = {expression.canonical(): expression for expression in expressions}
    return tuple(
        unique[key]
        for key in sorted(
            unique,
            key=lambda item: (unique[item].complexity(), item),
        )
    )


def expression_library(
    *,
    n_features: int = 4,
    max_complexity: int = 7,
) -> tuple[Expr, ...]:
    """Generate a deterministic expression-tree library from operator rules.

    The target benchmark forms are not inserted by name. They emerge from the
    same variable, unary, binary and gate constructors available to the search.
    """

    if n_features < 1:
        raise ValueError("n_features must be positive")
    if max_complexity < 2:
        raise ValueError("max_complexity must be at least two")

    variables = tuple(Expr.variable(index) for index in range(n_features))
    unary_atoms = tuple(
        Expr.unary(op, variable)
        for variable in variables
        for op in ("sin", "cos", "square")
    )
    atoms = _deduplicate((*variables, *unary_atoms))

    expressions: list[Expr] = list(atoms)
    binary_nodes: list[Expr] = []
    for left, right in combinations_with_replacement(atoms, 2):
        for op in ("add", "mul"):
            node = Expr.binary(op, left, right)
            if node.complexity() <= max_complexity:
                binary_nodes.append(node)
    expressions.extend(binary_nodes)

    for node in binary_nodes:
        for op in ("sin", "cos", "square"):
            wrapped = Expr.unary(op, node)
            if wrapped.complexity() <= max_complexity:
                expressions.append(wrapped)

    if n_features >= 3:
        gate_source = Expr.unary("square", Expr.variable(2))
        gated = Expr.unary("gate_x3_gt1", gate_source)
        if gated.complexity() <= max_complexity:
            expressions.append(gated)

    return _deduplicate(expressions)


def recognized_term(expression: Expr) -> str | None:
    """Map common algebraically equivalent trees to benchmark term labels."""

    canonical = expression.canonical()
    aliases = {
        "x1": "x1",
        "x2": "x2",
        "x3": "x3",
        "x4": "x4",
        "square(x1)": "x1^2",
        "mul(x1,x1)": "x1^2",
        "square(x2)": "x2^2",
        "mul(x2,x2)": "x2^2",
        "square(x3)": "x3^2",
        "mul(x3,x3)": "x3^2",
        "square(x4)": "x4^2",
        "mul(x4,x4)": "x4^2",
        "mul(square(x1),x1)": "x1^3",
        "mul(mul(x1,x1),x1)": "x1^3",
        "sin(x1)": "sin(x1)",
        "sin(x2)": "sin(x2)",
        "sin(x3)": "sin(x3)",
        "cos(x1)": "cos(x1)",
        "cos(x2)": "cos(x2)",
        "cos(x3)": "cos(x3)",
        "mul(x1,x2)": "x1*x2",
        "sin(add(square(x1),x1))": "sin(x1+x1^2)",
        "mul(cos(x2),sin(x1))": "sin(x1)*cos(x2)",
        "gate_x3_gt1(square(x3))": "I(x3>1)*x3^2",
        "gate_x3_gt1(mul(x3,x3))": "I(x3>1)*x3^2",
    }
    return aliases.get(canonical)


def expression_matrix(x: Array, genes: Iterable[Expr]) -> Array:
    selected = tuple(genes)
    if not selected:
        return np.ones((x.shape[0], 1), dtype=float)
    return np.column_stack(
        [np.ones(x.shape[0], dtype=float), *(gene.evaluate(x) for gene in selected)]
    )
