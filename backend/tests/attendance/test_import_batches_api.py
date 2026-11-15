"""Import commit, discard, revoke, and batch queries (spec 6.6-6.8, 8.3.4).

Seam: ``/api/v1/attendance/imports`` action and query endpoints. Commit is one
transaction that supersedes the current committed batch for the same company,
month, and data type, commits the preview, and marks the attendance month
stale. The batch is the unit of audit: superseded rows remain, while discarded
and revoked rows are deleted immediately.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, func, select

from app.enums import (
    AttendanceMonthStatus,
    ImportBatchStatus,
    ImportDataType,
    ImportSeverity,
)
from app.models import (
    AttendanceMonth,
    ImportBatch,
    ImportBatchError,
    PunchRecord,
    User,
)
from tests.utils.attendance_factories import (
    create_attendance_month,
    create_import_batch,
    create_import_batch_error,
    create_punch_record,
)
from tests.utils.attendance_imports import (
    IMPORTS_URL,
    preview_fixture,
    seed_fixture_employees,
)
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)
from tests.utils.utils import random_upper_code

MONTH = "2026-09"
MONTH_DATE = date(2026, 9, 1)


def error_detail(response: object) -> dict[str, object]:
    body = response.json()  # type: ignore[attr-defined]
    assert isinstance(body["detail"], dict), body
    return body["detail"]


def commit(client: TestClient, headers: dict[str, str], batch_id: str) -> object:
    return client.post(f"{IMPORTS_URL}/{batch_id}/commit", headers=headers)


def test_commit_supersedes_the_current_batch_and_marks_the_month_stale(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    employees = seed_fixture_employees(db, company)
    user = db.exec(select(User)).first()
    assert user is not None
    month_row = create_attendance_month(
        db, company_id=company.id, month=MONTH_DATE, is_stale=False
    )
    old_batch = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        status=ImportBatchStatus.COMMITTED,
        committed_at=datetime.now(UTC),
        valid_records=1,
    )
    create_punch_record(
        db,
        company_id=company.id,
        batch_id=old_batch.id,
        employee_id=employees["E101"].id,
    )
    preview = preview_fixture(
        client, superuser_token_headers, company.id, ImportDataType.PUNCH
    )
    assert preview.status_code == 200, preview.text
    batch_id = preview.json()["batch"]["id"]

    response = commit(client, superuser_token_headers, batch_id)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["superseded_batch_id"] == str(old_batch.id)
    assert body["month"] == MONTH
    assert body["is_stale"] is True
    assert body["batch"]["id"] == batch_id
    assert body["batch"]["status"] == "committed"
    assert body["batch"]["committed_at"] is not None
    assert body["batch"]["expires_at"] is None

    db.expire_all()
    superseded = db.get(ImportBatch, old_batch.id)
    assert superseded is not None
    assert superseded.status == ImportBatchStatus.SUPERSEDED
    assert superseded.superseded_at is not None
    assert str(superseded.superseded_by_batch_id) == batch_id
    assert (
        db.exec(
            select(func.count())
            .select_from(PunchRecord)
            .where(PunchRecord.batch_id == old_batch.id)
        ).one()
        == 1
    )
    committed = db.get(ImportBatch, uuid.UUID(batch_id))
    assert committed is not None
    assert committed.status == ImportBatchStatus.COMMITTED
    assert committed.committed_at is not None
    assert committed.expires_at is None
    refreshed_month = db.get(AttendanceMonth, month_row.id)
    assert refreshed_month is not None
    assert refreshed_month.status == AttendanceMonthStatus.DRAFT
    assert refreshed_month.is_stale is True


def test_commit_is_idempotent_for_an_already_committed_batch(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)
    preview = preview_fixture(
        client, superuser_token_headers, company.id, ImportDataType.PUNCH
    )
    assert preview.status_code == 200, preview.text
    batch_id = preview.json()["batch"]["id"]

    first = commit(client, superuser_token_headers, batch_id)
    assert first.status_code == 200, first.text

    second = commit(client, superuser_token_headers, batch_id)

    assert second.status_code == 200, second.text
    body = second.json()
    assert body["batch"]["id"] == batch_id
    assert body["batch"]["status"] == "committed"
    assert body["batch"]["committed_at"] == first.json()["batch"]["committed_at"]
    assert body["superseded_batch_id"] is None
    db.expire_all()
    assert db.exec(select(func.count()).select_from(ImportBatch)).one() == 1
    month_row = db.exec(select(AttendanceMonth)).one()
    assert month_row.status == AttendanceMonthStatus.DRAFT
    assert month_row.is_stale is True


def _batch_for(
    db: Session,
    company_id: uuid.UUID,
    *,
    status: ImportBatchStatus = ImportBatchStatus.PREVIEW,
    valid_records: int = 1,
    expires_at: datetime | None = None,
    discard_reason: str | None = None,
) -> ImportBatch:
    user = db.exec(select(User)).first()
    assert user is not None
    batch = create_import_batch(
        db,
        company_id=company_id,
        operator_id=user.id,
        status=status,
        valid_records=valid_records,
        expires_at=expires_at,
    )
    if discard_reason is not None:
        batch.discard_reason = discard_reason
        db.add(batch)
        db.commit()
        db.refresh(batch)
    return batch


def test_commit_unknown_batch_is_404(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = commit(client, superuser_token_headers, str(uuid.uuid7()))

    assert response.status_code == 404
    assert error_detail(response)["code"] == "not_found"


def test_commit_requires_authentication(client: TestClient) -> None:
    response = client.post(f"{IMPORTS_URL}/{uuid.uuid7()}/commit")

    assert response.status_code == 401


@pytest.mark.parametrize(
    "status",
    [
        ImportBatchStatus.SUPERSEDED,
        ImportBatchStatus.REVOKED,
        ImportBatchStatus.DISCARDED,
    ],
)
def test_commit_rejects_terminal_batches(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    status: ImportBatchStatus,
) -> None:
    company = create_company(db)
    batch = _batch_for(db, company.id, status=status)

    response = commit(client, superuser_token_headers, str(batch.id))

    assert response.status_code == 409
    assert error_detail(response)["code"] == "import_commit_conflict"


def test_commit_rejects_an_expired_preview(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    batch = _batch_for(
        db,
        company.id,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    response = commit(client, superuser_token_headers, str(batch.id))

    assert response.status_code == 409
    assert error_detail(response)["code"] == "preview_expired"
    db.expire_all()
    stored = db.get(ImportBatch, batch.id)
    assert stored is not None
    assert stored.status == ImportBatchStatus.DISCARDED
    assert stored.discard_reason == "expired"


def test_commit_reports_an_expired_preview_that_cleanup_already_discarded(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    batch = _batch_for(
        db,
        company.id,
        status=ImportBatchStatus.DISCARDED,
        discard_reason="expired",
    )

    response = commit(client, superuser_token_headers, str(batch.id))

    assert response.status_code == 409
    assert error_detail(response)["code"] == "preview_expired"


def test_commit_rejects_a_preview_without_valid_rows(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    batch = _batch_for(db, company.id, valid_records=0)

    response = commit(client, superuser_token_headers, str(batch.id))

    assert response.status_code == 409
    assert error_detail(response)["code"] == "no_valid_rows"


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (AttendanceMonthStatus.CONFIRMED, "month_confirmed"),
        (AttendanceMonthStatus.LOCKED, "month_locked"),
    ],
)
def test_commit_respects_the_month_gate(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    status: AttendanceMonthStatus,
    reason: str,
) -> None:
    company = create_company(db)
    create_attendance_month(db, company_id=company.id, month=MONTH_DATE, status=status)
    batch = _batch_for(db, company.id)

    response = commit(client, superuser_token_headers, str(batch.id))

    assert response.status_code == 409
    assert error_detail(response)["code"] == reason
    db.expire_all()
    stored = db.get(ImportBatch, batch.id)
    assert stored is not None
    assert stored.status == ImportBatchStatus.PREVIEW


def test_concurrent_commits_for_one_scope_return_one_success_and_one_conflict(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Lock, get_ident

    from app.core.db import engine
    from app.core.errors import DomainError
    from app.services.attendance import imports as import_service

    company = create_company(db)
    employees = seed_fixture_employees(db, company)
    user = db.exec(select(User)).first()
    assert user is not None
    first = _batch_for(db, company.id)
    second = _batch_for(db, company.id)
    create_punch_record(
        db,
        company_id=company.id,
        batch_id=first.id,
        employee_id=employees["E101"].id,
    )
    create_punch_record(
        db,
        company_id=company.id,
        batch_id=second.id,
        employee_id=employees["E102"].id,
        source_row_number=3,
    )

    barrier = Barrier(2, timeout=10)
    original = import_service._current_committed
    seen: set[int] = set()
    guard = Lock()

    def synchronized(session: Session, batch: ImportBatch) -> ImportBatch | None:
        thread = get_ident()
        with guard:
            is_first_call = thread not in seen
            seen.add(thread)
        if is_first_call:
            barrier.wait()
        return original(session, batch)

    monkeypatch.setattr(import_service, "_current_committed", synchronized)

    def run(batch_id: uuid.UUID) -> tuple[str, str]:
        with Session(engine) as session:
            operator = session.get(User, user.id)
            assert operator is not None
            try:
                result = import_service.commit_batch(
                    session, batch_id, operator=operator
                )
            except DomainError as error:
                return "error", error.code
            return "ok", str(result.batch.id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, batch.id) for batch in (first, second)]
        results = [future.result(timeout=30) for future in futures]

    assert sorted(result[0] for result in results) == ["error", "ok"]
    error = next(result for result in results if result[0] == "error")
    assert error[1] == "import_commit_conflict"

    db.expire_all()
    committed = db.exec(
        select(ImportBatch).where(ImportBatch.status == ImportBatchStatus.COMMITTED)
    ).all()
    assert len(committed) == 1
    previews = db.exec(
        select(ImportBatch).where(ImportBatch.status == ImportBatchStatus.PREVIEW)
    ).all()
    assert len(previews) == 1


def test_commit_failure_rolls_back_and_leaves_the_preview_retryable(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sqlalchemy.exc import IntegrityError

    from app.services.attendance import imports as import_service

    company = create_company(db)
    employees = seed_fixture_employees(db, company)
    user = db.exec(select(User)).first()
    assert user is not None
    month_row = create_attendance_month(
        db, company_id=company.id, month=MONTH_DATE, is_stale=False
    )
    old_batch = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        status=ImportBatchStatus.COMMITTED,
        valid_records=1,
    )
    old_row = create_punch_record(
        db,
        company_id=company.id,
        batch_id=old_batch.id,
        employee_id=employees["E101"].id,
    )
    preview = preview_fixture(
        client, superuser_token_headers, company.id, ImportDataType.PUNCH
    )
    assert preview.status_code == 200, preview.text
    batch_id = preview.json()["batch"]["id"]

    original_save = import_service._save_mapping_template

    def fail_save(*_args: object, **_kwargs: object) -> None:
        raise IntegrityError("INSERT", {}, Exception("simulated conflict"))

    monkeypatch.setattr(import_service, "_save_mapping_template", fail_save)
    failed = commit(client, superuser_token_headers, batch_id)
    assert failed.status_code == 409, failed.text
    assert error_detail(failed)["code"] == "import_commit_conflict"

    db.expire_all()
    target = db.get(ImportBatch, uuid.UUID(batch_id))
    assert target is not None
    assert target.status == ImportBatchStatus.PREVIEW
    assert target.committed_at is None
    restored = db.get(ImportBatch, old_batch.id)
    assert restored is not None
    assert restored.status == ImportBatchStatus.COMMITTED
    assert restored.superseded_at is None
    assert restored.superseded_by_batch_id is None
    assert db.get(AttendanceMonth, month_row.id).is_stale is False  # type: ignore[union-attr]
    assert db.get(PunchRecord, old_row.id) is not None

    monkeypatch.setattr(import_service, "_save_mapping_template", original_save)
    retried = commit(client, superuser_token_headers, batch_id)
    assert retried.status_code == 200, retried.text
    assert retried.json()["superseded_batch_id"] == str(old_batch.id)


def discard(client: TestClient, headers: dict[str, str], batch_id: str) -> object:
    return client.post(f"{IMPORTS_URL}/{batch_id}/discard", headers=headers)


def revoke(client: TestClient, headers: dict[str, str], batch_id: str) -> object:
    return client.post(f"{IMPORTS_URL}/{batch_id}/revoke", headers=headers)


def test_discard_deletes_preview_rows_and_marks_the_batch_discarded(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    employees = seed_fixture_employees(db, company)
    batch = _batch_for(db, company.id)
    create_punch_record(
        db,
        company_id=company.id,
        batch_id=batch.id,
        employee_id=employees["E101"].id,
    )
    create_import_batch_error(db, batch_id=batch.id)

    response = discard(client, superuser_token_headers, str(batch.id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "discarded"
    assert body["discard_reason"] == "user"
    assert body["discarded_at"] is not None
    assert body["expires_at"] is None
    db.expire_all()
    stored = db.get(ImportBatch, batch.id)
    assert stored is not None
    assert stored.status == ImportBatchStatus.DISCARDED
    assert stored.discard_reason == "user"
    assert stored.discarded_at is not None
    assert (
        db.exec(
            select(func.count())
            .select_from(PunchRecord)
            .where(PunchRecord.batch_id == batch.id)
        ).one()
        == 0
    )
    assert (
        db.exec(
            select(func.count())
            .select_from(ImportBatchError)
            .where(ImportBatchError.batch_id == batch.id)
        ).one()
        == 0
    )


def test_discard_rejects_a_non_preview_batch(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    batch = _batch_for(db, company.id, status=ImportBatchStatus.COMMITTED)

    response = discard(client, superuser_token_headers, str(batch.id))

    assert response.status_code == 409
    assert error_detail(response)["code"] == "batch_not_preview"
    db.expire_all()
    stored = db.get(ImportBatch, batch.id)
    assert stored is not None
    assert stored.status == ImportBatchStatus.COMMITTED


def test_discard_unknown_batch_is_404_and_requires_authentication(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    missing = discard(client, superuser_token_headers, str(uuid.uuid7()))
    assert missing.status_code == 404
    assert error_detail(missing)["code"] == "not_found"
    assert client.post(f"{IMPORTS_URL}/{uuid.uuid7()}/discard").status_code == 401


def test_revoke_deletes_committed_rows_and_marks_the_month_stale(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    employees = seed_fixture_employees(db, company)
    month_row = create_attendance_month(
        db, company_id=company.id, month=MONTH_DATE, is_stale=False
    )
    batch = _batch_for(db, company.id, status=ImportBatchStatus.COMMITTED)
    create_punch_record(
        db,
        company_id=company.id,
        batch_id=batch.id,
        employee_id=employees["E101"].id,
    )
    create_import_batch_error(db, batch_id=batch.id)

    response = revoke(client, superuser_token_headers, str(batch.id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "revoked"
    assert body["revoked_at"] is not None
    assert body["expires_at"] is None
    db.expire_all()
    stored = db.get(ImportBatch, batch.id)
    assert stored is not None
    assert stored.status == ImportBatchStatus.REVOKED
    assert stored.revoked_at is not None
    assert (
        db.exec(
            select(func.count())
            .select_from(PunchRecord)
            .where(PunchRecord.batch_id == batch.id)
        ).one()
        == 0
    )
    assert (
        db.exec(
            select(func.count())
            .select_from(ImportBatchError)
            .where(ImportBatchError.batch_id == batch.id)
        ).one()
        == 0
    )
    refreshed_month = db.get(AttendanceMonth, month_row.id)
    assert refreshed_month is not None
    assert refreshed_month.is_stale is True


def test_revoke_does_not_restore_the_superseded_batch(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    user = db.exec(select(User)).first()
    assert user is not None
    create_attendance_month(db, company_id=company.id, month=MONTH_DATE)
    previous = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        status=ImportBatchStatus.SUPERSEDED,
    )
    active = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        status=ImportBatchStatus.COMMITTED,
        committed_at=datetime.now(UTC),
    )
    previous.superseded_by_batch_id = active.id
    db.add(previous)
    db.commit()

    response = revoke(client, superuser_token_headers, str(active.id))

    assert response.status_code == 200, response.text
    db.expire_all()
    assert db.get(ImportBatch, previous.id).status == ImportBatchStatus.SUPERSEDED  # type: ignore[union-attr]
    assert db.get(ImportBatch, active.id).status == ImportBatchStatus.REVOKED  # type: ignore[union-attr]


def test_revoke_rejects_a_non_committed_batch(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    batch = _batch_for(db, company.id)

    response = revoke(client, superuser_token_headers, str(batch.id))

    assert response.status_code == 409
    assert error_detail(response)["code"] == "batch_not_revocable"


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        (AttendanceMonthStatus.CONFIRMED, "month_confirmed"),
        (AttendanceMonthStatus.LOCKED, "month_locked"),
    ],
)
def test_revoke_respects_the_month_gate(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    status: AttendanceMonthStatus,
    reason: str,
) -> None:
    company = create_company(db)
    create_attendance_month(db, company_id=company.id, month=MONTH_DATE, status=status)
    batch = _batch_for(db, company.id, status=ImportBatchStatus.COMMITTED)

    response = revoke(client, superuser_token_headers, str(batch.id))

    assert response.status_code == 409
    assert error_detail(response)["code"] == reason
    db.expire_all()
    assert db.get(ImportBatch, batch.id).status == ImportBatchStatus.COMMITTED  # type: ignore[union-attr]


def test_revoke_unknown_batch_is_404_and_requires_authentication(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    missing = revoke(client, superuser_token_headers, str(uuid.uuid7()))
    assert missing.status_code == 404
    assert error_detail(missing)["code"] == "not_found"
    assert client.post(f"{IMPORTS_URL}/{uuid.uuid7()}/revoke").status_code == 401


def test_batch_list_filters_by_company_type_month_and_status(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    other_company = create_company(db)
    user = db.exec(select(User)).first()
    assert user is not None
    older = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        data_type=ImportDataType.PUNCH,
        month=MONTH_DATE,
        status=ImportBatchStatus.PREVIEW,
    )
    newer = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        data_type=ImportDataType.PUNCH,
        month=MONTH_DATE,
        status=ImportBatchStatus.COMMITTED,
    )
    trip = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        data_type=ImportDataType.TRIP,
        month=MONTH_DATE,
        status=ImportBatchStatus.COMMITTED,
    )
    october = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        data_type=ImportDataType.PUNCH,
        month=date(2026, 10, 1),
        status=ImportBatchStatus.COMMITTED,
    )
    foreign = create_import_batch(
        db,
        company_id=other_company.id,
        operator_id=user.id,
        data_type=ImportDataType.PUNCH,
        month=MONTH_DATE,
        status=ImportBatchStatus.COMMITTED,
    )
    for batch, hour in (
        (older, 1),
        (trip, 2),
        (october, 3),
        (foreign, 4),
        (newer, 5),
    ):
        batch.created_at = datetime(2026, 9, 1, hour, tzinfo=UTC)
        db.add(batch)
    db.commit()

    response = client.get(
        f"{IMPORTS_URL}/",
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["count"] == 4
    assert body["data"][0]["id"] == str(newer.id)
    assert {batch["company_id"] for batch in body["data"]} == {str(company.id)}

    filtered = client.get(
        f"{IMPORTS_URL}/",
        headers=superuser_token_headers,
        params={
            "company_id": str(company.id),
            "data_type": "punch",
            "month": MONTH,
            "status": "committed",
        },
    )
    assert filtered.status_code == 200, filtered.text
    filtered_body = filtered.json()
    assert filtered_body["count"] == 1
    assert [batch["id"] for batch in filtered_body["data"]] == [str(newer.id)]

    page = client.get(
        f"{IMPORTS_URL}/",
        headers=superuser_token_headers,
        params={"company_id": str(company.id), "skip": 1, "limit": 2},
    )
    assert page.status_code == 200, page.text
    assert page.json()["count"] == 4
    assert len(page.json()["data"]) == 2


def test_batch_list_unknown_company_is_404_and_requires_authentication(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{IMPORTS_URL}/",
        headers=superuser_token_headers,
        params={"company_id": str(uuid.uuid7())},
    )
    assert response.status_code == 404
    assert error_detail(response)["code"] == "not_found"
    assert client.get(f"{IMPORTS_URL}/").status_code == 401


def test_batch_detail_returns_counts_mapping_samples_and_supersede_link(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)
    preview = preview_fixture(
        client, superuser_token_headers, company.id, ImportDataType.PUNCH
    )
    assert preview.status_code == 200, preview.text
    batch_id = preview.json()["batch"]["id"]

    response = client.get(f"{IMPORTS_URL}/{batch_id}", headers=superuser_token_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == batch_id
    assert body["status"] == "preview"
    assert body["valid_records"] == 27
    assert body["column_mapping"]["employee_no"] == {
        "column": "工号",
        "index": 0,
    }
    assert body["header_columns"][0] == "工号"
    assert len(body["samples"]) == 20
    assert body["samples"][0]["employee_no"] == "E101"
    assert body["samples"][0]["attendance_date"] == "2026-09-01"
    assert body["superseded_by_batch_id"] is None

    user = db.exec(select(User)).first()
    assert user is not None
    successor = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        status=ImportBatchStatus.COMMITTED,
    )
    superseded = db.get(ImportBatch, uuid.UUID(batch_id))
    assert superseded is not None
    superseded.status = ImportBatchStatus.SUPERSEDED
    superseded.superseded_by_batch_id = successor.id
    db.add(superseded)
    db.commit()

    linked = client.get(f"{IMPORTS_URL}/{batch_id}", headers=superuser_token_headers)
    assert linked.status_code == 200, linked.text
    assert linked.json()["superseded_by_batch_id"] == str(successor.id)


def test_batch_detail_unknown_batch_is_404_and_requires_authentication(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{IMPORTS_URL}/{uuid.uuid7()}", headers=superuser_token_headers
    )
    assert response.status_code == 404
    assert error_detail(response)["code"] == "not_found"
    assert client.get(f"{IMPORTS_URL}/{uuid.uuid7()}").status_code == 401


def test_batch_errors_filter_by_severity_and_page(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    user = db.exec(select(User)).first()
    assert user is not None
    batch = create_import_batch(db, company_id=company.id, operator_id=user.id)
    for index in range(25):
        create_import_batch_error(db, batch_id=batch.id, source_row_number=index + 2)
    for index in range(5):
        create_import_batch_error(
            db,
            batch_id=batch.id,
            source_row_number=index + 2,
            severity=ImportSeverity.WARNING,
        )

    response = client.get(
        f"{IMPORTS_URL}/{batch.id}/errors", headers=superuser_token_headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["count"] == 30
    assert len(body["data"]) == 30
    assert [row["source_row_number"] for row in body["data"][:3]] == [2, 2, 3]

    errors_only = client.get(
        f"{IMPORTS_URL}/{batch.id}/errors",
        headers=superuser_token_headers,
        params={"severity": "error"},
    )
    assert errors_only.status_code == 200, errors_only.text
    assert errors_only.json()["count"] == 25
    assert all(row["severity"] == "error" for row in errors_only.json()["data"])

    warnings_only = client.get(
        f"{IMPORTS_URL}/{batch.id}/errors",
        headers=superuser_token_headers,
        params={"severity": "warning", "skip": 2, "limit": 2},
    )
    assert warnings_only.status_code == 200, warnings_only.text
    assert warnings_only.json()["count"] == 5
    assert len(warnings_only.json()["data"]) == 2
    assert all(row["severity"] == "warning" for row in warnings_only.json()["data"])

    missing = client.get(
        f"{IMPORTS_URL}/{uuid.uuid7()}/errors", headers=superuser_token_headers
    )
    assert missing.status_code == 404
    assert client.get(f"{IMPORTS_URL}/{batch.id}/errors").status_code == 401


@pytest.mark.parametrize(
    ("data_type", "valid"),
    [
        (ImportDataType.PUNCH, 27),
        (ImportDataType.TRIP, 8),
        (ImportDataType.OT, 8),
        (ImportDataType.LEAVE, 8),
    ],
)
def test_batch_records_return_the_typed_union(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    data_type: ImportDataType,
    valid: int,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)
    preview = preview_fixture(client, superuser_token_headers, company.id, data_type)
    assert preview.status_code == 200, preview.text
    batch_id = preview.json()["batch"]["id"]

    response = client.get(
        f"{IMPORTS_URL}/{batch_id}/records", headers=superuser_token_headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data_type"] == data_type.value
    assert body["count"] == valid
    assert len(body["records"]) == valid
    if data_type == ImportDataType.OT:
        assert any(record["days"] for record in body["records"])
    else:
        assert body["records"][0]["batch_id"] == batch_id

    page = client.get(
        f"{IMPORTS_URL}/{batch_id}/records",
        headers=superuser_token_headers,
        params={"skip": 2, "limit": 3},
    )
    assert page.status_code == 200, page.text
    assert page.json()["count"] == valid
    assert len(page.json()["records"]) == 3


def test_batch_records_unknown_batch_is_404_and_requires_authentication(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{IMPORTS_URL}/{uuid.uuid7()}/records", headers=superuser_token_headers
    )
    assert response.status_code == 404
    assert client.get(f"{IMPORTS_URL}/{uuid.uuid7()}/records").status_code == 401


def test_list_cleans_expired_previews(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    employees = seed_fixture_employees(db, company)
    now = datetime.now(UTC)
    expired = _batch_for(db, company.id, expires_at=now - timedelta(hours=1))
    create_punch_record(
        db,
        company_id=company.id,
        batch_id=expired.id,
        employee_id=employees["E101"].id,
    )
    create_import_batch_error(db, batch_id=expired.id)
    live = _batch_for(db, company.id, expires_at=now + timedelta(hours=1))

    response = client.get(
        f"{IMPORTS_URL}/",
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    db.expire_all()
    discarded = db.get(ImportBatch, expired.id)
    assert discarded is not None
    assert discarded.status == ImportBatchStatus.DISCARDED
    assert discarded.discard_reason == "expired"
    assert (
        db.exec(
            select(func.count())
            .select_from(PunchRecord)
            .where(PunchRecord.batch_id == expired.id)
        ).one()
        == 0
    )
    assert db.get(ImportBatch, live.id).status == ImportBatchStatus.PREVIEW  # type: ignore[union-attr]


def test_commit_cleans_expired_previews(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    employees = seed_fixture_employees(db, company)
    user = db.exec(select(User)).first()
    assert user is not None
    target = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        valid_records=1,
    )
    create_punch_record(
        db,
        company_id=company.id,
        batch_id=target.id,
        employee_id=employees["E101"].id,
    )
    expired = _batch_for(
        db,
        company.id,
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    create_import_batch_error(db, batch_id=expired.id)

    response = commit(client, superuser_token_headers, str(target.id))

    assert response.status_code == 200, response.text
    db.expire_all()
    discarded = db.get(ImportBatch, expired.id)
    assert discarded is not None
    assert discarded.status == ImportBatchStatus.DISCARDED
    assert discarded.discard_reason == "expired"
    assert (
        db.exec(
            select(func.count())
            .select_from(ImportBatchError)
            .where(ImportBatchError.batch_id == expired.id)
        ).one()
        == 0
    )


def test_list_clears_superseded_raw_payloads_after_ninety_days(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    employees = seed_fixture_employees(db, company)
    user = db.exec(select(User)).first()
    assert user is not None
    now = datetime.now(UTC)
    old = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        status=ImportBatchStatus.SUPERSEDED,
    )
    old.superseded_at = now - timedelta(days=91)
    db.add(old)
    recent = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        status=ImportBatchStatus.SUPERSEDED,
    )
    recent.superseded_at = now - timedelta(days=10)
    db.add(recent)
    db.commit()
    old_row = create_punch_record(
        db,
        company_id=company.id,
        batch_id=old.id,
        employee_id=employees["E101"].id,
        raw_row={"工号": "E101"},
    )
    recent_row = create_punch_record(
        db,
        company_id=company.id,
        batch_id=recent.id,
        employee_id=employees["E102"].id,
        raw_row={"工号": "E102"},
    )
    create_import_batch_error(db, batch_id=old.id)
    create_import_batch_error(db, batch_id=recent.id, source_row_number=3)

    response = client.get(
        f"{IMPORTS_URL}/",
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    db.expire_all()
    assert db.get(PunchRecord, old_row.id).raw_row == {}  # type: ignore[union-attr]
    assert db.get(PunchRecord, recent_row.id).raw_row == {"工号": "E102"}  # type: ignore[union-attr]
    assert (
        db.exec(
            select(func.count())
            .select_from(ImportBatchError)
            .where(ImportBatchError.batch_id == old.id)
        ).one()
        == 0
    )
    assert (
        db.exec(
            select(func.count())
            .select_from(ImportBatchError)
            .where(ImportBatchError.batch_id == recent.id)
        ).one()
        == 1
    )


def test_cleanup_respects_the_row_budget(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.attendance import imports as import_service

    company = create_company(db)
    employees = seed_fixture_employees(db, company)
    user = db.exec(select(User)).first()
    assert user is not None
    old = create_import_batch(
        db,
        company_id=company.id,
        operator_id=user.id,
        status=ImportBatchStatus.SUPERSEDED,
    )
    old.superseded_at = datetime.now(UTC) - timedelta(days=91)
    db.add(old)
    db.commit()
    for index in range(3):
        create_punch_record(
            db,
            company_id=company.id,
            batch_id=old.id,
            employee_id=employees["E101"].id,
            source_row_number=index + 2,
            punch_time=datetime(2026, 9, 1, 8, index, tzinfo=UTC),
            raw_row={"工号": "E101"},
        )
    for index in range(2):
        create_import_batch_error(db, batch_id=old.id, source_row_number=index + 2)
    monkeypatch.setattr(import_service, "CLEANUP_ROW_BUDGET", 3)

    result = import_service.list_batches(
        db,
        company_id=company.id,
        data_type=None,
        month=None,
        status=None,
        skip=0,
        limit=100,
    )

    assert result.count == 1
    db.expire_all()
    cleared_errors = db.exec(
        select(func.count())
        .select_from(ImportBatchError)
        .where(ImportBatchError.batch_id == old.id)
    ).one()
    records = db.exec(select(PunchRecord).where(PunchRecord.batch_id == old.id)).all()
    cleared_records = sum(1 for record in records if record.raw_row == {})
    assert (2 - cleared_errors) + cleared_records == 3


def test_reimport_commits_a_new_batch_and_supersedes_the_previous_one(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)
    first_preview = preview_fixture(
        client, superuser_token_headers, company.id, ImportDataType.PUNCH
    )
    assert first_preview.status_code == 200, first_preview.text
    first_id = first_preview.json()["batch"]["id"]
    first_commit = commit(client, superuser_token_headers, first_id)
    assert first_commit.status_code == 200, first_commit.text

    second_preview = preview_fixture(
        client, superuser_token_headers, company.id, ImportDataType.PUNCH
    )
    assert second_preview.status_code == 200, second_preview.text
    second_id = second_preview.json()["batch"]["id"]
    second_commit = commit(client, superuser_token_headers, second_id)

    assert second_commit.status_code == 200, second_commit.text
    assert second_commit.json()["superseded_batch_id"] == first_id
    db.expire_all()
    committed = db.exec(
        select(ImportBatch).where(ImportBatch.status == ImportBatchStatus.COMMITTED)
    ).all()
    assert [str(batch.id) for batch in committed] == [second_id]
    superseded = db.get(ImportBatch, uuid.UUID(first_id))
    assert superseded is not None
    assert superseded.status == ImportBatchStatus.SUPERSEDED
    assert str(superseded.superseded_by_batch_id) == second_id

    repeated = commit(client, superuser_token_headers, second_id)
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["superseded_batch_id"] == first_id


def test_commit_is_allowed_in_a_calculated_month(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)
    month_row = create_attendance_month(
        db,
        company_id=company.id,
        month=MONTH_DATE,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )
    preview = preview_fixture(
        client, superuser_token_headers, company.id, ImportDataType.PUNCH
    )
    assert preview.status_code == 200, preview.text

    response = commit(client, superuser_token_headers, preview.json()["batch"]["id"])

    assert response.status_code == 200, response.text
    db.expire_all()
    assert db.get(AttendanceMonth, month_row.id).is_stale is True  # type: ignore[union-attr]


def test_revoke_is_allowed_in_a_calculated_month(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    month_row = create_attendance_month(
        db,
        company_id=company.id,
        month=MONTH_DATE,
        status=AttendanceMonthStatus.CALCULATED,
        is_stale=False,
    )
    batch = _batch_for(db, company.id, status=ImportBatchStatus.COMMITTED)

    response = revoke(client, superuser_token_headers, str(batch.id))

    assert response.status_code == 200, response.text
    db.expire_all()
    assert db.get(AttendanceMonth, month_row.id).is_stale is True  # type: ignore[union-attr]


def test_commit_saves_the_mapping_template(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    from app.models import ImportMappingTemplate

    company = create_company(db)
    seed_fixture_employees(db, company)
    preview = preview_fixture(
        client, superuser_token_headers, company.id, ImportDataType.PUNCH
    )
    assert preview.status_code == 200, preview.text
    batch = preview.json()["batch"]

    response = commit(client, superuser_token_headers, batch["id"])

    assert response.status_code == 200, response.text
    db.expire_all()
    template = db.exec(select(ImportMappingTemplate)).one()
    assert template.company_id == company.id
    assert template.data_type == ImportDataType.PUNCH
    assert template.mapping == batch["column_mapping"]
    assert template.header_columns == batch["header_columns"]

    second_preview = preview_fixture(
        client, superuser_token_headers, company.id, ImportDataType.PUNCH
    )
    assert second_preview.status_code == 200, second_preview.text
    commit(client, superuser_token_headers, second_preview.json()["batch"]["id"])
    db.expire_all()
    assert db.exec(select(func.count()).select_from(ImportMappingTemplate)).one() == 1


def test_revoke_removes_overtime_days_with_the_batch(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    from app.models import OaOvertime, OaOvertimeDay

    company = create_company(db)
    seed_fixture_employees(db, company)
    preview = preview_fixture(
        client, superuser_token_headers, company.id, ImportDataType.OT
    )
    assert preview.status_code == 200, preview.text
    batch_id = preview.json()["batch"]["id"]
    committed = commit(client, superuser_token_headers, batch_id)
    assert committed.status_code == 200, committed.text

    response = revoke(client, superuser_token_headers, batch_id)

    assert response.status_code == 200, response.text
    db.expire_all()
    assert db.exec(select(func.count()).select_from(OaOvertime)).one() == 0
    assert db.exec(select(func.count()).select_from(OaOvertimeDay)).one() == 0


def test_expired_preview_cleanup_respects_the_budget_and_resumes(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.attendance import imports as import_service

    company = create_company(db)
    employees = seed_fixture_employees(db, company)
    expired = _batch_for(
        db,
        company.id,
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    for index in range(3):
        create_punch_record(
            db,
            company_id=company.id,
            batch_id=expired.id,
            employee_id=employees["E101"].id,
            source_row_number=index + 2,
            punch_time=datetime(2026, 9, 1, 8, index, tzinfo=UTC),
        )
    monkeypatch.setattr(import_service, "CLEANUP_ROW_BUDGET", 2)

    first = client.get(
        f"{IMPORTS_URL}/",
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert first.status_code == 200, first.text
    db.expire_all()
    partially_cleaned = db.get(ImportBatch, expired.id)
    assert partially_cleaned is not None
    assert partially_cleaned.status == ImportBatchStatus.PREVIEW
    assert (
        db.exec(
            select(func.count())
            .select_from(PunchRecord)
            .where(PunchRecord.batch_id == expired.id)
        ).one()
        == 1
    )

    second = client.get(
        f"{IMPORTS_URL}/",
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )
    assert second.status_code == 200, second.text
    db.expire_all()
    discarded = db.get(ImportBatch, expired.id)
    assert discarded is not None
    assert discarded.status == ImportBatchStatus.DISCARDED
    assert discarded.discard_reason == "expired"
    assert (
        db.exec(
            select(func.count())
            .select_from(PunchRecord)
            .where(PunchRecord.batch_id == expired.id)
        ).one()
        == 0
    )


@pytest.mark.parametrize(
    ("data_type", "sample_count", "sample_key"),
    [
        (ImportDataType.PUNCH, 20, "punch_time"),
        (ImportDataType.TRIP, 8, "split_index"),
        (ImportDataType.OT, 8, "days"),
        (ImportDataType.LEAVE, 8, "leave_kind"),
    ],
)
def test_batch_detail_samples_follow_the_data_type(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    data_type: ImportDataType,
    sample_count: int,
    sample_key: str,
) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)
    preview = preview_fixture(client, superuser_token_headers, company.id, data_type)
    assert preview.status_code == 200, preview.text
    batch_id = preview.json()["batch"]["id"]

    response = client.get(f"{IMPORTS_URL}/{batch_id}", headers=superuser_token_headers)

    assert response.status_code == 200, response.text
    samples = response.json()["samples"]
    assert len(samples) == sample_count
    assert sample_key in samples[0]
    if data_type == ImportDataType.OT:
        assert samples[0]["days"]


def test_commit_rejected_as_expired_still_runs_staging_cleanup(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    employees = seed_fixture_employees(db, company)
    expired_at = datetime.now(UTC) - timedelta(hours=1)
    target = _batch_for(db, company.id, expires_at=expired_at)
    other = _batch_for(db, company.id, expires_at=expired_at)
    create_punch_record(
        db,
        company_id=company.id,
        batch_id=other.id,
        employee_id=employees["E101"].id,
    )
    create_import_batch_error(db, batch_id=other.id)

    response = commit(client, superuser_token_headers, str(target.id))

    assert response.status_code == 409
    assert error_detail(response)["code"] == "preview_expired"
    db.expire_all()
    cleaned = db.get(ImportBatch, other.id)
    assert cleaned is not None
    assert cleaned.status == ImportBatchStatus.DISCARDED
    assert cleaned.discard_reason == "expired"
    assert (
        db.exec(
            select(func.count())
            .select_from(PunchRecord)
            .where(PunchRecord.batch_id == other.id)
        ).one()
        == 0
    )


def test_import_scopes_are_isolated_between_companies(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company_a = create_company(db)
    company_b = create_company(db)
    seed_fixture_employees(db, company_a)
    user = db.exec(select(User)).first()
    assert user is not None
    dept_b = create_department(db, company=company_b)
    position_b = create_position(db, company=company_b)
    employee_b = create_employee(
        db,
        dept=dept_b,
        position=position_b,
        employee_no=random_upper_code("E"),
        hire_date=date(2020, 1, 1),
    )
    batch_b = create_import_batch(
        db,
        company_id=company_b.id,
        operator_id=user.id,
        status=ImportBatchStatus.COMMITTED,
        valid_records=1,
        committed_at=datetime.now(UTC),
    )
    create_punch_record(
        db,
        company_id=company_b.id,
        batch_id=batch_b.id,
        employee_id=employee_b.id,
    )

    preview_a = preview_fixture(
        client, superuser_token_headers, company_a.id, ImportDataType.PUNCH
    )
    assert preview_a.status_code == 200, preview_a.text
    commit_a = commit(client, superuser_token_headers, preview_a.json()["batch"]["id"])
    assert commit_a.status_code == 200, commit_a.text

    db.expire_all()
    committed_b = db.exec(
        select(ImportBatch).where(
            ImportBatch.company_id == company_b.id,
            ImportBatch.status == ImportBatchStatus.COMMITTED,
        )
    ).all()
    assert [str(batch.id) for batch in committed_b] == [str(batch_b.id)]
    assert committed_b[0].superseded_by_batch_id is None

    for company, batch_id in (
        (company_a, preview_a.json()["batch"]["id"]),
        (company_b, str(batch_b.id)),
    ):
        response = client.get(
            f"{IMPORTS_URL}/",
            headers=superuser_token_headers,
            params={"company_id": str(company.id)},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["count"] == 1
        assert body["data"][0]["id"] == batch_id
        assert body["data"][0]["company_id"] == str(company.id)


def test_list_hard_deletes_discarded_metadata_after_ninety_days(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    company = create_company(db)
    now = datetime.now(UTC)
    old = _batch_for(db, company.id, status=ImportBatchStatus.DISCARDED)
    old.discard_reason = "user"
    old.discarded_at = now - timedelta(days=91)
    recent = _batch_for(db, company.id, status=ImportBatchStatus.DISCARDED)
    recent.discard_reason = "user"
    recent.discarded_at = now - timedelta(days=10)
    db.add(old)
    db.add(recent)
    db.commit()
    old_id = old.id
    recent_id = recent.id

    response = client.get(
        f"{IMPORTS_URL}/",
        headers=superuser_token_headers,
        params={"company_id": str(company.id)},
    )

    assert response.status_code == 200, response.text
    db.expire_all()
    assert db.get(ImportBatch, old_id) is None
    assert db.get(ImportBatch, recent_id) is not None
