# Test fixtures

Every fixture is a real body that a source sent, trimmed by removing whole rows or pages. Nothing inside what is kept was changed. Source paths are in the handsard-scraper repo, under `plans/bill-debate-linking/`.

| Fixture | Source | Archive stamp | Kept |
|---|---|---|---|
| `sso_listing/browse-all-p1-20240716-trimmed.html` | `lh/browse-all-p1-20240716.html` | 20240716234218 | The whole page, with the listing table's header row and its first three data rows (AA2004, ACRAA2004, ASA2007). The other 497 data rows were removed. |
| `sso_listing/browse-all-p2-20240719-trimmed.html` | `lh/browse-all-p2-20240719.html` | 20240719042908 | The whole page, with the listing table's header row and its first three data rows (TCA2005, TA1967, UPA1967). The other 20 data rows were removed. |
| `archive/temporarily-offline-20261104.html` | `pages/judge/cdx-acts-10-1988.json` | None: the Internet Archive's answer of 4 November 2026 to a CDX query | The whole answer, the archive's "Temporarily Offline" page, renamed for what it holds. |
| `cdx/cdx-cltpa-pdf-trimmed.json` | `pages/judge/cdx-cltpa-pdf.json` | None: a CDX answer with the default fields | The header row and the first four capture rows, all `/Historical/` versions of CLTPA1955. The other rows were removed, and the comma after the last kept row became the closing bracket. |
| `cdx/cdx-bills-browse-trimmed.json` | `pages/cdx-bills-browse.json` | None: a CDX answer with the default fields | The header row and the first three capture rows, all Bills-Supp browse pages. The other rows were removed, and the comma after the last kept row became the closing bracket. |

`tests/test_archive_capture.py` also builds a few `CdxCapture` values in code. Their original URLs and timestamps are copied from rows of `cdx-2025-2026/cdx.json` (AA1906, AA2001 and AA2004). That file has no digest column, so those values carry an empty digest.
