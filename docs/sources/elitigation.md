# eLitigation

The Supreme Court's eLitigation service publishes the written judgments of the Supreme Court, the State Courts and the Family Justice Courts. `gateway/elitigation.py` fetches its listing pages and its judgment pages. Nothing in this repo parses them yet, and no stage runs the gateway.

## Endpoints

- Listing: `https://www.elitigation.sg/gd/Home/Index?Filter=<court>&YearOfDecision=<year>&SortBy=Score&CurrentPage=<n>`. `get_elitigation_listing_response` builds it. `SUPCT` is the Supreme Court filter. The filters for the State Courts and the Family Justice Courts are not known yet, so the court filter is a plain string.
- Total: the listing page prints the count as "Total Judgment(s) Found".
- Judgment link: each listing row links to its judgment with `a.gd-heardertext`. `get_elitigation_judgment_response` fetches the URL that link gives.
- Citation: a judgment page prints its neutral citation in `.HN-NeutralCit`, such as `[2026] SGHC 229`.

## Quirks

These come from the sg-legal-corpus project, which crawled the same pages.

- The filters `STATECT` and `FAMCT` answered with status 200 and an error page, not a listing.
- A maintenance notice comes back with status 200.

So a status of 200 does not show that a page holds judgments. The stage that reads these pages must check the body.

## Pacing

One request every 2 seconds, through `ELITIGATION_PACER` in `gateway/http.py`. A request that fails with a connection error, a timeout, a 429 or a 5xx is sent again by `send_with_retry`, up to five sends in all, each through the pacer. Every request sends the project's user agent, `CRAWL_USER_AGENT`.

## What we promised

Letter 1, to the Supreme Court (`plans/letters/1-supreme-court.md`, line 15), promises:

> Fetch at most one page every 2 seconds, outside office hours, from a client that names the project and gives a contact address.

The gateway keeps the 2 second gap and the user agent. The refusal to fetch during office hours is not built yet. It must be built with the eLitigation stage, before that stage sends anything, with the allowed hours for Royce to set (gate ruling G5.4; the stage is parked).
