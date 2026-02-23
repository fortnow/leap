"""Disambiguation types for when a click target has multiple possible rules."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from leap.core.rules import RuleName


@dataclass(frozen=True)
class AmbiguousChoice:
    """Represents a choice the user must make."""
    rule: RuleName
    label: str
    description: str


@dataclass(frozen=True)
class Ambiguity:
    """The click maps to multiple possible rules — user must choose."""
    choices: tuple[AmbiguousChoice, ...]
    message: str


@dataclass(frozen=True)
class NeedsInput:
    """The rule requires additional input from the user (e.g., a witness term)."""
    rule: RuleName
    prompt: str           # what to ask the user
    input_type: str       # "term" for term input, "formula" for formula input
    placeholder: str = ""
