# Attendance Management

Attendance Management (考勤管理) covers shifts, scheduling, imports, calculation
results, manual adjustments, month closing, and CSV exports. It builds on Basic
Management: companies, departments, positions, and employees are read-only
sources, and every attendance table is attendance-owned.

- Full field-level contract and test matrix:
  [`docs/specs/attendance-management.md`](./specs/attendance-management.md)
- Domain vocabulary: [`GLOSSARY.md`](../GLOSSARY.md)
- Architecture decisions: [`docs/adr/`](./adr/)

The UI is Simplified Chinese only (ADR-0002). Every logged-in user has full
access; this effort introduces no RBAC and no self-service H5. Attendance never
writes payroll: the payroll read contract is query + CSV export only.

## Pages

Scheme A is authoritative. The sidebar's 「考勤管理」 group has five entries:

| Page | Path | Purpose |
|---|---|---|
| 排班工作台 | `/attendance/schedule` | Plans, merged calendar, day sheet, employee calendar, manual exceptions, personnel sync, copy next month |
| 导入中心 | `/attendance/imports` | Punch/OA upload or paste, mapping, preview, commit, batch history, discard/revoke |
| 考勤结果 | `/attendance/results` | Day results, anomaly filter, four-way day drawer, adjustments, month summary, calculation runs, snapshots, exports, month closing |
| 规则与节假日 | `/attendance/rules` | Company default rules, plan overrides, holiday calendar, copy previous year |
| 班次 | `/attendance/shifts` | Shift CRUD, validation, deactivate/delete reference blockers |

The company switcher is shared with Basic Management. The attendance month
defaults to the current `Asia/Shanghai` month and persists in `localStorage`
under `attendance.month`.

## API

All routes are under `/api/v1/attendance` and require the existing JWT bearer
token. Collection routes end with `/`; item and action routes do not. Month
parameters are `YYYY-MM`; dates are `YYYY-MM-DD`.

| Service | Endpoints | Scope |
|---|---|---|
| `AttendanceShiftsService` | `GET/POST /shifts/`, `GET/PATCH/DELETE /shifts/{shift_id}` | Company-level shift templates |
| `AttendanceSchedulePlansService` | `GET/POST /schedule-plans/`, `POST /schedule-plans/preview`, `GET/PATCH/DELETE /schedule-plans/{plan_id}`, expand/expand-preview/archive/unarchive/copy-preview/copy, `GET/PUT /schedule-plans/{plan_id}/rule-overrides` | Plans expand to roster entries |
| `AttendanceRosterService` | `GET /roster/calendar`, `/roster/day`, `/roster/month`, `/roster/employees`, `/roster/sync-preview`, `POST /roster/sync`; `GET/POST /roster-entries/`, `GET/PATCH/DELETE /roster-entries/{entry_id}`, `POST /roster-entries/batch` | Employee-day schedule, manual exceptions |
| `AttendanceImportsService` | `POST /imports/preview`, `POST /imports/{batch_id}/commit`, `discard`, `revoke`; `GET /imports/`, `/imports/{batch_id}`, `/errors`, `/records`, `/mapping-template` | Four data types: punch, trip, ot, leave |
| `AttendanceResultsService` | `GET /results/days/`, `/results/days/{employee_id}/{work_date}`, `/results/summary/`, `/results/calendar` | Day/shift results, month summaries |
| `AttendanceAdjustmentsService` | `GET/POST /results/adjustments/`, `GET /results/adjustments/{adjustment_id}` | Versioned manual adjustment |
| `AttendanceMonthsService` | `GET /months/`, `/months/{month}`, calculate/confirm/unconfirm/lock/unlock, `/calc-runs/`, `/snapshots/`, `GET /calc-runs/{id}`, `/snapshots/{id}` | Month state machine, snapshots |
| `AttendanceRulesService` | `GET/PUT /rules/` | Company default rules |
| `AttendanceHolidaysService` | `GET/POST /holidays/`, `GET/PATCH/DELETE /holidays/{holiday_id}`, `POST /holidays/copy-year/preview`, `copy-year` | Holiday calendar |
| `AttendanceExportsService` | `GET /months/{month}/exports/payroll.csv`, `detail.csv` | 14-column payroll CSV + detail CSV |

Conventions:

- List responses are `{"data": [...], "count": int}`; `skip` ≥ 0, `limit`
  1–500 (default 100). Sorting is fixed.
- Decimals serialize as strings; minutes and counts are integers; enums are
  lowercase snake_case. Writes use `extra="forbid"`.
- An absent `attendance_month` row is returned as a synthetic draft
  (`exists = false`, `status = "draft"`, `is_stale = true`, zero counts); `GET`
  never writes.
- Cross-company **references** return 409 `cross_company`; cross-company
  **resource-id access** returns 404 `not_found`.
- Import commit, plan/roster edits, and rule/holiday changes only set
  `is_stale = true`; calculation is always explicit.
- Locked months are read-only everywhere; unlock requires a reason and returns
  the month to `calculated` with `is_stale = true`.
- The generated client is authoritative: run `bash scripts/generate-client.sh`
  and commit `frontend/openapi.json` plus `frontend/src/client`.

## Error model

| HTTP | Shape | Use |
|---|---|---|
| 422 | `{"detail": [{"loc": [...], "msg": "中文", "type": "..."}]}` | Request shape, type, range, enum, regex, immutable fields |
| 404 | `{"detail": {"code": "not_found", "message": "中文"}}` | Path/query ID missing; cross-company resource-id access |
| 409 | `{"detail": {"code", "message", "field_errors", "blockers", "blocker_count"}}` | Business-rule conflicts |
| 413 | `ErrorResponse` | Upload over 10 MB |
| 415 | `ErrorResponse` | Unsupported file type |

Attendance business codes:

| Group | Codes |
|---|---|
| Common | `not_found`, `cross_company`, `invalid_reference`, `inactive_reference`, `referenced`, `duplicate_code` |
| Shift / plan / roster | `deactivate_blocked`, `activation_blocked`, `invalid_time_range`, `invalid_scope`, `schedule_conflict`, `schedule_expansion_blocked`, `plan_archived`, `employee_out_of_range`, `roster_entry_not_manual`, `roster_batch_invalid` |
| Month / calculation / adjustment | `month_confirmed`, `month_locked`, `month_not_calculated`, `month_stale`, `invalid_month_transition`, `calc_in_progress`, `calc_run_failed`, `adjustment_conflict` |
| Holiday | `duplicate_holiday`, `holiday_conflict` |
| Import | `import_parse_failed`, `missing_required_column`, `sheet_required`, `preview_expired`, `import_commit_conflict`, `no_valid_rows`, `batch_not_preview`, `batch_not_revocable`, `file_too_large`, `unsupported_file_type` |

Row-level import problems (`unknown_employee`, `out_of_employment`,
`invalid_punch`, `duplicate_punch`, `duplicate_name`, `amount_mismatch`, …) are
stored in `import_batch_error` and rendered as table data; they are not
promoted to the HTTP error envelope.

## Development seed

The seed lives in `backend/app/seed_dev.py` and is guarded by
`FASTAPI_ENV=development`. It is never called by `prestart.sh` and must not run
in production.

From the `backend` directory, after migrations and initial data exist:

```bash
uv run python -m app.seed_dev
```

With the Compose stack running, from the repository root:

```bash
docker compose exec backend python -m app.seed_dev
```

The script needs the first superuser as the import operator; run
`backend/scripts/prestart.sh` (which runs `app/initial_data.py`) first.

The dataset is generated deterministically (fixed random seed). `main()` seeds
`FULL_SCALE`: `C1` 华信建设 (240 employees), `C2` 云启科技 (420), and `C3`
明德考勤演示 (520). The test suite uses `seed_dev.SMALL_SCALE` against the same
code paths.

What it creates for `C3` 「明德考勤演示」:

- Departments `D1`–`D13` (生产部, 财务部, 技术部, 行政部, three workshops,
  质检组, 仓储组, two R&D groups, 后勤组, 人力资源部) and positions
  `P1 生产操作工` through `P12 人力资源专员`.
- Employees `E3001`–`E3520` with unique names inside the company (OA imports
  match by name) and employment windows that exercise expansion: one
  resignation before August, one on 2026-09-10, a hire on 2026-09-15, and a
  hire on 2026-10-08.
- Seven golden-case shifts (`ADM`, `TEC`, `YL`, `EARLY`, `MID`, `NIGHT`,
  `DAWN`), the company default rule (14 fields), and holidays for 2026-09/10
  (09-25 中秋节, 09-27 调休上班, 10-01…10-07 国庆节, 10-10 调休上班).
- Four plans for **each** of 2026-08, 2026-09, and 2026-10 through the real
  expansion path: 行政班 (`all`), 财务技术班 (`dept` 财务部), 园林班
  (`position` 园林工 with `ot_threshold_min = 15`), and an employee-scope
  night-shift plan (`E3215 金佳丹`, night shifts on 08-27, 09-30, 10-29;
  09-27/10-10 adjusted-workday overrides).
- Two manual exceptions after expansion: `E3001 吕倩` rests on 2026-09-10;
  `E3002 邓丹静` works 2026-09-11 with `EARLY` + `MID`.
- Twelve committed import batches (punch/trip/OT/leave × three months) through
  the real preview/commit path. Generated files are named
  `punch-YYYY-MM.csv`, `oa-trip-YYYY-MM.csv`, `oa-overtime-YYYY-MM.csv`, and
  `oa-leave-YYYY-MM.csv`.
- One successful calculation per month through `calculate_month`, leaving all
  three months `calculated` with day results and month summaries. Snapshots,
  confirmations, and locks are deliberately left to the demo.

Idempotency keys: company `company_code`; department `dept_code`; position
`position_code`; employee `employee_no`; shift `shift_code`; rule `company_id`;
holiday `(company_id, date)`; plan `(company_id, month, plan_name)`; roster
entry `(employee_id, work_date)`; committed batch
`(company_id, data_type, month, committed)`; calculation `(month, successful
calc_run)`. The script only inserts missing rows, never updates or deletes user
edits, and running it twice leaves counts stable. A month is re-expanded only
when one of its plans was recreated or it has no roster yet. Attendance seed
rows never touch `C1`–`C2`.

## Migrations and backups

The attendance chain adds four migrations after `d66acc907e93`:

| Order | Revision file | Tables |
|---|---|---|
| 1 | `attendance_core` | `shift`, `holiday`, `attendance_rule`, `attendance_month`, `calc_run`, `attendance_month_snapshot` |
| 2 | `attendance_scheduling` | `schedule_plan`, `plan_scope`, `plan_day`, `plan_rule_override`, `roster_entry`, `roster_entry_shift` |
| 3 | `attendance_imports` | `import_batch`, `import_batch_error`, `import_mapping_template`, `punch_record`, `oa_trip`, `oa_overtime`, `oa_overtime_day`, `oa_leave` |
| 4 | `attendance_results` | `attendance_day_result`, `attendance_day_shift_result`, `attendance_month_summary`, `attendance_result_adjustment` |

24 tables total. Migrations insert no rows.

From the `backend` directory:

```bash
uv run alembic upgrade head
uv run alembic downgrade base   # development and test databases only
uv run alembic upgrade head
```

Each attendance migration supports an individual `upgrade → downgrade →
upgrade` round trip; CI runs those plus the full chain against a throwaway
database. Before applying or rolling back a shared database, take a backup:

```bash
pg_dump --format=custom --no-owner \
  --dbname="$DATABASE_URL" --file="anysys-$(date +%Y%m%d-%H%M).dump"
```

For a local development reset, `docker compose down -v` followed by
`prestart.sh` and the seed is the supported path. Fix a wrong merged migration
with a new migration in the owning slice; never rewrite a merged migration.

## Demo script (14 steps)

1. Start Compose; run migrations and the seed
   (`docker compose run --rm backend bash scripts/prestart.sh`, then
   `docker compose exec backend python -m app.seed_dev`).
2. Log in and switch to `C3` 「明德考勤演示」.
3. 班次: create/edit a shift; show deactivation blocked by an enabled plan and
   deletion blocked by references.
4. 规则与节假日: edit company default rules and a plan override; show the stale
   hint on 考勤结果 after the change.
5. 规则与节假日: maintain the holiday calendar; copy the previous year and show
   the conflict/overwrite flow.
6. 排班工作台: create a plan → conflict preview → expand → copy next month
   (big/small month hints) → personnel sync → manual exception.
7. 导入中心: review the twelve committed batches (three months × four types) →
   re-upload a generated CSV to show mapping, preview counts, and errors → show
   the superseded old batch in history.
8. 考勤结果: review the pre-calculated day results, anomalies, and month
   summaries for the three months; recalculate one month to show the new run.
9. Open a day detail four-way comparison (roster/punch/OA/result) → create a
   manual adjustment → recalculate and verify idempotency/re-application.
10. 考勤结果: confirm → lock → view snapshot versions.
11. Export the 14-column payroll CSV and the detail CSV; verify BOM, escaping,
    and header-only output for an empty month.
12. Unlock with a reason → recalculate → confirm again.
13. Error scenarios: concurrent calculation, stale confirm, cross-company
    reference, dirty import file, revoke in a locked month.
14. Empty/loading/error/locked/stale states; dark theme and narrow screen.

## Requirement-prototype differences

The requirement prototype
([`docs/requirement/rx-hr-prototype.html`](./requirement/rx-hr-prototype.html))
is one long page: shift table → schedule table → punch textarea → OA textarea
→ result table → “backfill to payroll”. This implementation separates the work
rhythms into five pages and makes the import/closing boundaries explicit.

| Dimension | Requirement prototype | This implementation | Why |
|---|---|---|---|
| Navigation | One long page with tabs; attendance mixed with payroll | Scheme A: five independent entries | Scheduling, importing, and result review are different work rhythms |
| Scheduling | Plan and detail mixed in one table | Merged plan view + employee detail + day sheet + month calendar | Answers both “who works that day” and “how this person works this month” |
| Batch operations | Fill/clear/copy without impact preview | Impact preview before fill, copy, and sync | Prevents silent overwrites |
| Import | Two textareas + parse/confirm | Upload/paste → mapping → preview → commit + history + error report + overwrite impact | Auditable, reversible overwrite refresh |
| Results | One wide table + buttons | Full day results by default, anomaly toggle, four-way drawer, timeline | Review everything, focus on exceptions |
| Manual adjustment | Not represented | Versioned result adjustment with original value, reason, operator, history | Traceable before month closing |
| Month closing | Only “backfill to payroll” | draft → calculated → confirmed → locked; unlock reason; snapshot | Separates usable results from immutable results |
| Rules/holidays | Scattered inputs; no holiday calendar | Company default + plan overrides; holiday calendar; impact hints | Know what a change affects before saving |
| States/accessibility | Mostly happy path | Loading/empty/error; dark; narrow; keyboard/focus | Abnormal states are first-class |

“One-click backfill” is the query API plus the 14-column CSV export; it never
writes a payroll table. Schemes B (single workbench + tabs) and C
(anomaly-first cockpit) remain in the prototype as reference only. The
prototype's local result evaluator is for UI demonstration and is not the
calculation contract.

## Verification

From the `backend` directory, with `TEST_DATABASE_URL` pointing at a database
whose name ends with `_test`:

```bash
uv run bash scripts/create-test-db.sh
uv run coverage run -m pytest tests/ -m "not performance"
uv run coverage report --fail-under=90
uv run coverage report --fail-under=95 --include="*/app/services/attendance/calc/*"
uv run pytest tests/attendance -m "not performance"   # goldens, fixtures, API
uv run pytest tests/test_migrations.py tests/test_attendance_schema.py tests/scripts/test_seed_dev.py
uv run pytest tests/attendance/test_performance_smoke.py -m performance
```

The golden-case suite must pass 26/26; the four imports are asserted row by row;
the migration tests assert 24 tables, constraints, and indexes; the seed test
runs twice and asserts stable counts; `tests/attendance/test_query_counts.py`
fails if day results, month summaries, or roster employee lists add one query
per row. From the repository root, Playwright runs the attendance specs in four
shards:

```bash
cd frontend
bunx playwright test attendance-navigation attendance-shifts \
  attendance-rules-holidays attendance-schedule attendance-imports \
  attendance-results attendance-months attendance-states attendance-isolation
```

Data-driven Playwright tests create their own company; navigation and
loading-state tests do not read seeded business data. No test depends on the
development seed or on global counts. The generated client must stay clean:

```bash
bash scripts/generate-client.sh
git diff --exit-code -- frontend/openapi.json frontend/src/client
```
