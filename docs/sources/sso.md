# Singapore Statutes Online (SSO)

The Attorney-General's Chambers publishes the current consolidated text of every Act on Singapore Statutes Online. `gateway/sso.py` fetches its `robots.txt`, its listing of current Acts and the PDF of each Act. `services/sso_answer.py` decides whether each answer is what was asked for, a failure, or a challenge.

## Terms

- Clause 13 sets the conditions for reusing SSO text. Automated extraction is allowed only from 03:00 to 07:00 SGT (cl 13(d)(i)). This repo stops sending at 06:55 SGT, and checks the time when the request is about to go out, after the pacer's wait, so no request starts at or after 06:55.
- Every request is honest: it sends the project's user agent, `CRAWL_USER_AGENT`, and never a browser's. No headless browser is used, and nothing tries to get around the firewall.
- We are responsible for the accuracy of what we publish (cl 13(b)), and nothing suggests AGC endorses the site.
- No images are reproduced (cl 6). A provision that holds an image links to SSO.
- AGC may revoke the permission (cl 14). Royce then withdraws the source with `python -m scripts.publish_source --withdraw`, which revokes the site's grants in the same transaction.

## Endpoints

- `https://sso.agc.gov.sg/robots.txt`
- Listing, first page: `https://sso.agc.gov.sg/Browse/Act/Current/All?PageSize=500`
- Listing, later pages: `https://sso.agc.gov.sg/Browse/Act/Current/All/<n>?PageSize=500&SortBy=Title&SortOrder=ASC`, where `<n>` is the zero-based page index, so the second page is `1`. The first page has no index segment. In July 2024 the listing held 523 Acts in 2 pages.
- Act PDF: the path the listing row links to, such as `/Act/AA2004?ViewType=Pdf&_=20240702194429`. The `_=` value is SSO's version stamp, `YYYYMMDDhhmmss`.
- A listed Act may have no PDF link. The listing of 16 July 2024 shows two, GSTVFA2012 and GCA1966. Such a row is kept with no PDF path and no version stamp, so the Act still gets a `legislation` row, and the SSO stage requests no PDF for it.

The search pages are never requested.

## robots.txt

On 5 November 2026 SSO's `robots.txt` said `Crawl-delay: 6` and `Disallow: /search`. This repo sends one request every 6 seconds, through `SSO_PACER`, the delay it asks for.

## The trial of 5 November 2026

At 03:00 SGT a trial script sent requests 8 seconds apart with a browser user agent. SSO answered six of them, then answered with a 202 and an empty body: its firewall's challenge. The repo first waited a minute between requests and stopped at the first challenge because of that trial. On 8 November 2026 Royce moved it to the `robots.txt` delay with the backoff below, before any request had gone out at either rate.

## The block of 9 November 2026

The first SSO night began at 03:02 SGT with `CRAWL_USER_AGENT`. CloudFront answered its first request, for `robots.txt`, with a 403 and a 919-byte "Request blocked" page. All eight sends of the backoff got the same answer, so the run halted with SSO CHALLENGED before any listing page or PDF.

The block is not on the IP address. That morning the same URL loaded in a browser on the same connection, then answered one curl request carrying `CRAWL_USER_AGENT` with the same 403 and `X-Cache: Error from cloudfront`.

The block is older than this repo's first request. `kevanwee/sg-legal-corpus` recorded on 19 September 2026 (commit `020c6d94`) that SSO "rejects non-browser UAs at CloudFront". The trial of 5 November sent a browser user agent from Python's `urllib` and got six answers, so the user agent is the likely trigger. Only AGC can confirm the rule.

Waiting or slowing down will not lift a rule of this kind, and this repo does not send a browser's user agent. SSO stays CHALLENGED until AGC replies.

## Answers

`get_sso_answer` sorts every answer into one of three kinds. The rule is total.

- **Failure:** a 404 or any 5xx, whatever its body. The trial's one 404 came with a 24 KB HTML page.
- **Expected:** a 200 whose body is the kind that was asked for. A PDF starts with `%PDF-`. A listing page is `text/html` and holds `class="non-ajax file-download"`. `robots.txt` is `text/plain`.
- **Challenge:** everything else. That covers a 202 with or without a body, a 401, a 403, a 429, any 3xx, and a 200 of the wrong kind. It raises `OpenSgLawSsoChallengeError`.

A challenge starts the backoff below. A night that ends on a challenge sets the SSO source to CHALLENGED, and nothing more is sent to SSO until Royce reads the log and runs `python -m scripts.clear_sso_challenge`. A change in SSO's markup would also read as a challenge. That errs toward AGC.

## Backoff on a challenge, no redirect

A challenged request is sent again after 6, 10, 30, 60, 120, 240 and 360 seconds, eight sends over about 14 minutes (`SSO_CHALLENGE_BACKOFF_SECONDS`), with the same user agent. Royce ruled this on 8 November 2026, reversing the earlier rule that any resend after a challenge got around the firewall.

A PDF still challenged after the last wait goes to the end of the list, and the stage moves on to the next PDF. When the list ends it goes back to those PDFs with the same backoff. Three PDFs in a row that stay challenged end the night, with a PDF that gets any other answer resetting the count. A robots file or listing page that stays challenged ends the night too, because the PDF list depends on them. The window check runs before every send, so a backoff that runs past 06:55 sends nothing more.

A failure (404, 5xx or a transport error) is not resent within the night. The SSO gateway never calls `send_with_retry`. Redirects are not followed (`allow_redirects=False`), so a 3xx is stored as it came and read as a challenge.

## Request order

The SSO stage asks for, in order:

1. `robots.txt`.
2. Listing page 0. If it fails, the night ends.
3. Listing pages 1 onward, up to the page count page 0 prints. A failed page is skipped.
4. The Act PDFs. A PDF whose stored copy already carries the listing's version stamp is not requested. Acts never stored come first, then the Acts whose newest stored copy is oldest.

The stored copy may be an Internet Archive capture, since the stage reads the stored PDFs of both sources. The archive harvest therefore runs before the first SSO night, so SSO serves only the Acts whose version stamp changed after the archive's newest capture (Royce, 7 November 2026).

Three failures in a row halt the run. So does a database past 10 GB, checked before the first request and after each answer. A night that reaches 06:55 with work left ends as SUCCEEDED, and the next night carries on. Subsidiary legislation is not requested yet.
