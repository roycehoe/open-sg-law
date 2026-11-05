# Data loss register

Every step that changes or drops source content between the raw bodies in `source_response` and any derived table, with its cost and the reason for it. Any change that cleans data adds or updates a row here in the same change. Cleaning means dropping, merging, deduplicating, trimming, normalising, overriding, reclassifying or deleting anything the source holds. Update a row in the same change that moves its figure.

## Principle

The raw bodies in `source_response` are stored exactly as received and are never rewritten or deleted. Everything else is derived and can be rebuilt from them: listings, legislation rows, versions, sections. A step in this register therefore loses nothing for good. It loses it from the derived layer, and the parser can bring it back from the raw body.

Where the record prints something, store what it prints and put our reading in a separate column.

## How to read the register

- **Cost** is the count the records give. "Not measured" means no file holds a count.
- **Reversible from the raw body** is "yes" when running the parser again on the stored body regains the content.
- **Decided** gives the date and who decided, as the records show. "Project" means a commit or doc with no recorded user decision.

## Register

| What changes or is dropped | Where in code | Why | Cost | Reversible from the raw body | Decided |
|---|---|---|---|---|---|
| Reports the act-links plan skipped because their title names no bill (`skipped_reports`) get no `bill_report` row. | `services/hansard_links.py::build_hansard_link_plan` | The plan finds a bill by the title of its reports, so a report with no bill in its title has no bill to belong to. | counted by the first dry run | yes, from the act-links plan and the report export, kept outside git | plan step 30, 5 November 2026 |
| History entries the plan left unlinked keep `bill_id` NULL. The dry run logs them by kind and decade of first reading. | `services/hansard_links.py::build_hansard_link_plan` | The plan links an entry only when a rule finds one bill for it. An entry no rule matches stays without a bill rather than take a guess. | counted by the first dry run | yes, from the act-links plan and the report export, kept outside git | plan step 30, 5 November 2026 |
| The Hansard row id is kept on `bill_report.hansard_row_id` for tracing only. It is neither public nor stable, and the site must link by `openhansard_url`. | `services/hansard_links.py::build_hansard_link_plan` | The row id belongs to the Hansard database and can change when that database is rebuilt. The printed report id gives the stable link. | counted by the first dry run | yes, from the act-links plan and the report export, kept outside git | plan step 30, 5 November 2026 |
| Links stop at the Legislative History in the plan's copies. An Act passed after them has no links until the Hansard project ships a new plan. | `services/hansard_links.py::build_hansard_link_plan` | The plan is built from the Legislative History text the Hansard project stored, and this repo fetches nothing from Hansard. | counted by the first dry run | yes, from the act-links plan and the report export, kept outside git | plan step 30, 5 November 2026 |
| The plan's `defects` per entry are logged, not stored. | `services/hansard_links.py::build_hansard_link_plan` | The defects describe how the source text was misprinted. No table column needs them, and the dry run counts them by kind (G4.1). | counted by the first dry run | yes, from the act-links plan and the report export, kept outside git | plan step 30, 5 November 2026 |
| The plan's `unfetched_sso_codes` and `unparsed_entries` are logged, not stored. | `services/hansard_links.py::build_hansard_link_plan` | An Act the plan could not fetch, and an entry it could not parse, have no row to attach a link to, so the dry run lists them instead. | counted by the first dry run | yes, from the act-links plan and the report export, kept outside git | plan step 30, 5 November 2026 |
| A line keeps its text and top position only, so the indentation of subsections and paragraphs is lost. | `utils/pdf_text.py::get_pdf_pages` | The section parser needs line breaks and bold, not x positions, and the site shows plain text. | every version | yes, from the stored PDF | plan step 32, 5 November 2026 |
| A line keeps only whether its characters are bold, and its bold prefix. Font size, italics and font name are dropped. | `utils/pdf_text.py::get_pdf_pages` | Bold is the only weight the parser needs, to tell a section number and a heading from running text. | every version | yes, from the stored PDF | plan step 32, 5 November 2026 |
| Images are counted per page and never read or stored (brief decision 6). | `utils/pdf_text.py::get_pdf_pages` | The text tables store no image, and a page with an image is flagged for a link to the SSO page (commit 56). | every version | yes, from the stored PDF | plan step 32, 5 November 2026 |
| Running headers, footers and page numbers are marked `is_margin`. The section parser drops them, and only the version date reader reads them. | `utils/pdf_text.py::get_pdf_pages` | A margin line is not part of any section, and a repeated header would otherwise land in the section text. | every version | yes, from the stored PDF | plan step 32, 5 November 2026 |
| Hyphenation at line ends is kept as printed: no line is joined to the next. | `utils/pdf_text.py::get_pdf_pages` | Joining lines would change printed words, and the register keeps what the record prints. | every version | yes, from the stored PDF | plan step 32, 5 November 2026 |
| A stored Act PDF whose code has no `legislation` row, or that does not read as a PDF, gets no version. The dry run lists each with its reason. | `populate/legislation_versions.py::get_legislation_version_write` | A version must hang on an Act the listings name. | counted by the first dry run | yes, the raw row stays | plan step 37, 5 November 2026 |
