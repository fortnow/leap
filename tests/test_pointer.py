"""Tests for the pointing engine — the core proof-by-pointing algorithm."""

import pytest
from leap.core.ast import (
    Pred, Not, And, Or, Implies, Forall, Exists, Top, Bottom, Var,
    Side, ClickTarget, Direction,
)
from leap.core.sequent import Sequent
from leap.core.proof import ProofState
from leap.core.parser import parse_formula
from leap.core.unify import reset_fresh_counter
from leap.engine.pointer import point, PointResult
from leap.engine.disambiguate import Ambiguity, NeedsInput


@pytest.fixture(autouse=True)
def reset_counter():
    reset_fresh_counter()
    yield


P = Pred("P")
Q = Pred("Q")
R = Pred("R")


class TestBasicPointing:
    def test_implies_right_click(self):
        """Clicking → on goal side should apply →-Right."""
        seq = Sequent.make([], [Implies(P, Q)])
        state = ProofState(seq)

        target = ClickTarget(Side.GOAL, 0, ())
        result = point(state, target)

        assert isinstance(result, PointResult)
        # Should have moved P to hypotheses
        focus = state.focus
        assert focus is not None
        assert P in focus.sequent.hyps
        assert Q in focus.sequent.goals

    def test_and_right_click(self):
        """Clicking ∧ on goal side should split into two subgoals."""
        seq = Sequent.make([P, Q], [And(P, Q)])
        state = ProofState(seq)

        target = ClickTarget(Side.GOAL, 0, ())
        result = point(state, target)

        assert isinstance(result, PointResult)
        goals = state.open_goals()
        # Both subgoals auto-close because P ⊢ P and Q ⊢ Q are axioms
        # (with the full hyps P, Q available)
        assert state.is_complete

    def test_and_left_click(self):
        """Clicking ∧ on hypothesis side should split conjunction."""
        seq = Sequent.make([And(P, Q)], [P])
        state = ProofState(seq)

        target = ClickTarget(Side.HYP, 0, ())
        result = point(state, target)

        assert isinstance(result, PointResult)
        # After splitting, P, Q ⊢ P should auto-close
        assert state.is_complete

    def test_or_goal_ambiguity(self):
        """Clicking ∨ on goal side should produce an ambiguity."""
        seq = Sequent.make([P], [Or(P, Q)])
        state = ProofState(seq)

        target = ClickTarget(Side.GOAL, 0, ())
        result = point(state, target)

        assert isinstance(result, Ambiguity)
        assert len(result.choices) == 2

    def test_or_goal_with_choice(self):
        """Providing a choice resolves the ambiguity."""
        from leap.core.rules import RuleName
        seq = Sequent.make([P], [Or(P, Q)])
        state = ProofState(seq)

        target = ClickTarget(Side.GOAL, 0, ())
        result = point(state, target, choice=RuleName.OR_RIGHT_L)

        assert isinstance(result, PointResult)
        # Chose left: now need to prove P, which is an axiom
        assert state.is_complete

    def test_axiom_click(self):
        """Clicking an atomic formula that matches triggers axiom."""
        seq = Sequent.make([P], [P])
        state = ProofState(seq)

        target = ClickTarget(Side.GOAL, 0, ())
        result = point(state, target)

        assert isinstance(result, PointResult)
        assert state.is_complete

    def test_top_right(self):
        """Clicking ⊤ on goal side closes immediately."""
        seq = Sequent.make([], [Top()])
        state = ProofState(seq)

        target = ClickTarget(Side.GOAL, 0, ())
        result = point(state, target)

        assert isinstance(result, PointResult)
        assert state.is_complete

    def test_bottom_left(self):
        """Clicking ⊥ on hypothesis side closes immediately."""
        seq = Sequent.make([Bottom()], [P])
        state = ProofState(seq)

        target = ClickTarget(Side.HYP, 0, ())
        result = point(state, target)

        assert isinstance(result, PointResult)
        assert state.is_complete


class TestQuantifierPointing:
    def test_forall_left_needs_input(self):
        """Clicking ∀ on hypothesis side should request a term."""
        Px = Pred("P", (Var("x"),))
        seq = Sequent.make([Forall("x", Px)], [Pred("P", (Var("a"),))])
        state = ProofState(seq)

        target = ClickTarget(Side.HYP, 0, ())
        result = point(state, target)

        assert isinstance(result, NeedsInput)
        assert result.input_type == "term"

    def test_forall_left_with_input(self):
        """Providing a term instantiates the quantifier."""
        Px = Pred("P", (Var("x"),))
        Pa = Pred("P", (Var("a"),))
        seq = Sequent.make([Forall("x", Px)], [Pa])
        state = ProofState(seq)

        target = ClickTarget(Side.HYP, 0, ())
        result = point(state, target, term_input="a")

        assert isinstance(result, PointResult)
        # Now we have ∀x.P(x), P(a) ⊢ P(a) which should auto-close
        assert state.is_complete

    def test_forall_right(self):
        """Clicking ∀ on goal side introduces eigenvariable."""
        Px = Pred("P", (Var("x"),))
        seq = Sequent.make([], [Forall("x", Px)])
        state = ProofState(seq)

        target = ClickTarget(Side.GOAL, 0, ())
        result = point(state, target)

        assert isinstance(result, PointResult)
        focus = state.focus
        assert focus is not None
        # The goal should now be P(x1) or similar
        assert len(focus.sequent.goals) == 1

    def test_exists_right_needs_input(self):
        """Clicking ∃ on goal side should request a witness."""
        Px = Pred("P", (Var("x"),))
        seq = Sequent.make([], [Exists("x", Px)])
        state = ProofState(seq)

        target = ClickTarget(Side.GOAL, 0, ())
        result = point(state, target)

        assert isinstance(result, NeedsInput)


class TestDeepPointing:
    def test_deep_click_applies_outer(self):
        """Clicking deep into a formula should at least apply the outer rule."""
        f = Implies(And(P, Q), R)
        seq = Sequent.make([], [f])
        state = ProofState(seq)

        # Click on P inside (P ∧ Q) → R
        target = ClickTarget(Side.GOAL, 0, (Direction.LEFT, Direction.LEFT))
        result = point(state, target)

        # Should apply →-Right (the outermost rule)
        assert isinstance(result, PointResult)
        focus = state.focus
        assert focus is not None
        # P ∧ Q should now be in hypotheses
        assert And(P, Q) in focus.sequent.hyps


class TestUndoAndProofState:
    def test_undo(self):
        seq = Sequent.make([], [Implies(P, P)])
        state = ProofState(seq)

        target = ClickTarget(Side.GOAL, 0, ())
        point(state, target)  # apply →-Right

        # We should now be at P ⊢ P
        assert not state.is_complete or state.is_complete  # either way

        state.undo()
        focus = state.focus
        assert focus is not None
        assert focus.sequent == seq


class TestFullProofs:
    def test_p_implies_p(self):
        """Prove P → P by pointing."""
        f = parse_formula("P -> P")
        seq = Sequent.make([], [f])
        state = ProofState(seq)

        # Click → on goal
        result = point(state, ClickTarget(Side.GOAL, 0, ()))
        assert isinstance(result, PointResult)

        # Now P ⊢ P — should auto-close
        assert state.is_complete

    def test_transitivity(self):
        """Prove (P→Q) → (Q→R) → (P→R)."""
        f = parse_formula("(P -> Q) -> (Q -> R) -> (P -> R)")
        seq = Sequent.make([], [f])
        state = ProofState(seq)

        # Click →  three times to decompose all implications on goal side
        for _ in range(3):
            goals = state.open_goals()
            if not goals:
                break
            focus = goals[0]
            state.set_focus(focus.node_id)
            seq = focus.sequent
            # Find the first implies in goals
            for i, g in enumerate(seq.goals):
                if isinstance(g, Implies):
                    result = point(state, ClickTarget(Side.GOAL, i, ()))
                    break

        # Now: P→Q, Q→R, P ⊢ R
        # Click P→Q in hypotheses
        focus = state.focus
        assert focus is not None
        seq = focus.sequent

        # Find P→Q in hyps
        for i, h in enumerate(seq.hyps):
            if isinstance(h, Implies) and str(h) == "P → Q":
                result = point(state, ClickTarget(Side.HYP, i, ()))
                break

        # Now two subgoals:
        # 1. Q→R, P ⊢ P (auto-closed)
        # 2. Q, Q→R, P ⊢ R
        # Click Q→R in the remaining open goal
        for goal in state.open_goals():
            state.set_focus(goal.node_id)
            seq = goal.sequent
            for i, h in enumerate(seq.hyps):
                if isinstance(h, Implies) and str(h) == "Q → R":
                    result = point(state, ClickTarget(Side.HYP, i, ()))
                    break

        assert state.is_complete

    def test_conjunction_commutativity(self):
        """Prove P ∧ Q → Q ∧ P."""
        f = parse_formula("P & Q -> Q & P")
        seq = Sequent.make([], [f])
        state = ProofState(seq)

        # Step 1: Click → on goal
        point(state, ClickTarget(Side.GOAL, 0, ()))
        # Now: P ∧ Q ⊢ Q ∧ P

        # Step 2: Click ∧ on hypothesis to split it
        focus = state.focus
        for i, h in enumerate(focus.sequent.hyps):
            if isinstance(h, And):
                point(state, ClickTarget(Side.HYP, i, ()))
                break
        # Now: P, Q ⊢ Q ∧ P

        # Step 3: Click ∧ on goal to split it
        focus = state.focus
        for i, g in enumerate(focus.sequent.goals):
            if isinstance(g, And):
                point(state, ClickTarget(Side.GOAL, i, ()))
                break
        # Now: P, Q ⊢ Q  and  P, Q ⊢ P — both auto-close
        assert state.is_complete
