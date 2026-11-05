# open-sg-law

A free, non-commercial, open-source platform that puts Singapore legislation and court judgments in one place, in plain language a non-lawyer can use, with lawyers as the main audience. It holds Acts and subsidiary legislation and judgments from eLitigation. Each Act links to the Hansard debates on its bills through [openhansard.sg](https://openhansard.sg).

This repository is the scraper and the database. A separate site repository follows, as [roycehoe/hansard](https://github.com/roycehoe/hansard) sits beside [roycehoe/hansard-scraper](https://github.com/roycehoe/hansard-scraper). Its layout follows hansard-scraper's.

## Status

Version 1 is in progress, and nothing is published yet. It ships in three stages:

- Release A: legislation and the Act-to-debate links.
- Release B: judgments added, once the Supreme Court agrees in writing.
- Release C: point-in-time versions of legislation added, once AGC grants bulk access to Singapore Statutes Online (SSO).

Letters to the Supreme Court, AGC and the SMU SOLID project ask for those permissions. This project asks first, unlike the Hansard project ([ADR 0001](docs/adr/0001-ask-before-publishing.md)).

## Getting the data

The database is not published. Each source has its own terms, and a table is opened to the site only once its sources are cleared ([ADR 0005](docs/adr/0005-publish-gate-by-database-role.md)). You can build your own copy with the steps under [Setup](#setup) once the harvest scripts land.

## What the record holds

| Source | Fetched | Published |
|---|---|---|
| SSO | Yes, 03:00 to 07:00 SGT, at one request a minute | Yes, under clause 13 |
| eGazette | Yes | Yes, under clause 11 |
| data.gov.sg eGazette indexes | Yes | Yes, under the Open Data Licence |
| Internet Archive copies of SSO | Yes, about 10 a minute | Probably, under clause 13 |
| eLitigation judgments (Supreme Court, State Courts, Family Justice Courts) | Yes | After the Supreme Court's written yes |
| Act-to-debate links | Copied from the bill-debate-linking job in hansard-scraper | Links only, no Hansard text |

Every source not in version 1 is listed in [docs/backlog.md](docs/backlog.md), with its fetch and publish status.

## Known limits

- No Singapore Law Reports (SLR) content. There are no headnotes, SLR citations or SLR page numbers. A lawyer who must cite a reported case still opens LawNet.
- eLitigation holds few judgments from before 2000. The missing cases exist only in reported series this project does not copy.
- Section links into SSO are built from the printed section number as `#pr<number>-`. This is a guess at SSO's anchors, and a wrong one opens the top of the SSO page ([ADR 0004](docs/adr/0004-pdf-as-legislation-text-source.md)).
- Until Release C, there are no point-in-time versions. A page shows the current consolidated text and links to SSO's history.
- Consolidated text from SSO is an unofficial version. The Gazette is the authoritative text.

## Repository layout

| Folder | What it holds |
|---|---|
| `gateway/` | HTTP calls to the sources |
| `schemas/` | Pydantic models of the answers and of hand-kept files |
| `services/` | Pure transforms, such as a PDF's lines into sections |
| `database/` | Table definitions |
| `crud/` | Database reads and writes |
| `populate/` | Pipeline stages, which join the folders above |
| `utils/` | Shared pure functions |
| `alembic/` | Database migrations |
| `scripts/` | Harvest scripts and supervised one-off writes |
| `docs/` | Decision records, the data-loss register, the vision and the backlog |
| `tests/` | Golden fixtures and stage tests |

Folders appear as the build reaches them.

## Tables

| Table | One row per |
|---|---|
| `source` | source, with its publish status and, for SSO, its access state |
| `harvest_run` | harvest run, with its counts and status |
| `source_response` | fetched body, stored as received |
| `legislation` | Act a stored listing page shows |
| `legislation_version` | stored Act PDF read as a version |
| `legislation_section` | section, Article or schedule of a version |
| `legislation_alias` | name an Act is looked up by |
| `bill` | bill found in the Hansard debates |
| `bill_report` | Hansard report of a bill's debate |
| `act_history_entry` | entry of an Act's Legislative History, with its bill |

The site reads only the tables whose sources are all published, never `source_response` or `harvest_run`. [CLAUDE.md](CLAUDE.md#database-models) says what each column holds.

## Scripts

Each runs as `python -m scripts.<name>`, and each one that writes is a dry run unless `--commit`.

| Script | What it does |
|---|---|
| `clear_sso_challenge` | sets a challenged SSO source back to untested |
| `publish_source` | publishes or withdraws a source and changes the site role's grants to match |
| `harvest_sso` | fetches one night's SSO listing pages and Act PDFs |
| `harvest_archive` | fetches the Internet Archive's copies of the Act PDFs and listings |
| `apply_legislation` | stores the Acts the listing pages show |
| `apply_hansard_links` | stores the bills, their Hansard reports and the links from each Act's history |
| `apply_legislation_versions` | stores a version for each Act PDF |
| `apply_legislation_sections` | splits each version into sections |
| `apply_legislation_aliases` | stores the names each Act is looked up by |
| `coverage_figures` | logs the coverage figures, and writes nothing to the database |

The harvests and the judgments wait on the permissions above, so no script has run against the sources yet. [CLAUDE.md](CLAUDE.md#scripts-directory) says what each script reads and writes.

## Setup

Requires Python 3.11+, [Poetry](https://python-poetry.org) and Docker.

```bash
git clone https://github.com/roycehoe/open-sg-law.git
cd open-sg-law
poetry install
docker-compose up -d    # local PostgreSQL on port 5436
python -m alembic upgrade head
```

`docker-compose up -d` serves PostgreSQL on port 5436, with the local database `open_sg_law` and the scratch database `open_sg_law_test`. `python -m alembic upgrade head` targets the local `open_sg_law` database only. The default `DATABASE_URL` is `postgresql://user:password@localhost:5436/open_sg_law`, and a write script refuses a local database off port 5436.

`poetry run ruff check .` lints the code and `poetry run ruff format --check .` checks its formatting. `poetry run basedpyright` type-checks it, and any diagnostic fails. `poetry run pytest` runs the tests against `open_sg_law_test` on port 5436, and `tests/conftest.py` refuses any other database. No test reaches the network.

## Documentation

- [Vision](docs/vision.md): the project's goals and how progress is measured.
- [Data-loss register](docs/data-loss-register.md): every step that drops or changes source text.
- [Backlog](docs/backlog.md): the sources left out of version 1.
- [Decision records](docs/adr/): why the project works the way it does.
- [STYLE.md](STYLE.md): the coding rules every change follows.

## Data source and terms

The text comes from Singapore Statutes Online (SSO), the Internet Archive's copies of SSO, eGazette and eLitigation. The Government of Singapore owns the legislation. This project is not affiliated with or endorsed by AGC, SSO, eGazette or the Judiciary.

SSO's terms of use, clause 13, say: "AGC has granted permission to the users of SSO to use/reproduce any Singapore legislation for the purposes of any print or electronic material or platform". The conditions are that the material says the legislation is subject to the copyright of the Singapore Government and is reproduced with the permission of AGC, that it tells users they may check SSO for the latest version, that the producer answers for accuracy, that nothing suggests AGC endorses the platform, and that automated extraction runs only from 3 a.m. to 7 a.m. Singapore time and is not abusive, intrusive or deceptive. AGC can revoke or change the permission at any time.

eGazette's terms of use, clause 11, give permission "to reproduce any e-Gazettes in any print or electronic material or platform". The conditions: the material says the Gazettes are Government copyright reproduced with its permission, the producer answers for accuracy, nothing suggests affiliation, and automated extraction is not abusive, deceptive or disruptive.

The Judiciary's terms of use, section 6, bar reproducing its content "for any commercial purposes whatsoever" without written permission. This project is non-commercial and stays so ([ADR 0002](docs/adr/0002-non-commercial-for-good.md)). No judgment is published until the Supreme Court says yes in writing.

Requests to SSO run only inside its window, at the rates the letters promise, with a user agent that names this project and its issues page. Nothing here works around a firewall or uses a headless browser.

## Credit

[kevanwee/sg-legal-corpus](https://github.com/kevanwee/sg-legal-corpus) (MIT) for notes on SSO and eLitigation.

## Contributing

Open an issue before you open a pull request. [CONTRIBUTING.md](CONTRIBUTING.md) says how.

## License

The code is under the [MIT license](LICENSE). The license does not cover the legislation and judgments the pipeline fetches, which belong to their owners.
