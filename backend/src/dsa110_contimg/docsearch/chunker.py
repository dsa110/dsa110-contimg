"""
Text chunking utilities for documentation indexing.

Splits documents into overlapping chunks suitable for embedding.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class Chunk:
    """A chunk of text from a document."""

    content: str
    file_path: str
    start_line: int
    end_line: int
    heading: str = ""


def chunk_document(
    content: str,
    file_path: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    min_chunk_size: int = 50,
) -> list[Chunk]:
    """
    Split document content into overlapping chunks.

    Uses markdown heading-aware splitting to keep related content together.

    Args:
        content: Document text content
        file_path: Source file path (for metadata)
        chunk_size: Target chunk size in tokens (approximate via chars/4)
        chunk_overlap: Overlap between chunks in tokens
        min_chunk_size: Minimum chunk size to keep

    Returns:
        List of Chunk objects
    """
    # Convert token targets to approximate character counts
    char_size = chunk_size * 4
    char_overlap = chunk_overlap * 4
    min_chars = min_chunk_size * 4

    lines = content.split("\n")
    chunks = []

    # Track current heading context
    current_heading = ""
    current_chunk_lines: list[tuple[int, str]] = []
    current_char_count = 0

    for line_num, line in enumerate(lines, start=1):
        # Check for heading
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            # Emit current chunk if it exists
            if current_chunk_lines and current_char_count >= min_chars:
                chunks.append(_create_chunk(current_chunk_lines, file_path, current_heading))
            current_heading = heading_match.group(2).strip()
            current_chunk_lines = []
            current_char_count = 0

        # Add line to current chunk
        current_chunk_lines.append((line_num, line))
        current_char_count += len(line) + 1  # +1 for newline

        # Check if chunk is full
        if current_char_count >= char_size:
            chunks.append(_create_chunk(current_chunk_lines, file_path, current_heading))

            # Keep overlap lines for next chunk
            overlap_chars = 0
            overlap_start = len(current_chunk_lines)
            for i in range(len(current_chunk_lines) - 1, -1, -1):
                overlap_chars += len(current_chunk_lines[i][1]) + 1
                if overlap_chars >= char_overlap:
                    overlap_start = i
                    break

            current_chunk_lines = current_chunk_lines[overlap_start:]
            current_char_count = sum(len(line) + 1 for _, line in current_chunk_lines)

    # Emit final chunk
    if current_chunk_lines and current_char_count >= min_chars:
        chunks.append(_create_chunk(current_chunk_lines, file_path, current_heading))

    return chunks


def _create_chunk(lines: list[tuple[int, str]], file_path: str, heading: str) -> Chunk:
    """Create a Chunk from accumulated lines."""
    content = "\n".join(line for _, line in lines)
    start_line = lines[0][0]
    end_line = lines[-1][0]

    return Chunk(
        content=content,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        heading=heading,
    )


def iter_documents(
    directory: Path,
    extensions: tuple[str, ...] = (".md", ".txt", ".rst", ".py"),
    exclude_patterns: tuple[str, ...] = ("__pycache__", ".git", "node_modules", "site"),
) -> Iterator[tuple[Path, str]]:
    """
    Iterate over documents in a directory.

    Args:
        directory: Root directory to scan
        extensions: File extensions to include
        exclude_patterns: Directory names to exclude

    Yields:
        Tuples of (file_path, content)
    """
    directory = Path(directory)

    for path in directory.rglob("*"):
        # Skip excluded directories
        if any(excl in path.parts for excl in exclude_patterns):
            continue

        # Check extension
        if path.suffix.lower() not in extensions:
            continue

        # Skip non-files
        if not path.is_file():
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            yield path, content
        except Exception:
            continue
