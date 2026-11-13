# Local manual engineering review

Updated 13 November 2026 at the user's request. This supersedes the profile and
passphrase requirement for the desktop review form.

## Using the form

1. Open the current project's Requirements review window.
2. Inspect the exact requirements package, evidence and outstanding issues.
3. Enter your reviewer name and substantive review comments.
4. If a permitted deferral is appropriate, explicitly enter its rationale,
   responsible owner and downstream gate. A deferral does not authorize physical work.
5. Choose Approve Requirements, Return for Changes or Reject Package.
6. A valid approval records the review decision. Stage completion remains a
   separate action and requires the core's remaining criteria and dependencies.

The form no longer loads reviewer profiles or asks for credentials. Names and
comments are mandatory. It labels new decisions **Manually declared human review**.
The default deferral gate now refers to Stage 3 feasibility, before detailed design;
Stage 6 is simulation, not hardware testing.

## Meaning and limits

A manually entered name is attribution, not authentication or proof of qualifications.
New payloads carry `review_mode=MANUALLY_DECLARED`, `identity_authenticated=false`
and `signature_kind=CONTENT_DIGEST_NOT_IDENTITY_PROOF`. The record digest must not
be described as an authenticated signature, safety certification or manufacturing
approval. Existing engineering evaluation remains independent and NOT_EVALUATED
where no actual validation evidence is available.

Local desktop submissions call `StudioService.reviews.record_manual_decision`.
Manual decisions are not added to MCP/CLI's decision tool schema. The existing
credential-based API remains compatible for legacy integrations and historical
data. Hiding a method from MCP is a workflow convention, not an OS security boundary:
software running as the same local user can invoke Python or desktop APIs. Without
authentication this system cannot prove that a human, rather than an agent, supplied
the name or decision. No automatic review of the actual SV-1000 project was performed.

## Checks and history

- The shared core still checks draft status, active stage attempt, requirements
  digest, specification hash, critical conflict dispositions and safety blockers.
- Desktop submissions include the document and evidence hashes displayed to the
  reviewer. A changed package is rejected rather than silently reviewing newer bytes.
- Mandatory safety blockers need exact matching safety-item deferrals with rationale,
  owner, scope and downstream gate. A partial phrase cannot match every blocker.
- Identified self-review is refused, but a typed name is not strong identity proof.
- Decisions and retry receipts remain in the existing append-only review tables.
  Later edits to reviewed files make effective review stale, preserving history.
- The final insert rechecks package context under the SQLite writer lock and
  rechecks retry receipts, avoiding duplicate or outdated decisions during races.

No schema migration or live-record rewrite is needed. The existing reviewer foreign
key is retained using an internal attribution row with no password, email or reviewer
authorization roles. These rows are excluded from the legacy profile picker API.
They do not require users to create an account. Existing reviewer records are retained;
new databases no longer seed default profiles or credentials.

## Verification

69 focused review, lifecycle, record and cross-client tests passed. After the final
transaction guard, all 18 review tests passed again. Coverage includes desktop
submission with zero profiles, missing name/comments, retry replay, rejection,
return-for-changes, blocked safety approval, exact deferrals, stale documents,
wrong attempts, identified self-review, and rejection of the manual payload by the
credential-based MCP schema. Fixtures explicitly provision any legacy test credentials.

The TypeScript/Vite production asset build passed. The running localhost backend
was restarted and a read-only validation probe confirmed it expects `reviewer_name`
and reviewed-document hashes, not a reviewer secret. No live approval was submitted.
Browser visual verification and a full native Windows installation test were not
performed for this change.
