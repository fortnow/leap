"""Parser for first-order logic formulas.

Grammar (informal):
    formula ::= implication
    implication ::= disjunction ( '->' implication )?    -- right-associative
    disjunction ::= conjunction ( '|' conjunction )*
    conjunction ::= unary ( '&' unary )*
    unary ::= '~' unary | 'forall' VAR '.' formula | 'exists' VAR '.' formula
            | atom
    atom ::= 'T' | 'F' | NAME '(' termlist ')' | NAME | '(' formula ')'
    term ::= NAME '(' termlist ')' | NAME
    termlist ::= term (',' term)*

Tokens: NAME, '(', ')', ',', '.', '->', '|', '&', '~', 'forall', 'exists', 'T', 'F'
"""

from __future__ import annotations
import re
from .ast import (
    Term, Var, Func, Const,
    Formula, Pred, Not, And, Or, Implies, Forall, Exists, Top, Bottom,
)

# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"""
    (?P<TURNSTILE>⊢|\|-)
    | (?P<ARROW>->|→)
    | (?P<AND>[&∧])
    | (?P<OR>[|∨])
    | (?P<NOT>[~¬!])
    | (?P<FORALL>forall|∀)
    | (?P<EXISTS>exists|∃)
    | (?P<TOP>⊤)
    | (?P<BOT>⊥)
    | (?P<DOT>\.)
    | (?P<COMMA>,)
    | (?P<LPAREN>\()
    | (?P<RPAREN>\))
    | (?P<NAME>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<WS>\s+)
    """,
    re.VERBOSE,
)


def _tokenize(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos = 0
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m:
            raise ValueError(f"Unexpected character at position {pos}: {text[pos:]!r}")
        pos = m.end()
        kind = m.lastgroup
        value = m.group()
        if kind == "WS":
            continue
        # Normalize keywords that might be NAME matches
        if kind == "NAME":
            if value in ("forall", "Forall", "FORALL"):
                kind = "FORALL"
            elif value in ("exists", "Exists", "EXISTS"):
                kind = "EXISTS"
            elif value == "T":
                kind = "TOP"
            elif value == "F":
                kind = "BOT"
        tokens.append((kind, value))
    return tokens


# ---------------------------------------------------------------------------
# Recursive-descent parser
# ---------------------------------------------------------------------------

class _Parser:
    def __init__(self, tokens: list[tuple[str, str]]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> tuple[str, str] | None:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def peek_kind(self) -> str | None:
        t = self.peek()
        return t[0] if t else None

    def consume(self, expected_kind: str | None = None) -> tuple[str, str]:
        t = self.peek()
        if t is None:
            raise ValueError("Unexpected end of input")
        if expected_kind and t[0] != expected_kind:
            raise ValueError(f"Expected {expected_kind}, got {t[0]} ({t[1]!r})")
        self.pos += 1
        return t

    def at_end(self) -> bool:
        return self.pos >= len(self.tokens)

    # -- Formula parsing --

    def parse_formula(self) -> Formula:
        return self.parse_implication()

    def parse_implication(self) -> Formula:
        left = self.parse_disjunction()
        if self.peek_kind() == "ARROW":
            self.consume("ARROW")
            right = self.parse_implication()  # right-associative
            return Implies(left, right)
        return left

    def parse_disjunction(self) -> Formula:
        left = self.parse_conjunction()
        while self.peek_kind() == "OR":
            self.consume("OR")
            right = self.parse_conjunction()
            left = Or(left, right)
        return left

    def parse_conjunction(self) -> Formula:
        left = self.parse_unary()
        while self.peek_kind() == "AND":
            self.consume("AND")
            right = self.parse_unary()
            left = And(left, right)
        return left

    def parse_unary(self) -> Formula:
        pk = self.peek_kind()
        if pk == "NOT":
            self.consume("NOT")
            inner = self.parse_unary()
            return Not(inner)
        if pk == "FORALL":
            self.consume("FORALL")
            _, var_name = self.consume("NAME")
            self.consume("DOT")
            body = self.parse_formula()
            return Forall(var_name, body)
        if pk == "EXISTS":
            self.consume("EXISTS")
            _, var_name = self.consume("NAME")
            self.consume("DOT")
            body = self.parse_formula()
            return Exists(var_name, body)
        return self.parse_atom()

    def parse_atom(self) -> Formula:
        pk = self.peek_kind()
        if pk == "TOP":
            self.consume("TOP")
            return Top()
        if pk == "BOT":
            self.consume("BOT")
            return Bottom()
        if pk == "LPAREN":
            self.consume("LPAREN")
            f = self.parse_formula()
            self.consume("RPAREN")
            return f
        if pk == "NAME":
            _, name = self.consume("NAME")
            if self.peek_kind() == "LPAREN":
                self.consume("LPAREN")
                args: list[Term] = []
                if self.peek_kind() != "RPAREN":
                    args.append(self.parse_term())
                    while self.peek_kind() == "COMMA":
                        self.consume("COMMA")
                        args.append(self.parse_term())
                self.consume("RPAREN")
                return Pred(name, tuple(args))
            return Pred(name)
        raise ValueError(f"Unexpected token: {self.peek()}")

    # -- Term parsing --

    def parse_term(self) -> Term:
        _, name = self.consume("NAME")
        if self.peek_kind() == "LPAREN":
            self.consume("LPAREN")
            args: list[Term] = []
            if self.peek_kind() != "RPAREN":
                args.append(self.parse_term())
                while self.peek_kind() == "COMMA":
                    self.consume("COMMA")
                    args.append(self.parse_term())
            self.consume("RPAREN")
            return Func(name, tuple(args))
        # Heuristic: lowercase = variable, uppercase = constant
        if name[0].islower():
            return Var(name)
        return Func(name, ())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_formula(text: str) -> Formula:
    """Parse a string into a Formula AST."""
    tokens = _tokenize(text)
    parser = _Parser(tokens)
    result = parser.parse_formula()
    if not parser.at_end():
        raise ValueError(f"Unexpected trailing tokens: {parser.tokens[parser.pos:]}")
    return result


def parse_term(text: str) -> Term:
    """Parse a string into a Term AST."""
    tokens = _tokenize(text)
    parser = _Parser(tokens)
    result = parser.parse_term()
    if not parser.at_end():
        raise ValueError(f"Unexpected trailing tokens: {parser.tokens[parser.pos:]}")
    return result


def parse_sequent(text: str) -> tuple[list[Formula], list[Formula]]:
    """Parse 'A, B, C |- D, E' into (hyps, goals)."""
    tokens = _tokenize(text)
    # Find turnstile
    turnstile_idx = None
    for i, (kind, _) in enumerate(tokens):
        if kind == "TURNSTILE":
            turnstile_idx = i
            break
    if turnstile_idx is None:
        raise ValueError("No turnstile (⊢ or |-) found in sequent")

    hyp_tokens = tokens[:turnstile_idx]
    goal_tokens = tokens[turnstile_idx + 1:]

    hyps = _parse_formula_list(hyp_tokens) if hyp_tokens else []
    goals = _parse_formula_list(goal_tokens) if goal_tokens else []
    return hyps, goals


def _parse_formula_list(tokens: list[tuple[str, str]]) -> list[Formula]:
    """Parse a comma-separated list of formulas from tokens.

    Commas at the top level (not inside parens or pred args) separate formulas.
    """
    # Split on top-level commas
    groups: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    depth = 0
    for kind, value in tokens:
        if kind == "LPAREN":
            depth += 1
        elif kind == "RPAREN":
            depth -= 1
        if kind == "COMMA" and depth == 0:
            groups.append(current)
            current = []
        else:
            current.append((kind, value))
    if current:
        groups.append(current)

    result: list[Formula] = []
    for group in groups:
        parser = _Parser(group)
        f = parser.parse_formula()
        result.append(f)
    return result
