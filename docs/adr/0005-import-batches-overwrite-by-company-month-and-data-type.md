# Import batches overwrite by company, month, and data type

Attendance imports are month-scoped batches: each batch belongs to one company, one attendance month, and one data type (punch, trip, overtime, leave), and committing a new batch supersedes the previous active batch for that scope rather than merging rows. Parsing is server-side and two-phase: preview persists normalized rows into the final tables with a `preview` batch status, and commit only flips the batch to `committed` in a transaction that supersedes the old batch and marks the attendance month stale. Cross-month OA requests must be imported separately for each affected month because auto-splitting them would break the single-active-batch invariant.

We chose this over row-level upserts or a separate staging schema because it makes replacement auditable and keeps calculation reading exactly one active batch per type. The cost is duplicated OA requests across month batches and a 24-hour preview lifetime; we accept that for a simple, deterministic overwrite.

## Consequences

- Only one committed batch exists per company + month + data type; a partial unique index enforces it.
- Preview rows live in the final tables but are invisible to calculation until commit.
- Original file bytes are not retained; file metadata and per-row raw payloads provide traceability.
- Superseded batches keep normalized rows for audit but drop `raw_row` and error detail after 90 days; revoked and discarded batches lose their rows immediately.
