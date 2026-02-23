"""Flask web application for LEAP proof-by-pointing interface."""

from __future__ import annotations
import json
import os
from typing import Dict, Optional, Tuple, List
from flask import Flask, render_template, request, jsonify, session
from leap.core.ast import Side, ClickTarget, Direction
from leap.core.parser import parse_formula, parse_sequent
from leap.core.printer import sequent_to_html
from leap.core.sequent import Sequent
from leap.core.rules import RuleName
from leap.core.proof import ProofState
from leap.engine.pointer import point, PointResult
from leap.engine.disambiguate import Ambiguity, NeedsInput

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "leap-proof-by-pointing-dev-key")

# In-memory proof states (keyed by session)
_proof_states: Dict[str, ProofState] = {}


def _get_state() -> Optional[ProofState]:
    sid = session.get("proof_id")
    if sid and sid in _proof_states:
        return _proof_states[sid]
    return None


def _set_state(state: ProofState) -> str:
    import uuid
    sid = str(uuid.uuid4())
    session["proof_id"] = sid
    _proof_states[sid] = state
    return sid


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def start_proof():
    """Start a new proof. Body: {"formula": "P -> P"} or {"sequent": "A |- B"}"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    try:
        if "sequent" in data:
            hyps, goals = parse_sequent(data["sequent"])
        elif "formula" in data:
            formula = parse_formula(data["formula"])
            hyps, goals = [], [formula]
        else:
            return jsonify({"error": "Provide 'formula' or 'sequent'"}), 400
    except ValueError as e:
        return jsonify({"error": f"Parse error: {e}"}), 400

    seq = Sequent.make(hyps, goals)
    state = ProofState(seq)
    _set_state(state)

    return jsonify(_build_response(state))


@app.route("/api/click", methods=["POST"])
def handle_click():
    """Handle a click on a formula element."""
    state = _get_state()
    if state is None:
        return jsonify({"error": "No active proof. Start one first."}), 400

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    side = Side.HYP if data.get("side") == "hyp" else Side.GOAL
    idx = int(data.get("index", 0))
    addr_str = data.get("address", "")
    address = _parse_address(addr_str)

    target = ClickTarget(side=side, index=idx, address=address)

    term_input = data.get("term_input")
    choice_str = data.get("choice")
    choice = RuleName[choice_str] if choice_str else None

    outcome = point(state, target, term_input=term_input, choice=choice)

    if isinstance(outcome, PointResult):
        resp = _build_response(state)
        resp["action"] = "applied"
        resp["message"] = outcome.message
        return jsonify(resp)

    elif isinstance(outcome, Ambiguity):
        return jsonify({
            "action": "ambiguity",
            "message": outcome.message,
            "choices": [
                {"rule": c.rule.name, "label": c.label, "description": c.description}
                for c in outcome.choices
            ],
            **_build_response(state),
        })

    elif isinstance(outcome, NeedsInput):
        return jsonify({
            "action": "needs_input",
            "rule": outcome.rule.name,
            "prompt": outcome.prompt,
            "input_type": outcome.input_type,
            "placeholder": outcome.placeholder,
            **_build_response(state),
        })

    else:
        return jsonify({
            "action": "error",
            "message": str(outcome),
            **_build_response(state),
        })


@app.route("/api/undo", methods=["POST"])
def undo():
    state = _get_state()
    if state is None:
        return jsonify({"error": "No active proof"}), 400
    if state.undo():
        resp = _build_response(state)
        resp["action"] = "undone"
        resp["message"] = "Last step undone"
        return jsonify(resp)
    return jsonify({"action": "error", "message": "Nothing to undo",
                     **_build_response(state)})


@app.route("/api/focus", methods=["POST"])
def set_focus():
    state = _get_state()
    if state is None:
        return jsonify({"error": "No active proof"}), 400
    data = request.get_json()
    node_id = int(data.get("node_id", 0))
    if state.set_focus(node_id):
        resp = _build_response(state)
        resp["action"] = "focused"
        return jsonify(resp)
    return jsonify({"action": "error", "message": "Cannot focus on that node",
                     **_build_response(state)})


@app.route("/api/state", methods=["GET"])
def get_state():
    state = _get_state()
    if state is None:
        return jsonify({"error": "No active proof"}), 400
    return jsonify(_build_response(state))


def _build_response(state: ProofState) -> dict:
    focus = state.focus
    focus_sequent_html = ""
    if focus and focus.is_open:
        focus_sequent_html = sequent_to_html(
            list(focus.sequent.hyps), list(focus.sequent.goals))

    return {
        "proof": state.to_dict(),
        "focus_html": focus_sequent_html,
        "is_complete": state.is_complete,
    }


def _parse_address(addr_str: str) -> tuple:
    """Parse 'L.R.B' into a tuple of Direction values."""
    if not addr_str:
        return ()
    parts = addr_str.split(".")
    dirs = []
    for p in parts:
        upper = p.upper()
        if upper == "L":
            dirs.append(Direction.LEFT)
        elif upper == "R":
            dirs.append(Direction.RIGHT)
        elif upper == "B":
            dirs.append(Direction.BODY)
        else:
            raise ValueError(f"Unknown direction: {p}")
    return tuple(dirs)


# ---------------------------------------------------------------------------
# Example formulas
# ---------------------------------------------------------------------------

EXAMPLES = [
    {"label": "P → P", "formula": "P -> P"},
    {"label": "(P → Q) → (Q → R) → (P → R)", "formula": "(P -> Q) -> (Q -> R) -> (P -> R)"},
    {"label": "P ∧ Q → Q ∧ P", "formula": "P & Q -> Q & P"},
    {"label": "P ∨ Q → Q ∨ P", "formula": "P | Q -> Q | P"},
    {"label": "¬¬P → P", "formula": "~~P -> P"},
    {"label": "(P → Q) → (¬Q → ¬P)", "formula": "(P -> Q) -> (~Q -> ~P)"},
    {"label": "P ∧ (Q ∨ R) → (P ∧ Q) ∨ (P ∧ R)", "formula": "P & (Q | R) -> (P & Q) | (P & R)"},
    {"label": "⊥ → P", "formula": "F -> P"},
]


@app.route("/api/examples", methods=["GET"])
def examples():
    return jsonify({"examples": EXAMPLES})


def main():
    app.run(debug=True, port=5000)


if __name__ == "__main__":
    main()
