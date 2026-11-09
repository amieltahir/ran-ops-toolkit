"""Tests for the formula engine, catalogue and KPI evaluator."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ranops.core import (
    CounterDef,
    KpiDef,
    KpiSample,
    Unit,
    UnitKind,
    evaluate_kpi,
    load_counters,
    load_kpis,
)
from ranops.core.formula import FormulaError, evaluate_formula, formula_names

T0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("formula", "values", "expected"),
    [
        ("100 * a / b", {"a": 98.0, "b": 100.0}, 98.0),
        ("-a + 2 * (b - 1)", {"a": 1.0, "b": 3.0}, 3.0),
        ("1.5", {}, 1.5),
    ],
)
def test_evaluate_formula(
    formula: str, values: dict[str, float], expected: float
) -> None:
    assert evaluate_formula(formula, values) == pytest.approx(expected)


def test_division_by_zero_is_none() -> None:
    assert evaluate_formula("a / b", {"a": 1.0, "b": 0.0}) is None


def test_missing_input_is_none() -> None:
    assert evaluate_formula("a / b", {"a": 1.0}) is None


def test_non_finite_input_is_none() -> None:
    assert evaluate_formula("a + 1", {"a": float("nan")}) is None


@pytest.mark.parametrize(
    "formula",
    [
        "__import__('os').system('true')",
        "a ** b",
        "a.real",
        "a[0]",
        "'text'",
        "True",
        "a if b else c",
        "lambda: 1",
        "a +",
    ],
)
def test_disallowed_formulas_rejected(formula: str) -> None:
    with pytest.raises(FormulaError):
        evaluate_formula(formula, {"a": 1.0, "b": 1.0, "c": 1.0})


def test_formula_names() -> None:
    assert formula_names("100 * succ / att") == {"succ", "att"}


def test_packaged_catalogue_is_consistent() -> None:
    counters = load_counters()
    kpis = load_kpis()
    assert kpis
    for kpi in kpis.values():
        assert set(kpi.inputs.values()) <= set(counters)


def test_kpi_rejects_undeclared_input() -> None:
    with pytest.raises(ValidationError):
        KpiDef(
            name="k",
            description="d",
            unit="percent",
            formula="a / b",
            inputs={"a": "x"},
            reference="r",
        )


def test_counter_def_requires_fields() -> None:
    with pytest.raises(ValidationError):
        CounterDef.model_validate({"name": "c"})


def test_evaluate_kpi_computes_value_and_inputs() -> None:
    kpi = load_kpis()["rrc_setup_success_rate"]
    sample = evaluate_kpi(
        kpi,
        "C1",
        T0,
        {"RRC.ConnEstabSucc.Sum": 95.0, "RRC.ConnEstabAtt.Sum": 100.0},
    )
    assert sample.value == pytest.approx(95.0)
    assert sample.inputs == {
        "RRC.ConnEstabSucc.Sum": 95.0,
        "RRC.ConnEstabAtt.Sum": 100.0,
    }


def test_evaluate_kpi_missing_or_zero_gives_none() -> None:
    kpi = load_kpis()["rrc_setup_success_rate"]
    assert evaluate_kpi(kpi, "C1", T0, {"RRC.ConnEstabAtt.Sum": 10.0}).value is None
    zero = {"RRC.ConnEstabSucc.Sum": 0.0, "RRC.ConnEstabAtt.Sum": 0.0}
    assert evaluate_kpi(kpi, "C1", T0, zero).value is None


def test_kpi_sample_inputs_are_immutable() -> None:
    source = {"c": 1.0}
    sample = KpiSample(cell_id="C1", kpi="k", period_start=T0, value=1.0, inputs=source)
    source["c"] = 2.0
    assert sample.inputs["c"] == 1.0
    with pytest.raises(TypeError):
        sample.inputs["c"] = 3.0  # type: ignore[index]


def test_kpi_sample_serialises_inputs_to_dict() -> None:
    sample = KpiSample(
        cell_id="C1", kpi="k", period_start=T0, value=1.0, inputs={"c": 1.0}
    )
    assert sample.model_dump()["inputs"] == {"c": 1.0}


def test_unit_model() -> None:
    unit = Unit(id="U1", node_id="N1", kind=UnitKind.BASEBAND)
    assert unit.kind is UnitKind.BASEBAND
    with pytest.raises(ValidationError):
        Unit.model_validate({"id": "U1", "node_id": "N1", "kind": "other"})
