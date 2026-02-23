"""Integration tests: drive the full proof-by-pointing flow via the Flask API."""

import json
import pytest
from leap.ui.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestAPI:
    def test_index(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_examples(self, client):
        resp = client.get("/api/examples")
        data = resp.get_json()
        assert "examples" in data
        assert len(data["examples"]) > 0

    def test_start_proof(self, client):
        resp = client.post("/api/start",
                           json={"formula": "P -> P"})
        data = resp.get_json()
        assert "proof" in data
        assert "focus_html" in data
        assert data["is_complete"] is False

    def test_start_invalid(self, client):
        resp = client.post("/api/start",
                           json={"formula": "P ->-> Q"})
        assert resp.status_code == 400

    def test_click_without_proof(self, client):
        resp = client.post("/api/click",
                           json={"side": "goal", "index": 0, "address": ""})
        assert resp.status_code == 400

    def test_prove_p_implies_p(self, client):
        """Full proof of P → P through the API."""
        # Start
        resp = client.post("/api/start", json={"formula": "P -> P"})
        data = resp.get_json()
        assert data["is_complete"] is False

        # Click → on goal to apply →-Right
        resp = client.post("/api/click",
                           json={"side": "goal", "index": 0, "address": ""})
        data = resp.get_json()
        # P → P becomes P ⊢ P which auto-closes
        assert data["is_complete"] is True
        assert data["action"] == "applied"

    def test_prove_conjunction_commutativity(self, client):
        """Full proof of P ∧ Q → Q ∧ P."""
        # Start
        resp = client.post("/api/start", json={"formula": "P & Q -> Q & P"})
        data = resp.get_json()
        assert not data["is_complete"]

        # Step 1: Click → on goal
        resp = client.post("/api/click",
                           json={"side": "goal", "index": 0, "address": ""})
        data = resp.get_json()
        assert data["action"] == "applied"
        # Now: P ∧ Q ⊢ Q ∧ P

        # Step 2: Click ∧ on hypothesis
        resp = client.post("/api/click",
                           json={"side": "hyp", "index": 0, "address": ""})
        data = resp.get_json()
        assert data["action"] == "applied"
        # Now: P, Q ⊢ Q ∧ P

        # Step 3: Click ∧ on goal
        resp = client.post("/api/click",
                           json={"side": "goal", "index": 0, "address": ""})
        data = resp.get_json()
        assert data["action"] == "applied"
        # Should auto-close: P, Q ⊢ Q  and  P, Q ⊢ P
        assert data["is_complete"] is True

    def test_or_disambiguation(self, client):
        """Test that ∨ on goal side triggers disambiguation."""
        resp = client.post("/api/start", json={"formula": "P -> P | Q"})
        data = resp.get_json()

        # Click → first
        resp = client.post("/api/click",
                           json={"side": "goal", "index": 0, "address": ""})
        data = resp.get_json()
        # Now: P ⊢ P ∨ Q

        # Click ∨ on goal — should get ambiguity
        resp = client.post("/api/click",
                           json={"side": "goal", "index": 0, "address": ""})
        data = resp.get_json()
        assert data["action"] == "ambiguity"
        assert len(data["choices"]) == 2

        # Resolve: choose left disjunct (P)
        resp = client.post("/api/click",
                           json={"side": "goal", "index": 0, "address": "",
                                  "choice": "OR_RIGHT_L"})
        data = resp.get_json()
        assert data["action"] == "applied"
        assert data["is_complete"] is True

    def test_undo(self, client):
        """Test undo functionality."""
        resp = client.post("/api/start",
                           json={"formula": "(P -> Q) -> (Q -> R) -> (P -> R)"})
        data = resp.get_json()

        # Apply one step
        resp = client.post("/api/click",
                           json={"side": "goal", "index": 0, "address": ""})
        data = resp.get_json()
        assert data["proof"]["can_undo"] is True

        # Undo
        resp = client.post("/api/undo")
        data = resp.get_json()
        assert data["action"] == "undone"

    def test_sequent_input(self, client):
        """Test starting with a sequent instead of a formula."""
        resp = client.post("/api/start",
                           json={"sequent": "P, P -> Q |- Q"})
        data = resp.get_json()
        assert not data["is_complete"]
        assert "proof" in data

    def test_bottom_proves_anything(self, client):
        """⊥ → P should be provable."""
        resp = client.post("/api/start", json={"formula": "F -> P"})
        data = resp.get_json()

        # Click → on goal
        resp = client.post("/api/click",
                           json={"side": "goal", "index": 0, "address": ""})
        data = resp.get_json()
        # Now: ⊥ ⊢ P — should auto-close due to ⊥ in hyps
        assert data["is_complete"] is True
