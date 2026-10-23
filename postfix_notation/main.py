
import argparse
import math
import sys

def pop_operands(stack: list) -> tuple:
    if len(stack) < 2:
        raise ValueError(
            f"нужны два операнда, а в стеке их {len(stack)}."
        )
    right = stack.pop()
    left = stack.pop()
    return left, right


def add(stack: list) -> float:
    left, right = pop_operands(stack)
    return left + right


def subtract(stack: list) -> float:
    left, right = pop_operands(stack)
    return left - right


def multiply(stack: list) -> float:
    left, right = pop_operands(stack)
    return left * right


def divide(stack: list) -> float:
    left, right = pop_operands(stack)
    if right == 0:
        raise ValueError("делить на ноль нельзя.")
    return left / right

def pow(stack: list) -> float:
    left, right = pop_operands(stack)
    return left ** right


def special(stack: list) -> float:
    left, right = pop_operands(stack)
    if left != 0 and right != 0:
        return abs(left - right)
    total = sum(stack) + left + right
    stack.clear()
    return total * total

OPERATIONS = {
    "+": add,
    "-": subtract,
    "*": multiply,
    "/": divide,
    "~": special,
    "!": pow
}


def format_number(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value)


def evaluate(expression: str, trace: bool = False) -> float:
    tokens = expression.split()
    if not tokens:
        raise ValueError("Выражение пустое. Введите, например: '2 3 +'.")

    stack = []
    for step, token in enumerate(tokens, start=1):
        if token in OPERATIONS:
            try:
                result = OPERATIONS[token](stack)
            except ValueError as error:
                raise ValueError(
                    f"Шаг {step}, операция '{token}': {error}"
                ) from None

            if not math.isfinite(result):
                raise ValueError(f"Шаг {step}: результат слишком велик для вычисления.")
            stack.append(result)
        else:
            try:
                number = float(token)
            except ValueError:
                raise ValueError(
                    f"Шаг {step}: '{token}' - неизвестное число или операция. "
                    f"Допустимые операции: {', '.join(OPERATIONS)}. "
                    "Разделяйте числа и операции пробелами; "
                    "дробную часть числа отделяйте точкой. "
                    'Передайте всё выражение в кавычках, например: "2 3 ~".'
                ) from None
            if not math.isfinite(number):
                raise ValueError(f"Шаг {step}: число '{token}' должно быть конечным.")
            stack.append(number)

        if trace:
            contents = ", ".join(format_number(value) for value in stack)
            print(f"Шаг {step}: {token} -> стек: [{contents}]")

    if len(stack) != 1:
        raise ValueError(
            f"После вычисления в стеке осталось {len(stack)} чисел. "
            "Проверьте, хватает ли операций: должен остаться один результат."
        )
    return stack[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Вычисление выражения в постфиксной нотации.",
        epilog='Пример запуска: python main.py "3 0 4 ~ 2 ~"',
    )
    parser.add_argument(
        "expression", nargs="+", help='выражение, рекомендуется в кавычках, например "2 3 ~"'
    )
    args = parser.parse_args()
    expression = " ".join(args.expression).strip()
    try:
        result = evaluate(expression, trace=True)
    except ValueError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    print(f"{expression} = {format_number(result)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
