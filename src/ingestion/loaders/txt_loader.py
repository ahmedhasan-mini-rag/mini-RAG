"""Plain-text loader.

Reads the entire file as UTF-8 and returns a single
:class:`LoadedDocument`.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from exceptions import FileIOError
from .base import BaseLoader, register_loader
from .schemas import LoadedDocument

logger = logging.getLogger(__name__)


@register_loader('.txt')
class TxtLoader(BaseLoader):
    """Load a plain-text file into a single :class:`LoadedDocument`."""

    async def load(self, file_path: Path) -> list[LoadedDocument]:
        try:
            text = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
        except UnicodeDecodeError:
            # fallback to latin-1 which never raises
            try:
                text = await asyncio.to_thread(file_path.read_text, encoding="latin-1")
                logger.warning(
                    f"File {file_path.name} is not valid UTF-8; fell back to latin-1."
                )
            except Exception as exc:
                raise FileIOError(
                    f"Failed to read text file '{file_path.name}'",
                    detail=str(exc),
                ) from exc
        except Exception as exc:
            raise FileIOError(
                f"Failed to read text file '{file_path.name}'",
                detail=str(exc),
            ) from exc

        if not text.strip():
            return []

        return [
            LoadedDocument(
                text=text,
                metadata={
                    "source": str(file_path),
                    "format": ".txt",
                },
            )
        ]

