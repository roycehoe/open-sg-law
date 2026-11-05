# 0004. PDF as the legislation text source

Status: accepted, 5 November 2026. Royce ruled it in round 1 of the plan questions (ruling 3).

Context. Singapore Statutes Online (SSO) serves each Act as HTML, paged by Part, and as one PDF. The browse listing puts a version stamp in each PDF link. The Internet Archive holds the same PDFs: 523 Act PDFs, 149 MB in all. SSO allows automated requests only from 03:00 to 07:00 SGT, and at one request a minute that is about 235 requests a night.

Decision. Legislation text comes from the consolidated PDF, for archive and SSO copies alike, through one parser. The PDF text library is `pdfplumber` (MIT, built on `pdfminer.six`, MIT). It gives a font name for each character, so bold is "Bold" in the font name, and it lists the images on each page. PyMuPDF is AGPL and was ruled out. `pypdfium2` gives no font weight.

Section links to SSO are built from the printed section number as `#pr<number>-`, such as `#pr9A-`. This is a guess at SSO's anchors. A wrong anchor opens the top of the SSO page. Once SSO serves, check a sample of anchors.

A raw body is stored as text when it decodes strictly with the charset its `Content-Type` names, or UTF-8 when none is named, and holds no NUL byte. Otherwise it is stored as bytes. A PDF is always bytes. The exact bytes and their SHA-256 can always be rebuilt.

Why. The Acts take about 3 SSO nights as PDFs, against about 7 as HTML, where each Act needs the page plus batched `?ProvIds=` requests. The archive copies are PDFs already, so one parser reads both sources.

Consequences.

- The parse is harder than HTML. A PDF has no section markup, so the parser reads numbers and headings from the text and from font weight.
- The anchors are guessed until a sample is checked against SSO.
- PDF layout is lost, such as indentation and tables. [docs/data-loss-register.md](../data-loss-register.md) records each step that drops it.
- A scanned PDF has no text layer, and this project does no OCR. All 523 archive Act PDFs gave text.

Alternatives.

- Fetch the HTML pages. Rejected for the extra requests, and because archive copies would still need a second parser for archive HTML.
- Read the PDFs with PyMuPDF. Rejected for its AGPL licence, which does not sit with this project's MIT code.
