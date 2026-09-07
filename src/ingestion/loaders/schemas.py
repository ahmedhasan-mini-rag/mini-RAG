from pydantic import BaseModel, Field
import uuid
from enum import Enum

class ProcessingOutputType(str, Enum):
    TEXT = 'text'
    IMAGE = 'image'
    TABLE = 'table'

class DocumentMetaData(BaseModel):
    doc_type: ProcessingOutputType | None = None
    source: str | None = None
    format: str | None = None
    page: int | None = 0
    total_pages: int | None = None
    section: str | None = None
    section_level: int | None = None
    img_url: str | None = None
    table_md: str | None = None

class LoadedDocument(BaseModel):
    """Unified output produced by every loader.

    Each instance represents a logical unit of extracted content
    (e.g. one section/chunk of a PDF, one section of a Markdown file, or an
    entire plain-text file).

    Metadata conventions
    --------------------
    Loaders should populate the ``metadata`` dict with the following
    keys where applicable:

    * ``type``  - type of the text content, e.g. text, image(for image description), table
    * ``source``  - absolute path to the source file`
    * ``format``  - file extension, e.g. ``".pdf"``
    * ``page``    - 1-based page number (paginated formats like PDF)
    * ``section`` - heading / section title (structure-aware formats like Markdown and HTML)
    * ``section_level`` - heading depth, e.g. 1 for ``#``, 2 for ``##``
    """

    text: str = Field(description="Extracted text content")
    metadata: DocumentMetaData = Field(default_factory=DocumentMetaData, description="source path, page number, format, section")
