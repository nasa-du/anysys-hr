"""Every payroll golden and security case validates against its schema.

Phase 0 gate (spec sections 17.1 and 20): the 17 formula cases and the 18-case
security corpus are approved JSON fixtures. This test keeps fixture and schema
in lockstep before the formula engine is wired; the engine slice later
evaluates the same files without duplicating their structure.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_CASES_DIR = REPO_ROOT / "docs" / "specs" / "payroll-golden-cases"
SCHEMA_PATH = GOLDEN_CASES_DIR / "schema.json"
SECURITY_SCHEMA_PATH = GOLDEN_CASES_DIR / "security-schema.json"
SECURITY_CORPUS_PATH = GOLDEN_CASES_DIR / "security-corpus.json"
CASES_DIR = GOLDEN_CASES_DIR / "cases"

CASE_PATHS = sorted(CASES_DIR.glob("*.json"))
ENGINE_VERSION = "1.0.0"


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def test_all_17_golden_cases_are_present() -> None:
    assert len(CASE_PATHS) == 17, [path.name for path in CASE_PATHS]


def test_golden_case_schema_is_valid() -> None:
    Draft202012Validator.check_schema(_load_json(SCHEMA_PATH))


@pytest.mark.parametrize("case_path", CASE_PATHS, ids=lambda path: path.stem)
def test_golden_case_matches_the_schema(case_path: Path) -> None:
    validator = Draft202012Validator(_load_json(SCHEMA_PATH))

    errors = sorted(validator.iter_errors(_load_json(case_path)), key=str)

    assert errors == [], "\n".join(
        f"{case_path.name}: {'/'.join(str(part) for part in error.path)}: "
        f"{error.message}"
        for error in errors
    )


def test_golden_cases_share_the_engine_version() -> None:
    versions = {_load_json(case_path)["engine_version"] for case_path in CASE_PATHS}

    assert versions == {ENGINE_VERSION}


def test_security_corpus_matches_the_schema_and_count() -> None:
    corpus = _load_json(SECURITY_CORPUS_PATH)
    security_schema = _load_json(SECURITY_SCHEMA_PATH)
    Draft202012Validator.check_schema(security_schema)
    Draft202012Validator(security_schema).validate(corpus)

    assert corpus["engine_version"] == ENGINE_VERSION
    assert len(corpus["items"]) == 18
    assert len({item["id"] for item in corpus["items"]}) == 18
