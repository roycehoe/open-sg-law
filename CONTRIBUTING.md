# Contributing

Open an issue before you write code. A pull request that nobody discussed first may not be reviewed.

## Reporting an error in the record

A wrong or missing piece of legislation or a judgment is a data error. Open an issue at [github.com/roycehoe/open-sg-law/issues](https://github.com/roycehoe/open-sg-law/issues) and name the Act, section or citation involved. For an error in a Hansard debate link, say which Act and which debate.

## Proposing a change

1. Open an issue that says what you want to change and why. Name the source, script or module involved.
2. Wait for Royce Hoe to reply. He decides whether the change fits the project.
3. Fork the repository, make the change, and open a pull request that links the issue.

Keep each pull request to one change. Subjects follow Conventional Commits, such as `fix: read a bold section number set in an Adobe font`, under 72 characters.

## Checks

CI runs `poetry run ruff check .`, `poetry run ruff format --check .`, `poetry run basedpyright` and `poetry run pytest` on every pull request. The tests need a separate PostgreSQL database named `open_sg_law_test` on port 5436. `docker-compose up -d` starts one beside the local `open_sg_law` database. `tests/conftest.py` refuses any other database, and no test reaches the network.

- Code follows [STYLE.md](STYLE.md). Read it before you write any.
- A parser fix adds a golden fixture in `tests/` for the defect it closes. A fixture is a real, trimmed body from a source, and `tests/fixtures/SOURCES.md` names where each one came from.
- A change that cleans data adds or updates a row in [docs/data-loss-register.md](docs/data-loss-register.md) in the same change.
- A change never sends a request to a source from a test.

## Changes to stored data

A merged pull request never changes a stored row. A write script is a dry run unless it gets `--commit`, and it refuses a local database off port 5436. The database is not published, so you cannot run a write against it. If your change needs one, say so in the issue. The script can come with the pull request. Only Royce can run it.

SSO allows automated requests only from 03:00 to 07:00 Singapore time. Do not add a script or a change that sends requests to a source outside the rules in [the README](README.md#data-source-and-terms).
