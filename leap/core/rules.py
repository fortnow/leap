"""LK-style sequent calculus inference rules for classical first-order logic.

Each rule takes a sequent and a target (side + index), plus optional parameters,
and returns a RuleResult containing the subgoals.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, List, Set, Tuple, Union

from .ast import (
    Formula, Pred, Not, And, Or, Implies, Forall, Exists, Top, Bottom,
    Side, free_vars,
)
from .sequent import Sequent
from .unify import substitute_formula, fresh_var, Substitution


class RuleName(Enum):
    # Structural
    AXIOM = auto()

    # Right rules (formula in goal)
    AND_RIGHT = auto()
    OR_RIGHT_L = auto()
    OR_RIGHT_R = auto()
    IMPLIES_RIGHT = auto()
    NOT_RIGHT = auto()
    FORALL_RIGHT = auto()
    EXISTS_RIGHT = auto()
    TOP_RIGHT = auto()

    # Left rules (formula in hypothesis)
    AND_LEFT_L = auto()
    AND_LEFT_R = auto()
    AND_LEFT = auto()
    OR_LEFT = auto()
    IMPLIES_LEFT = auto()
    NOT_LEFT = auto()
    FORALL_LEFT = auto()
    EXISTS_LEFT = auto()
    BOTTOM_LEFT = auto()

    # Weakening / contraction
    WEAKEN_LEFT = auto()
    WEAKEN_RIGHT = auto()


@dataclass(frozen=True)
class RuleResult:
    """Result of applying an inference rule."""
    rule: RuleName
    premises: Tuple[Sequent, ...]
    message: str = ""


def apply_rule(rule: RuleName, sequent: Sequent, index: int,
               term_arg: Optional[Union[Formula, str]] = None,
               all_free: Optional[Set[str]] = None) -> RuleResult:
    """Apply a named rule to the formula at the given index."""
    if rule == RuleName.AXIOM:
        return _axiom(sequent)
    elif rule == RuleName.AND_RIGHT:
        return _and_right(sequent, index)
    elif rule == RuleName.OR_RIGHT_L:
        return _or_right(sequent, index, choose_left=True)
    elif rule == RuleName.OR_RIGHT_R:
        return _or_right(sequent, index, choose_left=False)
    elif rule == RuleName.IMPLIES_RIGHT:
        return _implies_right(sequent, index)
    elif rule == RuleName.NOT_RIGHT:
        return _not_right(sequent, index)
    elif rule == RuleName.FORALL_RIGHT:
        return _forall_right(sequent, index, all_free)
    elif rule == RuleName.EXISTS_RIGHT:
        return _exists_right(sequent, index, term_arg)
    elif rule == RuleName.TOP_RIGHT:
        return RuleResult(RuleName.TOP_RIGHT, (), "⊤ is trivially true")
    elif rule == RuleName.AND_LEFT:
        return _and_left(sequent, index)
    elif rule == RuleName.OR_LEFT:
        return _or_left(sequent, index)
    elif rule == RuleName.IMPLIES_LEFT:
        return _implies_left(sequent, index)
    elif rule == RuleName.NOT_LEFT:
        return _not_left(sequent, index)
    elif rule == RuleName.FORALL_LEFT:
        return _forall_left(sequent, index, term_arg)
    elif rule == RuleName.EXISTS_LEFT:
        return _exists_left(sequent, index, all_free)
    elif rule == RuleName.BOTTOM_LEFT:
        return RuleResult(RuleName.BOTTOM_LEFT, (), "⊥ in hypotheses closes the goal")
    elif rule == RuleName.WEAKEN_LEFT:
        return RuleResult(RuleName.WEAKEN_LEFT,
                          (sequent.remove_hyp(index),),
                          "Weakening: removed hypothesis")
    elif rule == RuleName.WEAKEN_RIGHT:
        return RuleResult(RuleName.WEAKEN_RIGHT,
                          (sequent.remove_goal(index),),
                          "Weakening: removed goal")

    raise ValueError(f"Unknown rule: {rule}")


# ---------------------------------------------------------------------------
# Axiom
# ---------------------------------------------------------------------------

def _axiom(sequent: Sequent) -> RuleResult:
    if sequent.is_axiom():
        return RuleResult(RuleName.AXIOM, (), "Axiom: goal is trivially provable")
    raise ValueError("Sequent is not an axiom")


# ---------------------------------------------------------------------------
# Right rules
# ---------------------------------------------------------------------------

def _and_right(sequent: Sequent, idx: int) -> RuleResult:
    f = sequent.goals[idx]
    if not isinstance(f, And):
        raise ValueError(f"Expected And at goal[{idx}], got {type(f).__name__}")
    s1 = sequent.replace_goal(idx, f.left)
    s2 = sequent.replace_goal(idx, f.right)
    return RuleResult(RuleName.AND_RIGHT, (s1, s2),
                      f"∧-Right: split {f} into two subgoals")


def _or_right(sequent: Sequent, idx: int, choose_left: bool) -> RuleResult:
    f = sequent.goals[idx]
    if not isinstance(f, Or):
        raise ValueError(f"Expected Or at goal[{idx}], got {type(f).__name__}")
    chosen = f.left if choose_left else f.right
    name = RuleName.OR_RIGHT_L if choose_left else RuleName.OR_RIGHT_R
    s = sequent.replace_goal(idx, chosen)
    side_name = "left" if choose_left else "right"
    return RuleResult(name, (s,), f"∨-Right: chose {side_name} disjunct")


def _implies_right(sequent: Sequent, idx: int) -> RuleResult:
    f = sequent.goals[idx]
    if not isinstance(f, Implies):
        raise ValueError(f"Expected Implies at goal[{idx}], got {type(f).__name__}")
    s = sequent.replace_goal(idx, f.right).add_hyp(f.left)
    return RuleResult(RuleName.IMPLIES_RIGHT, (s,),
                      f"→-Right: moved {f.left} to hypotheses")


def _not_right(sequent: Sequent, idx: int) -> RuleResult:
    f = sequent.goals[idx]
    if not isinstance(f, Not):
        raise ValueError(f"Expected Not at goal[{idx}], got {type(f).__name__}")
    s = sequent.remove_goal(idx).add_hyp(f.inner)
    return RuleResult(RuleName.NOT_RIGHT, (s,),
                      f"¬-Right: moved {f.inner} to hypotheses")


def _forall_right(sequent: Sequent, idx: int,
                  all_free: Optional[Set[str]] = None) -> RuleResult:
    f = sequent.goals[idx]
    if not isinstance(f, Forall):
        raise ValueError(f"Expected Forall at goal[{idx}], got {type(f).__name__}")

    if all_free is None:
        all_free = set()
        for h in sequent.hyps:
            all_free |= free_vars(h)
        for g in sequent.goals:
            all_free |= free_vars(g)

    from .ast import Var
    eigen = fresh_var(f.var, all_free)
    body = substitute_formula(f.body, {f.var: Var(eigen)})
    s = sequent.replace_goal(idx, body)
    return RuleResult(RuleName.FORALL_RIGHT, (s,),
                      f"∀-Right: introduced eigenvariable {eigen}")


def _exists_right(sequent: Sequent, idx: int,
                  witness: Optional[Union[Formula, str]] = None) -> RuleResult:
    f = sequent.goals[idx]
    if not isinstance(f, Exists):
        raise ValueError(f"Expected Exists at goal[{idx}], got {type(f).__name__}")

    if witness is None:
        from .ast import Var
        all_free: Set[str] = set()
        for h in sequent.hyps:
            all_free |= free_vars(h)
        for g in sequent.goals:
            all_free |= free_vars(g)
        witness_var = fresh_var("?w", all_free)
        witness_term = Var(witness_var)
    elif isinstance(witness, str):
        from .parser import parse_term
        witness_term = parse_term(witness)
    else:
        raise ValueError("witness must be a string (term text) or None")

    body = substitute_formula(f.body, {f.var: witness_term})
    s = sequent.replace_goal(idx, body)
    return RuleResult(RuleName.EXISTS_RIGHT, (s,),
                      f"∃-Right: instantiated with {witness_term}")


# ---------------------------------------------------------------------------
# Left rules
# ---------------------------------------------------------------------------

def _and_left(sequent: Sequent, idx: int) -> RuleResult:
    f = sequent.hyps[idx]
    if not isinstance(f, And):
        raise ValueError(f"Expected And at hyp[{idx}], got {type(f).__name__}")
    s = sequent.replace_hyp(idx, f.left, f.right)
    return RuleResult(RuleName.AND_LEFT, (s,),
                      f"∧-Left: split {f} into {f.left} and {f.right}")


def _or_left(sequent: Sequent, idx: int) -> RuleResult:
    f = sequent.hyps[idx]
    if not isinstance(f, Or):
        raise ValueError(f"Expected Or at hyp[{idx}], got {type(f).__name__}")
    s1 = sequent.replace_hyp(idx, f.left)
    s2 = sequent.replace_hyp(idx, f.right)
    return RuleResult(RuleName.OR_LEFT, (s1, s2),
                      f"∨-Left: case split on {f}")


def _implies_left(sequent: Sequent, idx: int) -> RuleResult:
    f = sequent.hyps[idx]
    if not isinstance(f, Implies):
        raise ValueError(f"Expected Implies at hyp[{idx}], got {type(f).__name__}")
    s1 = sequent.remove_hyp(idx).add_goal(f.left)
    s2 = sequent.replace_hyp(idx, f.right)
    return RuleResult(RuleName.IMPLIES_LEFT, (s1, s2),
                      f"→-Left: must prove {f.left}, then use {f.right}")


def _not_left(sequent: Sequent, idx: int) -> RuleResult:
    f = sequent.hyps[idx]
    if not isinstance(f, Not):
        raise ValueError(f"Expected Not at hyp[{idx}], got {type(f).__name__}")
    s = sequent.remove_hyp(idx).add_goal(f.inner)
    return RuleResult(RuleName.NOT_LEFT, (s,),
                      f"¬-Left: moved {f.inner} to goals")


def _forall_left(sequent: Sequent, idx: int,
                 instance: Optional[Union[Formula, str]] = None) -> RuleResult:
    f = sequent.hyps[idx]
    if not isinstance(f, Forall):
        raise ValueError(f"Expected Forall at hyp[{idx}], got {type(f).__name__}")

    if instance is None:
        from .ast import Var
        all_free: Set[str] = set()
        for h in sequent.hyps:
            all_free |= free_vars(h)
        for g in sequent.goals:
            all_free |= free_vars(g)
        inst_var = fresh_var("?t", all_free)
        inst_term = Var(inst_var)
    elif isinstance(instance, str):
        from .parser import parse_term
        inst_term = parse_term(instance)
    else:
        raise ValueError("instance must be a string (term text) or None")

    body = substitute_formula(f.body, {f.var: inst_term})
    s = sequent.add_hyp(body)
    return RuleResult(RuleName.FORALL_LEFT, (s,),
                      f"∀-Left: instantiated {f.var} with {inst_term}")


def _exists_left(sequent: Sequent, idx: int,
                 all_free: Optional[Set[str]] = None) -> RuleResult:
    f = sequent.hyps[idx]
    if not isinstance(f, Exists):
        raise ValueError(f"Expected Exists at hyp[{idx}], got {type(f).__name__}")

    if all_free is None:
        all_free = set()
        for h in sequent.hyps:
            all_free |= free_vars(h)
        for g in sequent.goals:
            all_free |= free_vars(g)

    from .ast import Var
    eigen = fresh_var(f.var, all_free)
    body = substitute_formula(f.body, {f.var: Var(eigen)})
    s = sequent.replace_hyp(idx, body)
    return RuleResult(RuleName.EXISTS_LEFT, (s,),
                      f"∃-Left: introduced eigenvariable {eigen}")


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def rules_for(formula: Formula, side: Side) -> List[RuleName]:
    """Return the applicable rule(s) for a formula on a given side."""
    if side == Side.GOAL:
        if isinstance(formula, And):
            return [RuleName.AND_RIGHT]
        elif isinstance(formula, Or):
            return [RuleName.OR_RIGHT_L, RuleName.OR_RIGHT_R]
        elif isinstance(formula, Implies):
            return [RuleName.IMPLIES_RIGHT]
        elif isinstance(formula, Not):
            return [RuleName.NOT_RIGHT]
        elif isinstance(formula, Forall):
            return [RuleName.FORALL_RIGHT]
        elif isinstance(formula, Exists):
            return [RuleName.EXISTS_RIGHT]
        elif isinstance(formula, Top):
            return [RuleName.TOP_RIGHT]
        elif isinstance(formula, Bottom):
            return []
        else:
            return [RuleName.AXIOM]
    else:  # HYP
        if isinstance(formula, And):
            return [RuleName.AND_LEFT]
        elif isinstance(formula, Or):
            return [RuleName.OR_LEFT]
        elif isinstance(formula, Implies):
            return [RuleName.IMPLIES_LEFT]
        elif isinstance(formula, Not):
            return [RuleName.NOT_LEFT]
        elif isinstance(formula, Forall):
            return [RuleName.FORALL_LEFT]
        elif isinstance(formula, Exists):
            return [RuleName.EXISTS_LEFT]
        elif isinstance(formula, Bottom):
            return [RuleName.BOTTOM_LEFT]
        elif isinstance(formula, Top):
            return []
        else:
            return [RuleName.AXIOM]
    return []
