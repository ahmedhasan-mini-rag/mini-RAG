from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Type

from .schemas import LoadedDocument

logger = logging.getLogger(__name__)


# maps file extensions to loader classes
_LOADER_REGISTRY: dict[str, Type[BaseLoader]] = {}


def register_loader(*extensions: str):
    """Class decorator that registers a :class:`BaseLoader` subclass for
    one or more file extensions.

    Usage::

        @register_loader('.pdf')
        class PdfLoader(BaseLoader):
            ...

        @register_loader('.htm', '.html')
        class HtmlLoader(BaseLoader):
            ...

    Raises ``ValueError`` if an extension is already claimed by another loader.
    """

    def decorator(cls: Type[BaseLoader]) -> Type[BaseLoader]:
        for ext in extensions:
            normalized = ext.lower()
            if normalized in _LOADER_REGISTRY:
                raise ValueError(
                    f"Extension '{normalized}' is already registered "
                    f"to {_LOADER_REGISTRY[normalized].__name__}"
                )
            _LOADER_REGISTRY[normalized] = cls
            logger.info(f"Registered loader {cls.__name__} for {normalized}")
        return cls

    return decorator


def get_registered_extensions() -> list[str]:
    """Return all file extensions that have a registered loader."""
    return list(_LOADER_REGISTRY.keys())

class BaseLoader(ABC):
    """Abstract interface for the format-specific loaders.

    Subclasses implement :meth:`load` and are registered via the
    :func:`register_loader` decorator.
    """

    @abstractmethod
    async def load(self, file_path: Path) -> list[LoadedDocument]:
        """Extract text and metadata from *file_path*.

        Returns a list of :class:`LoadedDocument` instances — one per logical unit (page, section, …).
        """
        ...
