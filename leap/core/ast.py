"""First-order logic AST with subformula addressing for proof-by-pointing."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Union, Tuple, Set, Dict


# ---------------------------------------------------------------------------
# Terms
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Term:
    """Base class for FOL terms."""
    pass


@dataclass(frozen=True)
class Var(Term):
    """A variable: x, y, z, ..."""
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Func(Term):
    """A function application: f(t1, ..., tn). Arity 0 = constant."""
    name: str
    args: Tuple[Term, ...] = ()

    def __str__(self) -> str:
        if not self.args:
            return self.name
        args_str = ", ".join(str(a) for a in self.args)
        return f"{self.name}({args_str})"


def Const(name: str) -> Func:
    """Convenience constructor for 0-ary function (constant)."""
    return Func(name, ())


# ---------------------------------------------------------------------------
# Formulas
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Formula:
    """Base class for FOL formulas."""
    pass


@dataclass(frozen=True)
class Pred(Formula):
    """Atomic predicate: P(t1, ..., tn). Arity 0 = propositional variable."""
    name: str
    args: Tuple[Term, ...] = ()

    def __str__(self) -> str:
        if not self.args:
            return self.name
        args_str = ", ".join(str(a) for a in self.args)
        return f"{self.name}({args_str})"


@dataclass(frozen=True)
class Not(Formula):
    inner: Formula

    def __str__(self) -> str:
        return f"¬{_paren(self.inner, self)}"


@dataclass(frozen=True)
class And(Formula):
    left: Formula
    right: Formula

    def __str__(self) -> str:
        return f"{_paren(self.left, self)} ∧ {_paren(self.right, self)}"


@dataclass(frozen=True)
class Or(Formula):
    left: Formula
    right: Formula

    def __str__(self) -> str:
        return f"{_paren(self.left, self)} ∨ {_paren(self.right, self)}"


@dataclass(frozen=True)
class Implies(Formula):
    left: Formula
    right: Formula

    def __str__(self) -> str:
        return f"{_paren(self.left, self)} → {_paren(self.right, self)}"


@dataclass(frozen=True)
class Forall(Formula):
    var: str
    body: Formula

    def __str__(self) -> str:
        return f"∀{self.var}. {_paren(self.body, self)}"


@dataclass(frozen=True)
class Exists(Formula):
    var: str
    body: Formula

    def __str__(self) -> str:
        return f"∃{self.var}. {_paren(self.body, self)}"


@dataclass(frozen=True)
class Top(Formula):
    def __str__(self) -> str:
        return "⊤"


@dataclass(frozen=True)
class Bottom(Formula):
    def __str__(self) -> str:
        return "⊥"


# Precedence for parenthesization
_PRECEDENCE: Dict[type, int] = {
    Top: 100, Bottom: 100, Pred: 100,
    Not: 90,
    And: 70,
    Or: 60,
    Implies: 50,
    Forall: 40, Exists: 40,
}


def _paren(child: Formula, parent: Formula) -> str:
    cp = _PRECEDENCE.get(type(child), 0)
    pp = _PRECEDENCE.get(type(parent), 0)
    s = str(child)
    if cp < pp:
        return f"({s})"
    if isinstance(parent, Implies) and isinstance(child, Implies):
        return f"({s})"
    return s


# ---------------------------------------------------------------------------
# Subformula Addressing
# ---------------------------------------------------------------------------

class Direction(Enum):
    LEFT = auto()
    RIGHT = auto()
    BODY = auto()
    INNER = auto()


Address = Tuple[Direction, ...]


def resolve_address(formula: Formula, addr: Address) -> Formula:
    """Follow an address path to retrieve a subformula."""
    current = formula
    for step in addr:
        if step in (Direction.BODY, Direction.INNER):
            if isinstance(current, (Forall, Exists)):
                current = current.body
            elif isinstance(current, Not):
                current = current.inner
            else:
                raise ValueError(f"Cannot go BODY/INNER into {type(current).__name__}")
        elif step == Direction.LEFT:
            if isinstance(current, (And, Or, Implies)):
                current = current.left
            else:
                raise ValueError(f"Cannot go LEFT into {type(current).__name__}")
        elif step == Direction.RIGHT:
            if isinstance(current, (And, Or, Implies)):
                current = current.right
            else:
                raise ValueError(f"Cannot go RIGHT into {type(current).__name__}")
        else:
            raise ValueError(f"Unknown direction: {step}")
    return current


def principal_connective(formula: Formula) -> str:
    """Return the name of the outermost connective of a formula."""
    if isinstance(formula, Pred):
        return "atom"
    elif isinstance(formula, Not):
        return "not"
    elif isinstance(formula, And):
        return "and"
    elif isinstance(formula, Or):
        return "or"
    elif isinstance(formula, Implies):
        return "implies"
    elif isinstance(formula, Forall):
        return "forall"
    elif isinstance(formula, Exists):
        return "exists"
    elif isinstance(formula, Top):
        return "top"
    elif isinstance(formula, Bottom):
        return "bottom"
    return "unknown"


def is_atomic(formula: Formula) -> bool:
    return isinstance(formula, (Pred, Top, Bottom))


# ---------------------------------------------------------------------------
# Click Targets
# ---------------------------------------------------------------------------

class Side(Enum):
    HYP = auto()
    GOAL = auto()


HypSide = Side.HYP
GoalSide = Side.GOAL


@dataclass(frozen=True)
class ClickTarget:
    """Identifies a location in a sequent: which formula (by side + index) and where within it."""
    side: Side
    index: int
    address: Address = ()


# ---------------------------------------------------------------------------
# Free variables
# ---------------------------------------------------------------------------

def free_vars_term(t: Term) -> Set[str]:
    if isinstance(t, Var):
        return {t.name}
    elif isinstance(t, Func):
        result: Set[str] = set()
        for a in t.args:
            result |= free_vars_term(a)
        return result
    return set()


def free_vars(f: Formula) -> Set[str]:
    if isinstance(f, Pred):
        result: Set[str] = set()
        for a in f.args:
            result |= free_vars_term(a)
        return result
    elif isinstance(f, Not):
        return free_vars(f.inner)
    elif isinstance(f, (And, Or, Implies)):
        return free_vars(f.left) | free_vars(f.right)
    elif isinstance(f, (Forall, Exists)):
        return free_vars(f.body) - {f.var}
    elif isinstance(f, (Top, Bottom)):
        return set()
    return set()
