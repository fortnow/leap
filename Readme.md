## **LEAP — Logic Engine for Argument by Pointing**

### **What's implemented**

**Layer 1: FOL Representation** (`leap/core/ast.py`, `parser.py`, `printer.py`)

* Frozen dataclass AST for terms (Var, Func) and formulas (Pred, Not, And, Or, Implies, Forall, Exists, Top, Bottom)  
* Subformula addressing via Direction/Address tuples  
* Parser supporting both ASCII (`->`, `&`, `|`, `~`) and Unicode (`→`, `∧`, `∨`, `¬`) syntax  
* HTML renderer producing nested `<span>` elements with `data-side`, `data-index`, `data-addr` attributes for click targeting

**Layer 2: Sequent Calculus Core** (`sequent.py`, `rules.py`, `proof.py`, `unify.py`)

* Full classical LK sequent calculus with all connective rules (left \+ right)  
* First-order unification and substitution with occurs check  
* Proof tree with open/closed nodes, automatic axiom closure  
* ProofState with undo via deep-copy snapshots

**Layer 3: Pointing Engine** (`pointer.py`, `decompose.py`, `disambiguate.py`)

* Maps `(Side, index, Address)` → rule application  
* Returns `Ambiguity` when multiple rules apply (e.g., ∨ on goal side)  
* Returns `NeedsInput` when a term is required (∀-Left, ∃-Right)  
* Deep clicks auto-apply the outermost connective's rule

**Layer 4: Web UI** (`app.py`, `templates/index.html`, `static/style.css`, `static/main.js`)

* Flask API endpoints: `/api/start`, `/api/click`, `/api/undo`, `/api/focus`, `/api/state`, `/api/examples`  
* Interactive clickable sequent display with color-coded hypotheses (green) and goals (blue)  
* Disambiguation dialog and term input dialog  
* Proof tree visualization, goal list with focus switching  
* QED victory screen on completion

### **How to run**

Render: https://leap-y2r7.onrender.com

For local machine:
pip install flask pytest  
python run.py          \# starts web UI on http://localhost:5000  
python \-m pytest tests/ \-v   \# runs 78 tests

Quick guide:

* Pick an example theorem or type your own formula  
* **Click connectives** (→, ∧, ∨, ¬) to apply the corresponding rule  
* **Green** formulas are hypotheses (left of ⊢), **blue** are goals (right)  
* For ∨ on the goal side, you'll be asked to choose left or right disjunct  
* For ∀/∃, you'll be prompted for a term  
* **Undo** button reverts the last step  
* Click open goals in the goal list to switch focus

