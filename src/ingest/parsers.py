"""Document parsing utilities for the Week 8 ingestion pipeline."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedDocument:
    """A parsed document and its source metadata."""

    text: str
    source: str
    metadata: dict


def parse_document(path: str | Path) -> ParsedDocument:
    """Read a Markdown or plain-text document."""

    file_path = Path(path)

    if not file_path.is_file():
        raise FileNotFoundError(f"Document not found: {file_path}")

    suffix = file_path.suffix.lower()

    if suffix not in {".md", ".markdown", ".txt"}:
        raise ValueError(
            f"Unsupported file type: {suffix}. "
            "This initial implementation supports Markdown and text."
        )

    text = file_path.read_text(encoding="utf-8-sig")

    return ParsedDocument(
        text=text,
        source=str(file_path),
        metadata={
            "filename": file_path.name,
            "format": suffix.lstrip("."),
            "character_count": len(text),
        },
    )
