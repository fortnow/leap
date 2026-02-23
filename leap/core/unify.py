"""First-order unification and substitution for terms and formulas."""

from __future__ import annotations
from typing import Dict, Optional, Set
from .ast import (
    Term, Var, Func,
    Formula, Pred, Not, And, Or, Implies, Forall, Exists, Top, Bottom,
)

Substitution = Dict[str, Term]


def substitute_term(t: Term, subst: Substitution) -> Term:
    if isinstance(t, Var) and t.name in subst:
        return subst[t.name]
    elif isinstance(t, Var):
        return t
    elif isinstance(t, Func):
        new_args = tuple(substitute_term(a, subst) for a in t.args)
        return Func(t.name, new_args)
    return t


def substitute_formula(f: Formula, subst: Substitution) -> Formula:
    if isinstance(f, Pred):
        new_args = tuple(substitute_term(a, subst) for a in f.args)
        return Pred(f.name, new_args)
    elif isinstance(f, Not):
        return Not(substitute_formula(f.inner, subst))
    elif isinstance(f, And):
        return And(substitute_formula(f.left, subst), substitute_formula(f.right, subst))
    elif isinstance(f, Or):
        return Or(substitute_formula(f.left, subst), substitute_formula(f.right, subst))
    elif isinstance(f, Implies):
        return Implies(substitute_formula(f.left, subst), substitute_formula(f.right, subst))
    elif isinstance(f, Forall):
        safe_subst = {k: v for k, v in subst.items() if k != f.var}
        return Forall(f.var, substitute_formula(f.body, safe_subst))
    elif isinstance(f, Exists):
        safe_subst = {k: v for k, v in subst.items() if k != f.var}
        return Exists(f.var, substitute_formula(f.body, safe_subst))
    elif isinstance(f, (Top, Bottom)):
        return f
    return f


def unify(t1: Term, t2: Term, subst: Optional[Substitution] = None) -> Optional[Substitution]:
    """Unify two terms, returning a substitution or None if they don't unify."""
    if subst is None:
        subst = {}

    t1 = _apply(t1, subst)
    t2 = _apply(t2, subst)

    if isinstance(t1, Var) and isinstance(t2, Var) and t1.name == t2.name:
        return subst
    elif isinstance(t1, Var):
        if _occurs(t1.name, t2):
            return None
        return {**subst, t1.name: t2}
    elif isinstance(t2, Var):
        if _occurs(t2.name, t1):
            return None
        return {**subst, t2.name: t1}
    elif isinstance(t1, Func) and isinstance(t2, Func):
        if t1.name != t2.name or len(t1.args) != len(t2.args):
            return None
        for a1, a2 in zip(t1.args, t2.args):
            subst = unify(a1, a2, subst)
            if subst is None:
                return None
        return subst
    return None


def _apply(t: Term, subst: Substitution) -> Term:
    if isinstance(t, Var) and t.name in subst:
        return _apply(subst[t.name], subst)
    elif isinstance(t, Var):
        return t
    elif isinstance(t, Func):
        return Func(t.name, tuple(_apply(a, subst) for a in t.args))
    return t


def _occurs(var_name: str, t: Term) -> bool:
    if isinstance(t, Var):
        return t.name == var_name
    elif isinstance(t, Func):
        return any(_occurs(var_name, a) for a in t.args)
    return False


# ---------------------------------------------------------------------------
# Fresh variable generation
# ---------------------------------------------------------------------------

_counter = 0


def fresh_var(prefix: str = "v", existing: Optional[Set[str]] = None) -> str:
    """Generate a fresh variable name not in `existing`."""
    global _counter
    if existing is None:
        existing = set()
    while True:
        _counter += 1
        name = f"{prefix}{_counter}"
        if name not in existing:
            return name


def reset_fresh_counter() -> None:
    """Reset for testing."""
    global _counter
    _counter = 0
