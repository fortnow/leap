"""Pretty-printer and HTML renderer for formulas and sequents.

The HTML renderer produces nested <span> elements with data attributes
for side, index, and address — the key interface for proof-by-pointing.
"""

from __future__ import annotations
import html as html_mod
from typing import List, Tuple
from .ast import (
    Term, Var, Func,
    Formula, Pred, Not, And, Or, Implies, Forall, Exists, Top, Bottom,
    Direction, Address, _PRECEDENCE,
)


# ---------------------------------------------------------------------------
# Plain-text rendering
# ---------------------------------------------------------------------------

def formula_to_str(f: Formula) -> str:
    return str(f)


def sequent_to_str(hyps: List[Formula], goals: List[Formula]) -> str:
    h = ", ".join(str(f) for f in hyps) if hyps else ""
    g = ", ".join(str(f) for f in goals) if goals else ""
    return f"{h} ⊢ {g}"


# ---------------------------------------------------------------------------
# HTML rendering with clickable addresses
# ---------------------------------------------------------------------------

def _addr_str(addr: Address) -> str:
    """Serialize an address to a string for data attributes."""
    parts: List[str] = []
    for d in addr:
        if d == Direction.LEFT:
            parts.append("L")
        elif d == Direction.RIGHT:
            parts.append("R")
        elif d in (Direction.BODY, Direction.INNER):
            parts.append("B")
    return ".".join(parts) if parts else ""


def _needs_paren(child: Formula, parent: Formula) -> bool:
    cp = _PRECEDENCE.get(type(child), 0)
    pp = _PRECEDENCE.get(type(parent), 0)
    if cp < pp:
        return True
    if isinstance(parent, Implies) and isinstance(child, Implies):
        return True
    return False


def term_to_html(t: Term) -> str:
    if isinstance(t, Var):
        return f'<span class="var">{html_mod.escape(t.name)}</span>'
    elif isinstance(t, Func) and not t.args:
        return f'<span class="const">{html_mod.escape(t.name)}</span>'
    elif isinstance(t, Func):
        args_html = ", ".join(term_to_html(a) for a in t.args)
        return f'<span class="func">{html_mod.escape(t.name)}({args_html})</span>'
    return html_mod.escape(str(t))


def formula_to_html(f: Formula, side: str, index: int, addr: Address = ()) -> str:
    """Render a formula as nested clickable HTML spans."""
    addr_s = _addr_str(addr)
    attrs = f'data-side="{side}" data-index="{index}" data-addr="{addr_s}"'

    if isinstance(f, Top):
        return f'<span class="formula atom top" {attrs}>⊤</span>'
    elif isinstance(f, Bottom):
        return f'<span class="formula atom bottom" {attrs}>⊥</span>'
    elif isinstance(f, Pred) and not f.args:
        return f'<span class="formula atom pred" {attrs}>{html_mod.escape(f.name)}</span>'
    elif isinstance(f, Pred):
        args_html = ", ".join(term_to_html(a) for a in f.args)
        return (f'<span class="formula atom pred" {attrs}>'
                f'{html_mod.escape(f.name)}({args_html})</span>')
    elif isinstance(f, Not):
        inner_html = _wrap(f.inner, f, formula_to_html(
            f.inner, side, index, addr + (Direction.BODY,)))
        conn = f'<span class="connective not" {attrs}>¬</span>'
        return f'<span class="formula not-formula" {attrs}>{conn}{inner_html}</span>'
    elif isinstance(f, And):
        return _binary_html(f, f.left, f.right, "∧", "and", side, index, addr)
    elif isinstance(f, Or):
        return _binary_html(f, f.left, f.right, "∨", "or", side, index, addr)
    elif isinstance(f, Implies):
        return _binary_html(f, f.left, f.right, "→", "implies", side, index, addr)
    elif isinstance(f, Forall):
        body_html = _wrap(f.body, f, formula_to_html(
            f.body, side, index, addr + (Direction.BODY,)))
        quant = f'<span class="connective forall" {attrs}>∀</span>'
        var_span = f'<span class="bound-var" {attrs}>{html_mod.escape(f.var)}</span>'
        return (f'<span class="formula forall-formula" {attrs}>'
                f'{quant}{var_span}. {body_html}</span>')
    elif isinstance(f, Exists):
        body_html = _wrap(f.body, f, formula_to_html(
            f.body, side, index, addr + (Direction.BODY,)))
        quant = f'<span class="connective exists" {attrs}>∃</span>'
        var_span = f'<span class="bound-var" {attrs}>{html_mod.escape(f.var)}</span>'
        return (f'<span class="formula exists-formula" {attrs}>'
                f'{quant}{var_span}. {body_html}</span>')

    return html_mod.escape(str(f))


def _binary_html(f: Formula, left: Formula, right: Formula,
                 symbol: str, cls: str, side: str, index: int,
                 addr: Address) -> str:
    addr_s = _addr_str(addr)
    attrs = f'data-side="{side}" data-index="{index}" data-addr="{addr_s}"'

    left_html = _wrap(left, f, formula_to_html(
        left, side, index, addr + (Direction.LEFT,)))
    right_html = _wrap(right, f, formula_to_html(
        right, side, index, addr + (Direction.RIGHT,)))
    conn = f'<span class="connective {cls}" {attrs}> {symbol} </span>'

    return (f'<span class="formula {cls}-formula" {attrs}>'
            f'{left_html}{conn}{right_html}</span>')


def _wrap(child: Formula, parent: Formula, child_html: str) -> str:
    if _needs_paren(child, parent):
        return f'({child_html})'
    return child_html


def sequent_to_html(hyps: List[Formula], goals: List[Formula]) -> str:
    """Render a full sequent as interactive HTML."""
    hyp_parts: List[str] = []
    for i, h in enumerate(hyps):
        hyp_parts.append(formula_to_html(h, "hyp", i))

    goal_parts: List[str] = []
    for i, g in enumerate(goals):
        goal_parts.append(formula_to_html(g, "goal", i))

    hyps_html = '<span class="comma">, </span>'.join(hyp_parts) if hyp_parts else ""
    goals_html = '<span class="comma">, </span>'.join(goal_parts) if goal_parts else ""
    turnstile = '<span class="turnstile"> ⊢ </span>'

    return f'<div class="sequent">{hyps_html}{turnstile}{goals_html}</div>'
