# 0003. Hansard links by openhansard.sg report id

Status: accepted, 5 November 2026. Royce ruled it while the project was being scoped. See decision 17 of `plans/open-sg-law-brief.md`.

Context. Every Act should link to the Hansard debates on its bills, because Interpretation Act s 9A lets a court read them. The links already exist. The bill-debate-linking job in handsard-scraper matched 523 Acts and 9,905 legislative history entries to Hansard reports, 5,103 of them to a debate, and stored them as `bill`, `billreport`, `act` and `acthistoryentry` rows in the Hansard database. This project needs those links but is a separate repo with its own deploy.

Decision. This database stores the openhansard.sg report id and URL for each linked debate, copied from the act-links plan. It never connects to the Hansard database and never queries it at run time. A refresh of the links is a planned copy from a new act-links plan, logged like any other write.

Why. A shared database would tie the two deploys together. A migration, an outage or a credential change on one side would break the other, and openhansard.sg's terms position (it waits for a takedown) would become this project's too. A report id is the primary key of the Hansard report row, and the writes there rebuild speech rows, not report ids. Copying a few thousand ids costs little and keeps the boundary clean.

Consequences.

- The links here can lag the Hansard database until the next copy. Each copy records the act-links plan it came from.
- If openhansard.sg takes a report down, our link to it breaks. The link check catches that, and the Act page falls back to the bill title and sitting date.
- This project publishes no Hansard text, only links to openhansard.sg pages.

Alternatives.

- Share the Hansard database, read only. Rejected for the coupling above.
- Rebuild the links here from SSO and Hansard data. Rejected because it repeats finished work, and the Hansard text it would need is not this project's to hold.
