"""Structure-aware document chunking utilities."""

from dataclasses import dataclass, field

from src.ingest.parsers import ParsedDocument


@dataclass
class DocumentChunk:
    """A text chunk with source and section metadata."""

    text: str
    metadata: dict = field(default_factory=dict)


def chunk_structurally(
    doc: ParsedDocument,
    max_chars: int = 800,
) -> list[DocumentChunk]:
    """Split a parsed document while preferring Markdown boundaries."""

    if max_chars < 1:
        raise ValueError("max_chars must be greater than zero")

    chunks: list[DocumentChunk] = []
    current_lines: list[str] = []
    current_length = 0
    current_section = "Document"
    chunk_number = 0

    def save_chunk() -> None:
        nonlocal current_lines, current_length, chunk_number

        content = "\n".join(current_lines).strip()
        if content:
            chunks.append(
                DocumentChunk(
                    text=content,
                    metadata={
                        "source": doc.source,
                        "section": current_section,
                        "chunk_index": chunk_number,
                    },
                )
            )
            chunk_number += 1

        current_lines = []
        current_length = 0

    for line in doc.text.splitlines():
        stripped = line.strip()

        if stripped.startswith("#"):
            if current_lines:
                save_chunk()
            current_section = stripped.lstrip("#").strip() or "Document"

        line_length = len(line) + (1 if current_lines else 0)

        if current_lines and current_length + line_length > max_chars:
            save_chunk()

        if len(line) > max_chars:
            if current_lines:
                save_chunk()

            for start in range(0, len(line), max_chars):
                piece = line[start:start + max_chars]
                current_lines = [piece]
                current_length = len(piece)
                save_chunk()
            continue

        current_lines.append(line)
        current_length += len(line) + (1 if len(current_lines) > 1 else 0)

    if current_lines:
        save_chunk()

    return chunks
