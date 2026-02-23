"""The pointing engine: maps click targets to proof actions.

This is the core of the proof-by-pointing paradigm. Given a sequent and a
click target (side, formula index, address within formula), it determines:
  1. Which rule(s) to apply
  2. Whether disambiguation or user input is needed
  3. For deep clicks, the chain of decomposition rules

The main entry point is `point()`.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Union, Optional, List

from leap.core.ast import (
    Formula, Pred, Not, And, Or, Implies, Forall, Exists, Top, Bottom,
    Direction, Address, Side, ClickTarget,
    resolve_address, is_atomic, principal_connective,
)
from leap.core.sequent import Sequent
from leap.core.rules import RuleName, RuleResult, apply_rule, rules_for
from leap.core.proof import ProofState
from .disambiguate import Ambiguity, NeedsInput, AmbiguousChoice


@dataclass
class PointResult:
    """Successful result: one or more rules were applied."""
    applied: List[RuleResult]
    message: str


# Return type of the point function
PointOutcome = Union[PointResult, Ambiguity, NeedsInput, str]


def point(state: ProofState, target: ClickTarget,
          term_input: Optional[str] = None,
          choice: Optional[RuleName] = None) -> PointOutcome:
    """Process a click on a sequent element."""
    focus = state.focus
    if focus is None:
        return "No open goal to work on"

    sequent = focus.sequent

    # Validate target
    if target.side == Side.HYP:
        if target.index < 0 or target.index >= len(sequent.hyps):
            return f"Invalid hypothesis index: {target.index}"
        root_formula = sequent.hyps[target.index]
    else:
        if target.index < 0 or target.index >= len(sequent.goals):
            return f"Invalid goal index: {target.index}"
        root_formula = sequent.goals[target.index]

    # Resolve the clicked subformula
    try:
        subformula = resolve_address(root_formula, target.address)
    except ValueError as e:
        return f"Invalid address: {e}"

    # If clicking on the root of the formula (no address), handle directly
    if not target.address:
        return _handle_root_click(state, sequent, target, root_formula,
                                  term_input, choice)

    # Deep click: apply the outermost rule
    return _handle_root_click(state, sequent,
                              ClickTarget(target.side, target.index, ()),
                              root_formula, term_input, choice)


def _handle_root_click(state: ProofState, sequent: Sequent,
                       target: ClickTarget, formula: Formula,
                       term_input: Optional[str],
                       choice: Optional[RuleName]) -> PointOutcome:
    """Handle a click on the outermost connective of a formula."""

    side = target.side
    idx = target.index

    # Check for axiom first (clicking an atomic formula)
    if is_atomic(formula):
        if isinstance(formula, Top) and side == Side.GOAL:
            result = apply_rule(RuleName.TOP_RIGHT, sequent, idx)
            state.apply(result)
            return PointResult([result], result.message)
        if isinstance(formula, Bottom) and side == Side.HYP:
            result = apply_rule(RuleName.BOTTOM_LEFT, sequent, idx)
            state.apply(result)
            return PointResult([result], result.message)
        # Try axiom (identity)
        if sequent.is_axiom():
            from leap.core.rules import _axiom
            result = _axiom(sequent)
            state.apply(result)
            return PointResult([result], result.message)
        return "No applicable rule for this atomic formula"

    # Determine applicable rules
    applicable = rules_for(formula, side)
    if not applicable:
        return f"No rules applicable to {principal_connective(formula)} on the {side.name} side"

    # If a choice was provided, use it
    if choice is not None:
        if choice not in applicable:
            return f"Rule {choice.name} is not applicable here"
        applicable = [choice]

    # Check if disambiguation is needed
    if len(applicable) > 1:
        choices = tuple(
            AmbiguousChoice(r, r.name, _rule_description(r))
            for r in applicable
        )
        return Ambiguity(choices, f"Multiple rules apply — please choose:")

    rule = applicable[0]

    # Check if input is needed
    if rule in (RuleName.FORALL_LEFT, RuleName.EXISTS_RIGHT):
        if term_input is None:
            prompt = ("Enter a term to instantiate the quantifier:"
                      if rule == RuleName.FORALL_LEFT
                      else "Enter a witness term:")
            return NeedsInput(rule, prompt, "term", "x")
        result = apply_rule(rule, sequent, idx, term_arg=term_input)
        state.apply(result)
        return PointResult([result], result.message)

    # Apply the rule
    result = apply_rule(rule, sequent, idx)
    state.apply(result)
    return PointResult([result], result.message)


def _rule_description(rule: RuleName) -> str:
    descriptions = {
        RuleName.AND_RIGHT: "Split into two subgoals (prove both sides)",
        RuleName.OR_RIGHT_L: "Prove the left disjunct",
        RuleName.OR_RIGHT_R: "Prove the right disjunct",
        RuleName.IMPLIES_RIGHT: "Move antecedent to hypotheses",
        RuleName.NOT_RIGHT: "Move negated formula to hypotheses",
        RuleName.FORALL_RIGHT: "Introduce a fresh variable",
        RuleName.EXISTS_RIGHT: "Provide a witness term",
        RuleName.TOP_RIGHT: "⊤ is trivially true",
        RuleName.AND_LEFT: "Split conjunction into both parts",
        RuleName.OR_LEFT: "Case split: prove for each disjunct",
        RuleName.IMPLIES_LEFT: "Use implication: prove antecedent, get consequent",
        RuleName.NOT_LEFT: "Move negated formula to goals",
        RuleName.FORALL_LEFT: "Instantiate with a term",
        RuleName.EXISTS_LEFT: "Introduce a fresh variable for witness",
        RuleName.BOTTOM_LEFT: "⊥ closes the goal",
        RuleName.AXIOM: "Goal matches a hypothesis",
    }
    return descriptions.get(rule, rule.name)
