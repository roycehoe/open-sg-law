# openhansard.sg

openhansard.sg is the Hansard site Royce runs. This repo does not fetch anything from it. It reads two files that Royce makes from the Hansard database and keeps outside git, and links each Act to the debates on its bills (ADR 0003).

## What the import reads

- The act-links plan Royce shipped to Hansard production.
- The report export, made from the replica with the query below.

Neither file is kept in git. The import logs each file's SHA-256, so a run can be matched to the files it read.

## The report export query

Royce runs this on the Hansard replica only, read only. `report-ids.txt` holds the Hansard row ids of every report the plan links to a bill.

```bash
jq -r '[.bills[].report_ids[]] | unique | join(",")' act-links-plan.json > report-ids.txt
PGOPTIONS='-c default_transaction_read_only=on' psql "$HANSARD_REPLICA_URL" -At \
  -v ids="$(cat report-ids.txt)" -f report-export.sql > report-export.json
```

`report-export.sql`:

```sql
SELECT json_build_object(
  'rows',
  coalesce(
    json_agg(
      json_build_object(
        'id', report.id,
        'report_id', report.report_id,
        'report_type', report.report_type,
        'sitting_date', report.sitting_date::date,
        'title', report.title
      )
      ORDER BY report.id
    ),
    '[]'::json
  )
)
FROM report
WHERE report.id = ANY (string_to_array(:'ids', ',')::int[]);
```

The export schema is `schemas/hansard_report_export.py`. `report_type` is the Hansard database's own string.

## The report URL

A report's address is `https://openhansard.sg/reports/` plus its SPRS id with the trailing `#` removed, percent-encoded with no safe characters. That is how the site's `get_report_slug` builds it (`hansard/api/utils/report_slug.py:4`), and `utils/openhansard_url.py` does the same. An inner `#` becomes `%23`.

The Hansard row id is kept in `bill_report.hansard_row_id` for tracing only. It is not public and not stable.

The site removed ten duplicate reports and sends their links to the kept copy. This repo does not remap them.

## What the follow-up plan should store

The first dry run here, on 8 November 2026, gave 523 Acts, 9,905 entries, 2,811 bills, 5,827 bill reports and 5,107 links. ADR 0003 says 5,103 entries link to a debate, and that figure is four short.

## Tables

The import rewrites `bill`, `bill_report` and `act_history_entry`. It only reads `legislation`, which is built from the SSO listings.
