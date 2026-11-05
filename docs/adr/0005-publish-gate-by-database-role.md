# 0005. Publish gate by database role

Status: accepted, 5 November 2026. Royce ruled it in round 1 of the plan questions (ruling 6).

Context. Fetching a source and publishing it need separate legal bases. The brief lists, for each source, whether it may be fetched and whether it may be published. Judgments, for one, are fetched now and published only after the Supreme Court agrees in writing. SSO's permission (clause 13) and eGazette's (clause 11) can be revoked at any time. A page of the site must never show text from a source that is not cleared.

Decision. The site reads through the `NOLOGIN` role `open_sg_law_site`. The role holds SELECT only on tables whose sources are all published. The `source` table records each source's publish status, the reason for the last change and its time.

`scripts/publish_source.py` is the only path that changes a status. It grants or revokes in the same transaction as the status change. Only migrations and that script issue grants. The raw table `source_response` and the `harvest_run` table are never granted.

A table that draws from several sources is granted only while every one of them is published. Withdrawing SSO therefore also withdraws the archive copies of SSO text held in the same tables.

The migration creates the role only when `pg_roles` has no row for it. One Postgres server holds both `open_sg_law` and `open_sg_law_test`, and a role belongs to the whole server, so a plain `CREATE ROLE` would fail on the second database. The migration's downgrade revokes the grants and keeps the role, for the same reason.

Why. A site bug cannot read a table its role has no grant on. The gate then does not depend on every query in the site being right.

Consequences.

- A rule per court for judgments needs a later change. The gate works per table, so it cannot open the Supreme Court's judgments and keep the State Courts' closed (ruling 13).
- The production plan must carry the `source` rows over, including the SSO access state.
- A test compares the site role's grants with the published sources.

Alternatives.

- A published flag on each row, checked by the site. Rejected, since one missed `where` in the site would publish a closed row.
- A row-level rule by court from the first day. Not built, because no site reads the tables yet and no split answer has arrived.
