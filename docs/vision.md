# Vision

A free, non-commercial place where a lawyer, or anyone else, can read current Singapore legislation and court judgments, with each Act linked to the Hansard debates on its bills. The platform is written in plain language and has no paid tier, no ads and no sponsored placement ([ADR 0002](adr/0002-non-commercial-for-good.md)). This repository is the scraper and the database. A separate site repository follows.

Fetching a source and publishing it need separate legal bases. The goals below say what the database holds. Whether a table opens to the site depends on the source's permission, and the publish gate enforces that ([ADR 0005](adr/0005-publish-gate-by-database-role.md)).

---

## Objectives

### 1. Current consolidated legislation, with links to SSO
Hold the current consolidated text of every Act and of subsidiary legislation, section by section, each section with a link to its page on Singapore Statutes Online (SSO). The raw body of every fetch is kept exactly as received. The words are shown verbatim, and only layout changes.

### 2. Act-to-debate links
Link each Act to the Hansard debates on its bills, by openhansard.sg report id ([ADR 0003](adr/0003-hansard-links-by-report-id.md)). The text of the debates is not held here.

### 3. Judgments, once permitted
Hold eLitigation judgments from the Supreme Court, the State Courts and the Family Justice Courts, identified by neutral citation. They are fetched and stored privately now. Nothing about them is published until the Supreme Court agrees in writing ([ADR 0001](adr/0001-ask-before-publishing.md)).

### 4. Keyword and citation search
Keyword search with section-level results, and citation lookup, so that "s 9A Interpretation Act" goes to the section. There are no AI answers in version 1.

---

## Strategies

### Raw first, derive second
Every fetched body goes into a raw table before anything reads it. A body is stored as text when it decodes strictly, and as bytes otherwise, with its SHA-256 ([ADR 0004](adr/0004-pdf-as-legislation-text-source.md)). Everything derived can be rebuilt from the raw bodies, and [data-loss-register.md](data-loss-register.md) lists each step that changes or drops anything.

### Ask before publishing
The project writes to the Supreme Court and to AGC before it publishes what their terms do not already allow. Legislation is published under SSO clause 13 and eGazette clause 11, which meet their conditions without a letter.

### Honest, slow requests
SSO gets automated requests only from 03:00 to 07:00 Singapore time, at one a minute, with a user agent that names the project and no retry after a challenge. Nothing works around a firewall, and no headless browser is used.

### One style
All code follows [STYLE.md](../STYLE.md), copied from hansard-scraper with its domain word changed.

---

## Measuring progress

`python -m scripts.coverage_figures` is the measure for the legislation objectives (1 and 2). It logs the numbers below, and `--output` keeps them in `docs/figures/`. No figures exist yet, because every harvest and write run is parked (`plans/open-sg-law-parked.md`), so nothing is published. When a figure moves, replace the current figure in the same change and keep the earlier one in a history file.

| Figure | What it counts |
|---|---|
| Acts with a consolidated version | By source (SSO, Internet Archive, eGazette), and by the year of the newest version |
| Sections parsed | Sections stored, and the share of each PDF's text that lands in a section |
| History entries linked | Legislative history entries linked to a Hansard report |

Run the script before and after any change to parsing or linking, and quote every number it logs.
