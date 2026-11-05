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
