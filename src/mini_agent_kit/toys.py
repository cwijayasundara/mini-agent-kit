"""Three toy tools: calculator, word_count and clock."""

import re
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from mini_agent_kit.registry import Registry

_TOKEN = re.compile(r"\d+(?:\.\d+)?|\.\d+|\S")


def _tokens(expression: str) -> list[str]:
    return _TOKEN.findall(expression)


class _Parser:
    """Recursive descent over: expr = term (+|- term)*, term = unary (*|/ unary)*."""

    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def take(self) -> str:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def parse(self) -> Decimal:
        value = self.expr()
        if self.peek() is not None:
            raise ValueError(f"unexpected {self.peek()!r}")
        return value

    def expr(self) -> Decimal:
        value = self.term()
        while self.peek() in ("+", "-"):
            value = value + self.term() if self.take() == "+" else value - self.term()
        return value

    def term(self) -> Decimal:
        value = self.unary()
        while self.peek() in ("*", "/"):
            if self.take() == "*":
                value = value * self.unary()
                continue
            divisor = self.unary()
            if divisor == 0:
                raise ValueError("division by zero")
            value = value / divisor
        return value

    def unary(self) -> Decimal:
        if self.peek() == "-":
            self.take()
            return -self.unary()
        return self.atom()

    def atom(self) -> Decimal:
        if self.peek() is None:
            raise ValueError("unexpected end of expression")
        token = self.take()
        if token == "(":
            value = self.expr()
            if self.peek() != ")":
                raise ValueError("missing closing parenthesis")
            self.take()
            return value
        if token[0].isdigit() or token[0] == ".":
            return Decimal(token)
        raise ValueError(f"unexpected {token!r}")


def _format(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), "f")


def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression with + - * / and parentheses."""
    return _format(_Parser(_tokens(expression)).parse())


def word_count(text: str) -> int:
    """Count the whitespace-separated words in text."""
    return len(text.split())


def make_clock(now: Callable[[], datetime]) -> Callable[[str], str]:
    """Build the clock tool around an injectable time source."""

    def clock(timezone: str = "UTC") -> str:
        """Current time in ISO 8601 for an IANA timezone name."""
        try:
            zone = ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown timezone: {timezone}") from exc
        return now().astimezone(zone).isoformat()

    return clock


clock = make_clock(lambda: datetime.now(UTC))


def toy_registry() -> Registry:
    """A registry holding the three toy tools."""
    registry = Registry()
    for fn in (calculator, word_count, clock):
        registry.register(fn)
    return registry
