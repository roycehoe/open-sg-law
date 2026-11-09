# Coverage

What this project collects, how far each part has got, and how it links to Hansard. Counts come from the local database on 9 November 2026. The grouping into strata is this project's own, and the sources do not print it. `python -m scripts.coverage_figures` remains the measure of the legislation objectives ([vision](vision.md#measuring-progress)).

## Legislation

| Stratum | Substratum | Source | Release | State |
|---|---|---|---|---|
| Consolidated text | Constitution | SSO listing, Internet Archive PDF | A | Held as CONS1963, 246 Articles. SSO lists it among the Acts. |
| Consolidated text | Acts | SSO listing, Internet Archive PDFs | A | 523 listed, 509 with a version, 507 parsed into sections. |
| Consolidated text | Subsidiary legislation | SSO | Follows the Acts and does not hold up Release A (Royce, 8 November 2026) | Nothing fetched. |
| As-enacted text | Acts Supplement, from 2024 | eGazette | Parked | Nothing fetched. |
| As-enacted text | Subsidiary Legislation Supplement, from 2024 | eGazette | Parked | Nothing fetched. |
| Indexes | eGazette index datasets | data.gov.sg | Parked | Nothing fetched. |
| Point-in-time text | Earlier consolidated versions | SSO | C, once AGC grants bulk access | Nothing fetched. |

eGazette and data.gov.sg stay parked until the SSO harvest shows a gap they would fill.

### Acts in detail

Every version comes from the Internet Archive, because SSO has served nothing. CloudFront answered all 8 sends of the first SSO night with a 403 on `robots.txt` ([details](sources/sso.md#the-block-of-9-november-2026)).

- The newest listing is the Internet Archive's capture of 7 November 2026. It shows all 523 Acts.
- Each Act has one version at most, the latest plain capture. Of the 509 versions, 339 were captured in 2024, 105 in 2025 and 65 in 2026, so an Act amended after its capture is out of date here.
- The 27,216 stored provisions are 26,372 sections, 246 Articles and 598 schedules.
- 14 Acts have no version: CAASA2009, CCA2006, CDCSA2001, CEA2000, CPFA1953, FAA2001, FCA1959, FNECDA1949, GIA1934, MA1975, MRA1997, NRDA2007, NUSCA2005 and WICA2019.
- 2 versions did not parse into sections: CYPA1993 and ISA1965.

## Judgments

eLitigation holds the judgments of three court groups under one listing. The harvest stores each judgment page raw. Nothing parses a judgment yet, and none is published until the Supreme Court agrees in writing ([ADR 0001](adr/0001-ask-before-publishing.md)). The court names below are our reading of the citation codes and of the courts the pages print.

| Stratum | Substratum | Citation code | Judgments stored |
|---|---|---|---|
| Supreme Court | Court of Appeal | SGCA | 2,789 |
| Supreme Court | Court of Appeal, on appeal from the international commercial court | SGCAI | 56 |
| Supreme Court | Appellate Division of the High Court | SGHCA | 197 |
| Supreme Court | High Court | SGHC | 11,338 |
| Supreme Court | High Court, Registrar | SGHCR | 300 |
| Supreme Court | Singapore International Commercial Court | SGHCI | 210 |
| Family Justice Courts | High Court, Family Division | SGHCF | 397 |
| Family Justice Courts | Family Courts | SGFC | 150 |
| Family Justice Courts | Youth Courts | SGYC | 8 |
| State Courts | District Courts | SGDC | 273 |
| State Courts | Magistrates' Courts | SGMC | 86 |
| State Courts | Small Claims Tribunals | SGSCT | 30 |
| State Courts | Employment Claims Tribunals | SGECT | 18 |
| State Courts | Protection from Harassment Court | SGPHC | 5 |
| State Courts | Community Disputes Resolution Tribunals | SGCDT | 4 |
| Other | Privy Council | SGPC | 55 |
| Other | Constitutional Tribunal | SGCT | 1 |
| Other | Printed as SGAD, a District Court appeal | SGAD | 1 |

The total is 15,918 judgment pages whose title is a neutral citation. The SGHC count includes one page whose citation prints as `[2013] SGHC115`.

| Citation decade | Judgments stored |
|---|---|
| 2020s | 4,003 |
| 2010s | 3,896 |
| 2000s | 3,369 |
| 1990s | 3,744 |
| 1980s | 733 |
| 1970s | 172 |
| 1960s | 1 |

The listing pages for 2026 down to 1975 total 15,948 judgments. Almost all of the difference is 1975, where 5 of 34 are stored. The years 1974 to 1965 are not walked yet. A year's stored count can differ slightly from its listed count, because the listing goes by year of decision and the count here by citation year.

The latest run stopped during 1975 on 8 November 2026. It recorded no reason and is still marked RUNNING.

## Links to Hansard

Only Acts link to Hansard, and they link at the level of the whole Act. The text of the debates is not held here ([ADR 0003](adr/0003-hansard-links-by-report-id.md)). No plan yet links a debate to a single section, to subsidiary legislation or to a judgment.

The chain is:

`legislation` → `act_history_entry` → `bill` → `bill_report` → the openhansard.sg report URL

| Table | Rows |
|---|---|
| `bill` | 2,811, of which 2,682 passed |
| `bill_report` | 5,827, of which 5,806 are `bill` or `bill-intro` reports and 21 are motions or oral answers |
| `act_history_entry` | 9,905, across 496 Acts |
| Entries linked to a bill | 5,107, reaching 482 Acts |

### How a link is made

The hansard-scraper project builds the links ([`services/act_link.py`](https://github.com/roycehoe/hansard-scraper/blob/d4f9818/services/act_link.py), as of commit `d4f9818`). This repo imports its plan and does not match anything itself.

1. Bills come from the Hansard reports. The `bill` and `bill-intro` reports are grouped by title key, which is the title in lower case with everything but letters and digits removed. A group closes after a report holding a third-reading line, and a gap of more than 366 days starts a new one. Six bills are kept by hand, because the grouping rule splits or misses their reports.
2. Legislative History entries come from the end of each Act's PDF. An entry prints the amending law's number and title, its bill number and its reading dates.
3. Each entry of kind ACT or ORDINANCE is turned into a bill title key. The steps drop a leading "The", a trailing "(Chapter ...)" and a trailing year, then change a final "Act" or "Ordinance" to "Bill".
4. The rules below run in order, and the first that finds a bill wins. A date counts as close when a report of the bill is within 1 day of it.

| Rule (`bill_link_source`) | What it needs | Entries |
|---|---|---|
| `HAND_KEPT` | A hand-kept file names the entry and its bill. This runs ahead of every other rule. | 3 |
| `FIRST_READING_DATE` | Same title key, close to the first-reading date. The nearest bill wins. | 5,010 |
| `THIRD_READING_DATE` | Same title key, close to the third-reading date. The nearest bill wins. | 55 |
| `SECOND_READING_DATE` | Same title key, close to the second-reading date. The nearest bill wins. | 0 |
| `LOOSE_TITLE_READING_DATES` | Same title key once "amendment" and "No N" are removed, close to the first and third readings where both are printed, and exactly one such bill. | 31 |
| `SIMILAR_TITLE_READING_DATES` | Both first and third readings printed, the bill's first report close to the first reading and its last report close to the third, title similarity of at least 0.85, and exactly one such bill. | 8 |

An omnibus bill is linked from many entries, which is correct. An entry no rule matches keeps `bill_id` NULL rather than take a guess ([data-loss register](data-loss-register.md)).

| Entry kind | Entries | Linked |
|---|---|---|
| ACT | 4,734 | 4,716 |
| ORDINANCE | 1,424 | 391 |
| REVISED_EDITION | 1,947 | 0 |
| SUBSIDIARY_LEGISLATION | 1,680 | 0 |
| OTHER | 120 | 0 |

Revised editions, subsidiary legislation and other entries are not matched, because the rules cover only entries of kind ACT or ORDINANCE.

### How the links reach this database

`scripts/apply_hansard_links.py` reads the act-links plan and a report export, two files kept outside git. It builds each report's URL with `utils/openhansard_url.py`, then rewrites the three link tables in one transaction ([how the files are made](sources/openhansard.md)). A new Act gets links only when hansard-scraper ships a new plan and this script imports it.

## Left out of version 1

[backlog.md](backlog.md) lists every other source, such as Practice Directions, tribunal and regulator decisions, LawNet and OpenLaw, with its fetch and publish status. Singapore Law Reports content is out of scope ([README](../README.md#known-limits)).
