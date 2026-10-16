"""Проверки вычислений, диагностики и интерфейса командной строки."""

import os
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

from postfix_notation import main as machine


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("3 0 4 ~ 2 ~", 47),
        ("2 2 + 4 - 4 ~ 2 3 * +", 22),
        ("2 3 + 4 5 + *", 45),
        ("10 3 -", 7),
        ("3 10 -", -7),
        ("10 4 /", 2.5),
        ("4 10 /", 0.4),
        ("-5 -2 *", 10),
        ("-5 2 /", -2.5),
        ("0", 0),
        ("-0", 0),
        ("2.5", 2.5),
        ("0.1 0.2 +", 0.3),
        ("1e2 2 /", 50),
        (" \t2\n3  +  ", 5),
        ("1 2 3 4 + + +", 10),
    ],
)
def test_evaluate(expression, expected):
    assert machine.evaluate(expression) == pytest.approx(expected)


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("3 8 ~", 5),
        ("8 3 ~", 5),
        ("-3 -8 ~", 5),
        ("3 3 ~", 0),
        ("7 3 8 ~ +", 12),  # Ненулевые операнды не затрагивают остаток стека.
        ("0 0 ~", 0),
        ("0 4 ~", 16),
        ("4 0 ~", 16),
        ("3 0 4 ~", 49),  # В сумму включается весь стек.
        ("3 4 0 ~", 49),
        ("1 2 0 4 ~", 49),
        ("-3 0 4 ~", 1),
        ("-4 0 4 ~", 0),
    ],
)
def test_special_operation(expression, expected):
    assert machine.evaluate(expression) == pytest.approx(expected)


@pytest.mark.parametrize("expression", ["", "   ", "\n\t"])
def test_empty_expression(expression):
    with pytest.raises(ValueError, match="Выражение пустое"):
        machine.evaluate(expression)


@pytest.mark.parametrize("operation", ["+", "-", "*", "/", "~"])
@pytest.mark.parametrize("prefix, step, available", [("", 1, 0), ("2 ", 2, 1)])
def test_missing_operands(operation, prefix, step, available):
    with pytest.raises(ValueError) as error:
        machine.evaluate(prefix + operation)
    message = str(error.value)
    assert f"Шаг {step}, операция '{operation}'" in message
    assert f"нужны два операнда, а в стеке их {available}" in message


@pytest.mark.parametrize("expression", ["1 0 /", "1 -0 /", "0 0 /"])
def test_division_by_zero(expression):
    with pytest.raises(ValueError, match="Шаг 3, операция '/': делить на ноль нельзя"):
        machine.evaluate(expression)


@pytest.mark.parametrize("token", ["abc", "%", "2,5", "2+3", "\\~"])
def test_invalid_token(token):
    with pytest.raises(ValueError) as error:
        machine.evaluate(f"2 {token}")
    message = str(error.value)
    assert f"Шаг 2: '{token}'" in message
    assert "Допустимые операции:" in message


@pytest.mark.parametrize("token", ["inf", "-inf", "nan", "NaN", "1e309"])
def test_nonfinite_number(token):
    with pytest.raises(ValueError, match="должно быть конечным"):
        machine.evaluate(token)


@pytest.mark.parametrize(
    "expression",
    ["1e308 10 *", "1e308 1e308 +", "1e308 -1e308 ~", "1e308 0 ~", "1e308 1e-308 /"],
)
def test_nonfinite_result(expression):
    with pytest.raises(ValueError, match="Шаг 3: результат слишком велик"):
        machine.evaluate(expression)


@pytest.mark.parametrize("expression, count", [("2 3", 2), ("2 3 + 4 5", 3)])
def test_unconsumed_numbers(expression, count):
    with pytest.raises(ValueError, match=f"в стеке осталось {count} чисел"):
        machine.evaluate(expression)


def test_trace(capsys):
    assert machine.evaluate("3 0 4 ~ 2 ~", trace=True) == 47
    captured = capsys.readouterr()
    assert captured.out.splitlines() == [
        "Шаг 1: 3 -> стек: [3]",
        "Шаг 2: 0 -> стек: [3, 0]",
        "Шаг 3: 4 -> стек: [3, 0, 4]",
        "Шаг 4: ~ -> стек: [49]",
        "Шаг 5: 2 -> стек: [49, 2]",
        "Шаг 6: ~ -> стек: [47]",
    ]
    assert captured.err == ""


def test_no_trace_by_default(capsys):
    assert machine.evaluate("2 3 +") == 5
    assert capsys.readouterr().out == ""


def test_independent_evaluations():
    with pytest.raises(ValueError):
        machine.evaluate("2 3")
    assert machine.evaluate("4 5 +") == 9


def test_register_unary_operation(monkeypatch):
    def negate(stack):
        return -stack.pop()

    monkeypatch.setitem(machine.OPERATIONS, "neg", negate)
    assert machine.evaluate("5 neg 2 +") == -3


@pytest.mark.parametrize("value, expected", [(5.0, "5"), (-0.0, "0"), (2.5, "2.5")])
def test_format_number(value, expected):
    assert machine.format_number(value) == expected


@pytest.mark.parametrize(
    "arguments, expected",
    [(["2 3 +"], "2 3 + = 5"), (["2", "3", "+"], "2 3 + = 5"),
     (["--", "-5 2 /"], "-5 2 / = -2.5")],
)
def test_main_success(monkeypatch, capsys, arguments, expected):
    monkeypatch.setattr(sys, "argv", ["main.py", *arguments])
    assert machine.main() == 0
    captured = capsys.readouterr()
    assert captured.out.splitlines()[-1] == expected
    assert captured.err == ""


@pytest.mark.parametrize("expression", ["1 0 /", "abc", "", "2 3"])
def test_main_error(monkeypatch, capsys, expression):
    monkeypatch.setattr(sys, "argv", ["main.py", expression])
    assert machine.main() == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("Ошибка: ")
    assert "Traceback" not in captured.err
    assert " = " not in captured.out


@pytest.mark.parametrize("arguments, exit_code", [([], 2), (["--help"], 0)])
def test_argument_parser(monkeypatch, capsys, arguments, exit_code):
    monkeypatch.setattr(sys, "argv", ["main.py", *arguments])
    with pytest.raises(SystemExit) as error:
        machine.main()
    assert error.value.code == exit_code
    captured = capsys.readouterr()
    if exit_code == 0:
        assert "Пример запуска:" in captured.out
    else:
        assert "expression" in captured.err


def test_script_entry_point(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["main.py", "2 3 +"])
    with pytest.raises(SystemExit) as error:
        runpy.run_path(machine.__file__, run_name="__main__")
    assert error.value.code == 0
    assert capsys.readouterr().out.splitlines()[-1] == "2 3 + = 5"


@pytest.mark.parametrize(
    "expression, exit_code, message",
    [("2 3 +", 0, "2 3 + = 5"), ("1 0 /", 1, "делить на ноль нельзя")],
)
def test_real_cli(expression, exit_code, message):
    script = Path(machine.__file__).resolve()
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    completed = subprocess.run(
        [sys.executable, "-B", str(script), expression],
        capture_output=True, text=True, encoding="utf-8", env=env, timeout=10,
    )
    assert completed.returncode == exit_code
    if exit_code == 0:
        assert completed.stdout.splitlines()[-1] == message
        assert completed.stderr == ""
    else:
        assert message in completed.stderr
        assert "Traceback" not in completed.stderr
