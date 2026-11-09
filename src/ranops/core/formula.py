"""Restricted arithmetic formula parsing and evaluation (no ``eval``).

Only numeric literals, variable names, unary +/-, and the binary operators
``+ - * /`` and parentheses are allowed. Anything else is rejected when the
formula is parsed.
"""

from __future__ import annotations

import ast
import math
import operator
from collections.abc import Callable, Mapping

_BINARY: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class FormulaError(ValueError):
    """The formula is syntactically invalid or uses a disallowed construct."""


def parse_formula(formula: str) -> ast.expr:
    """Parse and validate ``formula``; raise ``FormulaError`` if not allowed."""
    try:
        tree = ast.parse(formula.strip(), mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"invalid formula {formula!r}: {exc.msg}") from exc
    _validate(tree.body)
    return tree.body


def _validate(node: ast.expr) -> None:
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        _validate(node.left)
        _validate(node.right)
    elif isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        _validate(node.operand)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int | float):
            raise FormulaError(f"unsupported literal: {node.value!r}")
    elif not isinstance(node, ast.Name):
        raise FormulaError(f"unsupported expression: {type(node).__name__}")


def formula_names(formula: str) -> frozenset[str]:
    """Return the variable names used by ``formula``."""
    return frozenset(
        n.id for n in ast.walk(parse_formula(formula)) if isinstance(n, ast.Name)
    )


def evaluate_formula(formula: str, values: Mapping[str, float]) -> float | None:
    """Evaluate ``formula``; return ``None`` for missing inputs, division by zero
    or a non-finite result."""
    try:
        result = _eval(parse_formula(formula), values)
    except (KeyError, ZeroDivisionError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _eval(node: ast.expr, values: Mapping[str, float]) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)
    if isinstance(node, ast.Name):
        value = values[node.id]
        if not math.isfinite(value):
            raise KeyError(node.id)
        return float(value)
    if isinstance(node, ast.UnaryOp):
        return _UNARY[type(node.op)](_eval(node.operand, values))
    if isinstance(node, ast.BinOp):
        return _BINARY[type(node.op)](
            _eval(node.left, values), _eval(node.right, values)
        )
    raise FormulaError(f"unsupported expression: {type(node).__name__}")
