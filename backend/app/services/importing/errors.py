"""Shared, module-neutral import error codes.

The low-level file parser and generic header detection raise these codes so
they can be reused by any importing module without importing that module's
error vocabulary. Feature modules keep their own row-level error codes.
"""

from enum import StrEnum


class ImportErrorCode(StrEnum):
    IMPORT_PARSE_FAILED = "import_parse_failed"
    MISSING_REQUIRED_COLUMN = "missing_required_column"
    SHEET_REQUIRED = "sheet_required"
    FILE_TOO_LARGE = "file_too_large"
    UNSUPPORTED_FILE_TYPE = "unsupported_file_type"
