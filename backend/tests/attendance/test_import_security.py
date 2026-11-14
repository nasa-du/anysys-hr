"""XLSX archive protections (spec section 8.8).

Seam: ``app.services.attendance.import_parsing.parse_upload``. The container is
inspected before openpyxl: legacy/encrypted containers, macro payloads,
oversized archives, excessive zip entries, DTDs, and external entities are
rejected, and no batch can be created for them.
"""

import io
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from app.core.errors import DomainError
from app.services.attendance import import_parsing


@contextmanager
def zip_content(entries: list[tuple[str, bytes]]) -> Iterator[bytes]:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    yield buffer.getvalue()


def assert_parse_error(content: bytes, code: str) -> None:
    with pytest.raises(DomainError) as exc_info:
        import_parsing.parse_upload(content=content, file_name="punch.xlsx")
    assert exc_info.value.code == code


def test_legacy_ole_container_with_xlsx_extension_is_rejected() -> None:
    content = import_parsing.OLE_MAGIC + b"\x00" * 512

    assert_parse_error(content, "unsupported_file_type")


def test_macro_payload_is_rejected() -> None:
    with zip_content([("xl/vbaProject.bin", b"macro")]) as content:
        assert_parse_error(content, "unsupported_file_type")


def test_more_than_two_thousand_zip_entries_is_rejected() -> None:
    entries = [(f"xl/parts/part-{index}.xml", b"<x/>") for index in range(2001)]
    with zip_content(entries) as content:
        assert_parse_error(content, "import_parse_failed")


def test_uncompressed_size_over_fifty_megabytes_is_rejected() -> None:
    payload = b"\x00" * (import_parsing.MAX_XLSX_UNCOMPRESSED_BYTES + 1)
    with zip_content([("xl/worksheets/sheet1.xml", payload)]) as content:
        assert_parse_error(content, "import_parse_failed")


def test_dtd_in_an_xml_part_is_rejected() -> None:
    sheet = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE foo [<!ELEMENT foo ANY>]>'
        b"<worksheet><sheetData/></worksheet>"
    )
    with zip_content([("xl/worksheets/sheet1.xml", sheet)]) as content:
        assert_parse_error(content, "import_parse_failed")


def test_external_entity_declaration_is_rejected() -> None:
    sheet = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        b"<worksheet><sheetData/></worksheet>"
    )
    with zip_content([("xl/worksheets/sheet1.xml", sheet)]) as content:
        assert_parse_error(content, "import_parse_failed")


def test_non_xlsx_bytes_with_xlsx_extension_are_rejected() -> None:
    assert_parse_error(b"not a workbook", "import_parse_failed")
