# Settle Up API

![CI/CD](https://github.com/Varshan1144/settle-up-api/actions/workflows/ci.yml/badge.svg)

A REST API that tracks shared group expenses (trips, roommates, dinners) and works out the
**fewest payments** needed to settle everyone up. It is packaged with **Docker** and tested and
shipped automatically by a **GitHub Actions CI/CD pipeline**.

Built for the CSE 485 *Growing a Competency* assignment (CI/CD Pipelines with GitHub Actions & Docker).

---

## Example

Three friends go on a trip. Varshan pays $90 for the hotel and Anirudh pays $30 for gas.
The total is $120, so each person's share is $40.

| Member  | Paid | Share | Net  |
|---------|------|-------|------|
| Varshan | $90  | $40   | +$50 (is owed) |
| Anirudh | $30  | $40   | -$10 (owes)    |
| Sai     | $0   | $40   | -$40 (owes)    |

`GET /groups/trip/settle` returns the minimal set of payments:

```json
[
  {"from_member": "Sai",     "to_member": "Varshan", "amount": 40.0},
  {"from_member": "Anirudh", "to_member": "Varshan", "amount": 10.0}
]
```

## How it works

- **Exact money math:** amounts are stored in integer cents, so uneven splits (like $10 among
  three people) never lose or create a cent.
- **Minimal settlement:** a greedy algorithm repeatedly pairs the person who owes the most with
  the person owed the most, so a group of *n* people settles in at most *n - 1* payments.
- **Partial splits:** an expense can be split among everyone or only a chosen subset.

## Endpoints

| Method | Endpoint                   | Description                                           |
|--------|----------------------------|-------------------------------------------------------|
| GET    | `/health`                  | Health check (used by Docker and the pipeline)        |
| POST   | `/groups`                  | Create a group with its members                       |
| POST   | `/groups/{name}/expenses`  | Add an expense (who paid, amount, who it's split among) |
| GET    | `/groups/{name}/balances`  | Net balance per member                                |
| GET    | `/groups/{name}/settle`    | Fewest payments to settle the group                   |
| GET    | `/groups/{name}/summary`   | Per-member totals: paid, fair share, and net          |

Interactive docs are available at `http://localhost:8000/docs` once the app is running.

## CI/CD pipeline

Defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml). It runs on every push and pull request:

```
push / pull request
        │
        ▼
┌────────────────────┐      ┌──────────────────────────────────────┐
│ test               │      │ build-and-push  (only if tests pass) │
│  • ruff lint       │ ───▶ │  • docker build                      │
│  • 8 pytest tests  │      │  • run container, check /health      │
└────────────────────┘      │  • push image to GitHub Container    │
                            │    Registry (main branch only)       │
                            └──────────────────────────────────────┘
```

If any test fails, the image is never built or published. See the
[Actions tab](https://github.com/Varshan1144/settle-up-api/actions) for run history.

## Docker

The [`Dockerfile`](Dockerfile) uses:
- a **multi-stage build** (dependencies installed in a builder stage, copied into a slim runtime image)
- a **non-root user** for security
- a **HEALTHCHECK** that calls `/health`

## Run it locally

With Docker:
```bash
docker build -t settle-up-api .
docker run -p 8000:8000 settle-up-api
# open http://localhost:8000/docs
```

Run the tests:
```bash
pip install -r requirements-dev.txt
pytest -v
```

## Project structure

```
settle-up-api/
├── app/main.py               # API endpoints and settlement logic
├── tests/test_api.py         # unit tests
├── Dockerfile                # multi-stage container build
├── .github/workflows/ci.yml  # CI/CD pipeline
├── requirements.txt          # runtime dependencies
└── requirements-dev.txt      # test and lint dependencies
```

## Tech stack

Python 3.12 · FastAPI · pytest · ruff · Docker · GitHub Actions · GitHub Container Registry
