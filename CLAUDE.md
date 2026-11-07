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

Each stage is a script that runs one populate module, and each stage reads only what an earlier stage stored. No harvest has run yet: no request goes to a source until the permissions in the vision are in hand, so every table but `source` is empty.

1. **Harvest SSO** (`scripts/harvest_sso.py` + `populate/sso_responses.py` + `gateway/sso.py`): reads the SSO row of `source` and refuses to start while SSO is CHALLENGED or outside its window. Inside the 03:00 to 06:55 SGT window it sends the robots file, the Act listing pages and the Act PDFs, one at a time through the SSO pacer, with no retry and no redirect followed. `services/sso_request.py` holds the window check and the PDF paths to fetch, and `services/sso_answer.py` judges each answer; a challenge sets the access state to CHALLENGED and stops the run. `services/harvest_run.py` holds the run guards (one running run per source, consecutive failures, database size). Each body is stored once per requested URL and SHA-256 through `services/source_response.py` and `crud/source_response.py`. Writes `source_response`, `harvest_run` and the access state on `source`.

2. **Harvest the Internet Archive** (`scripts/harvest_archive.py` + `populate/archive_responses.py` + `gateway/internet_archive.py`): fetches the CDX answer for SSO's Act PDFs, then the latest plain capture of each Act (`services/archive_capture.py`) and the captures of the listing pages nearest the run's own time. Waits and retries on a 429. Stores bodies as stage 1 does. Writes `source_response` and `harvest_run`.

3. **Build legislation rows** (`scripts/apply_legislation.py` + `populate/legislation.py` + `services/legislation.py`): reads the stored listing pages of both sources from `source_response`, parses them with `utils/sso_listing.py`, and builds one listing per harvest run, skipping a run that lacks a page. Every Act any listing shows gets a row, with its title from the newest listing that shows it and a flag saying whether the newest listing still does. Inserts new Acts and updates the title and flag of stored ones (`utils/legislation_update.py`). Writes `legislation`.

4. **Import the Hansard links** (`scripts/apply_hansard_links.py` + `populate/hansard_links.py` + `services/hansard_links.py`): reads the act-links plan and the Hansard report export, two files kept outside git (`schemas/act_link_plan.py`, `schemas/hansard_report_export.py`), and the stored `legislation` rows. Builds each report's openhansard.sg URL with `utils/openhansard_url.py`. The dry run writes the plan (`schemas/hansard_link_plan.py`) for review; the commit builds it again, refuses unless it equals the reviewed file, then deletes and rewrites `bill`, `bill_report` and `act_history_entry` in one transaction.

5. **Build versions** (`scripts/apply_legislation_versions.py` + `populate/legislation_versions.py` + `services/legislation_version.py`): reads every stored PDF with status 200 from `source_response`, one body at a time, and keeps the plain Act PDFs (`utils/sso_act_url.py`) of Acts that have a `legislation` row. Reads the printed version date from the PDF's lines (`utils/pdf_text.py`) and, for an archive copy, the capture time and CDX digest. Marks each Act's newest version by printed date, then capture time (`utils/legislation_version_update.py`). Writes `legislation_version`.

6. **Parse sections** (`scripts/apply_legislation_sections.py` + `populate/legislation_sections.py` + `services/legislation_section.py`): reads each version's PDF, splits its lines (`utils/pdf_text.py`) into sections, Articles and schedules under their Part and Division headings, and compares the parse with the stored rows. One transaction per version: rewrites the sections when they changed and sets the version's two character counts. Postgres fills `search_vector` from the heading and text. A version that will not parse is listed with the reason and the run goes on. Writes `legislation_section` and the counts on `legislation_version`.

7. **Derive aliases** (`scripts/apply_legislation_aliases.py` + `populate/legislation_aliases.py` + `services/legislation_alias.py`): reads the stored `legislation` rows and plans each Act's full title, title without the year and SSO code. Deletes the stored aliases the plan lacks and inserts the new ones. Writes `legislation_alias`.

8. **Publish a source** (`scripts/publish_source.py` + `services/source_grants.py` + `crud/source_grant.py`): changes a source's publish status and, in the same transaction, grants and revokes the site role's `SELECT` so it can read exactly the tables whose sources are all published (see Site role below). Writes `source` and the grants.

9. **Report coverage** (`scripts/coverage_figures.py` + `populate/coverage_figures.py`): read only. Counts versions by source and year, sections by kind, the lowest text share and the Hansard links.

10. **Harvest eLitigation** (`scripts/harvest_elitigation.py` + `populate/elitigation_responses.py` + `gateway/elitigation.py`): for each year from the current year down to 1965 it fetches every listing page with the `SUPCT` filter (which lists all three courts, see `docs/sources/elitigation.md`), then each listed judgment page that has no stored 200 body holding a neutral citation. `utils/elitigation_listing.py` reads the total, the page count and each row's judgment path and printed citation, and `utils/elitigation_judgment.py` reads a judgment page's citation. A 200 body with no total or no citation is stored raw and counts as a failure. Guards and storage are stage 1's, with no time window. Ends with one log line per year. Writes `source_response` and `harvest_run`. The source stays UNPUBLISHED.

Not built: the eGazette and data.gov.sg stages, and subsidiary legislation. Each waits on real pages to test against or on requests that may not go out yet, as the run's parked list, kept outside git, records.

### Database models

Every enum column is `Text` with a check constraint, so a row loaded from the database holds a plain `str`: compare it through the enum member and format the column itself, never `.value`.

- `source`: one row per source (`SourceName`), with its `publish_status` (PUBLISHED or UNPUBLISHED), the reason and time of the last change, and for SSO alone its `sso_access_state` (UNTESTED, SERVING or CHALLENGED) with its own reason and time. Migration 0002 seeds the six rows.
- `harvest_run`: one row per harvest run of one source, with its counts (requests sent, bodies stored, bodies unchanged, failures), its start and finish times, its status (RUNNING, SUCCEEDED, HALTED or FAILED) and the halt or failure reason.
- `source_response`: the raw table. One row per body fetched, stored once per requested URL and SHA-256, with the final URL, status code, content type, the body as text or as bytes (never both), its length and fetch time, its kind (listing page, document, CDX answer, robots file), its source and its harvest run.
- `legislation`: one row per Act a stored listing page shows, keyed by its SSO code, with its title as the listing prints it, whether the newest listing still shows it, and the source of that listing.
- `legislation_version`: one row per stored Act PDF that reads as a version. `printed_version_date` holds the date as the PDF prints it, and `version_date` our reading of it. It also holds the SSO URL's `_` value (`version_stamp`), the archive timestamp and CDX digest of an archive copy, the capture time, whether it is the Act's newest version, and the two character counts the section stage sets (`body_character_count` and `section_character_count`).
- `legislation_section`: one row per section, Article or schedule of a version, in printed order. `printed_number` is the number or schedule label as printed, and the heading, Part heading, Division heading and text are kept as printed with the PDF's line breaks. `sso_anchor` is our guess at SSO's anchor (`#pr<number>-`). It also holds the first and last page, whether the section is repealed, whether it sits on a page with an image, and `search_vector`, Postgres's word index of the heading and text with a GIN index. A version holds each printed number once (`uq_legislation_section_legislation_version_id_printed_number`).
- `legislation_alias`: one row per name an Act is looked up by: its full title as printed, its title without the year, and its SSO code (`AliasKind`). The lookup index is on `lower(alias)` and is not unique, since two Acts may share a title without its year.
- `bill`: one row per bill the act-links plan found, with its title as printed, our `title_key` for matching, the first and last sitting dates of its debates and whether it passed.
- `bill_report`: one row per Hansard report of a bill's debate, with the SPRS report id as printed, the openhansard.sg URL built from it, the report type, sitting date and title, and the Hansard row id for tracing only.
- `act_history_entry`: one row per entry of an Act's Legislative History, from the act-links plan. `printed_text`, `printed_law_number`, `printed_title` and `printed_bill_number` are as printed, and the four reading and commencement dates are the plan's reading of them. `bill_id` and `bill_link_source` say which bill the entry links to and by which rule, and stay NULL when no rule found one.

### Site role

The site reads through the `NOLOGIN` role `open_sg_law_site` (ADR 0005). Migration 0012 creates it when `pg_roles` has none, grants it `USAGE` on `public`, and grants `SELECT` on the tables whose sources are published. `services/source_grants.py::TABLE_NAME_TO_SOURCES` names the sources each table draws from, and a table is granted only while all of them are published. `source` draws from none and is always granted. `source_response` and `harvest_run` are not in the map and are never granted. `scripts/publish_source.py` is the only other place that grants: it changes a status and grants and revokes in the same transaction, so the grants match the published sources. A change to `TABLE_NAME_TO_SOURCES` needs a new migration, and `tests/test_source_grants.py` fails until the migration's copy matches.

## `scripts/` directory

Every script runs as `python -m scripts.<name>`. A write script is a dry run unless `--commit`: the dry run logs what it would do and ends with `Dry run: nothing written`. With `--commit` it calls `validate_can_write`, commits, and runs `VACUUM (ANALYZE)` on the tables it wrote.

- `clear_sso_challenge.py`: sets a CHALLENGED SSO source back to UNTESTED, with `--reason`. Writes `source`. A dry run unless `--commit`.
- `publish_source.py`: sets a source PUBLISHED, or UNPUBLISHED with `--withdraw`, with `--reason`, and in the same transaction grants and revokes the site role's `SELECT` to match. Writes `source` and the grants. A dry run unless `--commit`; the dry run logs the grants and revokes it would make.
- `harvest_sso.py`: sends one night's SSO requests, inside 03:00 to 06:55 SGT, and stores each body. Writes `source_response`, `harvest_run` and the SSO access state on `source`. A dry run unless `--commit`; the dry run logs the SSO state and the stored counts and sends nothing.
- `harvest_elitigation.py`: sends the eLitigation requests of every year and stores each body. Writes `source_response` and `harvest_run`. A dry run unless `--commit`; the dry run logs the stored counts and sends nothing.
- `harvest_archive.py`: fetches the Internet Archive's CDX answer, the latest plain capture of each Act PDF and the listing captures, and stores each body. Writes `source_response` and `harvest_run`. A dry run unless `--commit`; the dry run logs the stored counts and sends nothing.
- `apply_legislation.py`: reads the stored listing pages and stores the Acts they show. Writes `legislation`. A dry run unless `--commit`.
- `apply_hansard_links.py`: reads the act-links plan (`--plan-file`) and the Hansard report export (`--report-export-file`), both kept outside git, and the stored `legislation` rows. The dry run writes the plan to `--plan-output` for review. The commit builds the plan again, refuses unless it equals the reviewed file, and writes `bill`, `bill_report` and `act_history_entry` in one transaction.
- `apply_legislation_versions.py`: reads the stored Act PDFs and CDX answers and builds one version per PDF, marking each Act's newest. Writes `legislation_version`. A dry run unless `--commit`.
- `apply_legislation_sections.py`: parses each stored version's PDF into sections, one transaction per version, and lists each version it cannot parse with the reason. Writes `legislation_section` and the two character counts on `legislation_version`. A dry run unless `--commit`.
- `apply_legislation_aliases.py`: reads the stored `legislation` rows and stores each Act's aliases. Writes `legislation_alias`. A dry run unless `--commit`.
- `coverage_figures.py`: read only. Logs the coverage figures for versions, sections and Hansard links; `--output` also writes them to a file under `docs/figures/`, and refuses one that exists.

## Module structure

```
open-sg-law/
│
├── settings.py                      # AppSettings: DATABASE_URL and the source base URLs
├── enums.py                         # SourceName, PublishStatus, SsoAccessState, HarvestRunStatus, ResponseKind, SsoAnswer, ActHistoryEntryKind, BillLinkSource, ActHistoryDefect, LegislationSectionKind, AliasKind
├── exceptions.py                    # OpenSgLawError and every subclass
├── logs.py                          # Loguru logger setup
│
├── schemas/                         # Pydantic models of answers and input files
│   ├── act_link_plan.py             # ActLinkPlan: the act-links plan file from hansard-scraper
│   ├── cdx_answer.py                # CdxAnswer: an Internet Archive CDX answer
│   ├── hansard_link_plan.py         # HansardLinkPlan: the reviewed plan file of apply_hansard_links
│   ├── hansard_report_export.py     # HansardReportExport: the Hansard report export file
│   └── source_http_response.py      # SourceHttpResponse: one HTTP answer as every gateway returns it
│
├── gateway/                         # HTTP calls to the sources
│   ├── http.py                      # CrawlPacer per host, paced_request, send_with_retry, one user agent
│   ├── sso.py                       # SSO robots file, listing pages and Act PDFs; never retries, never follows a redirect
│   ├── internet_archive.py          # CDX queries and capture fetches
│   └── elitigation.py               # eLitigation listing and judgment pages
│
├── services/                        # Pure transforms and rules
│   ├── sso_answer.py                # Judges an SSO answer: expected, failure, or a challenge that raises
│   ├── sso_request.py               # The SSO window check and the Act PDF paths to fetch
│   ├── harvest_run.py               # Harvest guards: one running run, consecutive failures, database size
│   ├── source_response.py           # Decodes a body as text unless it is a PDF, reads a listing page from an answer, and builds a source_response row
│   ├── archive_capture.py           # CDX answer → the latest plain capture of each Act
│   ├── legislation.py               # Stored listing pages → planned legislation rows
│   ├── hansard_links.py             # Act-links plan + report export → the Hansard link plan
│   ├── legislation_version.py       # Printed version date, archive capture and newest-version rules
│   ├── legislation_section.py       # PDF lines → sections, Articles and schedules under Part and Division headings
│   ├── legislation_alias.py         # Legislation rows → planned aliases
│   └── source_grants.py             # TABLE_NAME_TO_SOURCES and the tables the site role may read
│
├── database/                        # SQLModel table definitions
│   ├── init.py                      # Engine setup
│   ├── source.py                    # Source
│   ├── harvest_run.py               # HarvestRun
│   ├── source_response.py           # SourceResponse: the raw table
│   ├── legislation.py               # Legislation
│   ├── legislation_version.py       # LegislationVersion
│   ├── legislation_section.py       # LegislationSection, with its search vector
│   ├── legislation_alias.py         # LegislationAlias
│   ├── bill.py                      # Bill and BillReport
│   └── act_history_entry.py         # ActHistoryEntry
│
├── crud/                            # Database reads and writes, one file per table
│   ├── source.py
│   ├── harvest_run.py
│   ├── source_response.py
│   ├── legislation.py
│   ├── legislation_version.py
│   ├── legislation_section.py
│   ├── legislation_alias.py
│   ├── bill.py
│   ├── bill_report.py
│   ├── act_history_entry.py
│   ├── source_grant.py              # The site role's SELECT grants: read, grant, revoke
│   ├── database_size.py             # The database's size in bytes
│   └── vacuum.py                    # vacuum_count and VACUUM (ANALYZE) for a table the caller names
│
├── populate/                        # Pipeline stages: gateway + services + crud
│   ├── sso_responses.py             # The SSO harvest stage, with its window and challenge guards
│   ├── archive_responses.py         # The Internet Archive harvest stage
│   ├── elitigation_responses.py     # The eLitigation harvest stage
│   ├── legislation.py               # Plans and writes legislation rows from stored listings
│   ├── hansard_links.py             # Plans and writes the Hansard link tables in one transaction
│   ├── legislation_versions.py      # Plans and writes versions from stored PDFs
│   ├── legislation_sections.py      # Parses and writes the sections of each version
│   ├── legislation_aliases.py       # Plans and writes aliases
│   ├── coverage_figures.py          # Reads the coverage figures
│   └── written_tables.py            # VACUUM (ANALYZE) the tables a write script wrote, and check the count rose
│
├── utils/                           # Shared pure functions
│   ├── write_target.py              # validate_can_write: refuses a local database off port 5436
│   ├── sso_act_url.py               # Reads an SSO Act PDF URL: its code and version stamp, or None for a dated copy
│   ├── sso_listing.py               # Builds an SSO listing page URL, and parses a listing page into rows and its page index
│   ├── archive_capture_url.py       # Builds the Internet Archive URL of a capture
│   ├── elitigation_listing.py       # Parses an eLitigation listing page into its total, page count and rows
│   ├── elitigation_judgment.py      # Reads the neutral citation of an eLitigation judgment page
│   ├── openhansard_url.py           # Builds an openhansard.sg report URL as the site does
│   ├── pdf_text.py                  # PDF → lines with bold and margin marks, and images per page
│   ├── legislation_update.py        # LegislationUpdate: one legislation row's change, for a bulk update
│   └── legislation_version_update.py  # LegislationVersionNewestUpdate: one version's newest flag, for a bulk update
│
├── scripts/                         # Supervised scripts, run as modules
│   ├── clear_sso_challenge.py
│   ├── publish_source.py
│   ├── harvest_sso.py
│   ├── harvest_archive.py
│   ├── harvest_elitigation.py
│   ├── apply_legislation.py
│   ├── apply_hansard_links.py
│   ├── apply_legislation_versions.py
│   ├── apply_legislation_sections.py
│   ├── apply_legislation_aliases.py
│   └── coverage_figures.py
│
├── alembic/versions/                # Hand-written migrations 0001 to 0012
└── tests/                           # Tests on the scratch database, fixtures and their SOURCES.md
```
