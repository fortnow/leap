"""Sequent data type and basic operations."""

from __future__ import annotations
from dataclasses import dataclass
from .ast import Formula, Pred, Top, Bottom


@dataclass(frozen=True)
class Sequent:
    """A sequent Γ ⊢ Δ in classical first-order logic (LK).

    hyps: list of hypothesis formulas (left of turnstile)
    goals: list of goal formulas (right of turnstile)
    """
    hyps: tuple[Formula, ...]
    goals: tuple[Formula, ...]

    def __str__(self) -> str:
        h = ", ".join(str(f) for f in self.hyps)
        g = ", ".join(str(f) for f in self.goals)
        return f"{h} ⊢ {g}"

    @staticmethod
    def make(hyps: list[Formula] | tuple[Formula, ...],
             goals: list[Formula] | tuple[Formula, ...]) -> Sequent:
        return Sequent(tuple(hyps), tuple(goals))

    def is_axiom(self) -> bool:
        """Check if this sequent is trivially provable (identity axiom or ⊥-L or ⊤-R)."""
        # Identity: same formula on both sides
        for h in self.hyps:
            for g in self.goals:
                if h == g:
                    return True
        # ⊥ in hypotheses
        for h in self.hyps:
            if isinstance(h, Bottom):
                return True
        # ⊤ in goals
        for g in self.goals:
            if isinstance(g, Top):
                return True
        return False

    def replace_hyp(self, index: int, *new_formulas: Formula) -> Sequent:
        """Replace hypothesis at index with zero or more formulas."""
        hyps = list(self.hyps)
        hyps[index:index + 1] = list(new_formulas)
        return Sequent(tuple(hyps), self.goals)

    def replace_goal(self, index: int, *new_formulas: Formula) -> Sequent:
        """Replace goal at index with zero or more formulas."""
        goals = list(self.goals)
        goals[index:index + 1] = list(new_formulas)
        return Sequent(self.hyps, tuple(goals))

    def add_hyp(self, f: Formula) -> Sequent:
        return Sequent(self.hyps + (f,), self.goals)

    def add_goal(self, f: Formula) -> Sequent:
        return Sequent(self.hyps, self.goals + (f,))

    def remove_hyp(self, index: int) -> Sequent:
        hyps = list(self.hyps)
        del hyps[index]
        return Sequent(tuple(hyps), self.goals)

    def remove_goal(self, index: int) -> Sequent:
        goals = list(self.goals)
        del goals[index]
        return Sequent(self.hyps, tuple(goals))
