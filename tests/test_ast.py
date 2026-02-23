"""Tests for the FOL AST, parser, and printer."""

import pytest
from leap.core.ast import (
    Var, Func, Const, Pred, Not, And, Or, Implies, Forall, Exists, Top, Bottom,
    Direction, resolve_address, free_vars, principal_connective, is_atomic,
)
from leap.core.parser import parse_formula, parse_term, parse_sequent


# ---------------------------------------------------------------------------
# AST construction and str
# ---------------------------------------------------------------------------

class TestFormulaPrinting:
    def test_atomic(self):
        assert str(Pred("P")) == "P"
        assert str(Pred("R", (Var("x"), Const("A")))) == "R(x, A)"

    def test_connectives(self):
        P, Q = Pred("P"), Pred("Q")
        assert str(And(P, Q)) == "P ∧ Q"
        assert str(Or(P, Q)) == "P ∨ Q"
        assert str(Implies(P, Q)) == "P → Q"
        assert str(Not(P)) == "¬P"

    def test_quantifiers(self):
        P = Pred("P", (Var("x"),))
        assert str(Forall("x", P)) == "∀x. P(x)"
        assert str(Exists("x", P)) == "∃x. P(x)"

    def test_precedence(self):
        P, Q, R = Pred("P"), Pred("Q"), Pred("R")
        f = Implies(And(P, Q), R)
        assert str(f) == "P ∧ Q → R"  # no parens needed around And

        f2 = And(Implies(P, Q), R)
        assert str(f2) == "(P → Q) ∧ R"  # parens needed

    def test_top_bottom(self):
        assert str(Top()) == "⊤"
        assert str(Bottom()) == "⊥"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class TestParser:
    def test_simple_prop(self):
        f = parse_formula("P")
        assert f == Pred("P")

    def test_implication(self):
        f = parse_formula("P -> Q")
        assert f == Implies(Pred("P"), Pred("Q"))

    def test_right_associativity(self):
        f = parse_formula("P -> Q -> R")
        assert f == Implies(Pred("P"), Implies(Pred("Q"), Pred("R")))

    def test_conjunction(self):
        f = parse_formula("P & Q")
        assert f == And(Pred("P"), Pred("Q"))

    def test_disjunction(self):
        f = parse_formula("P | Q")
        assert f == Or(Pred("P"), Pred("Q"))

    def test_negation(self):
        f = parse_formula("~P")
        assert f == Not(Pred("P"))

    def test_forall(self):
        f = parse_formula("forall x. P(x)")
        assert f == Forall("x", Pred("P", (Var("x"),)))

    def test_exists(self):
        f = parse_formula("exists x. P(x)")
        assert f == Exists("x", Pred("P", (Var("x"),)))

    def test_complex(self):
        f = parse_formula("(P -> Q) -> (Q -> R) -> (P -> R)")
        expected = Implies(
            Implies(Pred("P"), Pred("Q")),
            Implies(
                Implies(Pred("Q"), Pred("R")),
                Implies(Pred("P"), Pred("R")),
            )
        )
        assert f == expected

    def test_top_bottom(self):
        assert parse_formula("T") == Top()
        assert parse_formula("F") == Bottom()

    def test_unicode_connectives(self):
        f = parse_formula("P ∧ Q → R")
        assert f == Implies(And(Pred("P"), Pred("Q")), Pred("R"))

    def test_predicate_with_args(self):
        f = parse_formula("R(x, A)")
        assert f == Pred("R", (Var("x"), Const("A")))

    def test_parse_term(self):
        t = parse_term("f(x, g(y))")
        assert t == Func("f", (Var("x"), Func("g", (Var("y"),))))

    def test_parse_sequent(self):
        hyps, goals = parse_sequent("P, Q |- R")
        assert hyps == [Pred("P"), Pred("Q")]
        assert goals == [Pred("R")]


# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------

class TestAddress:
    def test_empty_address(self):
        f = Implies(Pred("P"), Pred("Q"))
        assert resolve_address(f, ()) == f

    def test_left(self):
        f = Implies(Pred("P"), Pred("Q"))
        assert resolve_address(f, (Direction.LEFT,)) == Pred("P")

    def test_right(self):
        f = Implies(Pred("P"), Pred("Q"))
        assert resolve_address(f, (Direction.RIGHT,)) == Pred("Q")

    def test_deep(self):
        f = Implies(And(Pred("A"), Pred("B")), Pred("C"))
        assert resolve_address(f, (Direction.LEFT, Direction.RIGHT)) == Pred("B")

    def test_body(self):
        f = Forall("x", Pred("P", (Var("x"),)))
        assert resolve_address(f, (Direction.BODY,)) == Pred("P", (Var("x"),))

    def test_invalid_address(self):
        f = Pred("P")
        with pytest.raises(ValueError):
            resolve_address(f, (Direction.LEFT,))


# ---------------------------------------------------------------------------
# Free variables
# ---------------------------------------------------------------------------

class TestFreeVars:
    def test_pred(self):
        f = Pred("P", (Var("x"), Var("y")))
        assert free_vars(f) == {"x", "y"}

    def test_bound(self):
        f = Forall("x", Pred("P", (Var("x"),)))
        assert free_vars(f) == set()

    def test_mixed(self):
        f = Forall("x", Pred("R", (Var("x"), Var("y"))))
        assert free_vars(f) == {"y"}


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

class TestUtility:
    def test_principal_connective(self):
        assert principal_connective(Pred("P")) == "atom"
        assert principal_connective(And(Pred("P"), Pred("Q"))) == "and"
        assert principal_connective(Implies(Pred("P"), Pred("Q"))) == "implies"

    def test_is_atomic(self):
        assert is_atomic(Pred("P"))
        assert is_atomic(Top())
        assert not is_atomic(And(Pred("P"), Pred("Q")))
