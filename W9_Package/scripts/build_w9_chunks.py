
"""Build Week 9 chunks while preserving Markdown structure where possible."""

import json
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parent

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.rag.naive_rag import load_corpus

CORPUS_DIR = REPO_ROOT / "data" / "corpus"
OUTPUT_FILE = PACKAGE_ROOT / "data" / "w9_common_chunks.json"

# Target size is approximate; complete paragraphs and table blocks are preferred.
TARGET_CHUNK_SIZE = 900
OVERLAP_BLOCKS = 1


def split_oversized_block(block: str, size: int) -> list[str]:
    """Split an oversized block at paragraph or sentence boundaries when possible."""
    if len(block) <= size:
        return [block]

    pieces = []
    remaining = block.strip()

    while len(remaining) > size:
        boundary = remaining.rfind("\n", 0, size + 1)

        if boundary < size // 2:
            boundary = remaining.rfind(". ", 0, size + 1)
            if boundary >= size // 2:
                boundary += 1

        if boundary < size // 2:
            boundary = size

        piece = remaining[:boundary].strip()
        if piece:
            pieces.append(piece)

        remaining = remaining[boundary:].strip()

    if remaining:
        pieces.append(remaining)

    return pieces



def split_markdown_blocks(text: str) -> list[str]:
    """Group headings with following content and preserve Markdown structures."""
    lines = text.strip().splitlines()
    blocks = []
    current = []
    current_type = None

    def flush():
        nonlocal current, current_type
        content = "\n".join(current).strip()
        if content:
            blocks.append(content)
        current = []
        current_type = None

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush()
            continue

        if stripped.startswith("|"):
            line_type = "table"
        elif stripped.startswith("#"):
            line_type = "heading"
        elif stripped.startswith(("- ", "* ", "+ ")):
            line_type = "list"
        else:
            line_type = "paragraph"

        if line_type == "heading":
            # Keep a heading pending so it can join the next content block.
            flush()
            current.append(line)
            current_type = "heading"
            continue

        if current_type == "heading":
            # Attach the following block to its heading.
            current.append(line)
            current_type = line_type
            continue

        if current and line_type != current_type:
            flush()

        current.append(line)
        current_type = line_type

    flush()
    return blocks


    """Group Markdown tables, headings, paragraphs, and list runs into blocks."""
    lines = text.strip().splitlines()
    blocks = []
    current = []
    current_type = None

    def flush():
        nonlocal current, current_type
        content = "\n".join(current).strip()
        if content:
            blocks.append(content)
        current = []
        current_type = None

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush()
            continue

        if stripped.startswith("|"):
            line_type = "table"
        elif stripped.startswith("#"):
            line_type = "heading"
        elif stripped.startswith(("- ", "* ", "+ ")):
            line_type = "list"
        else:
            line_type = "paragraph"

        # Keep consecutive table rows together. Keep consecutive list items together.
        if current and line_type != current_type:
            flush()

        # Start a new paragraph for a new heading or a separate prose line.
        if current and line_type in {"heading", "paragraph"}:
            flush()

        current.append(line)
        current_type = line_type

    flush()
    return blocks


def make_chunks(text: str, target_size: int) -> list[str]:
    """Create chunks that prefer complete Markdown blocks."""
    blocks = split_markdown_blocks(text)
        # Merge a standalone heading with the following block.
    merged_blocks = []
    pending_heading = None

    for block in blocks:
        if block.lstrip().startswith("#") and "\n" not in block:
            if pending_heading is not None:
                merged_blocks.append(pending_heading)
            pending_heading = block
            continue

        if pending_heading is not None:
            merged_blocks.append(pending_heading + "\n\n" + block)
            pending_heading = None
        else:
            merged_blocks.append(block)

    if pending_heading is not None:
        if merged_blocks:
            merged_blocks[-1] += "\n\n" + pending_heading
        else:
            merged_blocks.append(pending_heading)

    blocks = merged_blocks


    chunks = []
    current = []

    for block in blocks:
        parts = split_oversized_block(block, target_size)

        for part in parts:
            candidate = "\n\n".join(current + [part])

            if current and len(candidate) > target_size:
                chunks.append("\n\n".join(current))
                current = []

            current.append(part)

            if len(current) == 1 and len(current[0]) > target_size:
                chunks.append(current.pop())

    if current:
        chunks.append("\n\n".join(current))

    # Stable IDs and deduplication make the output reproducible.
    return list(dict.fromkeys(chunk for chunk in chunks if chunk.strip()))


def main():
    documents = load_corpus(CORPUS_DIR)
    chunks = []

    for document in documents:
        document_chunks = make_chunks(
            document["text"],
            TARGET_CHUNK_SIZE,
        )

        for index, text in enumerate(document_chunks):
            chunks.append({
                "chunk_id": f"{document['doc_id']}::chunk-{index}",
                "doc_id": document["doc_id"],
                "text": text,
            })

    output = {
        "chunking_strategy": "markdown_structure_aware",
        "target_chunk_size": TARGET_CHUNK_SIZE,
        "chunks": chunks,
    }

    OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Created: {OUTPUT_FILE}")
    print(f"Documents: {len(documents)}")
    print(f"Chunks: {len(chunks)}")
    print(f"Target chunk size: {TARGET_CHUNK_SIZE}")


if __name__ == "__main__":
    main()
