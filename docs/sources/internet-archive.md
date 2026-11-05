# Internet Archive

The Internet Archive's Wayback Machine holds captures of the Act PDFs that Singapore Statutes Online serves. `gateway/internet_archive.py` asks it which captures exist and fetches them. It is the source for Acts that SSO has stopped serving, and a second copy of those it still serves.

## Endpoints

- CDX query: `https://web.archive.org/cdx/search/cdx?url=<prefix>&matchType=prefix&filter=mimetype%3Aapplication%2Fpdf&output=json`. `get_archive_cdx_response` builds it. There is no `fl` parameter, so each row carries the default fields (`urlkey`, `timestamp`, `original`, `mimetype`, `statuscode`, `digest`, `length`), and there is no date range, because the stage takes the latest capture of any year.
- Capture: `https://web.archive.org/web/<timestamp>id_/<original url>`. `build_archive_capture_url` builds it. The `id_` form returns the captured bytes with no Wayback toolbar. A timestamp with no exact capture redirects to the nearest one, and `requests` follows the redirect, so `final_url` records where the answer landed. The stage asks for its own run time to get the newest capture of a listing page.

## Pacing

One request every 6 seconds, about 10 a minute, through `INTERNET_ARCHIVE_PACER` in `gateway/http.py`. Every request sends the project's user agent, `CRAWL_USER_AGENT`.

A connection error, a timeout or a 5xx is sent again with the short paced backoff, up to five sends in all. A 429 skips that backoff. The gateway waits 300 seconds and sends again, up to three waits. A fourth 429 raises `OpenSgLawGatewayError`, so one request makes at most four sends.

On 4 November 2026 the archive answered 429 to every request for about 45 minutes.

## Quirks

- When the archive is down for maintenance it answers a CDX query with status 200 and an HTML page, "Temporarily Offline". `tests/fixtures/archive/temporarily-offline-20261104.html` holds that page. A status of 200 does not show that a CDX answer is a list of rows, so the parser checks the body.
- An empty CDX answer is the JSON list `[]`.

## Which captures count

A capture is an Act's current text when its original URL is `/Act/<code>` with a query of `ViewType` and `_` only (`utils/sso_act_url.py`). A capture with `ValidDate`, `TransactionDate` or `DocDate` in the query is a historical version and is skipped. The latest qualifying capture of each code wins, whatever its year. `services/archive_capture.py` applies the rule.
