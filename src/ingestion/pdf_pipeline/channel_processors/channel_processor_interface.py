from abc import ABC, abstractmethod
from pydantic import BaseModel
import pymupdf

class ProcessingResult(BaseModel):
    """The result returned by every processing channel."""
    md_text: list[str] # markdown text
    images: dict[str, str] = {} # cloud_url -> description
    tables: list[list[dict[str, str]]] = []

class ChannelProcessorInterface(ABC):
    _SCANNED_TABLES_REGEX = r"<table_block>\s*<description>(.*?)</description>\s*<markdown>(.*?)</markdown>\s*</table_block>"
    
    @abstractmethod
    async def process(self, pages: list[int], doc: pymupdf.Document) -> ProcessingResult:
        """
        Process a list of pages in the given PDF document.
        
        :param pages: List of page numbers to process.
        :param doc: The opened PyMuPDF Document object.
        
        :return: ProcessingResult containing markdown text, images, and tables.
        """
        ...
