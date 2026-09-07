"""HTML loader using *BeautifulSoup*.

Parses HTML files, strips tags, and extracts text.  When the
document contains structural heading elements (``<h1>``-``<h6>``),
content is split into sections — one :class:`LoadedDocument` per
heading block.  If no headings exist, the full text is
returned as a single :class:`LoadedDocument`.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from exceptions import FileIOError
from .base import BaseLoader, register_loader
from .schemas import LoadedDocument, DocumentMetaData, ProcessingOutputType

logger = logging.getLogger(__name__)

_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


@register_loader('.html', '.htm')
class HtmlLoader(BaseLoader):
    """Extract text from HTML files with optional heading-based
    section splitting."""

    async def load(self, file_path: Path) -> list[LoadedDocument]:
        try:
            raw = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
        except UnicodeDecodeError:
            try:
                raw = await asyncio.to_thread(file_path.read_text, encoding="latin-1")
                logger.warning(
                    "HTML file %s is not valid UTF-8; fell back to latin-1.", file_path.name)
            except Exception as exc:
                raise FileIOError(
                    f"Failed to read HTML file '{file_path.name}'",
                    detail=str(exc),
                ) from exc
        except Exception as exc:
            raise FileIOError(
                f"Failed to read HTML file '{file_path.name}'",
                detail=str(exc),
            ) from exc

        try:
            soup = BeautifulSoup(raw, "html.parser")
        except Exception as exc:
            raise FileIOError(
                f"Failed to parse HTML file '{file_path.name}'",
                detail=str(exc),
            ) from exc

        # Remove non-visible elements
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        sections = self._split_by_headings(soup, file_path)
        if sections:
            return sections

        # if no headings found return entire content as one LoadedDocument
        text = soup.get_text(separator="\n", strip=True)
        if not text.strip():
            return []

        return [
            LoadedDocument(
                text=text,
                metadata=DocumentMetaData(
                    doc_type=ProcessingOutputType.TEXT,
                    source=str(file_path),
                    format=".html"
                )
            )
        ]

    def _split_by_headings(
        self,
        soup: BeautifulSoup,
        file_path: Path
    ) -> list[LoadedDocument]:

        documents: list[LoadedDocument] = []
        current_heading: str | None = None
        current_level: int | None = None
        current_parts: list[str] = []
        has_headings = False

        def _flush():
            if current_heading is None:
                return

            parts = [current_heading] + current_parts
            section_text = "\n".join(parts)

            documents.append(
                LoadedDocument(
                    text=section_text,
                    metadata=DocumentMetaData(
                        doc_type=ProcessingOutputType.TEXT,
                        source=str(file_path),
                        format=".html",
                        section=current_heading,
                        section_level=current_level
                    )
                )
            )

        for element in soup.body.children if soup.body else soup.children:
            tag_name = getattr(element, "name", None)

            if tag_name in _HEADING_TAGS:
                has_headings = True
                _flush()

                current_heading = element.get_text(strip=True)
                current_level = int(tag_name[1])  # "h2" -> 2
                current_parts = []
            else:
                text = (
                    element.get_text(separator="\n", strip=True)
                    if tag_name
                    else str(element).strip()
                )
                if text:
                    current_parts.append(text)

        # flush the last section
        _flush()

        if not has_headings:
            return []

        return documents

