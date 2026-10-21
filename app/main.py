"""Settle Up API - track shared group expenses and compute the fewest payments to settle.

Each group holds members and expenses. An expense is paid by one member and split
equally among a chosen subset. /settle computes everyone's net balance and returns
a minimal list of transfers (greedy: largest debtor pays largest creditor).
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Settle Up API", version="1.0.0")


class GroupIn(BaseModel):
    name: str = Field(min_length=1)
    members: list[str] = Field(min_length=2)


class ExpenseIn(BaseModel):
    description: str
    paid_by: str
    amount: float = Field(gt=0)
    split_among: list[str] | None = None  # defaults to everyone


class Transfer(BaseModel):
    from_member: str
    to_member: str
    amount: float


# In-memory store keyed by group name.
GROUPS: dict[str, dict] = {}


def compute_balances(members: list[str], expenses: list[dict]) -> dict[str, int]:
    """Net balance per member in cents (positive = is owed money)."""
    bal = {m: 0 for m in members}
    for e in expenses:
        cents = round(e["amount"] * 100)
        people = e["split_among"]
        share, remainder = divmod(cents, len(people))
        bal[e["paid_by"]] += cents
        for i, p in enumerate(people):
            # spread leftover cents over the first few people so totals stay exact
            bal[p] -= share + (1 if i < remainder else 0)
    return bal


def minimize_transfers(balances: dict[str, int]) -> list[Transfer]:
    """Greedy settlement: repeatedly match the largest debtor with the largest creditor."""
    creditors = sorted(((v, k) for k, v in balances.items() if v > 0), reverse=True)
    debtors = sorted(((-v, k) for k, v in balances.items() if v < 0), reverse=True)
    transfers = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        owe, d = debtors[i]
        due, c = creditors[j]
        pay = min(owe, due)
        transfers.append(Transfer(from_member=d, to_member=c, amount=pay / 100))
        debtors[i] = (owe - pay, d)
        creditors[j] = (due - pay, c)
        if debtors[i][0] == 0:
            i += 1
        if creditors[j][0] == 0:
            j += 1
    return transfers


def get_group(name: str) -> dict:
    if name not in GROUPS:
        raise HTTPException(404, f"group '{name}' not found")
    return GROUPS[name]


@app.get("/health")
def health():
    return {"status": "ok", "groups": len(GROUPS)}


@app.post("/groups", status_code=201)
def create_group(group: GroupIn):
    if group.name in GROUPS:
        raise HTTPException(409, "group already exists")
    if len(set(group.members)) != len(group.members):
        raise HTTPException(422, "duplicate member names")
    GROUPS[group.name] = {"members": group.members, "expenses": []}
    return {"name": group.name, "members": group.members}


@app.post("/groups/{name}/expenses", status_code=201)
def add_expense(name: str, expense: ExpenseIn):
    g = get_group(name)
    people = expense.split_among or g["members"]
    unknown = {expense.paid_by, *people} - set(g["members"])
    if unknown:
        raise HTTPException(422, f"not in group: {sorted(unknown)}")
    record = {**expense.model_dump(), "split_among": people}
    g["expenses"].append(record)
    return record


@app.get("/groups/{name}/balances")
def balances(name: str):
    g = get_group(name)
    return {m: c / 100 for m, c in compute_balances(g["members"], g["expenses"]).items()}


@app.get("/groups/{name}/settle", response_model=list[Transfer])
def settle(name: str):
    g = get_group(name)
    return minimize_transfers(compute_balances(g["members"], g["expenses"]))


@app.get("/groups/{name}/summary")
def summary(name: str):
    """Per-member totals: how much each person paid, their fair share, and net balance."""
    g = get_group(name)
    paid = {m: 0 for m in g["members"]}
    for e in g["expenses"]:
        paid[e["paid_by"]] += round(e["amount"] * 100)
    net = compute_balances(g["members"], g["expenses"])
    total = sum(paid.values())
    return {
        "total_spent": total / 100,
        "members": [
            {"member": m, "paid": paid[m] / 100, "share": (paid[m] - net[m]) / 100, "net": net[m] / 100}
            for m in g["members"]
        ],
    }
