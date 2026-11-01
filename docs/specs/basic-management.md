# Basic Management Implementation Specification

- Status: Approved (2026-11-01)
- Date: 2026-11-01
- Scope: Company, Department, Position, Cost Center, Employee
- Source decisions: [organization model (#5)](https://github.com/nasa-du/anysys-hr/issues/5), [employee model (#6)](https://github.com/nasa-du/anysys-hr/issues/6), [API contract (#7)](https://github.com/nasa-du/anysys-hr/issues/7), [frontend IA (#8)](https://github.com/nasa-du/anysys-hr/issues/8), [implementation plan (#9)](https://github.com/nasa-du/anysys-hr/issues/9)
- Audience: implementers who should not need further product or architecture decisions

## Table of Contents

1. [Background and Goals](#1-background-and-goals)
2. [Scope and Non-Goals](#2-scope-and-non-goals)
3. [Terminology and References](#3-terminology-and-references)
4. [Domain Model](#4-domain-model)
5. [API Contract](#5-api-contract)
6. [Authentication and Authorization](#6-authentication-and-authorization)
7. [Frontend Information Architecture and Interaction](#7-frontend-information-architecture-and-interaction)
8. [Implementation Architecture](#8-implementation-architecture)
9. [Migration Strategy](#9-migration-strategy)
10. [Implementation Order and Parallelism](#10-implementation-order-and-parallelism)
11. [Test Strategy](#11-test-strategy)
12. [Development Seed Data](#12-development-seed-data)
13. [Acceptance Criteria and Demo Script](#13-acceptance-criteria-and-demo-script)
14. [Risks and Rollback](#14-risks-and-rollback)
15. [Future Extensions](#15-future-extensions)
16. [References](#16-references)

---

## 1. Background and Goals

AnySys HR is an employee management and payroll calculation system for small and medium-sized businesses. This effort covers **Basic Management**: companies, departments, positions, cost centers, and employees.

The goal of this specification is a handoff artifact that is complete enough to start implementation without further product or architecture decisions. It consolidates the decisions recorded in tickets #5–#9 and adds the final implementation architecture, file layout, and delivery plan.

Deliverables of this effort:

- A finalized data model and database migration plan.
- A finalized REST API contract.
- A finalized frontend information architecture and interaction model.
- An implementation order with parallel points.
- A test matrix, seed data plan, acceptance checklist, and risk register.
- No production code; implementation is a separate effort.

## 2. Scope and Non-Goals

### 2.1 In Scope

- Multi-company modeling; companies are flat (no parent company).
- Departments with arbitrary depth under a company.
- Positions as company-level reusable records with an optional default department.
- Cost centers with arbitrary depth under a company; independent from the administrative organization.
- Employees with required department and position, optional cost center, optional manager, lifecycle status, and profile fields.
- Hard delete for the four organization entities when unreferenced; no physical delete for employees.
- `is_active` deactivation for the four organization entities.
- Search, filtering, pagination, and tree reads.
- Simplified Chinese UI, validation messages, and API error details.
- Backend tests, Playwright E2E tests, developer seed data, and acceptance criteria.
- Existing login is reused; every logged-in user has full Basic Management access.

### 2.2 Out of Scope

The following work is explicitly outside this effort. It is not fog and must not be added to this map:

- Attendance management (shifts, scheduling, clock-in, OA requests, attendance result write-back).
- Payroll management (compensation components, calculation schemes, workday parameters, formula engine, payroll calculation, payroll lists, payslips, reports).
- Account and role management (RBAC, department data scope, audit).
- Excel bulk import and export templates (people/organization, positions, cost organization).
- Employee self-service H5 and release snapshots.
- Payroll expense statistics and budget alerts (cost center CRUD and budget entry are in scope).
- Group–subsidiary multi-level company hierarchy.
- Transfer history, effective dates, and approval flows.
- Rehire (resignation is terminal).
- DingTalk / OA integration.
- Production code implementation and deployment execution (separate effort).

## 3. Terminology and References

### 3.1 Canonical Terms

Use the terms defined in [`GLOSSARY.md`](../../GLOSSARY.md). Do not substitute synonyms such as 「组织」「人员」「职位」 for the canonical terms.

| Term | Meaning |
|---|---|
| Company (公司) | Top-level organization; owner of departments, positions, and cost centers. Companies are flat and multi-tenant in this phase. |
| Department (部门) | Administrative organization node under a company; arbitrary depth; the employee's administrative assignment. |
| Position (岗位) | Company-level reusable job record; employees must reference one; optional default department. |
| Default Department (默认部门) | Optional department on a position; used to prefill the employee form, not to restrict the employee's actual department. |
| Employee (员工) | Managed person record with administrative and cost assignments; not a system user. |
| Employee No (工号) | Globally unique, immutable business code for an employee. |
| Manager (直属上级) | Optional employee-to-employee reporting relationship; same company; no self-reference or cycle. |
| Employee Status (员工状态) | `active` (在职), `probation` (试用期), `resigned` (离职); resignation is terminal. |
| System User (用户) | Login account; separate from the employee record. |
| Cost Center (成本中心) | Second organization dimension under a company; arbitrary depth; used for cost allocation; independent from the administrative organization. |
| Unassigned (未分配) | The state of an employee with no cost center. |
| Active / Inactive (启用 / 停用) | Whether an organization entity can be referenced by new structural relationships; inactive records are retained. |
| Administrative Organization (行政架构) | Company → department dimension. |
| Cost Organization (成本架构) | Company → cost center dimension. |
| Basic Management (基础管理) | The five-module scope described in this document. |

### 3.2 Architecture Decision Records

- [ADR-0001: UUID v7 for primary keys](../adr/0001-uuid-v7-primary-keys.md)
- [ADR-0002: Simplified Chinese only, no i18n framework](../adr/0002-chinese-only-no-i18n.md)
- [ADR-0003: UUID v7 primary keys with separate business codes](../adr/0003-uuid-v7-with-business-codes.md)

### 3.3 Requirement and Prototype References

- Requirement source: [`docs/requirement/rx-hr-requirement.html`](../requirement/rx-hr-requirement.html), sections 3.1, 3.1.0–3.1.2, 3.5; M0/M1/M5/M14 basic profile parts.
- Frontend prototype (approved Scheme A): [`docs/prototypes/basic-management-ia/index.html`](../prototypes/basic-management-ia/index.html)
- Prototype notes: [`docs/prototypes/basic-management-ia/README.md`](../prototypes/basic-management-ia/README.md)
- Prototype screenshots: [`docs/prototypes/basic-management-ia/screenshots/`](../prototypes/basic-management-ia/screenshots/)

### 3.4 Decision Provenance

| Section | Source ticket |
|---|---|
| Domain model | #5 (organizations), #6 (employee) |
| API contract | #7 |
| Frontend IA and interaction | #8 |
| Migration, implementation order, tests, seed, acceptance, risks | #9 |

The source tickets remain the rationale record. This document is the implementation handoff.

## 4. Domain Model

### 4.1 Entity Overview

```text
Company 1 ─── N Department        (administrative organization, self-referencing tree)
Company 1 ─── N Position          (company-level reusable records)
Company 1 ─── N CostCenter        (cost organization, self-referencing tree)
Department 1 ─ N Employee         (required administrative assignment)
Position   1 ─ N Employee         (required job assignment)
CostCenter 0 ─ N Employee         (optional cost assignment; null = Unassigned)
Employee   0 ─ N Employee         (manager relationship, self-referencing)
```

- Every entity has a UUID v7 primary key and a separate immutable business code (ADR-0003).
- All foreign keys reference UUIDs, never business codes.
- Employee does not store `company_id`; the company is derived from `dept_id`.
- The four organization entities use `is_active`; employees use `status`.

### 4.2 Company

| Field | Type | Required | Default | Constraints |
|---|---|---|---|---|
| `id` | UUID | yes | UUID v7 | Primary key |
| `company_code` | str(32) | yes | — | Globally unique; immutable; uppercase `^[A-Z0-9_-]{1,32}$` |
| `company_name` | str(100) | yes | — | Not unique |
| `is_active` | bool | yes | `true` | Deactivation rules below |
| `note` | str(500) | no | `null` | — |
| `created_at` | datetime | yes | UTC now | — |
| `updated_at` | datetime | yes | UTC now | Refreshed by the service layer on update |

Rules:

- Companies are flat; there is no `parent_company_id`.
- Delete: blocked if any department, position, cost center, or employee exists; otherwise hard delete.
- Deactivate: blocked if any active department, active position, active cost center, or active/probation employee exists. Resigned employees do not block.
- Reactivate: allowed; a company has no parent.

### 4.3 Department

| Field | Type | Required | Default | Constraints |
|---|---|---|---|---|
| `id` | UUID | yes | UUID v7 | Primary key |
| `dept_code` | str(32) | yes | — | Unique within company; immutable; uppercase `^[A-Z0-9_-]{1,32}$` |
| `dept_name` | str(100) | yes | — | Not unique |
| `company_id` | UUID | yes | — | FK `company.id`; immutable after creation |
| `parent_id` | UUID | no | `null` | FK `department.id`; same company; no self-reference or descendant cycle |
| `manager_id` | UUID | no | `null` | FK `employee.id`; same company; active/probation at assignment |
| `order_no` | int | yes | `0` | No uniqueness |
| `is_active` | bool | yes | `true` | Deactivation rules below |
| `note` | str(500) | no | `null` | — |
| `created_at` | datetime | yes | UTC now | — |
| `updated_at` | datetime | yes | UTC now | Refreshed by the service layer on update |

Rules:

- Arbitrary depth; root nodes have `parent_id = null`.
- The position list under a department is derived from `position.dept_id`; there is no many-to-many table.
- No `department.cost_center` text field; cost allocation is expressed only through `employee.cost_org_id`.
- Delete: blocked if child departments or any employee (including resigned) reference the department; deleting a department sets `position.dept_id` to null for positions that used it as default.
- Deactivate: blocked if active child departments or active/probation employees with `dept_id` pointing to this department exist. Resigned employees do not block.
- Structural changes require the entity itself and the target parent to be active.
- Reactivation requires the company and all ancestors to be active.

### 4.4 Position

| Field | Type | Required | Default | Constraints |
|---|---|---|---|---|
| `id` | UUID | yes | UUID v7 | Primary key |
| `position_code` | str(32) | yes | — | Unique within company; immutable; uppercase `^[A-Z0-9_-]{1,32}$` |
| `position_name` | str(100) | yes | — | Not unique |
| `company_id` | UUID | yes | — | FK `company.id`; immutable after creation |
| `dept_id` | UUID | no | `null` | FK `department.id`; same company; active when set/updated; default department |
| `order_no` | int | yes | `0` | No uniqueness |
| `is_active` | bool | yes | `true` | Deactivation rules below |
| `note` | str(500) | no | `null` | — |
| `created_at` | datetime | yes | UTC now | — |
| `updated_at` | datetime | yes | UTC now | Refreshed by the service layer on update |

Rules:

- Positions are company-level reusable records; `dept_id` is only a default department.
- An employee's actual department may differ from the position's default department.
- No compensation components, calculation schemes, workday parameters, job category, level, or headcount in this phase.
- Delete: blocked if any employee (including resigned) references the position.
- Deactivate: blocked if active/probation employees reference the position. Resigned employees do not block. An inactive default department does not block deactivation; keep the default department and display it as inactive.
- Reactivation requires the company to be active; the default department may be inactive and is displayed as such.
- Structural changes require the position and the target default department to be active.

### 4.5 Cost Center

| Field | Type | Required | Default | Constraints |
|---|---|---|---|---|
| `id` | UUID | yes | UUID v7 | Primary key |
| `cost_org_code` | str(32) | yes | — | Unique within company; immutable; uppercase `^[A-Z0-9_-]{1,32}$` |
| `cost_org_name` | str(100) | yes | — | Not unique |
| `company_id` | UUID | yes | — | FK `company.id`; immutable after creation |
| `parent_id` | UUID | no | `null` | FK `cost_center.id`; same company; no self-reference or descendant cycle |
| `manager_id` | UUID | no | `null` | FK `employee.id`; same company; active/probation at assignment |
| `budget` | Decimal(14,2) | yes | `0` | `>= 0`; `0` means no budget |
| `warn_pct` | int | yes | `85` | `1..100` |
| `order_no` | int | yes | `0` | No uniqueness |
| `is_active` | bool | yes | `true` | Deactivation rules below |
| `note` | str(500) | no | `null` | — |
| `created_at` | datetime | yes | UTC now | — |
| `updated_at` | datetime | yes | UTC now | Refreshed by the service layer on update |

Rules:

- Independent second organization dimension; arbitrary depth.
- `budget` and `warn_pct` are recorded in this phase; no payroll statistics or alerts.
- Delete: blocked if child cost centers or any employee (including resigned) reference the cost center; migrate employee cost assignments first.
- Deactivate: blocked if active child cost centers or active/probation employees reference the cost center. Resigned employees do not block.
- Reactivation requires the company and all ancestors to be active.
- Structural changes require the entity itself and the target parent to be active.

### 4.6 Employee

| Field | Type | Required | Default | Constraints |
|---|---|---|---|---|
| `id` | UUID | yes | UUID v7 | Primary key |
| `employee_no` | str(32) | yes | — | Globally unique; immutable; uppercase `^[A-Z0-9_-]{1,32}$` |
| `name` | str(100) | yes | — | Duplicate names allowed |
| `gender` | enum(`male`/`female`/`unknown`) | no | `null` | 男 / 女 / 未说明; null = not provided |
| `dept_id` | UUID | yes | — | FK `department.id`; RESTRICT; same company; active on create/update |
| `position_id` | UUID | yes | — | FK `position.id`; RESTRICT; same company; active on create/update |
| `cost_org_id` | UUID | no | `null` | FK `cost_center.id`; RESTRICT; null = Unassigned; same company; active on create/update |
| `manager_id` | UUID | no | `null` | FK `employee.id`; SET NULL; same company; active/probation at assignment; no self-reference or cycle |
| `status` | enum(`active`/`probation`/`resigned`) | yes | `active` | 在职 / 试用期 / 离职 |
| `hire_date` | date | yes | — | `<= today` |
| `resign_date` | date | no | `null` | Required only when `status = resigned`; `hire_date <= resign_date <= today` |
| `contract_type` | enum(`full_time`/`part_time`/`intern`/`labor`) | yes | — | 全职 / 兼职 / 实习 / 劳务 |
| `daily_hours` | Decimal(4,2) | no | `null` | `0 < daily_hours <= 24`; profile only |
| `monthly_rest` | int | no | `null` | `>= 0`; profile only |
| `confidentiality_level` | int | no | `null` | `1..5`; profile only |
| `note` | str(500) | no | `null` | — |
| `created_at` | datetime | yes | UTC now | — |
| `updated_at` | datetime | yes | UTC now | Refreshed by the service layer on update |

Rules:

- No `company_id` column; the company is derived from `dept_id`.
- No `is_active`; lifecycle is expressed by `status`.
- Employees are not system users: no `user_id`, no automatic login account.
- No physical delete; `status = resigned` is the lifecycle endpoint.
- No contact fields (phone, email, ID number) in this phase.
- `daily_hours`, `monthly_rest`, and `confidentiality_level` are profile-only; they do not participate in payroll, attendance, or any calculation.
- Assignments: `dept_id`, `position_id`, and `cost_org_id` must belong to the same company; `dept_id` determines the company; changing `dept_id` to another company is rejected.
- No transfer history; editing changes the current assignment directly.
- No status-change history.

Status machine:

| From | To | Allowed |
|---|---|---|
| `active` | `probation` | No |
| `probation` | `active` | Yes |
| `active` / `probation` | `resigned` | Yes, with `resign_date` |
| `resigned` | `active` / `probation` | No |
| `resigned` | `resigned` | Yes, only `note` / `resign_date` corrections |

- Create accepts only `active` or `probation`; `resigned` on create returns 409 `invalid_status_transition`.
- Transitioning to `resigned` requires `resign_date`; the request may contain only `status`, `resign_date`, and `note`. Other field changes in the same request return 409 `locked_field`.
- An already-resigned employee may only edit `note` and `resign_date` (correction); other fields return 409 `locked_field`.
- `resign_date` on a non-resigned employee returns 409 `invalid_status_transition`.
- `resign_date < hire_date` returns 409 `invalid_status_transition`; `resign_date > today` returns 422.

Manager rules:

- `manager_id` is nullable and self-referencing.
- The manager must belong to the same company and be `active` or `probation` at assignment.
- Self-reference and cycles are rejected with 409 `cycle`.
- A resigned manager reference is retained and displayed as 「已离职」; it is not automatically cleared.
- A manager may be in another department or cost center; an employee has at most one manager; a manager may have multiple reports.
- No manager-change history.

### 4.7 Relationships and Delete Matrix

| Relationship | Foreign key | Delete behavior |
|---|---|---|
| `department.company_id` → `company.id` | Required | RESTRICT |
| `department.parent_id` → `department.id` | Nullable | RESTRICT (delete children first) |
| `department.manager_id` → `employee.id` | Nullable | SET NULL |
| `position.company_id` → `company.id` | Required | RESTRICT |
| `position.dept_id` → `department.id` | Nullable | SET NULL |
| `cost_center.company_id` → `company.id` | Required | RESTRICT |
| `cost_center.parent_id` → `cost_center.id` | Nullable | RESTRICT (delete children first) |
| `cost_center.manager_id` → `employee.id` | Nullable | SET NULL |
| `employee.dept_id` → `department.id` | Required | RESTRICT |
| `employee.position_id` → `position.id` | Required | RESTRICT |
| `employee.cost_org_id` → `cost_center.id` | Nullable | RESTRICT |
| `employee.manager_id` → `employee.id` | Nullable | SET NULL |

- The application performs full reference checks before deleting and returns Chinese 409 errors.
- Database `RESTRICT` / `SET NULL` behavior is the backstop.
- `SET NULL` on manager relationships is reserved for a future physical employee deletion; employees are not physically deleted in this phase.

### 4.8 `is_active` Rules

- The four organization entities use `is_active`, default `true`.
- Deactivation is bottom-up: an entity cannot be deactivated while it has active children or active/probation employees. Resigned employees do not block.
- Inactive entities:
  - Do not appear in create/edit selectors.
  - Remain visible in historical references and are labeled 「已停用」.
  - Allow non-structural edits: name, note, order, budget, `warn_pct`.
- Structural changes (create child, move node, change default department) require the entity itself and the target parent to be active.
- Reactivation requires the company and all ancestors to be active.
- Inactive business codes still occupy uniqueness; hard delete (when unreferenced) frees the code.
- `is_active` does not change delete rules; delete remains hard delete with reference constraints.

### 4.9 Enums

| Enum | Codes | Chinese labels |
|---|---|---|
| `Gender` | `male`, `female`, `unknown` | 男, 女, 未说明 |
| `EmployeeStatus` | `active`, `probation`, `resigned` | 在职, 试用期, 离职 |
| `ContractType` | `full_time`, `part_time`, `intern`, `labor` | 全职, 兼职, 实习, 劳务 |

- Database and API store English codes.
- Backend definitions live in `backend/app/enums.py`.
- Frontend labels and option lists live in `frontend/src/lib/enums.ts`; components import from there and do not hardcode Chinese labels.
- No i18n framework (ADR-0002).

### 4.10 Database Constraints and Indexes

Naming:

- Unique constraints: `uq_<table>_<columns>`.
- Foreign keys: `fk_<table>_<column>_<target>`.
- Indexes: `ix_<table>_<columns>`.
- Check constraints: `ck_<table>_<rule>`.

Unique constraints:

| Table | Constraint | Columns |
|---|---|---|
| `company` | `uq_company_company_code` | `company_code` |
| `department` | `uq_department_company_dept_code` | `company_id`, `dept_code` |
| `position` | `uq_position_company_position_code` | `company_id`, `position_code` |
| `cost_center` | `uq_cost_center_company_cost_org_code` | `company_id`, `cost_org_code` |
| `employee` | `uq_employee_employee_no` | `employee_no` |

Indexes:

| Table | Indexes |
|---|---|
| `department` | `ix_department_company_id`, `ix_department_parent_id`, `ix_department_manager_id` |
| `position` | `ix_position_company_id`, `ix_position_dept_id` |
| `cost_center` | `ix_cost_center_company_id`, `ix_cost_center_parent_id`, `ix_cost_center_manager_id` |
| `employee` | `ix_employee_dept_id`, `ix_employee_position_id`, `ix_employee_cost_org_id`, `ix_employee_manager_id`, `ix_employee_status` |

- Do not add standalone `is_active` indexes or full-text/trigram indexes in this phase.
- Do not index `order_no`.

Check constraints:

| Constraint | Rule |
|---|---|
| `ck_cost_center_budget_non_negative` | `budget >= 0` |
| `ck_cost_center_warn_pct_range` | `warn_pct BETWEEN 1 AND 100` |
| `ck_employee_daily_hours_range` | `daily_hours IS NULL OR (daily_hours > 0 AND daily_hours <= 24)` |
| `ck_employee_monthly_rest_non_negative` | `monthly_rest IS NULL OR monthly_rest >= 0` |
| `ck_employee_confidentiality_level_range` | `confidentiality_level IS NULL OR confidentiality_level BETWEEN 1 AND 5` |
| `ck_employee_resign_date_after_hire` | `resign_date IS NULL OR resign_date >= hire_date` |
| `ck_employee_resigned_date_required` | `(status = 'resigned') = (resign_date IS NOT NULL)` |
| `ck_employee_gender` | `gender IS NULL OR gender IN ('male','female','unknown')` |
| `ck_employee_status` | `status IN ('active','probation','resigned')` |
| `ck_employee_contract_type` | `contract_type IN ('full_time','part_time','intern','labor')` |

- Enums are stored as `VARCHAR + CHECK` via `SAEnum(..., native_enum=False, create_constraint=True, name=...)`; do not create PostgreSQL native enum types.
- UUID primary keys use `sa.UUID(as_uuid=True)` with Python `uuid.uuid7`; no database default.
- `created_at` / `updated_at` are `TIMESTAMPTZ NOT NULL`, generated in Python; `updated_at` is refreshed by the service layer; no database trigger.
- The `position` table name is a non-reserved PostgreSQL keyword collision with the `POSITION` function. Use `position` first; if Alembic or `psql` reports a quoting problem, rename to `position_arch` before merging and update all references consistently.

## 5. API Contract

### 5.1 Conventions

- Base path: `/api/v1`.
- All endpoints require the existing `CurrentUser` dependency (logged-in user); no RBAC or data scope.
- IDs are UUID v7 strings; business codes are uppercase and immutable.
- Public schemas include `created_at` / `updated_at` as UTC ISO 8601 strings (`...Z`).
- Decimal fields (`budget`, `daily_hours`) accept a JSON number or numeric string in requests and always serialize as strings in responses; Public schemas use `PlainSerializer(str, return_type=str)` so the generated OpenAPI type is `string`.
- List responses: `{"data": [...], "count": int}`; `count` is the total after filters, not the page size.
- Pagination: `skip >= 0` (default 0), `limit` 1..500 (default 100); out-of-range values return 422. No cursor.
- Tree responses: `{"data": [node]}`; each node has `children: []` (always an array, including leaves); no pagination.
- Fixed sorting; no `sort` parameter:
  - Company / Department / Position / Cost Center: `order_no ASC`, then business code ASC.
  - Employee: `employee_no ASC`, then `name ASC`.
  - Trees: same rule per level.
- `keyword`: max 100 characters; empty string means no filter; case-insensitive partial match. Organization entities match code + name; employees match `employee_no` + `name`.
- `is_active`: absent = all (management lists); `true` = active only (selectors). Employees have no `is_active`.
- Write schemas use `ConfigDict(extra="forbid")`; codes are uppercased before validation; `note: ""` is normalized to `null`.
- Authentication errors keep the existing string `detail` format: 401 unauthenticated/expired, 403 invalid token, 400 inactive account.

### 5.2 Endpoint Table

Path parameters use resource names; collection routes have a trailing slash; tree and item routes do not.

| Resource | Method and path | Request / query | Success response |
|---|---|---|---|
| Company | `GET /api/v1/companies/` | `skip, limit, keyword, is_active` | `CompaniesPublic` |
| | `POST /api/v1/companies/` | `CompanyCreate` | `CompanyPublic`, 201 |
| | `GET /api/v1/companies/{company_id}` | — | `CompanyPublic` |
| | `PATCH /api/v1/companies/{company_id}` | `CompanyUpdate` | `CompanyPublic` |
| | `DELETE /api/v1/companies/{company_id}` | — | `Message` |
| Department | `GET /api/v1/departments/` | `company_id*`, `parent_id`, `keyword`, `is_active`, `skip`, `limit` | `DepartmentsPublic` |
| | `GET /api/v1/departments/tree` | `company_id*`, `is_active` | `DepartmentTreePublic` |
| | `POST /api/v1/departments/` | `DepartmentCreate` | `DepartmentPublic`, 201 |
| | `GET /api/v1/departments/{department_id}` | — | `DepartmentPublic` |
| | `PATCH /api/v1/departments/{department_id}` | `DepartmentUpdate` | `DepartmentPublic` |
| | `DELETE /api/v1/departments/{department_id}` | — | `Message` |
| Position | `GET /api/v1/positions/` | `company_id*`, `dept_id`, `keyword`, `is_active`, `skip`, `limit` | `PositionsPublic` |
| | `POST /api/v1/positions/` | `PositionCreate` | `PositionPublic`, 201 |
| | `GET /api/v1/positions/{position_id}` | — | `PositionPublic` |
| | `PATCH /api/v1/positions/{position_id}` | `PositionUpdate` | `PositionPublic` |
| | `DELETE /api/v1/positions/{position_id}` | — | `Message` |
| Cost Center | `GET /api/v1/cost-centers/` | `company_id*`, `parent_id`, `keyword`, `is_active`, `skip`, `limit` | `CostCentersPublic` |
| | `GET /api/v1/cost-centers/tree` | `company_id*`, `is_active` | `CostCenterTreePublic` |
| | `POST /api/v1/cost-centers/` | `CostCenterCreate` | `CostCenterPublic`, 201 |
| | `GET /api/v1/cost-centers/{cost_center_id}` | — | `CostCenterPublic` |
| | `PATCH /api/v1/cost-centers/{cost_center_id}` | `CostCenterUpdate` | `CostCenterPublic` |
| | `DELETE /api/v1/cost-centers/{cost_center_id}` | — | `Message` |
| Employee | `GET /api/v1/employees/` | `company_id, dept_id, position_id, cost_org_id, unassigned_cost_org, status, keyword, skip, limit` | `EmployeesPublic` |
| | `POST /api/v1/employees/` | `EmployeeCreate` | `EmployeePublic`, 201 |
| | `GET /api/v1/employees/{employee_id}` | — | `EmployeePublic` |
| | `PATCH /api/v1/employees/{employee_id}` | `EmployeeUpdate` | `EmployeePublic` |

`*` = required. Employees have no DELETE endpoint. `Message` reuses the existing `{"message": "..."}` schema.

### 5.3 Request and Response Schemas

#### 5.3.1 Company

| Schema | Fields |
|---|---|
| `CompanyCreate` | `company_code: str` (required, ≤32)<br>`company_name: str` (required, 1..100)<br>`is_active: bool = true`<br>`note: str \| None = None` (≤500) |
| `CompanyUpdate` | `company_name?`, `is_active?`, `note?`; no `company_code` |
| `CompanyPublic` | `id: UUID`, `company_code: str`, `company_name: str`, `is_active: bool`, `note: str \| None`, `created_at`, `updated_at` |
| `CompaniesPublic` | `data: list[CompanyPublic]`, `count: int` |

#### 5.3.2 Department

| Schema | Fields |
|---|---|
| `DepartmentCreate` | `dept_code: str` (required, ≤32)<br>`dept_name: str` (required, 1..100)<br>`company_id: UUID` (required)<br>`parent_id: UUID \| None = None`<br>`manager_id: UUID \| None = None`<br>`order_no: int = 0`<br>`is_active: bool = true`<br>`note: str \| None = None` (≤500) |
| `DepartmentUpdate` | `dept_name?`, `parent_id?`, `manager_id?`, `order_no?`, `is_active?`, `note?`; no `dept_code` / `company_id` |
| `DepartmentPublic` | Model fields: `id`, `dept_code`, `dept_name`, `company_id`, `parent_id`, `manager_id`, `order_no`, `is_active`, `note`, `created_at`, `updated_at`<br>Display fields: `company_name`, `parent_name`, `manager_name`, `manager_status` (nullable) |
| `DepartmentTreeNode` | `DepartmentPublic` + `children: list[DepartmentTreeNode]` (always an array) |
| `DepartmentsPublic` | `data: list[DepartmentPublic]`, `count: int` |
| `DepartmentTreePublic` | `data: list[DepartmentTreeNode]` |

#### 5.3.3 Position

| Schema | Fields |
|---|---|
| `PositionCreate` | `position_code: str` (required, ≤32)<br>`position_name: str` (required, 1..100)<br>`company_id: UUID` (required)<br>`dept_id: UUID \| None = None` (default department)<br>`order_no: int = 0`<br>`is_active: bool = true`<br>`note: str \| None = None` (≤500) |
| `PositionUpdate` | `position_name?`, `dept_id?`, `order_no?`, `is_active?`, `note?`; no `position_code` / `company_id` |
| `PositionPublic` | Model fields: `id`, `position_code`, `position_name`, `company_id`, `dept_id`, `order_no`, `is_active`, `note`, `created_at`, `updated_at`<br>Display fields: `company_name`, `dept_name` (nullable) |
| `PositionsPublic` | `data: list[PositionPublic]`, `count: int` |

#### 5.3.4 Cost Center

| Schema | Fields |
|---|---|
| `CostCenterCreate` | `cost_org_code: str` (required, ≤32)<br>`cost_org_name: str` (required, 1..100)<br>`company_id: UUID` (required)<br>`parent_id: UUID \| None = None`<br>`manager_id: UUID \| None = None`<br>`budget: Decimal(14,2) = 0` (`>= 0`)<br>`warn_pct: int = 85` (1..100)<br>`order_no: int = 0`<br>`is_active: bool = true`<br>`note: str \| None = None` (≤500) |
| `CostCenterUpdate` | `cost_org_name?`, `parent_id?`, `manager_id?`, `budget?`, `warn_pct?`, `order_no?`, `is_active?`, `note?`; no `cost_org_code` / `company_id` |
| `CostCenterPublic` | Model fields: `id`, `cost_org_code`, `cost_org_name`, `company_id`, `parent_id`, `manager_id`, `budget`, `warn_pct`, `order_no`, `is_active`, `note`, `created_at`, `updated_at`<br>Display fields: `company_name`, `parent_name`, `manager_name`, `manager_status` (nullable) |
| `CostCenterTreeNode` | `CostCenterPublic` + `children: list[CostCenterTreeNode]` (always an array) |
| `CostCentersPublic` | `data: list[CostCenterPublic]`, `count: int` |
| `CostCenterTreePublic` | `data: list[CostCenterTreeNode]` |

#### 5.3.5 Employee

| Schema | Fields |
|---|---|
| `EmployeeCreate` | `employee_no: str` (required, ≤32)<br>`name: str` (required, 1..100)<br>`gender: enum(male/female/unknown) \| None = None`<br>`dept_id: UUID` (required)<br>`position_id: UUID` (required)<br>`cost_org_id: UUID \| None = None`<br>`manager_id: UUID \| None = None`<br>`status: enum(active/probation) = active`<br>`hire_date: date` (required, `<= today`)<br>`contract_type: enum(full_time/part_time/intern/labor)` (required)<br>`daily_hours: Decimal(4,2) \| None` (`0 < x <= 24`)<br>`monthly_rest: int \| None` (`>= 0`)<br>`confidentiality_level: int \| None` (1..5)<br>`note: str \| None = None` (≤500)<br>No `resign_date` |
| `EmployeeUpdate` | `name?`, `gender?`, `dept_id?`, `position_id?`, `cost_org_id?`, `manager_id?`, `status?`, `hire_date?`, `resign_date?`, `contract_type?`, `daily_hours?`, `monthly_rest?`, `confidentiality_level?`, `note?`; no `employee_no` |
| `EmployeePublic` | Model fields: `id`, `employee_no`, `name`, `gender`, `dept_id`, `position_id`, `cost_org_id`, `manager_id`, `status`, `hire_date`, `resign_date`, `contract_type`, `daily_hours`, `monthly_rest`, `confidentiality_level`, `note`, `created_at`, `updated_at`<br>Display fields: `company_id`, `company_name`, `dept_name`, `position_name`, `cost_org_name` (null = Unassigned), `manager_name`, `manager_status` (nullable) |
| `EmployeesPublic` | `data: list[EmployeePublic]`, `count: int` |

`EmployeePublic.company_id` / `company_name` are derived from `dept_id`. `manager_status` lets the UI label a resigned manager as 「已离职」.

### 5.4 Query Parameters

| Endpoint | Parameters and semantics |
|---|---|
| `GET /companies/` | `skip, limit, keyword, is_active`; no company filter |
| `GET /departments/` | `company_id` required; `parent_id` exact direct-child filter; `keyword, is_active, skip, limit` |
| `GET /departments/tree` | `company_id` required; optional `is_active`; returns the full tree, pruning inactive nodes when `is_active=true` while preserving parent/child structure |
| `GET /positions/` | `company_id` required; `dept_id` exact default-department filter; `keyword, is_active, skip, limit` |
| `GET /cost-centers/` | `company_id` required; `parent_id` exact direct-child filter; `keyword, is_active, skip, limit` |
| `GET /cost-centers/tree` | `company_id` required; optional `is_active`; same tree rules as departments |
| `GET /employees/` | `company_id` optional (absent = all companies); `dept_id` filter **includes all descendant departments**; `position_id`, `cost_org_id` exact; `unassigned_cost_org: bool = false`; `status` repeatable, default `active` + `probation`, pass all three for "all"; `keyword, skip, limit` |

- A `company_id`, `parent_id`, `dept_id`, `position_id`, or `cost_org_id` explicitly supplied in a query must exist; otherwise return 404 `not_found`.
- `unassigned_cost_org=true` together with `cost_org_id` returns 422 (query-parameter conflict, validation array).
- An invalid `status` enum returns 422.

### 5.5 Error Model

#### 5.5.1 Response Shapes

| HTTP | Shape | Use |
|---|---|---|
| 422 | `{"detail": [{"loc": [...], "msg": "中文", "type": "..."}]}` | Request shape, type, length, enum, single-field range, query conflict; reuse the existing `core/errors.py` Chinese translation |
| 404 | `{"detail": {"code": "not_found", "message": "部门不存在"}}` | Path ID or query ID not found |
| 409 | `{"detail": {"code": "...", "message": "中文", "field_errors": {...}, "blockers": [...], "blocker_count": 0}}` | Business-rule conflict |
| 401 / 403 / 400 | Existing string `detail` | Authentication and account state |

`field_errors` keys are request field names (`dept_code`, `parent_id`, `status`, ...); values are Chinese messages. `blockers` / `blocker_count` are returned only for `referenced` and `deactivate_blocked`.

#### 5.5.2 Business Error Codes

| Code | HTTP | Meaning |
|---|---|---|
| `not_found` | 404 | Resource or query ID does not exist |
| `duplicate_code` | 409 | Business code duplicate, including database unique-constraint races |
| `referenced` | 409 | Delete blocked by children or employees |
| `invalid_reference` | 409 | Referenced foreign-key target does not exist |
| `cross_company` | 409 | Reference crosses companies |
| `inactive_reference` | 409 | Referenced department/position/cost center/manager is inactive |
| `inactive_entity` | 409 | Current entity is inactive; structural change forbidden |
| `cycle` | 409 | Department/cost-center hierarchy or employee reporting cycle |
| `invalid_status_transition` | 409 | Illegal employee status transition or `resign_date` misuse |
| `locked_field` | 409 | Resigned employee field is locked, or a resignation transition request contains other fields |
| `deactivate_blocked` | 409 | Active children or active/probation employees prevent deactivation |
| `activation_blocked` | 409 | Company or an ancestor is inactive; reactivation forbidden |

`immutable_field` is not a `detail.code`: when an update payload contains `*_code` or `company_id`, `extra="forbid"` produces a 422 validation array; `translate_validation_error` translates `extra_forbidden` to 「该字段不可修改」.

#### 5.5.3 `blockers` Structure

```json
{
  "detail": {
    "code": "deactivate_blocked",
    "message": "无法停用：仍有 1 个启用中的下级部门、12 名在职/试用期员工引用",
    "field_errors": {"is_active": "存在启用中的下级部门"},
    "blockers": [
      {"type": "department", "id": "019...", "code": "D2", "label": "D2 生产部"},
      {"type": "employee", "id": "019...", "code": "E1001", "label": "E1001 张三"}
    ],
    "blocker_count": 13
  }
}
```

- `type`: `company`, `department`, `position`, `cost_center`, `employee`.
- `blockers` contains at most 20 entries, ordered by fixed type order and then `code` ascending; `blocker_count` is the total and is not truncated.
- `label` is `code + space + name`; for employees, `employee_no + space + name`.
- Delete blocked uses `referenced`; deactivate blocked uses `deactivate_blocked`; activation blocked uses `activation_blocked` with `field_errors.is_active` and does not require `blockers`.

#### 5.5.4 OpenAPI and Frontend Errors

- Each endpoint declares `responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}}`; 422 is generated by FastAPI automatically. Generated client types include these errors.
- Legacy endpoints (`login`, `users`, `items` before removal) keep string `detail`; the frontend error reader handles string, object, and array `detail`.

### 5.6 Validation Rules

#### 5.6.1 Layering

- **Pydantic / 422**: type, required, length, enum, regex, single-field range (`budget >= 0`, `warn_pct 1..100`, `daily_hours`, `monthly_rest`, `confidentiality_level`, `hire_date <= today`, `resign_date <= today`); query type/range.
- **Service layer / 409**: uniqueness, reference existence, same-company, cycles, inactive/active rules, status machine, delete references, cross-field date rules (`resign_date >= hire_date`).
- **Database backstop**: unique constraints and `RESTRICT`; catch `IntegrityError` and return 409 `duplicate_code` without exposing database text.

#### 5.6.2 Create and Update References

- Creating any organization entity requires the owning company to be active.
- Department / cost center: `parent_id` must be in the same company, not self, not a descendant, and the parent must be active.
- Position: `company_id` is immutable after creation; `dept_id` must be in the same company and the department must be active.
- Employee: `dept_id`, `position_id`, and `cost_org_id` must be in the same company and active; `manager_id` must be in the same company, active/probation, not self, and not create a cycle.
- Creating an entity with `is_active=false` is allowed, but the target parent must still be active.
- `company_id` on company-owned entities and all business codes are immutable after creation.

#### 5.6.3 PATCH Semantics

- Omitted field = unchanged; explicit `null` = clear a nullable field (`parent_id`, `manager_id`, `cost_org_id`, `note`, `resign_date`); `null` on a non-nullable field returns 422.
- `note: ""` is normalized to `null`.
- A PATCH may change multiple fields; validate against the final state (for example, changing `parent_id` and `is_active` together).
- Inactive entities allow non-structural edits (name, note, order, `budget`/`warn_pct`); structural fields (department `parent_id`, cost center `parent_id`, position `dept_id`) return 409 `inactive_entity`.
- Employee status:
  - `probation → active`: allowed, may be combined with other edits.
  - `active/probation → resigned`: must include `resign_date`; the request may contain only `status`, `resign_date`, and `note`; other fields return 409 `locked_field`.
  - Already resigned: only `note` and `resign_date` (correction) are editable; other fields return 409 `locked_field`.
  - `resigned → active/probation` and `active → probation` return 409 `invalid_status_transition`.
  - `status != resigned` with `resign_date` returns 409 `invalid_status_transition`.
  - `resign_date < hire_date` returns 409 `invalid_status_transition`; `resign_date > today` returns 422.

#### 5.6.4 Deactivation and Activation

- Deactivation blocked (`deactivate_blocked`):
  - Company: any active department/position/cost center or active/probation employee.
  - Department: any active child department or active/probation employee whose `dept_id` is this department.
  - Position: any active/probation employee.
  - Cost center: any active child cost center or active/probation employee.
  - Resigned employees do not block.
- Reactivation blocked (`activation_blocked`): the company must be active (companies have no parent); departments, positions, and cost centers require the company and all ancestors to be active. An inactive default department on a position does not block reactivation and is displayed as 「已停用」.

#### 5.6.5 Delete

- Company: any department, position, cost center, or employee blocks with 409 `referenced`.
- Department: any child department or any employee (including resigned) blocks with 409 `referenced`; deleting sets `position.dept_id` to null for positions that used it as default.
- Position: any employee (including resigned) blocks with 409 `referenced`.
- Cost center: any child cost center or any employee (including resigned) blocks with 409 `referenced`.
- Employee: no delete endpoint; `status=resigned` is terminal.
- Hard delete frees the business code for reuse.

### 5.7 Examples

#### 5.7.1 Create Employee (201)

```json
POST /api/v1/employees/
{
  "employee_no": "E1001",
  "name": "张三",
  "gender": "male",
  "dept_id": "019a...",
  "position_id": "019a...",
  "cost_org_id": "019a...",
  "manager_id": "019a...",
  "status": "probation",
  "hire_date": "2026-03-01",
  "contract_type": "full_time",
  "daily_hours": "8.00",
  "monthly_rest": 8,
  "confidentiality_level": 2,
  "note": null
}
```

```json
{
  "id": "019a...",
  "employee_no": "E1001",
  "name": "张三",
  "gender": "male",
  "dept_id": "019a...",
  "position_id": "019a...",
  "cost_org_id": "019a...",
  "manager_id": "019a...",
  "status": "probation",
  "hire_date": "2026-03-01",
  "resign_date": null,
  "contract_type": "full_time",
  "daily_hours": "8.00",
  "monthly_rest": 8,
  "confidentiality_level": 2,
  "note": null,
  "company_id": "019a...",
  "company_name": "荣新建设",
  "dept_name": "生产部",
  "position_name": "项目经理",
  "cost_org_name": "生产成本中心",
  "manager_name": "李四",
  "manager_status": "active",
  "created_at": "2026-11-01T08:00:00Z",
  "updated_at": "2026-11-01T08:00:00Z"
}
```

#### 5.7.2 Delete Blocked (409)

```json
DELETE /api/v1/departments/019a...
{
  "detail": {
    "code": "referenced",
    "message": "无法删除：仍有 1 个子部门、2 名员工引用",
    "blockers": [
      {"type": "department", "id": "019a...", "code": "D2", "label": "D2 生产部"},
      {"type": "employee", "id": "019a...", "code": "E1001", "label": "E1001 张三"},
      {"type": "employee", "id": "019a...", "code": "E1002", "label": "E1002 李四"}
    ],
    "blocker_count": 3
  }
}
```

#### 5.7.3 Cycle (409)

```json
PATCH /api/v1/departments/019a...
{"parent_id": "019a..."}

{
  "detail": {
    "code": "cycle",
    "message": "上级部门不能是自身或下级部门",
    "field_errors": {"parent_id": "上级部门不能是自身或下级部门"}
  }
}
```

#### 5.7.4 Validation Error (422)

```json
POST /api/v1/departments/
{"dept_name": "生产部"}

{
  "detail": [
    {
      "loc": ["body", "dept_code"],
      "msg": "此字段为必填项",
      "type": "missing"
    }
  ]
}
```

#### 5.7.5 Department Tree (200)

```json
GET /api/v1/departments/tree?company_id=019a...&is_active=true
{
  "data": [
    {
      "id": "019a...",
      "dept_code": "D1",
      "dept_name": "总部",
      "company_id": "019a...",
      "company_name": "荣新建设",
      "parent_id": null,
      "parent_name": null,
      "manager_id": "019a...",
      "manager_name": "张三",
      "manager_status": "active",
      "order_no": 0,
      "is_active": true,
      "note": null,
      "created_at": "2026-11-01T08:00:00Z",
      "updated_at": "2026-11-01T08:00:00Z",
      "children": [
        {
          "id": "019a...",
          "dept_code": "D2",
          "dept_name": "生产部",
          "children": [],
          "...": "..."
        }
      ]
    }
  ]
}
```

## 6. Authentication and Authorization

- Reuse the existing JWT login (`POST /api/v1/login/access-token`).
- All Basic Management endpoints depend on `CurrentUser` (any logged-in user); no superuser requirement, no RBAC, no department data scope.
- Existing authentication behavior is unchanged:
  - Missing/expired token: 401 with `{"detail": "未登录或登录状态已过期"}`.
  - Invalid token: 403 with `{"detail": "无法验证登录凭证"}`.
  - Inactive account: 400 with `{"detail": "账号已停用"}`.
- The frontend uses the generated client with the bearer token from the existing auth flow.
- Employees are not system users; creating an employee does not create a login account.

## 7. Frontend Information Architecture and Interaction

### 7.1 Navigation and Company Context

- Sidebar:
  - Dashboard (仪表盘).
  - Basic Management (基础管理) group with five entries: Companies (公司), Departments (部门), Employees (员工), Positions (岗位), Cost Centers (成本中心).
  - System (系统) group with Admin (管理后台), retained and not extended; superuser only.
- Remove the Items demo page and sidebar entry.
- Company context:
  - A global company switcher in the top bar applies to Departments, Positions, Employees, and Cost Centers.
  - The Companies page is the company profile maintenance page and is not scoped by the switcher.
  - Switching the company changes the data scope of all Basic Management pages.
  - The selected company is persisted in `localStorage`; if it is missing or inactive, fall back to the first active company.

### 7.2 Page Inventory

| Page | Layout | Main interactions |
|---|---|---|
| Companies (公司) | Table + form drawer | Create/edit company; toggle active; delete with blocked-reference dialog; switch company from the table or top bar |
| Departments (部门) | Left tree + right detail | Create/edit/move department; set manager; delete with blocked dialog; deactivate with blocked reasons; cycle prevention in parent selector; show child departments and positions using this default department |
| Positions (岗位) | Full-width table + form drawer | Create/edit position; select default department; delete with blocked dialog; deactivate |
| Employees (员工) | Left department tree + filters + full-width table + right detail/edit drawer | Create/edit employee; form groups Basic Info / Administrative Assignment / Cost Assignment / Reporting; filter by department subtree, status, keyword; leave action; resigned-field locking; Unassigned cost view |
| Cost Centers (成本中心) | Left tree + right detail | Create/edit/move cost center; set manager; budget / `warn_pct`; delete with blocked dialog; deactivate; tree tail 「未分配」 entry and employee list |

### 7.3 Page Flows

1. **Company management**: list companies → create/edit in drawer → toggle active → delete (blocked dialog if referenced) → switch company.
2. **Department management**: select company → tree → select node → right detail → create child/edit/move in drawer → delete (blocked dialog) → toggle active (blocked reasons).
3. **Position management**: select company → table → create/edit in drawer → choose default department → delete (blocked dialog) → toggle active.
4. **Employee management**: select company → department tree filters the table → create/edit in drawer → choose department/position/cost center/manager → save → filter by status/keyword → leave action → resigned fields locked.
5. **Cost center management**: select company → tree → select node → right detail → create child/edit/move → budget / `warn_pct` → delete (blocked dialog) → toggle active → 「未分配」 entry lists employees with no cost center.

### 7.4 Interaction Rules

- **Active/inactive**: use a switch (滑块) in create/edit forms for the four organization entities. Show 「启用 / 停用」. Blocked deactivation shows the reason(s) and does not change the switch.
- **Blocked delete**: show a dialog with the Chinese message, blocking references (`blockers`), total count, and a disabled delete confirmation.
- **Cycle prevention**: parent selectors disable the current node and its descendants; manager selectors disable self, descendants/reports that would create a cycle, and resigned employees (existing historical manager references remain visible).
- **Unassigned**: the cost organization tree has a 「未分配」 entry at the tail; it opens the employee list filtered by `unassigned_cost_org=true`.
- **Employee status**: three states; default list filter is active + probation; switch to all or resigned only.
- **Resigned employees**: show a read-only detail; only note and resign date are editable.
- **States**: every list/tree/detail has loading, empty, and error states; forms show field-level Chinese validation messages; 409 field errors map to the corresponding form fields when possible.
- **Responsive**: sidebar collapses on narrow screens; two-column layouts stack; tables scroll horizontally; drawers become full-width.
- **Theme**: dark mode follows the existing `.dark` variables; theme does not change the information architecture.

### 7.5 Prototype and Screenshots

- Prototype entry: [`docs/prototypes/basic-management-ia/index.html`](../prototypes/basic-management-ia/index.html)
- Prototype notes: [`docs/prototypes/basic-management-ia/README.md`](../prototypes/basic-management-ia/README.md)
- Screenshots: [`docs/prototypes/basic-management-ia/screenshots/`](../prototypes/basic-management-ia/screenshots/)
- Scheme A is authoritative. Schemes B and C remain in the prototype as alternatives and are not implemented.

## 8. Implementation Architecture

### 8.1 Backend File Map

```text
backend/app/
├── enums.py                     # Gender, EmployeeStatus, ContractType
├── models.py                    # SQLModel table models: User, Company, Department, Position, CostCenter, Employee
├── schemas_basic.py             # Basic Management Create/Update/Public/List/Tree/Error schemas
├── core/
│   └── errors.py                # DomainError, ErrorDetail, Blocker, ErrorResponse, handlers, 422 translation
├── services/
│   ├── __init__.py
│   ├── common.py                # shared validation, pagination, tree building, display enrichment, blockers
│   ├── companies.py
│   ├── departments.py
│   ├── positions.py
│   ├── cost_centers.py
│   └── employees.py
├── api/
│   ├── main.py                  # include five routers; remove items
│   └── routes/
│       ├── companies.py
│       ├── departments.py
│       ├── positions.py
│       ├── cost_centers.py
│       └── employees.py
├── crud.py                      # User-only CRUD; no new domain CRUD
└── seed_dev.py                  # dev-only idempotent seed script
```

Tests and scripts:

```text
backend/tests/
├── conftest.py                  # test DB override, guard, per-test cleanup
├── utils/                       # user/auth + company/department/position/cost_center/employee factories
├── api/routes/                  # API tests per resource
└── scripts/test_initial_data.py # retained/updated; add seed idempotency coverage
backend/scripts/
└── create-test-db.sh            # create app_test if missing
```

### 8.2 Backend Conventions

- **Models**: table-only SQLModel classes; no `Relationship` on the five new entities. Remove `Item` and `User.items`. Use UUID v7, `get_datetime_utc`, and non-native enum columns. Foreign keys and `ondelete` match section 4.7.
- **Schemas**: `schemas_basic.py` holds Pydantic request/response models. Write schemas use `extra="forbid"` and `from_attributes` where needed for responses. Public schemas include display fields; request schemas use IDs only.
- **Services**: one module per resource plus `common.py`. Functions:
  - `list_*`, `get_*`, `create_*`, `update_*`, `delete_*`, `tree_*`.
  - Shared helpers: code normalization and validation, company existence/active checks, same-company checks, parent/manager validation, cycle detection, blocker collection, display-name batch enrichment, pagination, tree construction.
  - Services set `updated_at` on update and catch `IntegrityError` for duplicate codes.
  - Display names are resolved with batched queries (avoid N+1); no ORM relationship traversal.
- **Routes**: thin; bind `SessionDep`, `CurrentUser`, path/query/body; call the service; return the response model. Use `APIRouter(prefix="/companies", tags=["companies"])` etc. Declare `responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}}`.
- **Errors**: raise `DomainError(code, message, field_errors, blockers, blocker_count)`; `not_found` maps to 404, other domain codes to 409. Register `domain_error_handler` in `app.main`. Extend `translate_validation_error` with `extra_forbidden` → 「该字段不可修改」.
- **Pagination**: shared helper returns `(items, count)`; `count` is computed with the same filters before applying `offset`/`limit`.
- **Trees**: build nested nodes after loading all nodes for the company in the fixed sort order; `children` is always an array.
- **Ordering**: use `col(...)` and explicit `order_by` per the API contract.
- **Generated client**: route function names and tags determine the generated service methods; do not hand-edit `frontend/src/client`.

### 8.3 Frontend File Map

```text
frontend/src/
├── routes/_layout/
│   ├── companies.tsx
│   ├── departments.tsx
│   ├── positions.tsx
│   ├── cost-centers.tsx
│   └── employees.tsx
├── components/
│   ├── BasicManagement/
│   │   ├── shared/
│   │   │   ├── CompanySwitcher.tsx
│   │   │   ├── TreePanel.tsx
│   │   │   ├── FormDrawer.tsx
│   │   │   ├── StatusSwitch.tsx
│   │   │   ├── DeleteBlockedDialog.tsx
│   │   │   ├── EntitySelect.tsx
│   │   │   └── StateViews.tsx      # LoadingState, EmptyState, ErrorState
│   │   ├── companies/             # CompanyTable, CompanyForm
│   │   ├── departments/           # DepartmentTree, DepartmentDetail, DepartmentForm
│   │   ├── positions/             # PositionTable, PositionForm
│   │   ├── cost-centers/          # CostCenterTree, CostCenterDetail, CostCenterForm, UnassignedEmployees
│   │   └── employees/             # EmployeeTable, EmployeeFilters, EmployeeDetail, EmployeeForm
│   └── Sidebar/AppSidebar.tsx      # five module entries + Admin; remove Items
├── contexts/
│   └── CompanyContext.tsx
├── lib/
│   ├── enums.ts                   # Chinese labels and option arrays
│   └── api-error.ts               # getErrorMessage, getFieldErrors
├── utils.ts                       # handleError delegates to api-error
└── routes/_layout.tsx             # mount CompanyProvider and CompanySwitcher in the header
```

Tests:

```text
frontend/tests/
├── auth.setup.ts                  # unchanged
├── navigation.spec.ts
├── companies.spec.ts
├── departments.spec.ts
├── positions.spec.ts
├── cost-centers.spec.ts
├── employees.spec.ts
├── states.spec.ts
└── utils/
    ├── api.ts                     # generated-client API setup helpers
    └── random.ts                  # random codes/names for unique test data
```

### 8.4 Frontend Conventions

- **Company context**: `CompanyContext.tsx` exports `CompanyProvider` and `useCompany()`. The provider loads companies (`GET /companies/?limit=100`), reads `basic-management.company_id` from `localStorage`, defaults to the first active company, and falls back if the stored company is missing/inactive. `CompanySwitcher` is mounted in the `_layout` header. Selected company changes drive all Basic Management queries.
- **Data fetching**: TanStack Query. Query keys:
  - `["basic","companies",filters]`
  - `["basic","departments","list",companyId,filters]`
  - `["basic","departments","tree",companyId,isActive]`
  - `["basic","positions","list",companyId,filters]`
  - `["basic","cost-centers","list",companyId,filters]`
  - `["basic","cost-centers","tree",companyId,isActive]`
  - `["basic","employees","list",filters]`
  - `["basic","<resource>","detail",id]`
  Mutations invalidate the affected list, tree, detail, and company keys.
- **Forms**: react-hook-form + zod; existing shadcn `Form`, `Sheet` (drawer), `Dialog` (confirmation), `Select`, `Switch`, `Button`, `LoadingButton`. Field-level errors come from zod and API `field_errors` / 422 `loc`.
- **Tables**: existing `DataTable` (TanStack Table) for companies, positions, employees. Trees use a recursive `TreePanel`.
- **Errors**: `src/lib/api-error.ts`:
  - `getErrorMessage(err)`: handles `detail` string, `detail` object (`detail.message`), and `detail` array (`detail[0].msg`).
  - `getFieldErrors(err)`: maps 409 `field_errors` and 422 `loc`/`msg` to form fields.
  - `src/utils.ts` `handleError` delegates to `getErrorMessage`; existing components keep working.
- **Enums**: `src/lib/enums.ts` is the only source for Chinese labels and option arrays; all components import from it.
- **State components**: `StateViews.tsx` provides loading, empty, and error states for lists, trees, and details.
- **State management**: no Zustand and no URL synchronization for the selected company in this phase. Company selection is context + `localStorage`.
- **Generated client**: run `bash scripts/generate-client.sh` after backend changes, commit `frontend/openapi.json` and `frontend/src/client`; never hand-edit generated files. Tags map to `CompaniesService`, `DepartmentsService`, `PositionsService`, `CostCentersService`, `EmployeesService`.

### 8.5 Generated Client Workflow

1. Backend routes/schemas change.
2. Run `bash scripts/generate-client.sh` from the repository root.
3. Review the diff in `frontend/openapi.json` and `frontend/src/client`.
4. Commit both generated files with the backend change.
5. Use the generated service methods from components; do not call `fetch`/`axios` directly for Basic Management.

## 9. Migration Strategy

### 9.1 Migration Chain

Current head: `fe56fa70289e`. Add three migrations after it:

| Order | Migration | down_revision | Content |
|---|---|---|---|
| 1 | `create_basic_management_tables` | `fe56fa70289e` | Create five tables, unique constraints, indexes, non-manager FKs; `manager_id` columns only |
| 2 | `add_manager_foreign_keys` | migration 1 | Add the three `manager_id` FKs (`ON DELETE SET NULL`) |
| 3 | `drop_item_table` | migration 2 | Drop the `item` table; downgrade recreates an empty table matching the current schema |

- File names follow the existing `<revision>_<slug>.py` style; hand-write or review autogenerated migrations line by line.
- Run `alembic upgrade head` from `backend/scripts/prestart.sh`; tests run the same migration chain against `app_test`.

### 9.2 Table Definitions

| Table | Key columns and constraints |
|---|---|
| `company` | `id` UUID PK; `company_code` VARCHAR(32) NOT NULL; `company_name` VARCHAR(100) NOT NULL; `is_active` BOOLEAN NOT NULL; `note` VARCHAR(500) NULL; `created_at` / `updated_at` TIMESTAMPTZ NOT NULL |
| `department` | `id` UUID PK; `dept_code` VARCHAR(32) NOT NULL; `dept_name` VARCHAR(100) NOT NULL; `company_id` UUID NOT NULL FK `company` RESTRICT; `parent_id` UUID NULL FK `department` RESTRICT; `manager_id` UUID NULL (FK added in migration 2); `order_no` INTEGER NOT NULL; `is_active` BOOLEAN NOT NULL; `note` VARCHAR(500) NULL; timestamps |
| `position` | `id` UUID PK; `position_code` VARCHAR(32) NOT NULL; `position_name` VARCHAR(100) NOT NULL; `company_id` UUID NOT NULL FK `company` RESTRICT; `dept_id` UUID NULL FK `department` SET NULL; `order_no` INTEGER NOT NULL; `is_active` BOOLEAN NOT NULL; `note` VARCHAR(500) NULL; timestamps |
| `cost_center` | `id` UUID PK; `cost_org_code` VARCHAR(32) NOT NULL; `cost_org_name` VARCHAR(100) NOT NULL; `company_id` UUID NOT NULL FK `company` RESTRICT; `parent_id` UUID NULL FK `cost_center` RESTRICT; `manager_id` UUID NULL (FK added in migration 2); `budget` NUMERIC(14,2) NOT NULL; `warn_pct` INTEGER NOT NULL; `order_no` INTEGER NOT NULL; `is_active` BOOLEAN NOT NULL; `note` VARCHAR(500) NULL; timestamps |
| `employee` | `id` UUID PK; `employee_no` VARCHAR(32) NOT NULL; `name` VARCHAR(100) NOT NULL; `gender` VARCHAR NULL; `dept_id` UUID NOT NULL FK `department` RESTRICT; `position_id` UUID NOT NULL FK `position` RESTRICT; `cost_org_id` UUID NULL FK `cost_center` RESTRICT; `manager_id` UUID NULL (FK added in migration 2); `status` VARCHAR NOT NULL; `hire_date` DATE NOT NULL; `resign_date` DATE NULL; `contract_type` VARCHAR NOT NULL; `daily_hours` NUMERIC(4,2) NULL; `monthly_rest` INTEGER NULL; `confidentiality_level` INTEGER NULL; `note` VARCHAR(500) NULL; timestamps |

- Enums: `gender` (`male`/`female`/`unknown`), `status` (`active`/`probation`/`resigned`), `contract_type` (`full_time`/`part_time`/`intern`/`labor`). Store as `VARCHAR + CHECK` via non-native `SAEnum`; do not create PostgreSQL native enum types.
- UUID primary keys: `sa.UUID(as_uuid=True)` with Python `uuid.uuid7`; no server default.
- Timestamps: `TIMESTAMPTZ NOT NULL`, Python defaults; `updated_at` refreshed by the service layer; no database trigger; no `created_by`/`updated_by`.
- `is_active`, `order_no`, `budget`, and `warn_pct` defaults are supplied by the model/Pydantic layer, matching the API contract.

### 9.3 Naming, Indexes, and Checks

- Unique constraints: `uq_company_company_code`, `uq_department_company_dept_code`, `uq_position_company_position_code`, `uq_cost_center_company_cost_org_code`, `uq_employee_employee_no`.
- Foreign keys: `fk_<table>_<column>_<target>`, for example `fk_department_company_id_company`, `fk_position_dept_id_department`, `fk_employee_manager_id_employee`.
- Indexes: `ix_<table>_<columns>`. Create:
  - `ix_department_company_id`, `ix_department_parent_id`, `ix_department_manager_id`;
  - `ix_position_company_id`, `ix_position_dept_id`;
  - `ix_cost_center_company_id`, `ix_cost_center_parent_id`, `ix_cost_center_manager_id`;
  - `ix_employee_dept_id`, `ix_employee_position_id`, `ix_employee_cost_org_id`, `ix_employee_manager_id`, `ix_employee_status`.
- No standalone `is_active` index, no full-text/trigram index; `order_no` is not indexed.
- Check constraints: `ck_cost_center_budget_non_negative`, `ck_cost_center_warn_pct_range`, `ck_employee_daily_hours_range`, `ck_employee_monthly_rest_non_negative`, `ck_employee_confidentiality_level_range`, `ck_employee_resign_date_after_hire`, `ck_employee_resigned_date_required`, plus enum checks `ck_employee_gender`, `ck_employee_status`, `ck_employee_contract_type`.
- Unique constraints and checks are backstops; the application still returns Chinese 409/422 and never exposes database text.

### 9.4 Migration 2: Manager Foreign Keys

- Add `fk_department_manager_id_employee`, `fk_cost_center_manager_id_employee`, `fk_employee_manager_id_employee`, all `ON DELETE SET NULL`.
- Separate migration reason: `department.manager_id` / `employee.dept_id` and `cost_center.manager_id` / `employee.cost_org_id` form circular foreign keys; splitting avoids `use_alter` and same-migration create-then-alter complexity.
- Downgrade drops the three FKs before dropping tables.

### 9.5 Migration 3: Remove Items

- `op.drop_table("item")`; downgrade recreates an empty table matching the current `item` schema (`id` UUID PK, `title` VARCHAR(255) NOT NULL, `description` VARCHAR(255) NULL, `owner_id` UUID NOT NULL FK `user.id` CASCADE, `created_at` TIMESTAMPTZ NULL).
- Data is not recoverable: run `pg_dump` before applying in a shared environment; use `docker compose down -v` in development.
- Single-instance Docker Compose deployments stop the old backend before migrating; for zero-downtime, split into two releases (remove code first, drop the table later).

### 9.6 Rollback

- Migration 3: downgrade recreates an empty `item` table; data is not restored.
- Migration 2: downgrade drops the three manager FKs.
- Migration 1: downgrade drops tables in reverse order (employee → cost_center → position → department → company).
- CI and local test databases run `upgrade → downgrade base → upgrade` as a round-trip; back up shared environments before rollback.

## 10. Implementation Order and Parallelism

### 10.1 Phase 0: Foundation

1. Remove Items:
   - Backend: delete `api/routes/items.py`, its registration in `api/main.py`, `Item*` models and `User.items`, `crud.create_item`, `tests/api/routes/test_items.py`, `tests/utils/item.py`; remove `Item` cleanup from `conftest.py`; remove item deletion from `users.delete_user` and its import.
   - Frontend: delete `routes/_layout/items.tsx`, `components/Items/*`, `components/Pending/PendingItems.tsx`, the sidebar entry, `tests/items.spec.ts`, and `randomItem*` helpers; regenerate the route tree and client.
   - README: remove the Items screenshot/section; delete `img/dashboard-items.png` (or leave unreferenced).
2. Models and enums: five tables, `app/enums.py`, `app/schemas_basic.py`.
3. Migrations: the three migrations in section 9; `alembic upgrade head` repeatable.
4. Error model: `DomainError`, `ErrorDetail`, `Blocker`, `ErrorResponse`, handler; `extra_forbidden` translation; route `responses`.
5. Test foundation: `TEST_DATABASE_URL`, `app_test`, `create-test-db.sh`, conftest override/guard, per-test cleanup, entity factories.
6. Frontend shell: sidebar five modules + Admin, top-bar company switcher, `enums.ts`, `api-error.ts`, basic route placeholders.
7. Seed skeleton: `app/seed_dev.py` guard and idempotent skeleton.
8. Generated artifacts: `bash scripts/generate-client.sh`; commit `frontend/openapi.json` and `frontend/src/client`; build passes.

Phase 0 gate: migration round-trip passes; backend tests green; `bun run build` passes; `/api/v1/items` returns 404; no Items references in code/tests/frontend.

### 10.2 Module Slices

```text
Phase 0 → Company → Department → (Position ∥ Cost Center) → Employee → Full E2E + demo + docs
```

| Slice | Scope | Depends on |
|---|---|---|
| Company | CRUD, active toggle, delete blockers, list/filter, page, tests, seed | Phase 0 |
| Department | Tree/list CRUD, parent/cycle, manager, delete/deactivate rules, page, tests, seed | Company |
| Position | CRUD, default department, delete/deactivate rules, page, tests, seed | Department |
| Cost Center | Tree/list CRUD, parent/cycle, budget/`warn_pct`, Unassigned, page, tests, seed | Department |
| Employee | CRUD (no delete), status machine, manager, assignments, filters, page, tests, seed | Position + Cost Center |

- Within a slice: model/schema → API + backend tests → regenerate client → frontend page + E2E → seed/docs.
- Position and cost center can run in parallel after department; employee is last and is the critical path end.
- Recommended ownership: one full-stack owner per slice; `frontend/src/client` is a shared serial point, generated and committed at each slice boundary.
- Do not split into long-lived "all API" and "all UI" swimlanes; feedback arrives too late.

### 10.3 Per-Slice Checklist

- [ ] Model/schema and migration dependencies in place.
- [ ] Endpoints implemented per #7, including query parameters and error responses.
- [ ] Service rules and Chinese messages implemented.
- [ ] Backend tests added and green (including error codes).
- [ ] Client regenerated, committed, and type-checks.
- [ ] Frontend page and interactions implemented per Scheme A.
- [ ] Loading/empty/error states and responsive/theme behavior.
- [ ] Playwright spec added and green.
- [ ] Seed data includes the module.
- [ ] Docs/demo script updated; no Items references.

## 11. Test Strategy

### 11.1 Backend Test Isolation

- Add `TEST_DATABASE_URL` (`app_test`); `conftest.py` overrides `DATABASE_URL` with it **before importing `app`**.
- The database name must end with `_test`; otherwise the test session fails immediately. Never truncate a development or production database.
- Session start: run `alembic upgrade head`; ensure `FIRST_SUPERUSER` exists.
- Before each test: `TRUNCATE company CASCADE` (cascades to department, position, cost_center, employee) and delete non-superuser users; keep `FIRST_SUPERUSER`.
- Fixtures: `client`, `session`, `superuser_token_headers`; add company/department/position/cost_center/employee factories under `backend/tests/utils/`.
- No transaction-rollback fixture: TestClient commits internally and nested transactions are costly; the tables are small and TRUNCATE is fast.

### 11.2 Backend Test Matrix

| Area | Coverage |
|---|---|
| Cross-cutting | 401; 422 Chinese translation; 404/409 envelope; `skip`/`limit` bounds; fixed sorting; `keyword`; display names; company scoping; `/api/v1/items` 404 |
| Company | CRUD; global `company_code` uniqueness; code/company immutability; delete blocked by department/position/cost center/employee; deactivate blocked by active children or active/probation employees; reactivate; list `is_active`/`keyword` |
| Department | CRUD; company-scoped `dept_code` uniqueness; parent same company/not self/not descendant; manager same company and active/probation; delete blocked by children/employees with `position.dept_id` set null; deactivate blocked by active children/active employees; inactive structural lock; reactivation requires ancestors; tree structure/order/`is_active`; `parent_id` filter |
| Position | CRUD; company-scoped `position_code` uniqueness; default department same company/active; delete blocked by employees (including resigned); deactivate blocked only by active/probation employees; reactivation requires company active; `dept_id` filter |
| Cost Center | CRUD; company-scoped `cost_org_code` uniqueness; parent same company/not self/not descendant; manager rules; `budget`/`warn_pct` ranges; delete blocked by children/employees; deactivate blocked by active children/active employees; reactivation requires ancestors; tree; Unassigned filter |
| Employee | Create only `active`/`probation`; global `employee_no` uniqueness; department/position/cost same company; manager same company/active/no cycle; status transitions and resigned locks; `hire_date`/`resign_date` rules; no DELETE; list filters (company/department subtree/status default/keyword/position/cost/Unassigned); display fields; company derived from department |
| Migration/seed | Upgrade from base; downgrade/upgrade round-trip; manager FKs exist; `item` table removed; seed idempotent across two runs; no active employees under inactive nodes |

### 11.3 Playwright E2E

| Spec | Coverage |
|---|---|
| `navigation.spec.ts` | Sidebar five modules, company switcher, Admin retained, Items entry gone |
| `companies.spec.ts` | Create/edit/deactivate/delete-blocked/switch company |
| `departments.spec.ts` | Tree CRUD, move, cycle prevention, delete blocked, deactivate blocked |
| `positions.spec.ts` | Create/edit, default department, delete blocked |
| `cost-centers.spec.ts` | Tree CRUD, budget/`warn_pct`, delete blocked, Unassigned entry |
| `employees.spec.ts` | Create (department tree/manager/cost), filters, leave, resigned lock, Unassigned cost |
| `states.spec.ts` | Representative loading/empty/error states, narrow-screen smoke |

- Each test creates its own company with a random code; all subsequent data belongs to that company. Assertions are scoped to the created company; no global count assertions.
- Setup data is created via `frontend/tests/utils/api.ts` using the generated client + a superuser token; primary flows use the UI.
- Empty-state tests create a fresh company with no children and switch to it.
- CI's four shards isolate via unique codes + company scope; do not rely on `afterEach` cleanup (deletion may be blocked); CI rebuilds the database at the end.
- E2E does not depend on developer seed data. Field-level validation and all error codes are covered by backend tests.

### 11.4 Migration and Seed Tests

- CI and the local test database run `alembic upgrade head → downgrade base → upgrade head`.
- A pytest guard asserts `/api/v1/items` returns 404 and the OpenAPI schema has no `items` tag.
- Seed runs twice against the test database; assert stable counts/codes, no duplicates, and no active employees under inactive nodes.

### 11.5 CI Gates

- Backend tests green; coverage ≥90%.
- `ruff`, `mypy`, `ty`, `biome` pass.
- `bun run build` passes.
- Playwright suite passes in four shards.
- Migration round-trip passes.
- Seed idempotency passes.
- `bash scripts/generate-client.sh` produces no uncommitted diff.
- `/api/v1/items` returns 404; OpenAPI has no `items` tag.

## 12. Development Seed Data

- Location: `backend/app/seed_dev.py`.
- Manual invocation:
  - Local: `cd backend && uv run python -m app.seed_dev`.
  - Compose: `docker compose exec backend python -m app.seed_dev`.
- Guard: refuse unless `settings.FASTAPI_ENV == "development"`; do not add to `prestart.sh`; never run in production.
- Idempotency: insert-if-missing by business code; never update, delete, or overwrite user edits.
- Dataset:
  - Three companies: a full organization (`C1`, 荣新建设), a small organization (`C2`, 荣新科技), and an empty company (`C3`, 荣新物流) for empty-state and switching demos.
  - Full company: 2–3 level department tree (总部 → 生产部 → 一车间, etc.), multi-level cost centers, 5–8 positions (some with default departments), 15–20 employees across active/probation/resigned with managers, some Unassigned cost centers, and varied contract types.
  - Small organization: 2–3 departments, 2 positions, 2 cost centers, 3–5 employees.
  - Include one inactive department and one inactive cost center with no active employee references to demonstrate the inactive state.
- Deterministic codes/names; dates not in the future; employees have no login accounts.
- Document the command in `development.md`; E2E does not use seed data.

## 13. Acceptance Criteria and Demo Script

### 13.1 Per-Module Definition of Done

Each module is done only when all eight items are true:

1. Migration/model/enums landed; `alembic upgrade head` repeatable.
2. All endpoints from the #7 contract implemented with matching schemas, auth, and error codes.
3. Service rules and Chinese messages complete (409/404/422 shapes).
4. Generated client regenerated and committed; frontend types are not hand-edited.
5. Page implements Scheme A: company context, loading/empty/error, form validation, blocked delete/deactivate/cycle dialogs, responsive layout, dark theme.
6. Backend pytest covers the module rules; Playwright covers the main flow and key blocking rules.
7. Developer seed data includes the module and is idempotent.
8. Docs/demo script updated; no Items references in code or tests.

### 13.2 Global Gates

- Backend tests green; coverage ≥90%.
- `ruff`, `mypy`, `ty`, `biome` pass.
- `bun run build` passes.
- Playwright suite passes (four CI shards).
- Migration `upgrade → downgrade → upgrade` round-trip passes.
- Seed runs twice with identical results.
- `bash scripts/generate-client.sh` leaves no uncommitted diff.
- `/api/v1/items` returns 404 and OpenAPI has no `items` tag.

### 13.3 Demo Script

1. Start Compose; run migrations and the development seed.
2. Log in.
3. Switch companies, including the empty company.
4. Company create/edit/delete; blocked delete shows blockers.
5. Department tree create/edit/move; cycle prevention; blocked delete; blocked deactivation.
6. Position create/edit; blocked delete.
7. Cost center tree; budget/`warn_pct`; Unassigned view; blocked delete.
8. Employee create with department tree, manager, and cost assignment; filters; leave; resigned-field lock.
9. Show Chinese errors and loading/empty/error states.
10. Switch back to another company and verify data-scope isolation.

## 14. Risks and Rollback

| Risk | Mitigation |
|---|---|
| Dropping `item` is irreversible | `pg_dump` before applying in shared environments; `docker compose down -v` in development; downgrade recreates an empty table only; README notes Items data is no longer available |
| Circular foreign keys break migrations | Split manager FKs into migration 2; downgrade drops FKs before tables |
| Stale Items references break frontend/tests | Phase 0 cleanup list; `/items` 404 guard; regenerate client/route tree and run a full build |
| `position` collides with a PostgreSQL keyword | Use `position` first; if Alembic/`psql` reports a reference error, rename to `position_arch` before merging and update all references consistently |
| `updated_at` not refreshed | Service layer refreshes it; tests assert `updated_at` changes after PATCH |
| Test database truncates development data | Conftest requires a `_test` database name; CI uses an isolated `app_test` |
| Playwright shard collisions | Unique company code per test + company-scoped assertions; no global count assertions |
| Coverage drops | Add tests with each slice; CI keeps the 90% gate |
| Seed overwrites user edits | Insert-if-missing by code; no update/delete; development guard |
| Old code still references `item` during deploy | Single-instance Compose stops the old backend before migrating; for zero-downtime, split into two releases (remove code first, drop table later) |
| Enum values change later | Non-native enum + `CHECK`; changing values requires a new migration, accepted cost |

## 15. Future Extensions

The following are outside this effort. They are recorded here so implementers do not accidentally design around them:

- Payroll binding: compensation components, calculation schemes, workday parameters on positions.
- Excel import/export templates for people/organization, positions, and cost organization.
- RBAC, department data scope, audit fields.
- Attendance management and DingTalk/OA integration.
- Transfer history, effective dates, approval flows.
- Rehire after resignation.
- Employee self-service H5 and release snapshots.
- Payroll expense statistics and budget alerts (cost center budget/warn are recorded but not computed).
- Group–subsidiary multi-level company hierarchy.
- Additional employee contact fields (phone, email, ID number), if the requirement adds them.
- i18n framework, only if a second locale becomes a real requirement (ADR-0002).

## 16. References

- [Organization model (#5)](https://github.com/nasa-du/anysys-hr/issues/5)
- [Employee model and lifecycle (#6)](https://github.com/nasa-du/anysys-hr/issues/6)
- [API contract (#7)](https://github.com/nasa-du/anysys-hr/issues/7)
- [Frontend IA and prototype (#8)](https://github.com/nasa-du/anysys-hr/issues/8)
- [Implementation order, migration, and acceptance plan (#9)](https://github.com/nasa-du/anysys-hr/issues/9)
- [Wayfinder map (#4)](https://github.com/nasa-du/anysys-hr/issues/4)
- [ADR-0001: UUID v7 primary keys](../adr/0001-uuid-v7-primary-keys.md)
- [ADR-0002: Simplified Chinese only, no i18n](../adr/0002-chinese-only-no-i18n.md)
- [ADR-0003: UUID v7 with business codes](../adr/0003-uuid-v7-with-business-codes.md)
- [GLOSSARY.md](../../GLOSSARY.md)
- [Requirement document](../requirement/rx-hr-requirement.html)
- [Prototype](../prototypes/basic-management-ia/index.html)
- [Prototype notes](../prototypes/basic-management-ia/README.md)
