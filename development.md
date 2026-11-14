# AnySys - Development

## Local Development

For local development, run PostgreSQL and Mailpit with Docker Compose, and run the FastAPI and Vite development servers locally.

Start the supporting services:

```bash
docker compose up -d db mailpit
```

Then, from the `backend` directory, install the dependencies and prepare the database:

```bash
uv sync
uv run bash scripts/prestart.sh
```

Start the FastAPI development server:

```bash
uv run fastapi dev
```

In another terminal, from the project root, install the frontend dependencies and start the Vite development server:

```bash
bun install
bun run dev
```

Now you can open these URLs:

Frontend development server: <http://localhost:5173>

Backend API: <http://localhost:8000>

Automatic interactive API documentation with Swagger UI: <http://localhost:8000/docs>

Mailpit: <http://localhost:8025>

The frontend development server uses the backend at `http://localhost:8000`, as configured in `frontend/.env`.

The interactive API documentation is only registered when `FASTAPI_ENV=development`. With `FASTAPI_ENV=production`, `/docs` and `/redoc` return 404.

### Development Seed Data

From the `backend` directory, seed the demo companies (`C1` 荣新建设, `C2` 荣新科技, `C3` 荣新物流, `C4` 荣新考勤演示) and their departments, positions, cost centers, and employees:

```bash
uv run python -m app.seed_dev
```

With the Docker Compose stack running, run the same script inside the backend
container (from the repository root):

```bash
docker compose exec backend python -m app.seed_dev
```

`C1` gets a three-level tree (`D1 总部` → `D2 生产部` → `D3 一车间` / `D4 二车间`, plus `D5 运营部` and `D6 财务部`), including the inactive `D7 旧项目部` for the inactive-state demo. `C2` gets a two-level tree, and `C3` stays empty for empty-state and company-switching demos.

`C1` also gets six positions (`P1 项目经理` through `P6 行政专员`), including positions with default departments and `P6` without one; `C2` gets two positions (`K1 研发工程师`, `K2 市场专员`).

`C1` gets a multi-level cost center tree (`K1 总部成本中心` → `K2 生产成本中心` → `K3 一车间成本中心` / `K4 二车间成本中心`, plus `K5 运营成本中心`), including the inactive `K6 旧项目成本中心` for the inactive-state demo; `C2` gets two cost centers (`K1 总部成本中心`, `K2 研发成本中心`).

`C1` also gets 16 employees (`E1001` 张建国 through `E1016` 周敏) with managers, a mix of active, probation, and resigned records, varied contract types, and two employees whose cost center is 「未分配」; `C2` gets four employees (`E2001` 李雷 through `E2004` 张军). Seeded employees have no login accounts.

`C4` is the attendance demo company. It has departments `D1`–`D4`, positions `P1`–`P5`, employees `E101`–`E113` (including duplicate names, one resignation before September, and one hire during September), the seven golden-case shifts, the company default attendance rule, and the 2026-09/2026-10 holidays. `C1`–`C3` never receive attendance rows. Plans, roster entries, and import batches are intentionally not seeded by the Phase 0 skeleton; later slices add them through the real service paths.

The script is idempotent — it inserts by business key and never overwrites existing rows — and refuses to run unless `FASTAPI_ENV=development`. It is not part of `prestart.sh`; run it manually when you want demo data.

The complete dataset, API/error model, migration chain, backup steps, and demo script are documented in [docs/basic-management.md](./docs/basic-management.md).

### Migrations and Backups

From the `backend` directory:

```bash
uv run alembic upgrade head
uv run alembic downgrade base   # development and test databases only
uv run alembic upgrade head
```

Back up a shared database with `pg_dump` before applying the migrations:
dropping the legacy `item` table is irreversible, and the downgrade recreates
only an empty table. For a local development reset, use
`docker compose down -v` and seed the fresh database again. See
[docs/basic-management.md](./docs/basic-management.md) for the full chain and a
backup example.

The attendance chain adds four migrations after `d66acc907e93`:
`attendance_core`, `attendance_scheduling`, `attendance_imports`, and
`attendance_results` (24 tables). Each migration supports an individual
`upgrade → downgrade → upgrade` round trip, and the full chain supports
`upgrade → downgrade base → upgrade`. Migrations insert no attendance rows.

### Attendance Foundation Tests

From the `backend` directory, with `TEST_DATABASE_URL` pointing at an existing
database whose name ends with `_test`:

```bash
uv run bash scripts/create-test-db.sh
uv run pytest tests/attendance -m "not performance"
uv run pytest tests/test_migrations.py tests/test_attendance_schema.py tests/scripts/test_seed_dev.py
uv run pytest tests/attendance/test_performance_smoke.py -m performance
```

The golden-case schema test validates all 26 cases in
`docs/specs/attendance-golden-cases/`. The test isolation fixture truncates
`company CASCADE` and asserts that all 24 attendance tables are empty before
every test.

### Frontend Served by FastAPI

Build the frontend from the `frontend` directory:

```bash
bun run build
```

The build is written to `backend/app/frontend` and served by FastAPI at <http://localhost:8000>. Rebuild the frontend after making frontend changes.

## Full Stack with Docker Compose

To run the backend and built frontend in Docker Compose:

```bash
docker compose run --rm backend bash scripts/prestart.sh
docker compose watch
```

Now you can open these URLs:

Application, with the frontend and API served by FastAPI: <http://localhost:8000>

Automatic interactive API documentation with Swagger UI: <http://localhost:8000/docs>

Adminer, database web administration: <http://localhost:8080>

Traefik UI, to see how the routes are being handled by the proxy: <http://localhost:8090>

Mailpit: <http://localhost:8025>

Stop a locally running FastAPI server before starting the Compose backend because both use port `8000`.

**Note**: The first time you start the stack, it might take a minute for all the services to be ready. To monitor it, use `docker compose logs`, or `docker compose logs backend` for the backend service.

## Mailpit

[Mailpit](https://mailpit.axllent.org) captures emails sent during local development instead of delivering them. The local backend connects to it at `localhost:1025`, and the Compose backend connects to the `mailpit` service. Captured emails are available at <http://localhost:8025>.

## Docker Compose Files and Environment Variables

The main `compose.yml` file contains the configuration shared by the whole stack. Docker Compose loads it automatically.

The `compose.override.yml` file adds local development settings, such as mounting the source code as a volume. Docker Compose also loads it automatically and applies it on top of `compose.yml`.

The `compose.deploy.yml` file contains the deployment-specific settings, including HTTPS and automatic certificate handling. It is explicitly combined with `compose.yml` when deploying the application.

The backend reads local settings from the `.env` file. Docker Compose also uses it for variable interpolation and passes the settings each container needs.

After changing variables, make sure you restart the stack:

```bash
docker compose watch
```

## The `.env` File

For a fresh checkout, create it from the template:

```bash
cp .env.example .env
```

The `.env` file contains local development defaults, passwords, and other configuration. Its hostnames use `localhost` for processes running on your machine. Docker Compose overrides hostnames such as the database and SMTP server with their Compose service names.

Do not store deployment secrets in `.env`. Configure them as described in the [Docker Compose deployment guide](./deployment-docker-compose.md).

## Pre-commit Hooks and Code Linting

The project uses [prek](https://prek.j178.dev/), a modern alternative to [pre-commit](https://pre-commit.com/), for code linting and formatting.

You can find a file `.pre-commit-config.yaml` with configurations at the root of the project.

### Install `prek` to Run Automatically

`prek` is already part of the dependencies of the project.

From the project root, install the Git hook so that `prek` runs automatically before each commit:

```bash
uv run prek install -f
```

The `-f` flag forces the installation, in case there was already a `pre-commit` hook previously installed.

Now whenever you try to commit, for example with:

```bash
git commit
```

`prek` will check and format the code you are about to commit. If it modifies any files, add those files to Git again before committing.

### Run `prek` Manually

You can also run `prek` manually on all files from the project root:

```bash
uv run prek run --all-files
```
