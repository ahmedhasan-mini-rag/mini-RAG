"""File loading pipeline — public API.

Import all loader modules to trigger their ``@register_loader``
decorators, then expose the dispatcher and schema as the package API.

Usage::

    from loaders import load_file, LoadedDocument

    docs: list[LoadedDocument] = load_file(Path("report.pdf"))
"""
from .dispatcher import load_file
from .schemas import LoadedDocument
from .base import get_registered_extensions

from . import pdf_loader
from . import txt_loader
from . import docx_loader
from . import html_loader
from . import markdown_loader

__all__ = ["load_file", "LoadedDocument", "get_registered_extensions"]
