"""Deep pointing: decompose a formula along an address path."""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from leap.core.ast import (
    Formula, Not, And, Or, Implies, Forall, Exists, Top, Bottom, Pred,
    Direction, Address, Side, resolve_address,
)
from leap.core.rules import RuleName


@dataclass
class DecompStep:
    """One step in the decomposition chain."""
    rule: RuleName
    description: str


def compute_decomposition(formula: Formula, address: Address,
                          side: Side) -> List[RuleName]:
    """Compute the sequence of rules to apply to reach the subformula at `address`."""
    if not address:
        return []

    rules: List[RuleName] = []
    current = formula

    for i, step in enumerate(address):
        rule = _rule_for_step(current, step, side)
        if rule is not None:
            rules.append(rule)

        # Navigate into the formula
        if step == Direction.LEFT:
            if isinstance(current, (And, Or, Implies)):
                if isinstance(current, Implies) and side == Side.GOAL:
                    side = Side.HYP
                current = current.left
            else:
                break
        elif step == Direction.RIGHT:
            if isinstance(current, (And, Or, Implies)):
                current = current.right
            else:
                break
        elif step in (Direction.BODY, Direction.INNER):
            if isinstance(current, (Forall, Exists)):
                current = current.body
            elif isinstance(current, Not):
                side = Side.HYP if side == Side.GOAL else Side.GOAL
                current = current.inner
            else:
                break

    return rules


def _rule_for_step(formula: Formula, step: Direction, side: Side) -> Optional[RuleName]:
    """Determine the rule to apply for a single step in the address path."""
    if side == Side.GOAL:
        if isinstance(formula, And):
            return RuleName.AND_RIGHT
        elif isinstance(formula, Or):
            if step == Direction.LEFT:
                return RuleName.OR_RIGHT_L
            else:
                return RuleName.OR_RIGHT_R
        elif isinstance(formula, Implies):
            return RuleName.IMPLIES_RIGHT
        elif isinstance(formula, Not):
            return RuleName.NOT_RIGHT
        elif isinstance(formula, Forall):
            return RuleName.FORALL_RIGHT
        elif isinstance(formula, Exists):
            return RuleName.EXISTS_RIGHT
        elif isinstance(formula, Top):
            return RuleName.TOP_RIGHT
    else:  # HYP
        if isinstance(formula, And):
            return RuleName.AND_LEFT
        elif isinstance(formula, Or):
            return RuleName.OR_LEFT
        elif isinstance(formula, Implies):
            return RuleName.IMPLIES_LEFT
        elif isinstance(formula, Not):
            return RuleName.NOT_LEFT
        elif isinstance(formula, Forall):
            return RuleName.FORALL_LEFT
        elif isinstance(formula, Exists):
            return RuleName.EXISTS_LEFT
        elif isinstance(formula, Bottom):
            return RuleName.BOTTOM_LEFT

    return None
