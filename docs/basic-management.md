# Basic Management

Basic Management maintains the organization foundation for later HR modules:
**Company (公司)**, **Department (部门)**, **Position (岗位)**,
**Cost Center (成本中心)**, and **Employee (员工)**.

- Field-level contract and full test matrix:
  [`docs/specs/basic-management.md`](./specs/basic-management.md)
- Domain vocabulary: [`GLOSSARY.md`](../GLOSSARY.md)
- Architecture decisions: [`docs/adr/`](./adr/)

The UI is Simplified Chinese only (ADR-0002). Every logged-in user has full
access; there is no RBAC or department data scope. Employees are records, not
system users.

## API

All routes are under `/api/v1` and require the existing JWT bearer token.
Collection routes end with `/`; item and tree routes do not.

| Resource | Endpoints |
|---|---|
| Company | `GET/POST /companies/`, `GET/PATCH/DELETE /companies/{company_id}` |
| Department | `GET/POST /departments/`, `GET /departments/tree`, `GET/PATCH/DELETE /departments/{department_id}` |
| Position | `GET/POST /positions/`, `GET/PATCH/DELETE /positions/{position_id}` |
| Cost Center | `GET/POST /cost-centers/`, `GET /cost-centers/tree`, `GET/PATCH/DELETE /cost-centers/{cost_center_id}` |
| Employee | `GET/POST /employees/`, `GET/PATCH /employees/{employee_id}` — **no DELETE** |

Key conventions:

- List responses are `{"data": [...], "count": int}`; `count` is the total
  after filters. `skip` ≥ 0 (default 0), `limit` 1–500 (default 100).
- Company routes are global. Department, position, and cost-center collections
  require `company_id`; employee listing accepts an optional `company_id`.
- `keyword` is a case-insensitive partial match (code/name, or employee number/
  name). `is_active` absent means all; `true` means active only.
- Employee `dept_id` filters include descendants; `status` is repeatable and
  defaults to `active` + `probation`; `unassigned_cost_org=true` conflicts with
  `cost_org_id` (422).
- Tree responses are `{"data": [node]}` with a `children` array on every node,
  including leaves. `is_active=true` prunes inactive nodes while preserving the
  parent/child structure.
- PATCH is partial: omitted means unchanged, explicit `null` clears a nullable
  field. Business codes and `company_id` are immutable; sending them returns 422
  with 「该字段不可修改」.
- `budget` and `daily_hours` accept a number or numeric string and always
  serialize as strings.
- Public responses embed display names (`company_name`, `parent_name`,
  `dept_name`, `position_name`, `cost_org_name`, `manager_name`,
  `manager_status`) so lists render without extra lookups.

## Error model

| HTTP | Shape | Use |
|---|---|---|
| 422 | `{"detail": [{"loc": [...], "msg": "中文", "type": "..."}]}` | Shape, type, range, enum, regex, query conflicts, immutable fields |
| 404 | `{"detail": {"code": "not_found", "message": "中文"}}` | Path or query ID does not exist |
| 409 | `{"detail": {"code", "message", "field_errors", "blockers", "blocker_count"}}` | Business-rule conflicts |
| 401/403/400 | Existing string `detail` | Authentication and account state |

Business error codes:

| Code | Meaning |
|---|---|
| `not_found` | Resource or query ID does not exist |
| `duplicate_code` | Business code duplicate |
| `referenced` | Delete blocked by children or employees |
| `invalid_reference` | Referenced foreign-key target does not exist |
| `cross_company` | Reference crosses companies |
| `inactive_reference` | Referenced entity or manager is inactive |
| `inactive_entity` | Current entity is inactive; structural change forbidden |
| `cycle` | Department/cost-center hierarchy or employee reporting cycle |
| `invalid_status_transition` | Illegal employee status transition or `resign_date` misuse |
| `locked_field` | Resigned employee field is locked |
| `deactivate_blocked` | Active children or active/probation employees prevent deactivation |
| `activation_blocked` | Company or an ancestor is inactive; reactivation forbidden |

`blockers` is returned only for `referenced` and `deactivate_blocked`. It holds
at most 20 entries ordered by type then code; `blocker_count` is the untruncated
total. Each blocker is `{type, id, code, label}` and `label` is
`code + space + name` (employee number instead of code for employees).

The frontend maps `detail.code`, `field_errors`, and 422 `loc`/`msg` to Chinese
form-field messages, and shows blockers plus the total in a blocked-operation
dialog.

## Development seed

Location: `backend/app/seed_dev.py`. It is development-only, manual, and
idempotent: it inserts rows missing by business code and never updates or
deletes user edits. It refuses to run unless `FASTAPI_ENV=development` and is
not part of `prestart.sh`.

Local:

```bash
cd backend
uv run python -m app.seed_dev
```

Docker Compose (backend running):

```bash
docker compose exec backend python -m app.seed_dev
```

Dataset:

| Company | Content |
|---|---|
| `C1` 荣新建设 | Full organization: 7 departments in a 3-level tree (`D1 总部` → `D2 生产部` → `D3 一车间`/`D4 二车间`, plus `D5`/`D6`), inactive `D7 旧项目部`; 6 positions (`P1`–`P6`, `P6` without a default department); 6 cost centers (`K1`–`K6`, `K6` inactive); 16 employees (`E1001`–`E1016`) across active/probation/resigned, with managers, varied contract types, and two employees with no cost center |
| `C2` 荣新科技 | Small organization: 3 departments, 2 positions, 2 cost centers, 4 employees (`E2001`–`E2004`) |
| `C3` 荣新物流 | Empty company for empty-state and company-switching demos |

The inactive department and cost center have no active/probation employee
references. Seeded employees have no login accounts. Re-running the script
produces the same counts and codes.

## Migrations and backups

The Basic Management schema is delivered by three migrations:

1. `cb05be899084` — create `company`, `department`, `position`, `cost_center`,
   `employee` with unique constraints, indexes, check constraints, and
   non-manager foreign keys.
2. `685e4091a8e5` — add the three circular manager foreign keys
   (`ON DELETE SET NULL`) after the tables exist.
3. `d66acc907e93` — drop the old `item` table.

Run migrations from `backend/`:

```bash
uv run alembic upgrade head
uv run alembic downgrade base        # development/test only
uv run alembic upgrade head
```

The backend test suite runs the same upgrade → downgrade → upgrade round-trip
against a throwaway database, plus a seed idempotency check. `item` is removed
in the round-trip and no `items` route or OpenAPI tag remains.

**Back up before applying this chain in any shared environment.** Dropping
`item` is irreversible; the downgrade recreates an empty table only.

```bash
# Example: backup, verify, then migrate
docker compose exec -T db pg_dump -U postgres -Fc app > app-before-basic-management.dump
pg_restore --list app-before-basic-management.dump >/dev/null
docker compose run --rm backend bash scripts/prestart.sh
```

For a local development reset, `docker compose down -v` removes the database
volume; seed the fresh database afterwards. Rolling back only migration 3 with
`alembic downgrade 685e4091a8e5` restores the empty `item` table structure but
not its data. `alembic downgrade fe56fa70289e` goes further and also drops the
five Basic Management tables.

## Demo script

Prerequisites: Docker Compose services, migrations applied, and the seed loaded
(commands above). Sign in with the credentials in `.env`
(`FIRST_SUPERUSER` / `FIRST_SUPERUSER_PASSWORD`).

1. **Switch companies.** Use the top-bar switcher: `C1 荣新建设` → `C2 荣新科技`
   → `C3 荣新物流`. Departments, positions, employees, and cost centers change
   scope; `C3` shows empty states. Reload the page and confirm the selection
   persists. The Companies page stays global.
2. **Companies.** Create a temporary company, edit its name/note, switch to it
   from the table, then try to delete `C1`: the blocked dialog lists the
   blocking departments, positions, cost centers, and employees with the total
   count. Delete the temporary company successfully.
3. **Departments.** In `C1`, open `D1 总部` → `D2 生产部` → `D3 一车间`. Create a
   child under `D2`, edit its name, and move it to `D5 运营部`. Open the parent
   selector and confirm `D2` and its descendants are disabled (no cycle). Try to
   delete `D2`: blocked by child departments and employees. Try to deactivate
   `D2`: blocked by active children/employees. Note `D7 旧项目部` is displayed
   as 「已停用」 and disappears from create/edit selectors.
4. **Positions.** Create a position with `D5` as the default department, edit it,
   then try to delete `P4 财务会计`: blocked by employees, including the
   resigned `E1013 李娜`. Delete the new position successfully. `P6 行政专员`
   has no default department.
5. **Cost centers.** In `C1`, explore the `K1 总部成本中心` → `K2 生产成本中心` →
   `K3`/`K4` tree. Create a child, edit `budget`/`warn_pct` (budget ≥ 0,
   warn 1–100). Click 「未分配」 at the end of the tree to list employees without
   a cost center (`E1009`). Try to delete `K3`: blocked by employees.
6. **Employees.** Create an employee under `D3 一车间`/`P3 车间工人`, choose a
   manager (`E1004`) and cost center, then filter by keyword, status, position,
   cost center, department subtree, and 「未分配」. Mark the employee as resigned
   with a resignation date: the record leaves the default list and its fields are
   locked except note and resignation-date correction (「离职为终态」).
7. **Chinese errors.** Submit a duplicate company code or duplicate employee
   number (409 `duplicate_code`) and an invalid budget or warn range (422) in the
   forms. Send an immutable code in a PATCH payload from Swagger or `curl` (422
   「该字段不可修改」). Confirm messages are Chinese and attached to the relevant
   field where possible.
8. **States.** Switch to `C3 荣新物流` for empty states in all four scoped
   modules. Use the browser network panel to fail a list request and show the
   error state with 「重试」; retry to recover. Loading skeletons appear while
   requests are in flight. Resize to a narrow viewport and confirm the sidebar
   collapses into a sheet, layouts stack, and drawers become full width.
9. **Data isolation.** Switch back to `C2 荣新科技` and confirm only its three
   departments, two positions, and two cost centers are shown. The employee list
   defaults to active/probation, so it shows three people (`E2001`–`E2003`);
   switching the status filter to 「离职」 shows `E2004 张军`. `C1` records are
   absent everywhere, including selectors.

## Verification gates

Backend (from `backend/`):

```bash
uv run bash scripts/test.sh              # pytest + coverage report
uv run coverage report --fail-under=90   # CI coverage gate
uv run bash scripts/lint.sh              # mypy, ty, ruff check, ruff format --check
```

Frontend (from the repository root/frontend):

```bash
bun run lint                       # biome
cd frontend && bun run build       # tsc + vite build
```

End-to-end (four shards in CI, same database isolation locally):

```bash
docker compose run --rm backend bash scripts/prestart.sh
docker compose run --rm playwright bunx playwright test --shard=1/4
# repeat for shards 2/4, 3/4, 4/4
```

Generated client cleanliness:

```bash
bash scripts/generate-client.sh
git diff --exit-code
```

Items removal:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/items/  # 404
```

The backend suite also asserts that OpenAPI has no `items` tag, that the
migration round-trip succeeds, and that the seed is idempotent.

### Cross-module matrix

The acceptance matrix is covered by backend API tests and Playwright:

- Company, department, position, and cost-center deletion and deactivation are
  blocked by employees (including resigned employees for deletion).
- Deleting an unreferenced department clears the default department on positions
  that used it.
- References never cross companies; employee company is derived from department.
- Department/cost-center parent selection and employee manager selection cannot
  create hierarchy or reporting cycles.
- Inactive nodes block structural edits; reactivation requires the company and
  all ancestors to be active.
