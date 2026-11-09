# 0007. Hansard links beyond a bill's own reports

Status: accepted, 9 November 2026. Royce ruled it on the findings of the Hansard link investigation. It amends [ADR 0003](0003-hansard-links-by-report-id.md).

Context. ADR 0003 says every link is copied from the act-links plan and is a link to a debate on a bill. Neither holds for the entries still unlinked. Of the 4,798, 1,051 Ordinance and Act entries were read before this Hansard starts on 22 April 1955 or print no reading date, 1,947 are Revised Editions, which Commissioners make without a bill, and 1,680 are subsidiary legislation, which is not read as a bill. "Debate" also says too much about the 5,107 existing links, since some are first-reading notices or a second reading where only the mover spoke.

Decision.

- At launch the site calls the 5,107 links "Hansard reports on this Bill", with their dates. Classifying them as a debate, a mover-only reading or a first reading comes after launch, once the grouping and seconder faults found by the investigation are fixed.
- Revised Editions get one standing note, citing section 4(1) of the Revised Edition of the Laws Act 1983 and Hansard reports 37828 and 10513. They get no link per entry.
- The 64 subsidiary legislation entries on which the House resolved are hand-kept on the site, keyed by SSO code and printed Gazette number, with SPRS report ids. They are not in the act-links plan. Royce spot-checks a few before they ship.
- The 26 Acts that print no Legislative History but have their own bill ship in Release A as a hand-kept list, keyed by SSO code, with SPRS report ids. The match is the exact title key, a passed bill, and a last sitting in the Act's year.
- No page calls the Act list current. Each Act index states the date of the listing it comes from.
- Where an entry has no link, the site gives the reason. A law read before 22 April 1955 is described as having no report in this Hansard, and never as having had no debate, because earlier legislatures kept their own proceedings ([coverage](../coverage.md#why-the-rest-have-no-link)).
- Legislative Council proceedings are probed on 30 entries after Release A.

Why. A hand-kept list and a note are short enough to read and check, and a new table would cost about 22 files across two repos for what is mostly 4 Acts. A title-mention match can show that a speech names an instrument but not that it is relevant, and Interpretation Act s 9A(3)(d) admits only relevant material.

Consequences.

- The note and the 64 rows sit outside the reviewed-plan check and outside `coverage_figures`, so each needs a data-loss register row when it ships.
- "History entries linked" stays the count of an entry's own bill, so these additions do not raise it.

Alternatives.

- A new `act_history_entry_report` table with a closed `meaning` column. Deferred until subsidiary legislation instruments are fetched or the links need the database's review path.
- Linking every Revised Edition to the law that allowed it, 1,599 links to the same few reports. Rejected because it repeats one fact and invites the reading that the edition itself was debated.
- Links from speech mentions, Gazette numbers or the enabling Act's debates. Rejected as above.
