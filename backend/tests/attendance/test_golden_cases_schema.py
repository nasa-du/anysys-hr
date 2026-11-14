"""Every golden case must validate against the approved JSON Schema.

The calculation kernel lands in a later slice; this Phase 0 gate keeps the
26 case files and their schema in lockstep so the kernel cannot start from
invalid fixtures.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_CASES_DIR = REPO_ROOT / "docs" / "specs" / "attendance-golden-cases"
SCHEMA_PATH = GOLDEN_CASES_DIR / "schema.json"
CASES_DIR = GOLDEN_CASES_DIR / "cases"

CASE_PATHS = sorted(CASES_DIR.glob("*.json"))


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def test_all_26_golden_cases_are_present() -> None:
    assert len(CASE_PATHS) == 26, [path.name for path in CASE_PATHS]


def test_golden_case_schema_is_valid() -> None:
    schema = _load_json(SCHEMA_PATH)

    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("case_path", CASE_PATHS, ids=lambda path: path.stem)
def test_golden_case_matches_the_schema(case_path: Path) -> None:
    schema = _load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)

    errors = sorted(validator.iter_errors(_load_json(case_path)), key=str)

    assert errors == [], "\n".join(
        f"{case_path.name}: {'/'.join(str(part) for part in error.path)}: "
        f"{error.message}"
        for error in errors
    )
