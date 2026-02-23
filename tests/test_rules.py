"""Tests for sequent calculus rules."""

import pytest
from leap.core.ast import Pred, Not, And, Or, Implies, Forall, Exists, Top, Bottom, Var, Side
from leap.core.sequent import Sequent
from leap.core.rules import apply_rule, RuleName, rules_for
from leap.core.unify import reset_fresh_counter


@pytest.fixture(autouse=True)
def reset_counter():
    reset_fresh_counter()
    yield


P = Pred("P")
Q = Pred("Q")
R = Pred("R")


class TestAxiom:
    def test_identity(self):
        seq = Sequent.make([P], [P])
        result = apply_rule(RuleName.AXIOM, seq, 0)
        assert result.premises == ()

    def test_bottom_left(self):
        seq = Sequent.make([Bottom()], [P])
        assert seq.is_axiom()

    def test_top_right(self):
        seq = Sequent.make([P], [Top()])
        assert seq.is_axiom()

    def test_not_axiom(self):
        seq = Sequent.make([P], [Q])
        assert not seq.is_axiom()
        with pytest.raises(ValueError):
            apply_rule(RuleName.AXIOM, seq, 0)


class TestRightRules:
    def test_and_right(self):
        seq = Sequent.make([], [And(P, Q)])
        result = apply_rule(RuleName.AND_RIGHT, seq, 0)
        assert len(result.premises) == 2
        assert result.premises[0] == Sequent.make([], [P])
        assert result.premises[1] == Sequent.make([], [Q])

    def test_or_right_l(self):
        seq = Sequent.make([], [Or(P, Q)])
        result = apply_rule(RuleName.OR_RIGHT_L, seq, 0)
        assert len(result.premises) == 1
        assert result.premises[0] == Sequent.make([], [P])

    def test_or_right_r(self):
        seq = Sequent.make([], [Or(P, Q)])
        result = apply_rule(RuleName.OR_RIGHT_R, seq, 0)
        assert len(result.premises) == 1
        assert result.premises[0] == Sequent.make([], [Q])

    def test_implies_right(self):
        seq = Sequent.make([], [Implies(P, Q)])
        result = apply_rule(RuleName.IMPLIES_RIGHT, seq, 0)
        assert len(result.premises) == 1
        assert result.premises[0] == Sequent.make([P], [Q])

    def test_not_right(self):
        seq = Sequent.make([], [Not(P)])
        result = apply_rule(RuleName.NOT_RIGHT, seq, 0)
        assert len(result.premises) == 1
        assert result.premises[0] == Sequent.make([P], [])

    def test_forall_right(self):
        Px = Pred("P", (Var("x"),))
        seq = Sequent.make([], [Forall("x", Px)])
        result = apply_rule(RuleName.FORALL_RIGHT, seq, 0)
        assert len(result.premises) == 1
        # Should use a fresh eigenvariable
        new_goals = result.premises[0].goals
        assert len(new_goals) == 1
        assert isinstance(new_goals[0], Pred)

    def test_exists_right_with_witness(self):
        Px = Pred("P", (Var("x"),))
        seq = Sequent.make([], [Exists("x", Px)])
        result = apply_rule(RuleName.EXISTS_RIGHT, seq, 0, term_arg="A")
        assert len(result.premises) == 1
        from leap.core.ast import Func
        expected_body = Pred("P", (Func("A", ()),))
        assert result.premises[0].goals[0] == expected_body


class TestLeftRules:
    def test_and_left(self):
        seq = Sequent.make([And(P, Q)], [R])
        result = apply_rule(RuleName.AND_LEFT, seq, 0)
        assert len(result.premises) == 1
        assert result.premises[0] == Sequent.make([P, Q], [R])

    def test_or_left(self):
        seq = Sequent.make([Or(P, Q)], [R])
        result = apply_rule(RuleName.OR_LEFT, seq, 0)
        assert len(result.premises) == 2
        assert result.premises[0] == Sequent.make([P], [R])
        assert result.premises[1] == Sequent.make([Q], [R])

    def test_implies_left(self):
        seq = Sequent.make([Implies(P, Q)], [R])
        result = apply_rule(RuleName.IMPLIES_LEFT, seq, 0)
        assert len(result.premises) == 2
        # Subgoal 1: prove the antecedent P
        assert P in result.premises[0].goals
        # Subgoal 2: use consequent Q
        assert Q in result.premises[1].hyps

    def test_not_left(self):
        seq = Sequent.make([Not(P)], [Q])
        result = apply_rule(RuleName.NOT_LEFT, seq, 0)
        assert len(result.premises) == 1
        assert P in result.premises[0].goals

    def test_exists_left(self):
        Px = Pred("P", (Var("x"),))
        seq = Sequent.make([Exists("x", Px)], [Q])
        result = apply_rule(RuleName.EXISTS_LEFT, seq, 0)
        assert len(result.premises) == 1
        # The existential should be replaced with a fresh eigenvariable
        new_hyps = result.premises[0].hyps
        assert len(new_hyps) == 1


class TestRulesFor:
    def test_goal_and(self):
        rules = rules_for(And(P, Q), Side.GOAL)
        assert RuleName.AND_RIGHT in rules

    def test_hyp_or(self):
        rules = rules_for(Or(P, Q), Side.HYP)
        assert RuleName.OR_LEFT in rules

    def test_goal_or_ambiguous(self):
        rules = rules_for(Or(P, Q), Side.GOAL)
        assert len(rules) == 2  # OR_RIGHT_L and OR_RIGHT_R

    def test_atom_goal(self):
        rules = rules_for(P, Side.GOAL)
        assert RuleName.AXIOM in rules
