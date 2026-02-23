"""Proof tree and proof state management with undo support."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .sequent import Sequent
from .rules import RuleName, RuleResult


@dataclass
class ProofNode:
    """A node in the proof tree.

    A leaf with rule=None is an open (unsolved) goal.
    A leaf with rule set and no children is an axiom.
    An internal node has a rule and children (subgoals).
    """
    sequent: Sequent
    rule: Optional[RuleName] = None
    message: str = ""
    children: list[ProofNode] = field(default_factory=list)
    node_id: int = 0

    @property
    def is_open(self) -> bool:
        return self.rule is None

    @property
    def is_proved(self) -> bool:
        if self.rule is None:
            return False
        if not self.children:
            return True  # axiom / zero-premise rule
        return all(c.is_proved for c in self.children)

    def open_goals(self) -> list[ProofNode]:
        """Return all open (unsolved) leaf nodes."""
        if self.is_open:
            return [self]
        result: list[ProofNode] = []
        for c in self.children:
            result.extend(c.open_goals())
        return result

    def find_by_id(self, node_id: int) -> Optional[ProofNode]:
        if self.node_id == node_id:
            return self
        for c in self.children:
            found = c.find_by_id(node_id)
            if found is not None:
                return found
        return None


class ProofState:
    """Manages the overall proof state with undo history."""

    def __init__(self, goal: Sequent):
        self._id_counter = 0
        self.root = self._make_node(goal)
        self._focus_id: int = self.root.node_id
        self._history: list[tuple[ProofNode, int]] = []  # (root_snapshot, focus_id)

    def _make_node(self, sequent: Sequent) -> ProofNode:
        self._id_counter += 1
        return ProofNode(sequent=sequent, node_id=self._id_counter)

    @property
    def is_complete(self) -> bool:
        return self.root.is_proved

    @property
    def focus(self) -> Optional[ProofNode]:
        return self.root.find_by_id(self._focus_id)

    @property
    def focus_id(self) -> int:
        return self._focus_id

    def open_goals(self) -> list[ProofNode]:
        return self.root.open_goals()

    def set_focus(self, node_id: int) -> bool:
        """Set focus to a specific open goal by node_id."""
        node = self.root.find_by_id(node_id)
        if node is not None and node.is_open:
            self._focus_id = node_id
            return True
        return False

    def apply(self, result: RuleResult) -> bool:
        """Apply a rule result to the currently focused goal.

        Returns True if successful, False if no focused open goal.
        """
        focus = self.focus
        if focus is None or not focus.is_open:
            # Try to auto-focus on first open goal
            goals = self.open_goals()
            if not goals:
                return False
            focus = goals[0]
            self._focus_id = focus.node_id

        # Save snapshot for undo (deep copy via reconstruction)
        self._history.append((self._deep_copy(self.root), self._focus_id))

        # Apply the rule
        focus.rule = result.rule
        focus.message = result.message
        focus.children = [self._make_node(s) for s in result.premises]

        # Auto-close any axiom children
        for child in focus.children:
            if child.sequent.is_axiom():
                from .rules import RuleName
                child.rule = RuleName.AXIOM
                child.message = "Axiom"

        # Move focus to first open child, or next open goal
        open_children = [c for c in focus.children if c.is_open]
        if open_children:
            self._focus_id = open_children[0].node_id
        else:
            remaining = self.open_goals()
            if remaining:
                self._focus_id = remaining[0].node_id

        return True

    def undo(self) -> bool:
        """Undo the last rule application."""
        if not self._history:
            return False
        self.root, self._focus_id = self._history.pop()
        return True

    def _deep_copy(self, node: ProofNode) -> ProofNode:
        """Create an independent copy of the proof tree."""
        copy = ProofNode(
            sequent=node.sequent,
            rule=node.rule,
            message=node.message,
            children=[self._deep_copy(c) for c in node.children],
            node_id=node.node_id,
        )
        return copy

    def to_dict(self) -> dict:
        """Serialize proof state for the UI."""
        return {
            "is_complete": self.is_complete,
            "focus_id": self._focus_id,
            "tree": self._node_to_dict(self.root),
            "open_goals": [
                {"id": g.node_id, "sequent": str(g.sequent)}
                for g in self.open_goals()
            ],
            "can_undo": len(self._history) > 0,
        }

    def _node_to_dict(self, node: ProofNode) -> dict:
        return {
            "id": node.node_id,
            "sequent": str(node.sequent),
            "rule": node.rule.name if node.rule else None,
            "message": node.message,
            "is_open": node.is_open,
            "is_proved": node.is_proved,
            "is_focused": node.node_id == self._focus_id,
            "children": [self._node_to_dict(c) for c in node.children],
        }
