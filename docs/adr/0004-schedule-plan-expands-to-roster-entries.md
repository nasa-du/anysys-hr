# Schedule plans expand into per-employee daily roster entries

Attendance scheduling uses a monthly schedule plan — company, month, scope (whole company / department / position / employee), daily shift pattern, and optional rule overrides — as a reusable template. Saving a plan validates scope conflicts, resolves all enabled plans for that company and month by specificity (employee > position > department > whole company), and expands the result into one roster entry per employee per day. Each roster entry records whether the day is work or rest, and each work day carries one or more shifts with snapshots of the shift's name, start/end time, cross-day flag, break segment, and rest deduction. Manual exceptions are roster entries with `source = manual`; expansion never touches them, so they always win over the plan-derived result. Attendance calculation reads only roster entries and never re-resolves plans, while copy-to-next-month copies the plan definition and re-expands it for the target month.

We chose expansion over calculating directly from plans because per-day manual changes, overlapping plans with different scopes, and historical stability would otherwise require re-deriving exceptions and precedence on every calculation. Storing only manual entries without a plan was rejected because it would lose the reusable monthly pattern and the copy-to-next-month workflow. Versioning plans was rejected because snapshotting the shift fields into each roster entry already gives history the stability it needs, without a second version chain. The cost is duplicated schedule data and an explicit re-expansion step when a plan or its people change; we accept that for a stable, auditable calculation input and simple per-day temporary changes.

## Consequences

- Plan edits, personnel sync, archive, and copy all trigger a company-plus-month re-expansion that preserves manual exceptions.
- Confirmed and locked months never change automatically; re-expansion is limited to draft and calculated months.
- Because the basic-management module has no transfer history, re-expansion uses current department and position for the whole month; manual exceptions are the way to preserve historical intent.
- Shift templates remain editable, but existing roster entries keep their snapshots and only draft/calculated months pick up new values on the next expansion.
