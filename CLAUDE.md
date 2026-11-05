# CLAUDE.md
@STYLE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Goal and how progress is measured

The goal is in `docs/vision.md`. Its "Measuring progress" section names the figures `scripts/coverage_figures.py` logs. Read it before planning work or reporting results.

- Run `python -m scripts.coverage_figures` before and after any change to parsing and quote its numbers.
- Every write to `legislation_version`, `legislation_section` or the link tables ends with `python -m scripts.coverage_figures --output docs/figures/YYYY-MM-DD-<write>.txt`, and the file is committed.
- The text share alone can rise when the parser drops a version, so quote the versions-not-parsed count beside it.

## Hard rules for agents

- Send no request to any source before the repository is public. Sources are SSO, eLitigation, the Internet Archive, eGazette, data.gov.sg, openhansard.sg, Parliament, LawNet, OpenLaw and PDPC.
- SSO gets automated requests only from 03:00 to 06:55 SGT.
- No write to a local database off port 5436.
- Run heavy jobs one at a time, under `nice -n 10`, with worker pools of 2 or fewer.

## Data loss register

`docs/data-loss-register.md` records everything the pipeline loses between the raw bodies in `source_response` and any derived table. Any change that cleans data adds or updates a row there in the same change, or it is not done. Cleaning means dropping, merging, deduplicating, trimming, normalising, overriding, reclassifying or deleting anything the source holds. The row says what is lost, where in code, why, the cost in counts, whether it can be rebuilt from the raw bodies, and who decided.

Where the source prints something, store what it prints and put our reading in a note column.

## Commands

```bash
# Install dependencies
poetry install

# Start local Postgres on port 5436 (open_sg_law and open_sg_law_test)
docker-compose up -d

# Run linting
ruff check .
ruff check --fix .
ruff format .

# Type check (no baseline: any diagnostic fails)
poetry run basedpyright

# Database migrations (Alembic)
python -m alembic upgrade head          # apply all pending migrations
python -m alembic check                 # verify DB matches models (no pending changes)
python -m alembic revision -m "describe change"  # a new migration, written by hand
python -m alembic downgrade -1          # roll back one migration
```

`poetry run pytest` runs the tests in `tests/`. Tests run only against the scratch database `open_sg_law_test` on port 5436, and `tests/conftest.py` refuses any other target.

## Architecture

### Layer rules

Each folder has a strict responsibility boundary. `populate/` is the only layer that may combine gateway calls, service transforms, and DB writes.

| Layer | Responsibility | Forbidden |
|---|---|---|
| `schemas/` | Pydantic models for external data shapes: API bodies and `data/` files | DB access, logic |
| `gateway/` | HTTP calls; return parsed Pydantic models from `schemas/` | Business logic, DB writes, interpreting a missing field |
| `services/` | Pure transforms: input data → output entity | HTTP calls, DB access |
| `database/` | SQLModel table class definitions | Logic of any kind |
| `crud/` | DB read/write helpers | Business logic, HTTP |
| `populate/` | Pipeline stages: orchestrate gateway + services + crud | None |
| `utils/` | Shared pure functions | DB access, HTTP |
| `scripts/` | One-off diagnostics: use Session + crud + services, and may call gateways | Raw SQL, direct `select()`/`session.add()` bypassing crud |

### Data flow

Filled as each phase lands.

### Database models

Filled as each phase lands.

## `scripts/` directory

Filled as each phase lands.

## Module structure

Filled as each phase lands.
