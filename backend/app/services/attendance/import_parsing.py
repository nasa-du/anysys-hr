"""Attendance-facing names for the shared import parser.

Parsing moved to ``app.services.importing.parsing`` so payroll can reuse the
same formats, encodings, limits, and safe-XLSX handling. This module keeps the
attendance import path working for existing callers and tests.
"""

from app.services.importing.parsing import (
    MAX_DATA_ROWS,
    MAX_FILE_BYTES,
    MAX_PARSED_ROWS,
    MAX_XLSX_ENTRIES,
    MAX_XLSX_UNCOMPRESSED_BYTES,
    OLE_MAGIC,
    PASTE_DELIMITERS,
    TOO_MANY_ROWS_MESSAGE,
    ZIP_MAGIC,
    FileKind,
    ParsedSheet,
    SourceRow,
    detect_file_kind,
    parse_paste,
    parse_upload,
)

__all__ = [
    "MAX_DATA_ROWS",
    "MAX_FILE_BYTES",
    "MAX_PARSED_ROWS",
    "MAX_XLSX_ENTRIES",
    "MAX_XLSX_UNCOMPRESSED_BYTES",
    "OLE_MAGIC",
    "PASTE_DELIMITERS",
    "TOO_MANY_ROWS_MESSAGE",
    "ZIP_MAGIC",
    "FileKind",
    "ParsedSheet",
    "SourceRow",
    "detect_file_kind",
    "parse_paste",
    "parse_upload",
]
