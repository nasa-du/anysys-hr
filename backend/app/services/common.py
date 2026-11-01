"""Helpers shared by the Basic Management services."""

from dataclasses import dataclass
from typing import Any

from sqlmodel import Session
from sqlmodel.sql.expression import SelectOfScalar

from app.core.errors import Blocker, BlockerType

MAX_BLOCKERS = 20


def normalize_code(value: str) -> str:
    return value.strip().upper()


@dataclass(frozen=True)
class BlockerQuery:
    """A single reference source that can block an operation."""

    type: BlockerType
    count_statement: SelectOfScalar[int]
    rows_statement: Any


def collect_blockers(
    session: Session, queries: list[BlockerQuery]
) -> tuple[int, list[Blocker]]:
    """Return the total blocker count and at most ``MAX_BLOCKERS`` entries.

    Entries keep the fixed type order of ``queries`` and are ordered by business
    code within a type. ``rows_statement`` must already sort by code.
    """
    total = sum(session.exec(query.count_statement).one() for query in queries)

    blockers: list[Blocker] = []
    for query in queries:
        remaining = MAX_BLOCKERS - len(blockers)
        if remaining <= 0:
            break
        rows = session.exec(query.rows_statement.limit(remaining)).all()
        for row in rows:
            blocker_id, code, name = row
            blockers.append(
                Blocker(
                    type=query.type,
                    id=blocker_id,
                    code=code,
                    label=f"{code} {name}",
                )
            )
    return total, blockers


def paginate[ItemT](
    session: Session,
    statement: SelectOfScalar[ItemT],
    count_statement: SelectOfScalar[int],
    *,
    skip: int,
    limit: int,
) -> tuple[list[ItemT], int]:
    """Return one page and the total count computed before pagination."""
    count = session.exec(count_statement).one()
    items = list(session.exec(statement.offset(skip).limit(limit)).all())
    return items, count
