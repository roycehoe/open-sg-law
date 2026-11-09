# eLitigation

The Supreme Court's eLitigation service publishes the written judgments of the Supreme Court, the State Courts and the Family Justice Courts. `gateway/elitigation.py` fetches its listing pages and its judgment pages, and `populate/elitigation_responses.py` (run by `scripts/harvest_elitigation.py`) walks them and stores every body raw. Nothing parses a judgment's text yet.

## Endpoints

- Listing: `https://www.elitigation.sg/gd/Home/Index?Filter=SUPCT&YearOfDecision=<year>&SortBy=Score&CurrentPage=<n>`. `get_elitigation_listing_response` builds it. A page holds 10 rows, and the last page of a year holds the rest.
- Total: the listing page prints the year's count as "Total Judgment(s) Found : 573" (2025).
- Page count: the page does not state it. Page 1 links to the last page with a "Last" link (`CurrentPage=58` for 2025), and the last page links to no later page and marks its own number as the active one. `utils/elitigation_listing.py` takes the highest page number any pagination link or active marker shows.
- Judgment link: each listing row links to its judgment with `a.gd-heardertext`, to a path like `/gd/s/2025_SGHC_267`. The row prints its neutral citation in `a.citation-num-link`, as the court spells it (`[2025] SGHC(A) 26` for the path `2025_SGHCA_26`).
- Judgment page: `get_elitigation_judgment_response` fetches the URL that path gives. The page holds the full text, and its title is its neutral citation as the court prints it, such as `[2025] SGHC 267` or `[2026] SGHC(A) 26`. Supreme Court pages also print it in `.HN-NeutralCit`, but State Courts and Family Justice Courts pages do not (run 3, 7 November 2026), so the stage reads the title. A listing or error page is titled `SG Courts Judgments`.
- Years: the year dropdown `#ddlYears` lists 2026 down to 1965. The stage walks the current year down to 1965.

## The SUPCT filter

Fetched on 7 November 2026: `Filter=SUPCT` lists the judgments of all three courts. Its page 1 for 2025 is row for row the page with no filter, and mixes SGHC, SGHCA, SGDC, SGFC and SGHCR citations. So the stage walks the years with `SUPCT` alone.

## Error page

`Filter=STATECT`, `Filter=FAMCT` and `Filter=ALL` each answer status 200 with a 4,226-byte page reading "A system error has occurred and the requested operation could not be completed." (fixture `tests/fixtures/elitigation/statect-2025-system-error.html`). A maintenance notice also comes back with status 200, as the sg-legal-corpus project saw. Run 4 stored three, each 847 bytes and titled `:: eLitigation - Maintenance Notice ::`. No fixture holds one.

A status of 200 does not show that a page holds judgments. A listing page with no total, and a judgment page whose title is not a neutral citation, are failures: the stage stores the body raw like any other, counts a failure, and leaves the URL for the next run. A judgment counts as stored when a 200 body has a title the neutral citation parser accepts. A failure on a year's first listing page halts the run. Reruns fetch listing pages again to find new judgments.

## Audit of 9 November 2026

Run 9 walked every year from 2026 down to 1965. Against the newest stored listing page of every year, the listings print 16,301 judgments and link 16,300 distinct pages, and all 16,300 are stored.

- The listing for 2015 shows `/gd/s/2015_SGHC_3` twice, so the log reports 426 of 427 for that year.
- `/gd/s/2013_SGHC115_` is stored, but its title prints as `[2013] SGHC115`, and the citation check rejects a title with no space before the number. Each run fetches the page again and counts one failure, which is run 9's one failure, and the log reports 346 of 347 for 2013.
- Three stored bodies from run 4 are the maintenance notices above. A later run stored the judgment at each of those URLs.

The code SGFC means two courts. The 80 pages from 1965 to 1969 are the Federal Court of the Republic of Singapore, and the 149 from 2024 on are the Family Courts.

## Pacing

One request every 2 seconds, through `ELITIGATION_PACER` in `gateway/http.py`. A request that fails with a connection error, a timeout, a 429 or a 5xx is sent again by `send_with_retry`, up to five sends in all, each through the pacer. Every request sends the project's user agent, `CRAWL_USER_AGENT`. The stage has no office-hours guard: on 7 November 2026 Royce ruled to fetch at any hour. It halts on 3 failures in a row or when the database passes 10 GB, and commits at least every 100 bodies.

## What we promised

Letter 1, to the Supreme Court (`plans/letters/1-supreme-court.md`), was rewritten on 7 November 2026 and no longer promises any rate or hours. It says only: "Until permission is in place, I will not publish any judgment."

The ELITIGATION source stays UNPUBLISHED, so the site role cannot read `source_response` rows or any table drawn from it. The gateway keeps the 2 second gap and the user agent.
