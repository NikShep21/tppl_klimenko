import runpy
import sys

import pytest

from tokenizer import main
from tokenizer.main import Lexer, LexicalError, Token


def test_assignment_from_task():
    assert Lexer("x = y * 2 + z * 3").scan() == [
        Token("IDENT", "x", 1, 1),
        Token("OP", "=", 1, 3),
        Token("IDENT", "y", 1, 5),
        Token("OP", "*", 1, 7),
        Token("INT", "2", 1, 9),
        Token("OP", "+", 1, 11),
        Token("IDENT", "z", 1, 13),
        Token("OP", "*", 1, 15),
        Token("INT", "3", 1, 17),
    ]


def test_keywords_and_identifiers():
    keywords = "if else while return for def".split()
    identifiers = ["if_count", "return2", "For", "_", "_2", "счётчик2"]
    tokens = Lexer(" ".join(keywords + identifiers)).scan()
    assert [(token.kind, token.value) for token in tokens] == [
        *(("KEYWORD", value) for value in keywords),
        *(("IDENT", value) for value in identifiers),
    ]


def test_adjacent_operators_and_separators():
    tokens = Lexer("+-*/=<> ==<=>=(){},;").scan()
    assert [(token.kind, token.value) for token in tokens] == [
        *(("OP", value) for value in ["+", "-", "*", "/", "=", "<", ">", "==", "<=", ">="]),
        *(("SEP", value) for value in "(){},;"),
    ]


def test_extending_operators(monkeypatch):
    monkeypatch.setattr(main, "OPERATORS", main.OPERATORS | {"!=", "**", "**="})
    assert Lexer("**=**!=*").scan() == [
        Token("OP", "**=", 1, 1),
        Token("OP", "**", 1, 4),
        Token("OP", "!=", 1, 6),
        Token("OP", "*", 1, 8),
    ]
    with pytest.raises(LexicalError, match="unexpected character '!'"):
        Lexer("!").scan()


def test_literal_spelling_and_positions():
    assert Lexer('-004 3.50 0.7 "" "a # b"').scan() == [
        Token("OP", "-", 1, 1),
        Token("INT", "004", 1, 2),
        Token("FLOAT", "3.50", 1, 6),
        Token("FLOAT", "0.7", 1, 11),
        Token("STRING", '""', 1, 15),
        Token("STRING", '"a # b"', 1, 18),
    ]


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_comments_and_multiline_positions(newline):
    source = newline.join(["  # ignore @", "", "\tif x>=2# comment", " return x", "# end"])
    assert Lexer(source).scan() == [
        Token("KEYWORD", "if", 3, 2),
        Token("IDENT", "x", 3, 5),
        Token("OP", ">=", 3, 6),
        Token("INT", "2", 3, 8),
        Token("KEYWORD", "return", 4, 2),
        Token("IDENT", "x", 4, 9),
    ]


@pytest.mark.parametrize("source", ["", " \t\n", "# comment with @"])
def test_no_tokens(source):
    assert Lexer(source).scan() == []


@pytest.mark.parametrize(
    "source, line, column, message",
    [
        ("a @ b", 1, 3, "unexpected character '@'"),
        ("# ignore @\n  @", 2, 3, "unexpected character '@'"),
        ("2.", 1, 2, "unexpected character '.'"),
        ("2.x", 1, 2, "unexpected character '.'"),
        ('x = "hello', 1, 5, "unterminated string literal"),
        ('\nx = "hello\nworld"', 2, 5, "unterminated string literal"),
    ],
)
def test_lexical_errors(source, line, column, message):
    with pytest.raises(LexicalError) as error:
        Lexer(source).scan()
    assert (error.value.line, error.value.column) == (line, column)
    assert str(error.value) == message


def test_script_output(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source code.txt"
    source.write_text('return "привет";', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["main.py", str(source)])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(main.__file__, run_name="__main__")
    assert exit_info.value.code == 0
    output = capsys.readouterr()
    assert output.out.splitlines() == [
        "(KEYWORD, return, 1:1)", '(STRING, "привет", 1:8)', "(SEP, ;, 1:16)"
    ]
    assert output.err == ""


def test_cli_lexical_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "input.txt").write_text("a @ b", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["main.py", "input.txt"])
    assert main.main() == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "input.txt:1:3: lexical: unexpected character '@'\n"


@pytest.mark.parametrize("invalid_encoding", [False, True])
def test_cli_unreadable_file(tmp_path, monkeypatch, capsys, invalid_encoding):
    source = tmp_path / "input.txt"
    if invalid_encoding:
        source.write_bytes(b"\xff")
    monkeypatch.setattr(sys, "argv", ["main.py", str(source)])
    assert main.main() == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.startswith(f"{source}:1:1: lexical: cannot read source file:")
