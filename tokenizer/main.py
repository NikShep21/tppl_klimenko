import argparse
from dataclasses import dataclass
from pathlib import Path
import sys


KEYWORDS = {"if", "else", "while", "return", "for", "def"}
OPERATORS = {"+", "-", "*", "/", "=", "<", ">", "==", "<=", ">="}
SEPARATORS = set("(){},;")


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    column: int


class LexicalError(ValueError):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(message)
        self.line = line
        self.column = column


class Lexer:

    def __init__(self, source: str):
        self._source = source
        self._length = len(source)
        self._index = 0
        self._line = 1
        self._line_start = 0
        self._operators = sorted(OPERATORS, key=len, reverse=True)

    def scan(self) -> list[Token]:
        tokens = []
        while True:
            self._skip_ignored()
            if self._index == self._length:
                return tokens
            tokens.append(self._read_token())

    def _skip_ignored(self) -> None:
        while self._index < self._length:
            char = self._source[self._index]
            if char in " \t":
                self._index += 1
            elif char in "\r\n":
                self._index += 2 if self._source.startswith("\r\n", self._index) else 1
                self._line += 1
                self._line_start = self._index
            elif char == "#":
                while self._index < self._length and self._source[self._index] not in "\r\n":
                    self._index += 1
            else:
                break

    def _read_token(self) -> Token:

        start = self._index
        line = self._line
        column = self._column()
        char = self._source[start]

        if char.isalpha() or char == "_":
            kind = self._read_identifier()
        elif char.isdecimal():
            kind = self._read_number()
        elif char == '"':
            kind = self._read_string()
        else:
            kind = self._read_symbol()

        return Token(kind, self._source[start:self._index], line, column)

    def _column(self) -> int:
        return self._index - self._line_start + 1

    def _read_identifier(self) -> str:
        start = self._index
        self._index += 1
        while self._index < self._length:
            char = self._source[self._index]
            if not (char.isalpha() or char.isdecimal() or char == "_"):
                break
            self._index += 1
        return "KEYWORD" if self._source[start:self._index] in KEYWORDS else "IDENT"

    def _skip_digits(self) -> None:
        while self._index < self._length and self._source[self._index].isdecimal():
            self._index += 1

    def _read_number(self) -> str:
        self._skip_digits()
        if (
            self._index + 1 < self._length
            and self._source[self._index] == "."
            and self._source[self._index + 1].isdecimal()
        ):
            self._index += 1
            self._skip_digits()
            return "FLOAT"
        return "INT"

    def _read_string(self) -> str:
        column = self._column()
        self._index += 1
        while self._index < self._length and self._source[self._index] not in '"\r\n':
            self._index += 1
        if self._index == self._length or self._source[self._index] != '"':
            raise LexicalError("unterminated string literal", self._line, column)
        self._index += 1
        return "STRING"

    def _read_symbol(self) -> str:
        for operator in self._operators:
            if self._source.startswith(operator, self._index):
                self._index += len(operator)
                return "OP"
        char = self._source[self._index]
        if char in SEPARATORS:
            self._index += 1
            return "SEP"
        raise LexicalError(f"unexpected character {char!r}", self._line, self._column())


def main() -> int:
    parser = argparse.ArgumentParser(description="Разбор исходного файла на токены.")
    parser.add_argument("file", help="путь к исходному файлу в UTF-8")
    args = parser.parse_args()

    try:
        source = Path(args.file).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        print(f"{args.file}:1:1: lexical: cannot read source file: {error}", file=sys.stderr)
        return 1

    try:
        tokens = Lexer(source).scan()
    except LexicalError as error:
        print(f"{args.file}:{error.line}:{error.column}: lexical: {error}", file=sys.stderr)
        return 1

    for token in tokens:
        print(f"({token.kind}, {token.value}, {token.line}:{token.column})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
