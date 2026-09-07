"""Markdown loader with heading-based section splitting.

Splits Markdown content on heading lines (``#``, ``##``, …) and
returns one :class:`LoadedDocument` per section.  Each document
carries ``section`` (the heading text) and ``section_level`` (heading
depth) in its metadata.  If the file contains no headings, the entire
content is returned as a single :class:`LoadedDocument`.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from exceptions import FileIOError
from .base import BaseLoader, register_loader
from .schemas import LoadedDocument, DocumentMetaData, ProcessingOutputType

logger = logging.getLogger(__name__)

# matches markdown headings
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


@register_loader('.md', '.markdown')
class MarkdownLoader(BaseLoader):
    """Extract text from Markdown files, splitting on headings."""

    async def load(self, file_path: Path) -> list[LoadedDocument]:
        try:
            text = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = await asyncio.to_thread(file_path.read_text, encoding="latin-1")
                logger.warning(
                    "Markdown file '%s' is not valid UTF-8; fell back to latin-1.",
                    file_path.name,
                )
            except Exception as exc:
                raise FileIOError(
                    f"Failed to read Markdown file '{file_path.name}'",
                    detail=str(exc),
                ) from exc
        except Exception as exc:
            raise FileIOError(
                f"Failed to read Markdown file '{file_path.name}'",
                detail=str(exc),
            ) from exc

        if not text.strip():
            return []

        sections = self._split_by_headings(text, file_path)
        if sections:
            return sections

        return [
            LoadedDocument(
                text=text,
                metadata=DocumentMetaData(
                    doc_type=ProcessingOutputType.TEXT,
                    source=str(file_path),
                    format=".md"
                )
            )
        ]

    @staticmethod
    def _split_by_headings(
        content: str, file_path: Path
    ) -> list[LoadedDocument]:
        """Split Markdown content by ATX headings (``# …``)."""

        matches = list(_HEADING_RE.finditer(content))
        if not matches:
            return []

        documents: list[LoadedDocument] = []

        # content before the first heading
        preamble = content[: matches[0].start()].strip()
        if preamble:
            documents.append(
                LoadedDocument(
                    text=preamble,
                    metadata=DocumentMetaData(
                        doc_type=ProcessingOutputType.TEXT,
                        source=str(file_path),
                        format=".md"
                    )
                )
            )

        for i, match in enumerate(matches):
            level = len(match.group(1))  # number of '#' 
            heading = match.group(2).strip()

            # Section body runs from end of this heading line to start
            # of the next heading (or end of file)
            body_start = match.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            body = content[body_start:body_end].strip()

            section_text = f"{heading}\n{body}" if body else heading

            documents.append(
                LoadedDocument(
                    text=section_text,
                    metadata=DocumentMetaData(
                        doc_type=ProcessingOutputType.TEXT,
                        source=str(file_path),
                        format=".md",
                        section=heading,
                        section_level=level
                    )
                )
            )

        return documents
    