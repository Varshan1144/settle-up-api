# Settle Up API

Track shared group expenses (trips, roommates, dinners) and compute the **fewest payments**
needed to settle everyone up. Built while learning **CI/CD with GitHub Actions & Docker**.

- Expenses split equally among all members or a chosen subset
- Money handled in integer cents so uneven splits stay exact
- Greedy settlement: largest debtor pays largest creditor (at most n-1 transfers)

## Run with Docker
```bash
docker build -t settle-up-api .
docker run -p 8000:8000 settle-up-api
# open http://localhost:8000/docs
```

## Run tests
```bash
pip install -r requirements-dev.txt
pytest -v
```

## Pipeline (`.github/workflows/ci.yml`)
1. **test**: ruff lint + pytest on every push and pull request
2. **build-and-push** (only if tests pass): build the image, smoke-test `/health` in the
   running container, then push to GitHub Container Registry on `main`
