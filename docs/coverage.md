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
| Consolidated text | Repealed and uncommenced Acts | SSO | Not planned | SSO lists them separately. Not on any listing this project reads. |
| As-enacted text | Published Bills | SSO | Not planned | SSO lists them separately. Nothing fetched. |

eGazette and data.gov.sg stay parked until the SSO harvest shows a gap they would fill.

### Acts in detail

Every version comes from the Internet Archive, because SSO has served nothing. CloudFront answered all 8 sends of the first SSO night with a 403 on `robots.txt` ([details](sources/sso.md#the-block-of-9-november-2026)).

- The newest listing is from 16 to 19 July 2024. The harvest asked the Internet Archive for November 2026 and got its nearest capture. It shows 523 Acts, and each is flagged as on the newest listing because no other listing exists, so the flag can show no repeal since then.
- About 17 new Acts passed since July 2024 have no row, going by the titles of 24 bills passed since then. The Act PDFs were captured later than the list.
- The Internet Archive holds a complete 27-page listing captured on 22 and 23 August 2026, at 20 Acts a page. The harvest requests only the 500-a-page URL, so that listing is not stored.
- Each Act has one version at most, the latest plain capture. Of the 509 versions, 339 were captured in 2024, 105 in 2025 and 65 in 2026, so an Act amended after its capture is out of date here.
- The 27,216 stored provisions are 26,372 sections, 246 Articles and 598 schedules.
- 14 Acts have no version: CAASA2009, CCA2006, CDCSA2001, CEA2000, CPFA1953, FAA2001, FCA1959, FNECDA1949, GIA1934, MA1975, MRA1997, NRDA2007, NUSCA2005 and WICA2019.
- 2 versions did not parse into sections: CYPA1993 and ISA1965.

## Judgments

eLitigation holds the judgments of three court groups under one listing. The harvest stores each judgment page raw. `scripts/apply_judgments.py` parses them into 16,299 judgments and 2,389,271 blocks. The one page it cannot parse, `[2022] SGHC 109`, holds no text. None is published until the Supreme Court agrees in writing ([ADR 0001](adr/0001-ask-before-publishing.md)). The court names below are our reading of the citation codes and of the courts the pages print.

| Stratum | Substratum | Citation code | Judgments stored |
|---|---|---|---|
| Supreme Court | Court of Appeal | SGCA | 2,851 |
| Supreme Court | Court of Appeal, on appeal from the international commercial court | SGCAI | 56 |
| Supreme Court | Appellate Division of the High Court | SGHCA | 197 |
| Supreme Court | High Court | SGHC | 11,565 |
| Supreme Court | High Court, Registrar | SGHCR | 300 |
| Supreme Court | Singapore International Commercial Court | SGHCI | 210 |
| Family Justice Courts | High Court, Family Division | SGHCF | 397 |
| Family Justice Courts | Family Courts, 2020s pages | SGFC | 149 |
| Family Justice Courts | Youth Courts | SGYC | 8 |
| State Courts | District Courts | SGDC | 273 |
| State Courts | Magistrates' Courts | SGMC | 86 |
| State Courts | Small Claims Tribunals | SGSCT | 30 |
| State Courts | Employment Claims Tribunals | SGECT | 18 |
| State Courts | Protection from Harassment Court | SGPHC | 5 |
| State Courts | Community Disputes Resolution Tribunals | SGCDT | 4 |
| Other | Federal Court, 1960s pages | SGFC | 80 |
| Other | Privy Council | SGPC | 69 |
| Other | Constitutional Tribunal | SGCT | 1 |
| Other | Printed as SGAD, a District Court appeal | SGAD | 1 |

The total is 16,300 judgment pages whose title is a neutral citation. The SGHC count includes one page whose citation prints as `[2013] SGHC115`.

| Citation decade | Judgments stored |
|---|---|
| 2020s | 4,003 |
| 2010s | 3,896 |
| 2000s | 3,369 |
| 1990s | 3,744 |
| 1980s | 733 |
| 1970s | 357 |
| 1960s | 198 |

The listing pages for 2026 down to 1965 total 16,301 judgments, and the harvest finished on 9 November 2026. A year's stored count can differ slightly from its listed count, because the listing goes by year of decision and the count here by citation year.

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

### Why the rest have no link

"No link" means no report in the Hansard this project links to, which starts on 22 April 1955. It does not mean no debate took place. Singapore did not start making its own law at independence. English law was received under the Second Charter of Justice of 1826, local legislatures passed laws alongside it long before 1965, and section 13 of the Republic of Singapore Independence Act 1965 continued all of it. So the body that made a law decides where its debate would be recorded.

| Law made by | Period | Unlinked entries | Where a record would be |
|---|---|---|---|
| Straits Settlements Legislative Council | 1867 to 1941 | 795 | [Proceedings of the Council](https://libguides.nus.edu.sg/SGlawhistory/hansard), 1867 to 1940. In print at NUS, online by subscription or for selected years |
| Colony of Singapore, before the 1948 election | 1946 to March 1948 | 28, of which 3 print no reading date | NUS lists the Advisory Council's public sessions. Whether these laws were debated there is unconfirmed |
| Singapore Legislative Council | April 1948 to January 1955 | 228 | Proceedings of the Council, in print at NUS. No complete online copy found |
| UK Parliament | To 1992 | 24 | [UK Hansard](https://api.parliament.uk/historic-hansard/index.html), 1803 to 2005 |
| Malayan and Malaysian legislatures | To 1965 | 40 | The [Parliament of Malaysia repository](https://repositori.parlimen.gov.my/) holds Dewan Rakyat reports from 1963. The Malayan Federal Legislative Council's are not located |
| Government of India's legislature | 1838 and 1865 | 2 | Not located |
| Federated Malay States and Selangor | 1905 to 1935 | 2 | Not located |
| Straits Settlements Gazette items | | 4 | Not located |
| British Military Administration | 1945 | 1 | None. It was a proclamation, with no legislature |
| Reprints | | 47 | None. A reprint republishes a law |

The first three rows hold the 1,051 Ordinance and Act entries, and the rows after them hold the 120 other entries. Periods are by the latest reading each entry prints. 13 of the 24 English enactments print an application date of 12 November 1993, the day the Application of English Law Act 1993 took effect, and that Act's bill is already in this Hansard.

27 Acts print no Legislative History, so they have no entry to count as unlinked. 26 of them have their own bill in `bill` with no link, such as the Foreign Interference (Countermeasures) Act 2021. The other is the Independence of Singapore Agreement 1965, a treaty.

Two kinds have no bill at all, so no legislature read them as bills.

- Revised Editions. Commissioners make them under the Revised Edition of the Laws Act 1983 or its predecessors. 1,599 of the 1,947 have only the law that allowed the edition in Hansard, and 348 editions predate Hansard.
- Subsidiary legislation. It is made under an Act. Of the 1,680 entries, 64 have a motion on which the House resolved, 41 predate Hansard, 1 is unresolved, and no motion was found for the other 1,574 in samples of 30 and 35.

### How the links reach this database

`scripts/apply_hansard_links.py` reads the act-links plan and a report export, two files kept outside git. It builds each report's URL with `utils/openhansard_url.py`, then rewrites the three link tables in one transaction ([how the files are made](sources/openhansard.md)). A new Act gets links only when hansard-scraper ships a new plan and this script imports it.

## Left out of version 1

[backlog.md](backlog.md) lists every other source, such as Practice Directions, tribunal and regulator decisions, LawNet and OpenLaw, with its fetch and publish status. Singapore Law Reports content is out of scope ([README](../README.md#known-limits)).
