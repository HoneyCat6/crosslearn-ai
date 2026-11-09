# M2 implementation contract

Status: local M2 implemented with FastAPI and PostgreSQL. Twelve backend tests and seven M1 tests pass. See [M2 documentation](M2.md) for the runnable workflow and remaining browser/live-model verification limits.

## Implementation order

1. Database migrations and synthetic fixtures for two schools, teachers, classes and pseudonymous learners.
2. Authentication, server-managed sessions, CSRF protection, role permissions and school isolation on every resource lookup.
3. Versioned content approval, puzzle assignments and session-scoped pupil access. Exclude answer keys and explanation text from baseline responses.
4. Server-owned stage transitions and deterministic scoring. Reject out-of-order submissions; idempotent response submission must reject changed payloads under reused keys. Ignore client-supplied scores.
5. Teacher dashboard, learner timeline, assignment controls, content review and permission-checked CSV export.
6. Allowlisted evidence tools and a provider-neutral model adapter. Validate recommendation structure, evidence references and permissible status; use a rule-based fallback for absent provider, timeouts or invalid outputs. Persist draft/review versions and audit events. Never send pupil free text as agent instructions.
7. Consent state, learner deletion, scoped audit history and retention documentation.

## Acceptance gates

- School A cannot read, change, analyze, export or delete School B resources, including guessed nested IDs.
- Teachers cannot acquire researcher/admin privileges through request parameters.
- Pupil session credentials cannot access teacher APIs or another session.
- Correctness comes exclusively from server-held item versions and keys.
- Repeated and conflicting submissions cannot inflate results.
- No correctness or target explanations leak during baseline.
- AI outage and invalid output preserve assessment data and produce reviewable fallback suggestions.
- Recommendations remain drafts until an authorized teacher reviews them.
- Deletion removes linked responses and learner-associated advice; audit metadata retains no identifying or educational payload.
- Integration tests exercise real HTTP requests and a database, alongside the existing M1 suite.

## Environment findings

Python 3.12.2 is at `P:/Python/python.exe`; dependencies are installed in `api/.venv`. PostgreSQL 18.6 runs on loopback port 5432. The user configured a dedicated CrossLearn database/login; credentials remain in `api/.env`. No SQLite substitution was made. M1 remains independently runnable.

## External configuration

Keep provider credentials exclusively on the backend. Start with no model configured and exercise the deterministic fallback. A real provider may be configured later without blocking normal assessment. Production authentication and hosting configuration must be documented separately from local synthetic demo access.
