from fastapi.testclient import TestClient

from app.main import GROUPS, app, compute_balances, minimize_transfers

client = TestClient(app)


def setup_function():
    GROUPS.clear()


def make_trip():
    client.post("/groups", json={"name": "trip", "members": ["A", "B", "C"]})


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_balances_sum_to_zero_with_uneven_cents():
    # $10.00 split 3 ways leaves a leftover cent; totals must still be exact
    bal = compute_balances(["A", "B", "C"], [
        {"paid_by": "A", "amount": 10.00, "split_among": ["A", "B", "C"]},
    ])
    assert sum(bal.values()) == 0


def test_settle_end_to_end():
    make_trip()
    client.post("/groups/trip/expenses", json={"description": "hotel", "paid_by": "A", "amount": 90})
    client.post("/groups/trip/expenses", json={"description": "gas", "paid_by": "B", "amount": 30})
    # A paid 90, owes 40 -> +50; B paid 30, owes 40 -> -10; C owes 40 -> -40
    assert client.get("/groups/trip/balances").json() == {"A": 50.0, "B": -10.0, "C": -40.0}
    transfers = client.get("/groups/trip/settle").json()
    assert len(transfers) == 2
    assert all(t["to_member"] == "A" for t in transfers)
    assert sum(t["amount"] for t in transfers) == 50.0


def test_partial_split():
    make_trip()
    client.post("/groups/trip/expenses", json={
        "description": "dinner", "paid_by": "C", "amount": 20, "split_among": ["B", "C"],
    })
    assert client.get("/groups/trip/settle").json() == [
        {"from_member": "B", "to_member": "C", "amount": 10.0}
    ]


def test_settlement_uses_at_most_n_minus_1_transfers():
    bal = {"A": 3000, "B": -1000, "C": -1000, "D": -1000}
    assert len(minimize_transfers(bal)) <= 3


def test_unknown_member_rejected():
    make_trip()
    r = client.post("/groups/trip/expenses", json={"description": "x", "paid_by": "Z", "amount": 5})
    assert r.status_code == 422


def test_missing_group_404():
    assert client.get("/groups/nope/settle").status_code == 404


def test_summary_totals():
    make_trip()
    client.post("/groups/trip/expenses", json={"description": "hotel", "paid_by": "A", "amount": 90})
    client.post("/groups/trip/expenses", json={"description": "gas", "paid_by": "B", "amount": 30})
    s = client.get("/groups/trip/summary").json()
    assert s["total_spent"] == 120.0
    a = next(m for m in s["members"] if m["member"] == "A")
    assert a == {"member": "A", "paid": 90.0, "share": 40.0, "net": 50.0}
