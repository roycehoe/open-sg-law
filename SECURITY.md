# Security policy

## Report a vulnerability

Use GitHub's private form: [report a vulnerability](https://github.com/roycehoe/open-sg-law/security/advisories/new). Do not open a public issue for a vulnerability.

Say which file or script is affected, the steps to reproduce it, and what an attacker could do with it.

Royce Hoe maintains this repository and reads each report himself.

## Scope

In scope:

- The code in this repository, including the write scripts in `scripts/` and the guards that keep them off other databases.
- The publish gate: the database role `open_sg_law_site` and the grants that decide which tables the site can read ([ADR 0005](docs/adr/0005-publish-gate-by-database-role.md)).

Out of scope:

- A wrong or missing piece of legislation or a judgment. Open an issue for that, as [CONTRIBUTING.md](CONTRIBUTING.md) says.
- Singapore Statutes Online, eGazette, eLitigation, the Internet Archive, and the services this project runs on. Report those to their operators.
- The website that reads this database, when it exists. It will have its own policy.
