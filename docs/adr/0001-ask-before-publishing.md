# 0001. Ask before publishing

Status: accepted, 5 November 2026. Royce ruled it while the project was being scoped ("We ask this time"). See decision 4 of `plans/open-sg-law-brief.md`.

Context. The sister project, openhansard.sg, publishes Hansard although Parliament's terms (clause 6) need written permission. On 2 November 2026 Royce ruled for that project not to ask and to act on a takedown request if one comes. This project's sources have different terms. SSO (clause 13) and eGazette (clause 11) already grant a standing permission to reproduce legislation, on conditions. The Judiciary's terms (section 6) bar only commercial reuse of judgments and say nothing about non-commercial reuse. A notice quoted by Oxford University Press describes Singapore decisions as © SAL under an exclusive licence from the Government, and we cannot tell from the outside whether that covers the text eLitigation serves.

Decision. We write to the Supreme Court before publishing any judgment, and to AGC for bulk access to SSO. Judgments are fetched and stored privately while we wait, and nothing about them is published until the Supreme Court says yes in writing. Legislation is published under SSO clause 13 and eGazette clause 11, which need no letter. We meet their conditions and still write to AGC to confirm.

Why. A takedown after launch costs more here than for the Hansard. SAL holds a licence with revenue behind it, and lawyers, the main audience, would lose a source they had started to rely on. The Judiciary's terms leave room for a yes, so asking is cheap and the answer settles the SAL question. The asymmetry with the Hansard project is deliberate. The two projects face different owners and different terms.

Consequences.

- Judgments ship in Release B, gated on the reply. Release A (legislation and Hansard links) waits on no one.
- The letters go out on day 0, before code, because the reply is the longest task on the critical path.
- A refusal binds us. Judgments then stay private, and the backlog records the refusal.
- Every page of legislation carries the clause 13 notices, and our own accuracy check runs on every sync.

Alternatives.

- Wait for a takedown. Rejected for the reasons above.
- Publish nothing until every owner replies. Rejected, because SSO and eGazette already give a standing permission and holding legislation back gains nothing.
