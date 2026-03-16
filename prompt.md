**Prompt given to Claude Code**
Architecture of a system to support proof by pointing in first order logic using LEAP
**Initial Response**
Now I have a solid understanding of the concept. Let me design the architecture.

---

## Architecture: LEAP — Logic Engine for Argument by Pointing

LEAP is a system that implements **proof by pointing** for first-order logic (FOL), based on the foundational ideas of [Bertot, Kahn & Théry (1994)](https://link.springer.com/chapter/10.1007/3-540-57887-0_94). The user constructs proofs by clicking on subformulas in a sequent, and the system determines the appropriate inference rule to apply based on the **location** of the click within the logical expression.

---

### Core Idea

In a sequent calculus presentation like `Γ ⊢ Δ`, every connective (∧, ∨, →, ¬, ∀, ∃) has exactly two rules: one for when it appears on the **left** of the turnstile (hypothesis), one for the **right** (conclusion). A click on a connective **uniquely determines** which rule to fire. The system decomposes the clicked formula, producing subgoals, and the proof tree grows.

---

### System Layers

```
┌─────────────────────────────────────────────────────┐
│                   UI Layer                          │
│  Interactive sequent display with clickable regions │
│  Proof tree visualization, undo/redo, goal list    │
├─────────────────────────────────────────────────────┤
│              Pointing Engine                        │
│  Maps (click location) → (inference rule + params) │
│  Address-based subformula resolution                │
│  Ambiguity resolution & user disambiguation        │
├─────────────────────────────────────────────────────┤
│            Sequent Calculus Core                    │
│  Inference rules (LK-style for classical FOL)      │
│  Rule application, unification, substitution       │
│  Proof state management, proof tree construction   │
├─────────────────────────────────────────────────────┤
│           FOL Representation Layer                  │
│  AST for terms and formulas                        │
│  Parser (text → AST), pretty-printer (AST → text)  │
│  Subformula addressing (paths into the AST)        │
└─────────────────────────────────────────────────────┘
```

---

### Layer 1: FOL Representation

**Purpose:** Define the data structures for first-order logic and the addressing scheme that makes "pointing" possible.

#### Formula AST

```
Term ::= Var(name)
       | Func(name, [Term...])       -- includes constants as 0-ary

Formula ::= Pred(name, [Term...])    -- atomic predicate
           | Not(Formula)
           | And(Formula, Formula)
           | Or(Formula, Formula)
           | Implies(Formula, Formula)
           | Forall(var, Formula)
           | Exists(var, Formula)
           | Top | Bottom
```

#### Subformula Addresses

A key insight from Bertot et al.: every position in a formula can be described by a **path** — a sequence of directions from the root. For example, in `(A ∧ B) → C`:

```
Address []        = (A ∧ B) → C       (the whole formula)
Address [Left]    = A ∧ B              (antecedent of →)
Address [Left, Left]  = A              (left of ∧)
Address [Left, Right] = B              (right of ∧)
Address [Right]   = C                  (consequent of →)
```

The address tells the pointing engine **which connective** was clicked and **on which side** of the turnstile it sits.

#### Key types:

```
Direction  ::= Left | Right | Body    -- Body for quantifier bodies
Address    = [Direction]              -- path into formula tree
Side       ::= Hyp(index) | Goal(index)  -- which side of ⊢
ClickTarget = (Side, Address)         -- full location in sequent
```

---

### Layer 2: Sequent Calculus Core

**Purpose:** Implement the inference rules of LK (classical first-order sequent calculus) and manage proof state.

#### Sequent

```
Sequent = { hyps: [Formula], goals: [Formula] }
-- represents: hyps[0], hyps[1], ... ⊢ goals[0], goals[1], ...
```

#### Inference Rules (LK-style)

Each connective has a **Left rule** (when it appears in hypotheses) and a **Right rule** (when it appears in goals):

| Connective | Right Rule (in goal) | Left Rule (in hypothesis) |
|---|---|---|
| `∧` | Split into two subgoals | Choose which conjunct to keep |
| `∨` | Choose which disjunct to prove | Split into two subgoals |
| `→` | Move antecedent to hyps, prove consequent | Requires proving antecedent, adds consequent |
| `¬` | Move formula to other side | Move formula to other side |
| `∀` | Introduce fresh variable / eigenvariable | Instantiate with a term (user provides or inferred) |
| `∃` | Instantiate with a witness term | Introduce fresh variable |
| `⊤` | Axiom (immediate) | Drop hypothesis |
| `⊥` | Cannot prove (stuck) | Axiom (immediate) |

#### Identity / Axiom detection

When a formula appears on **both** sides of the turnstile, the goal is closed (Axiom rule). Clicking an atomic formula triggers a search for a matching formula on the opposite side.

#### Proof Tree

```
ProofTree ::= Open(Sequent)                        -- unsolved goal
            | Closed(rule, Sequent, [ProofTree...]) -- rule applied, children
```

#### Proof State

```
ProofState = {
    tree:       ProofTree,
    focus:      Path-to-Open-node,    -- which open goal is active
    history:    [ProofState],         -- for undo
}
```

---

### Layer 3: Pointing Engine

**Purpose:** The core innovation — translate a user's click into a proof step.

#### Algorithm (following Bertot et al.)

```
point(sequent, click_target) → RuleApplication | Ambiguity | Error

1. Resolve click_target = (side, address) to a subformula F
2. Determine the principal connective of F
3. Based on (side, connective), select the inference rule:
     - side=Goal  + connective=And  → Right-And
     - side=Hyp   + connective=And  → Right-And requires disambiguation (L or R?)
     - side=Goal  + connective=Or   → disambiguation (L or R?)
     - side=Hyp   + connective=Or   → Left-Or
     - ... etc for all connectives
4. If the rule needs parameters (e.g., ∀-Left needs a term):
     - Return Ambiguity/NeedsInput with a description of what's needed
5. If the address is deeper than the outermost connective:
     - Decompose the formula top-down along the address path,
       applying structural rules as needed to "reach" the target
     - This is the key insight: pointing deep into a formula
       triggers a SEQUENCE of rule applications automatically
6. Return the RuleApplication (or sequence of applications)
```

#### Deep Pointing

This is what makes the system powerful. If the user clicks on `B` inside `(A ∧ B) → C` on the goal side:

1. Address is `[Left, Right]`
2. The engine first applies `→-Right` (outermost connective), producing `A ∧ B ⊢ C`
3. Then applies `∧-Left` on `A ∧ B` in the hypotheses (navigating further)
4. Then the focus lands on `B`

One click triggers a chain of decompositions.

#### Ambiguity Resolution

Some clicks are inherently ambiguous:
- **∨-Right**: which disjunct? → Ask user or infer from click sub-address
- **∀-Left**: which instantiation term? → Open a term input dialog
- **Atomic on one side**: search for matching formula on opposite side

The pointing engine returns an `Ambiguity` value and the UI layer presents choices.

---

### Layer 4: UI Layer

**Purpose:** Render sequents as interactive, clickable regions and display the proof tree.

#### Sequent Rendering

Each formula is rendered as a tree of **nested clickable spans**, where every subformula and connective is individually addressable:

```
<span data-side="goal" data-addr="[]">
  <span data-addr="[L]">
    <span data-addr="[L,L]">A</span>
    <span class="connective" data-addr="[L]">∧</span>
    <span data-addr="[L,R]">B</span>
  </span>
  <span class="connective" data-addr="[]">→</span>
  <span data-addr="[R]">C</span>
</span>
```

Clicking any span fires `point(current_sequent, (side, address))`.

#### Proof Tree Display

A visual tree showing:
- **Closed nodes**: grayed out, showing the rule name
- **Open nodes**: highlighted, showing the sequent to prove
- **Active node**: the currently focused open goal

#### Interaction Modes

| Action | Effect |
|---|---|
| Click connective in goal | Apply right-rule |
| Click connective in hypothesis | Apply left-rule |
| Click atomic formula | Attempt axiom closure |
| Click quantified variable | Open term input for instantiation |
| Undo button / Ctrl+Z | Revert last step |
| Click open node in proof tree | Switch focus to that subgoal |

#### Drag-and-Drop Extension (future)

Following later work inspired by Bertot et al., allow **dragging** one subformula onto another to trigger rewrites or cuts — e.g., drag a hypothesis onto a matching goal subformula to close it.

---

### Module Dependency Graph

```
                    ┌──────────┐
                    │    UI    │
                    └────┬─────┘
                         │ click events
                    ┌────▼─────────────┐
                    │  Pointing Engine  │
                    └────┬─────────────┘
                         │ rule applications
              ┌──────────▼──────────┐
              │  Sequent Calculus   │
              │  Core               │
              └──────────┬──────────┘
                         │ formula manipulation
              ┌──────────▼──────────┐
              │  FOL Representation │
              │  (AST, Addresses,   │
              │   Parser, Printer)  │
              └─────────────────────┘
```

---

### Key Design Decisions

1. **Classical LK, not intuitionistic LJ.** LK allows multiple formulas on the right side of the sequent, which is more symmetric and maps more naturally to pointing (every connective has clean left/right rule pairs). Can restrict to LJ later if desired.

2. **Addresses as first-class values.** The address scheme is the bridge between the visual layout and the logical structure. Making addresses explicit and composable is what enables deep pointing.

3. **Rule chains, not just single steps.** The pointing engine can return a *sequence* of rule applications for deep clicks, making the system feel responsive — one click can do significant work.

4. **Separation of pointing logic from UI.** The pointing engine is a pure function `(Sequent, ClickTarget) → [RuleApplication]`. This makes it testable independently of any rendering framework and portable across UIs (web, terminal, editor plugin).

5. **Explicit proof terms (optional extension).** Each rule application can emit a proof term (à la Curry-Howard), building a lambda-term alongside the proof tree. This enables proof export and verification.

---

### Suggested File Structure

```
leap/
├── core/
│   ├── ast.py          -- Formula, Term, Address types
│   ├── parser.py       -- Text → AST
│   ├── printer.py      -- AST → text / unicode / LaTeX
│   ├── sequent.py      -- Sequent type, manipulation
│   ├── rules.py        -- LK inference rules
│   ├── proof.py        -- ProofTree, ProofState, undo
│   └── unify.py        -- First-order unification for ∀/∃
├── engine/
│   ├── pointer.py      -- The pointing algorithm
│   ├── decompose.py    -- Deep pointing / rule chain generation
│   └── disambiguate.py -- Ambiguity resolution strategies
├── ui/
│   ├── app.py          -- Main application entry
│   ├── sequent_view.py -- Interactive sequent rendering
│   ├── tree_view.py    -- Proof tree visualization
│   └── term_input.py   -- Dialog for term instantiation
└── tests/
    ├── test_ast.py
    ├── test_rules.py
    ├── test_pointer.py
    └── test_integration.py
```

---

### Example Walkthrough

**Goal:** Prove `⊢ (P → Q) → (Q → R) → (P → R)` (transitivity of implication)

1. **Initial sequent:** `⊢ (P → Q) → (Q → R) → (P → R)`
2. **User clicks `→` (outermost).** Engine applies →-Right. New sequent: `P → Q ⊢ (Q → R) → (P → R)`
3. **User clicks `→` (now outermost on right).** Engine applies →-Right. New: `P → Q, Q → R ⊢ P → R`
4. **User clicks `→` on `P → R` in goal.** Engine applies →-Right. New: `P → Q, Q → R, P ⊢ R`
5. **User clicks `P → Q` in hypotheses.** Engine applies →-Left, generating two subgoals:
   - Subgoal 1: `Q → R, P ⊢ P` — closed by axiom (P on both sides)
   - Subgoal 2: `Q, Q → R, P ⊢ R`
6. **User clicks `Q → R` in hypotheses.** Engine applies →-Left:
   - Subgoal 2a: `Q, P ⊢ Q` — closed by axiom
   - Subgoal 2b: `R, Q, P ⊢ R` — closed by axiom
7. **Proof complete.** All leaves are closed.

Each step was a single click. No tactics language. No memorized rule names.

---

### Technology Recommendations

- **Language:** Python (rapid prototyping, pattern matching on AST via dataclasses/match) or TypeScript (if targeting web-first)
- **UI:** Web-based (React/Svelte) with nested `<span>` elements for clickable subformulas, or a terminal TUI with `rich`/`textual` for a lighter prototype
- **Testing:** Property-based testing (Hypothesis for Python) to verify rule soundness — e.g., any rule application on a valid sequent produces valid subgoals

Would you like me to proceed with implementing any of these layers?

Sources:
- [Proof by Pointing (Bertot, Kahn & Théry, 1994) — Springer](https://link.springer.com/chapter/10.1007/3-540-57887-0_94)
- [Proof by Pointing — Semantic Scholar](https://www.semanticscholar.org/paper/Proof-by-Pointing-Bertot-Kahn/7bdbcd42b8e96802cc4bf26d044272330f7343d4)
- [Logitext — Interactive Sequent Calculus Tutorial (MIT)](http://logitext.mit.edu/tutorial)
- [Sequent Calculus — CMU](https://www.cs.cmu.edu/~fp/courses/atp/handouts/ch3-seqcalc.pdf)
