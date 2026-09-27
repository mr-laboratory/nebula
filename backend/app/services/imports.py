"""Turns an uploaded .md, .txt or .docx file into a draft title and Markdown body.

Nothing is stored: the editor receives the result and the author decides whether to save it.
Files are identified by their bytes, not only their name, and .docx archives are checked
before they are opened, so a renamed binary, a macro document or a zip bomb is refused.
"""

import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath

import anyio
import mammoth  # type: ignore[import-untyped]
from markdownify import markdownify

from app.core.errors import PayloadTooLargeError, UnprocessableError, UnsupportedMediaTypeError
from app.schemas.post import CONTENT_MAX, TITLE_MAX

MAX_FILE_BYTES = 1024 * 1024
TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}
DOCX_EXTENSION = ".docx"
ACCEPTED = ".md, .markdown, .txt or .docx"
# Limits on the .docx archive, checked from its directory before anything is decompressed.
MAX_ZIP_ENTRIES = 1000
MAX_UNZIPPED_BYTES = 20 * 1024 * 1024
CONVERT_TIMEOUT_SECONDS = 10

ZIP_MAGIC = b"PK\x03\x04"
PDF_MAGIC = b"%PDF"
OLE_MAGIC = b"\xd0\xcf\x11\xe0"  # legacy .doc / .xls
MACRO_MARKER = b"macroEnabled"

_HEADING = re.compile(r"^#\s+(.+?)\s*#*\s*$")
_BLANK_RUNS = re.compile(r"\n{3,}")


@dataclass(frozen=True, slots=True)
class ImportedDraft:
    title: str
    content: str
    removed_images: int


def extension_of(filename: str) -> str:
    return PurePosixPath(filename.replace("\\", "/")).suffix.lower()


async def convert(filename: str, data: bytes) -> ImportedDraft:
    """Validate and convert an upload. Raises 413, 415 or 422 with a message for the author."""
    if len(data) > MAX_FILE_BYTES:
        raise PayloadTooLargeError("Files can be up to 1 MB.")
    extension = extension_of(filename)
    _reject_known_unsupported(extension, data)

    if extension in TEXT_EXTENSIONS:
        body, removed = _decode_text(data), 0
    elif extension == DOCX_EXTENSION:
        _check_docx_archive(data)
        with anyio.fail_after(CONVERT_TIMEOUT_SECONDS):
            body, removed = await anyio.to_thread.run_sync(
                _docx_to_markdown, data, abandon_on_cancel=True
            )
    else:
        raise UnsupportedMediaTypeError(f"Choose a {ACCEPTED} file.")

    title, content = _split_title(body, filename)
    if not content:
        raise UnprocessableError("The file has no text to import.")
    if len(content) > CONTENT_MAX:
        raise UnprocessableError(
            f"The file has more than {CONTENT_MAX:,} characters, the longest a post can be."
        )
    return ImportedDraft(title=title, content=content, removed_images=removed)


def _reject_known_unsupported(extension: str, data: bytes) -> None:
    if extension == ".pdf" or data.startswith(PDF_MAGIC):
        raise UnsupportedMediaTypeError(
            "PDF files can't be imported reliably. Open it in Word or Google Docs, "
            "save it as .docx, and import that instead."
        )
    if extension in {".docm", ".dotm"}:
        raise UnsupportedMediaTypeError(
            "Documents with macros can't be imported. Save it as a regular .docx first."
        )
    if extension == ".doc" or data.startswith(OLE_MAGIC):
        raise UnsupportedMediaTypeError("Old .doc files aren't supported. Save it as .docx first.")


def _decode_text(data: bytes) -> str:
    if b"\x00" in data:
        raise UnsupportedMediaTypeError(f"This doesn't look like a text file. Choose a {ACCEPTED}.")
    try:
        text = data.decode("utf-8-sig")  # tolerate the byte-order mark some editors add
    except UnicodeDecodeError:
        raise UnsupportedMediaTypeError("Text files must be saved as UTF-8.") from None
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _check_docx_archive(data: bytes) -> None:
    not_docx = UnsupportedMediaTypeError("This file isn't a valid .docx document.")
    if not data.startswith(ZIP_MAGIC):
        raise not_docx
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            names = {entry.filename for entry in entries}
            content_types = (
                archive.read("[Content_Types].xml") if "[Content_Types].xml" in names else b""
            )
    except zipfile.BadZipFile:
        raise not_docx from None
    if "word/document.xml" not in names:
        raise not_docx
    if len(entries) > MAX_ZIP_ENTRIES or sum(e.file_size for e in entries) > MAX_UNZIPPED_BYTES:
        raise UnsupportedMediaTypeError("This document is too large to import.")
    # A .docm renamed to .docx still declares its macro content type.
    if MACRO_MARKER in content_types or "word/vbaProject.bin" in names:
        raise UnsupportedMediaTypeError(
            "Documents with macros can't be imported. Save it as a regular .docx first."
        )


def _docx_to_markdown(data: bytes) -> tuple[str, int]:
    removed = 0

    def drop_image(image: object) -> dict[str, str]:
        nonlocal removed
        removed += 1
        return {"src": ""}  # the <img> is stripped below; image bytes are never read

    result = mammoth.convert_to_html(
        io.BytesIO(data), convert_image=mammoth.images.img_element(drop_image)
    )
    markdown = markdownify(
        result.value,
        heading_style="ATX",
        bullets="-",
        strip=["img"],
        escape_underscores=False,
    )
    return markdown, removed


def _split_title(body: str, filename: str) -> tuple[str, str]:
    """Use a leading `# Heading` as the title (and drop it from the body), else the file name."""
    text = _BLANK_RUNS.sub("\n\n", body).strip()
    first, _, rest = text.partition("\n")
    match = _HEADING.match(first)
    if match:
        title, text = match.group(1), rest.strip()
    else:
        stem = PurePosixPath(filename.replace("\\", "/")).stem
        title = re.sub(r"[-_]+", " ", stem).strip() or "Imported post"
        title = title[0].upper() + title[1:]
    return title[:TITLE_MAX].strip(), text
