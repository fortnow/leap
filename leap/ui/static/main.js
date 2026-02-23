// LEAP — Proof by Pointing frontend

// State tracking for pending disambiguation/input
let pendingClickData = null;

// -----------------------------------------------------------------------
// Startup
// -----------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
    loadExamples();
    document.getElementById("formula-input").addEventListener("keydown", (e) => {
        if (e.key === "Enter") startProof();
    });
});

async function loadExamples() {
    const resp = await fetch("/api/examples");
    const data = await resp.json();
    const container = document.getElementById("example-list");
    data.examples.forEach((ex) => {
        const btn = document.createElement("button");
        btn.className = "example-btn";
        btn.textContent = ex.label;
        btn.onclick = () => {
            document.getElementById("formula-input").value = ex.formula;
            startProof();
        };
        container.appendChild(btn);
    });
}

// -----------------------------------------------------------------------
// Start / Reset
// -----------------------------------------------------------------------

async function startProof() {
    const input = document.getElementById("formula-input").value.trim();
    if (!input) return;

    // Detect if it contains a turnstile
    const isSequent = input.includes("|-") || input.includes("\u22A2");

    const body = isSequent ? { sequent: input } : { formula: input };
    const resp = await fetch("/api/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const data = await resp.json();

    if (data.error) {
        showMessage(data.error, "error");
        return;
    }

    document.getElementById("start-screen").style.display = "none";
    document.getElementById("proof-screen").style.display = "block";
    document.getElementById("victory-overlay").style.display = "none";

    updateUI(data);
}

function resetProof() {
    document.getElementById("start-screen").style.display = "block";
    document.getElementById("proof-screen").style.display = "none";
    document.getElementById("victory-overlay").style.display = "none";
    hideDialogs();
}

// -----------------------------------------------------------------------
// Click handling
// -----------------------------------------------------------------------

function handleFormulaClick(event) {
    // Find the innermost element with data-side
    let el = event.target;
    while (el && !el.dataset.side) {
        el = el.parentElement;
    }
    if (!el || !el.dataset.side) return;

    // Stop event from bubbling to parent formula spans
    event.stopPropagation();

    const side = el.dataset.side;
    const index = parseInt(el.dataset.index, 10);
    const address = el.dataset.addr || "";

    sendClick(side, index, address);
}

async function sendClick(side, index, address, termInput, choice) {
    const body = { side, index, address };
    if (termInput !== undefined) body.term_input = termInput;
    if (choice !== undefined) body.choice = choice;

    // Save for potential reuse in disambiguation
    pendingClickData = { side, index, address };

    const resp = await fetch("/api/click", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const data = await resp.json();

    if (data.error) {
        showMessage(data.error, "error");
        return;
    }

    handleResponse(data);
}

function handleResponse(data) {
    hideDialogs();

    switch (data.action) {
        case "applied":
            showMessage(data.message, "success");
            break;
        case "ambiguity":
            showChoiceDialog(data);
            break;
        case "needs_input":
            showTermDialog(data);
            break;
        case "error":
            showMessage(data.message, "error");
            break;
        case "undone":
            showMessage(data.message, "info");
            break;
        case "focused":
            break;
    }

    updateUI(data);
}

// -----------------------------------------------------------------------
// Disambiguation dialog
// -----------------------------------------------------------------------

function showChoiceDialog(data) {
    const dialog = document.getElementById("choice-dialog");
    const prompt = document.getElementById("choice-prompt");
    const buttons = document.getElementById("choice-buttons");

    prompt.textContent = data.message;
    buttons.innerHTML = "";

    data.choices.forEach((c) => {
        const btn = document.createElement("button");
        btn.className = "choice-btn";
        btn.innerHTML = `<strong>${c.label}</strong><span class="choice-desc">${c.description}</span>`;
        btn.onclick = () => {
            if (pendingClickData) {
                sendClick(
                    pendingClickData.side,
                    pendingClickData.index,
                    pendingClickData.address,
                    undefined,
                    c.rule
                );
            }
        };
        buttons.appendChild(btn);
    });

    dialog.style.display = "block";
}

// -----------------------------------------------------------------------
// Term input dialog
// -----------------------------------------------------------------------

function showTermDialog(data) {
    const dialog = document.getElementById("term-dialog");
    const prompt = document.getElementById("term-prompt");
    const input = document.getElementById("term-input");

    prompt.textContent = data.prompt;
    input.placeholder = data.placeholder || "x";
    input.value = "";
    dialog.style.display = "block";
    input.focus();

    // Handle enter key
    input.onkeydown = (e) => {
        if (e.key === "Enter") submitTerm();
        if (e.key === "Escape") cancelInput();
    };

    // Store the rule for submission
    dialog.dataset.rule = data.rule;
}

function submitTerm() {
    const input = document.getElementById("term-input");
    const term = input.value.trim();
    if (!term) return;

    if (pendingClickData) {
        sendClick(
            pendingClickData.side,
            pendingClickData.index,
            pendingClickData.address,
            term
        );
    }
}

function cancelInput() {
    hideDialogs();
}

function hideDialogs() {
    document.getElementById("choice-dialog").style.display = "none";
    document.getElementById("term-dialog").style.display = "none";
}

// -----------------------------------------------------------------------
// Undo
// -----------------------------------------------------------------------

async function undoStep() {
    const resp = await fetch("/api/undo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
    });
    const data = await resp.json();
    handleResponse(data);
}

// -----------------------------------------------------------------------
// Focus on a specific goal
// -----------------------------------------------------------------------

async function focusGoal(nodeId) {
    const resp = await fetch("/api/focus", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ node_id: nodeId }),
    });
    const data = await resp.json();
    handleResponse(data);
}

// -----------------------------------------------------------------------
// UI updates
// -----------------------------------------------------------------------

function updateUI(data) {
    const proof = data.proof;

    // Update sequent display
    const display = document.getElementById("sequent-display");
    if (data.focus_html) {
        display.innerHTML = data.focus_html;
        // Attach click handlers to all formula elements
        display.querySelectorAll(".formula, .connective").forEach((el) => {
            el.addEventListener("click", handleFormulaClick);
        });
    } else if (data.is_complete) {
        display.innerHTML = '<span style="color: var(--proved-color)">All goals proved!</span>';
    }

    // Update goal counter
    const counter = document.getElementById("goal-counter");
    const openGoals = proof.open_goals;
    counter.textContent = openGoals.length > 0
        ? `(${openGoals.length} remaining)`
        : "(none remaining)";

    // Update undo button
    document.getElementById("undo-btn").disabled = !proof.can_undo;

    // Update status
    const status = document.getElementById("status-text");
    if (data.is_complete) {
        status.textContent = "Proof complete!";
        status.style.color = "var(--proved-color)";
    } else {
        status.textContent = `${openGoals.length} open goal${openGoals.length !== 1 ? "s" : ""}`;
        status.style.color = "var(--text-dim)";
    }

    // Update goals list
    const goalsList = document.getElementById("goals-list-content");
    goalsList.innerHTML = "";
    openGoals.forEach((g, i) => {
        const item = document.createElement("div");
        item.className = "goal-item" + (g.id === proof.focus_id ? " focused" : "");
        item.innerHTML = `<span class="goal-number">${i + 1}.</span><span class="tree-sequent">${escapeHtml(g.sequent)}</span>`;
        item.onclick = () => focusGoal(g.id);
        goalsList.appendChild(item);
    });

    // Update proof tree
    const treeContainer = document.getElementById("proof-tree");
    treeContainer.innerHTML = renderTree(proof.tree, proof.focus_id);

    // Victory check
    if (data.is_complete) {
        setTimeout(() => {
            document.getElementById("victory-overlay").style.display = "flex";
        }, 400);
    }
}

function renderTree(node, focusId) {
    let cls = "tree-label";
    if (node.is_proved) cls += " proved";
    else if (node.is_open) cls += " open";
    if (node.id === focusId && node.is_open) cls += " focused";

    const icon = node.is_proved ? "\u2713" : node.is_open ? "\u25CB" : "\u25CF";
    const rule = node.rule ? `<span class="tree-rule">[${node.rule}]</span>` : "";
    const sequent = `<span class="tree-sequent">${escapeHtml(node.sequent)}</span>`;

    let html = `<div class="tree-node">`;
    html += `<div class="${cls}">${icon} ${sequent} ${rule}</div>`;

    if (node.children && node.children.length > 0) {
        node.children.forEach((child) => {
            html += renderTree(child, focusId);
        });
    }

    html += `</div>`;
    return html;
}

// -----------------------------------------------------------------------
// Messages
// -----------------------------------------------------------------------

function showMessage(text, type) {
    const area = document.getElementById("message-area");
    area.textContent = text;
    area.className = "message-area " + type;
    area.style.display = "block";
    // Auto-hide after a few seconds
    setTimeout(() => {
        area.style.display = "none";
    }, 4000);
}

// -----------------------------------------------------------------------
// Utilities
// -----------------------------------------------------------------------

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
