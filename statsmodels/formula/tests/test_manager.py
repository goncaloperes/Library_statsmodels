import numpy as np
import pandas as pd
import pytest

import statsmodels.formula
from statsmodels.formula._manager import FormulaManager, LinearConstraintValues
from statsmodels.formula._manager import FormulaManager

HAS_FORMULAIC = HAS_PATSY = False
try:
    import patsy

    HAS_PATSY = True
except ImportError:
    pass

try:
    import formulaic

    HAS_FORMULAIC = True
except ImportError:
    pass

has_formulaic = pytest.mark.skipif(
    HAS_FORMULAIC, reason="can only run when patsy is installed and formulaic is not."
)

has_patsy = pytest.mark.skipif(
    HAS_PATSY, reason="can only run when formulaic is installed and patsy is not."
)

require_formulaic = pytest.mark.skipif(not HAS_FORMULAIC, reason="Requires formulaic")

ENGINES = ["patsy"]
if HAS_FORMULAIC:
    ENGINES += ["formulaic"]

@pytest.fixture(params=ENGINES)
def engine(request):
    return request.param


def g(x):
    return x**2


@pytest.fixture
def data(request):
    return pd.DataFrame(
        {
            "y": [1, 2, 3, 4, 5, 6, 7.2],
            "x": [1, 2, 3, 9, 8, 7, 6.3],
            "z": [-1, 2, -3, 9, -8, 7, -6.1],
            "c": ["a", "a", "b", "a", "b", "b", "b"],
        }
    )


def check_type(arr, engine):
    if engine == "patsy":
        return isinstance(arr, pd.DataFrame)
    else:
        return isinstance(arr, formulaic.ModelMatrix)


def test_engine_options_engine():
    default = statsmodels.formula.options.formula_engine
    assert default in ("patsy", "formulaic")

    statsmodels.formula.options.formula_engine = "patsy"
    mgr = FormulaManager()
    assert mgr.engine == "patsy"
    mgr = FormulaManager(engine="formulaic")
    assert mgr.engine == "formulaic"

    statsmodels.formula.options.formula_engine = "formulaic"
    mgr = FormulaManager()
    assert mgr.engine == "formulaic"

    mgr = FormulaManager(engine="patsy")
    assert mgr.engine == "patsy"

    statsmodels.formula.options.formula_engine = default


def test_engine_options_engine(engine):
    default = statsmodels.formula.options.formula_engine
    assert default in ("patsy", "formulaic")

    statsmodels.formula.options.formula_engine = engine
    mgr = FormulaManager()
    assert mgr.engine == engine

    if HAS_FORMULAIC:
        statsmodels.formula.options.formula_engine = "formulaic"
        mgr = FormulaManager()
        assert mgr.engine == "formulaic"
        if HAS_PATSY:
            mgr = FormulaManager(engine="patsy")
            assert mgr.engine == "patsy"

    statsmodels.formula.options.formula_engine = default


@pytest.mark.parametrize("ordering", ["degree", "sort", "none"])
def test_engine_options_order(ordering):
    default = statsmodels.formula.options.ordering
    assert default in ("degree", "sort", "none")

    statsmodels.formula.options.ordering = ordering
    assert statsmodels.formula.options.ordering == ordering
    statsmodels.formula.options.ordering = default

    with pytest.raises(ValueError):
        statsmodels.formula.options.ordering = "unknown"


@require_formulaic
def test_engine_options_order_effect(data):
    default = statsmodels.formula.options.ordering
    statsmodels.formula.options.ordering = "degree"
    mgr = FormulaManager(engine="formulaic")
    _, rhs0 = mgr.get_arrays("y ~ 1 + x + z + c", data)
    statsmodels.formula.options.ordering = "sort"
    _, rhs1 = mgr.get_arrays("y ~ 1 + x + z + c", data)
    statsmodels.formula.options.ordering = "none"
    _, rhs2 = mgr.get_arrays("y ~ 1 + x + c + z", data)
    assert len(rhs0.columns) == 4
    assert len(rhs1.columns) == 4
    assert len(rhs2.columns) == 4
    assert list(rhs0.columns) != list(rhs1.columns)
    assert list(rhs0.columns) != list(rhs2.columns)
    assert list(rhs1.columns) != list(rhs2.columns)
    statsmodels.formula.options.ordering = default


def test_engine_options_err():
    with pytest.raises(ValueError, match="Invalid formula engine option"):
        statsmodels.formula.options.formula_engine = "unknown"


def test_engine(engine):
    mgr = FormulaManager(engine=engine)
    assert mgr.engine == engine

    with pytest.raises(ValueError):
        FormulaManager(engine="other")


def test_single_array(engine, data):
    mgr = FormulaManager(engine=engine)
    fmla = "1 + x + z"
    output = mgr.get_arrays(fmla, data)
    assert check_type(output, engine)


def test_two_arrays(engine, data):
    mgr = FormulaManager(engine=engine)
    fmla = "y ~ 1 + x + z"
    output = mgr.get_arrays(fmla, data)
    assert isinstance(output, tuple)
    assert len(output) == 2
    assert check_type(output[0], engine)
    assert check_type(output[1], engine)


def test_get_column_names(engine, data):
    mgr = FormulaManager(engine=engine)
    fmla = "y ~ 1 + x + z"
    output = mgr.get_arrays(fmla, data)
    names = mgr.get_column_names(output[0])
    assert names == ["y"]

    names = mgr.get_column_names(output[1])
    assert names == ["Intercept", "x", "z"]


def test_get_empty_eval_patsy(data):
    mgr = FormulaManager(engine="patsy")
    fmla = "y ~ 1 + x + g(z)"
    output = mgr.get_arrays(fmla, data)
    assert check_type(output[0], "patsy")
    assert check_type(output[1], "patsy")
    names = mgr.get_column_names(output[0])
    assert names == ["y"]
    names = mgr.get_column_names(output[1])
    assert names == ["Intercept", "x", "g(z)"]

    output = mgr.get_arrays(fmla, data, eval_env=0)
    assert check_type(output[0], "patsy")
    assert check_type(output[1], "patsy")
    names = mgr.get_column_names(output[0])
    assert names == ["y"]
    names = mgr.get_column_names(output[1])
    assert names == ["Intercept", "x", "g(z)"]

    eval_env = mgr.get_empty_eval_env()
    with pytest.raises(patsy.PatsyError):
        mgr.get_arrays(fmla, data, eval_env=7)

    with pytest.raises(patsy.PatsyError):
        mgr.get_arrays(fmla, data, eval_env=eval_env)

@require_formulaic
def test_get_empty_eval_formulaic(data):
    mgr = FormulaManager(engine="formulaic")
    fmla = "y ~ 1 + x + g(z)"
    output = mgr.get_arrays(fmla, data)
    assert check_type(output[0], "formulaic")
    assert check_type(output[1], "formulaic")

    output = mgr.get_arrays(fmla, data, eval_env=0)
    assert check_type(output[0], "formulaic")
    assert check_type(output[1], "formulaic")
    names = mgr.get_column_names(output[0])
    assert names == ["y"]
    names = mgr.get_column_names(output[1])
    assert names == ["Intercept", "x", "g(z)"]

    eval_env = mgr.get_empty_eval_env()
    eval_env["g"] = g
    output = mgr.get_arrays(fmla, data, eval_env=eval_env)
    assert check_type(output[0], "formulaic")
    assert check_type(output[1], "formulaic")
    names = mgr.get_column_names(output[0])
    assert names == ["y"]
    names = mgr.get_column_names(output[1])
    assert names == ["Intercept", "x", "g(z)"]


def test_has_intercept(engine, data):
    mgr = FormulaManager(engine=engine)
    fmla = "y ~ 1 + x + z"
    output = mgr.get_arrays(fmla, data)
    assert mgr.has_intercept(mgr.spec)
    assert mgr.has_intercept(mgr.get_model_spec(output[1]))

    fmla = "y ~ x + z - 1"
    output = mgr.get_arrays(fmla, data)
    assert not mgr.has_intercept(mgr.spec)
    assert not mgr.has_intercept(mgr.get_model_spec(output[1]))


def test_get_intercept_idx(engine, data):
    mgr = FormulaManager(engine=engine)
    fmla = "y ~ 1 + x + z"
    output = mgr.get_arrays(fmla, data)
    result = mgr.intercept_idx(mgr.spec)
    np.testing.assert_equal(result, np.array([True, False, False]))
    result = mgr.intercept_idx(mgr.get_model_spec(output[1]))
    np.testing.assert_equal(result, np.array([True, False, False]))

    fmla = "y ~ x + z - 1"
    output = mgr.get_arrays(fmla, data)
    result = mgr.intercept_idx(mgr.spec)
    np.testing.assert_equal(result, np.array([False, False]))
    result = mgr.intercept_idx(mgr.get_model_spec(output[1]))
    np.testing.assert_equal(result, np.array([False, False]))


def test_remove_intercept(engine, data):
    mgr = FormulaManager(engine=engine)
    fmla = "y ~ 1 + x + z"
    output = mgr.get_arrays(fmla, data)
    orig = mgr.spec.terms[:]
    result = mgr.remove_intercept(mgr.spec.terms)
    assert result == orig[1:]

    result = mgr.remove_intercept(mgr.get_model_spec(output[1]).terms)
    assert result == orig[1:]

    fmla = "y ~ x + z - 1"
    output = mgr.get_arrays(fmla, data)
    orig = mgr.spec.terms[:]
    result = mgr.remove_intercept(mgr.spec.terms)
    assert result == orig

    result = mgr.remove_intercept(mgr.get_model_spec(output[1]).terms)
    assert result == orig


def test_default_value():
    from statsmodels.formula._manager import _Default, _NoDefault

    assert isinstance(_NoDefault, _Default)
    _NoDefault.__str__()
    assert str(_NoDefault) == "<no default value>"
    assert repr(_NoDefault) == "<no default value>"


def test_get_spec(engine):
    mgr = FormulaManager(engine=engine)
    spec = mgr.get_spec("y ~ 1 + x + z")

    if engine == "patsy":
        assert isinstance(spec, patsy.desc.ModelDesc)
        assert len(spec.lhs_termlist) == 1
        assert len(spec.rhs_termlist) == 3
    else:
        assert isinstance(spec, formulaic.formula.Formula)
        assert len(spec.lhs) == 1
        assert len(spec.rhs) == 3


def test_get_na_action(engine, data):
    mgr = FormulaManager(engine=engine)
    result = mgr.get_na_action("drop")
    if engine == "patsy":
        assert result.on_NA == "drop"
        assert result.NA_types == ("None", "NaN")
    else:
        assert result == "drop"

    result = mgr.get_na_action(action="raise", types=["None"])
    if engine == "patsy":
        assert result.on_NA == "raise"
        assert result.NA_types == ("None",)
    else:
        assert result == "raise"


def test_get_model_spec(engine, data):
    mgr = FormulaManager(engine=engine)
    fmla = "y ~ 1 + x + z"
    lhs, rhs = mgr.get_arrays(fmla, data)
    result = mgr.get_model_spec(rhs)
    if engine == "patsy":
        assert isinstance(result, patsy.design_info.DesignInfo)
    else:
        assert isinstance(result, formulaic.model_spec.ModelSpec)

    result = mgr.get_model_spec(data, optional=True)
    assert result is None


def test_na_action(engine, data):
    mgr = FormulaManager(engine=engine)
    fmla = "y ~ 1 + x + z"
    missing = data.copy()
    missing.iloc[::3, 1] = np.nan
    dropper = mgr.get_na_action("drop")
    lhs, rhs = mgr.get_arrays(fmla, missing, na_action=dropper)
    assert rhs.shape[0] == lhs.shape[0]
    assert rhs.shape[0] == 4

    raiser = mgr.get_na_action("raise")
    if engine == "patsy":
        exception = patsy.PatsyError
    else:
        exception = ValueError

    with pytest.raises(exception):
        mgr.get_arrays(fmla, missing, na_action=raiser)

    if engine == "patsy":
        return
    ignorer = mgr.get_na_action("ignore")
    lhs, rhs = mgr.get_arrays(fmla, missing, na_action=ignorer)
    assert lhs.shape[0] == rhs.shape[0]
    assert rhs.shape[0] == missing.shape[0]


def test_get_term_name_slices(engine, data):
    mgr = FormulaManager(engine=engine)
    fmla = "y ~ 1 + x + z + c"
    lhs, rhs = mgr.get_arrays(fmla, data)
    slices = mgr.get_term_name_slices(rhs)
    for i, key in enumerate(slices):
        assert slices[key] == slice(i, i + 1, None)


@pytest.mark.parametrize(
    "constraint",
    [
        ["Intercept = 0", "x + z = 1"],
        np.eye(4),
        (np.eye(4), np.zeros(4)),
        {"Intercept": 0, "z": 1},
        "x + z = 1",
    ],
)
def test_get_linear_constraints(engine, data, constraint):
    mgr = FormulaManager(engine=engine)
    fmla = "y ~ 1 + x + z + c"
    lhs, rhs = mgr.get_arrays(fmla, data)
    constraints = mgr.get_linear_constraints(constraint, rhs.columns)
    assert isinstance(constraints[0], np.ndarray)
    assert isinstance(constraints[1], np.ndarray)
    assert isinstance(constraints[2], list)
    assert isinstance(constraints, LinearConstraintValues)

    constraints = mgr.get_linear_constraints(constraint, rhs.columns)
    assert isinstance(constraints[0], np.ndarray)
    assert isinstance(constraints[1], np.ndarray)
    assert isinstance(constraints[2], list)
    assert isinstance(constraints, LinearConstraintValues)


def test_bad_constraint(engine, data):
    mgr = FormulaManager(engine=engine)
    with pytest.raises(ValueError):
        mgr.get_linear_constraints(["x = 0", 7], ["Intercept", "x", "z", "c"])

@has_formulaic
def test_formula_manager_no_formulaic():
    with pytest.raises(ImportError):
        FormulaManager(engine="formulaic")

@has_patsy
def test_formula_manager_no_patsy():
    with pytest.raises(ImportError):
        FormulaManager(engine="patsy")
