"""Dispatcher - single entry point for the loading pipeline.

Routes a file to its registered loader based on the file extension.
"""

from __future__ import annotations

import logging
from pathlib import Path

from exceptions import FileValidationError
from .base import _LOADER_REGISTRY
from .schemas import LoadedDocument

logger = logging.getLogger(__name__)


async def load_file(file_path: Path | str) -> list[LoadedDocument]:
    """Load a file by dispatching to the appropriate registered loader.

    Parameters
    ----------
    file_path : Path or str
        Absolute or relative path to the file to load.

    Returns
    -------
    list[LoadedDocument]
        One or more extracted document units.

    Raises
    ------
    FileValidationError
        If no loader is registered for the file's extension.
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()

    loader_cls = _LOADER_REGISTRY.get(ext)
    if loader_cls is None:
        raise FileValidationError(
            f"Unsupported file extension '{ext}' for file '{file_path.name}'. "
            f"Supported extensions: {', '.join(sorted(_LOADER_REGISTRY.keys()))}"
        )

    logger.info("Loading '%s' with %s", file_path.name, loader_cls.__name__)
    loader = loader_cls()
    return await loader.load(file_path)

