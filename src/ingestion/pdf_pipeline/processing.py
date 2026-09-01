import asyncio
from pathlib import Path
import pymupdf
import yaml

from exceptions import FileIOError
from .enums import ProcessingChannel
from .channel_processors import (
    ScannedChannelProcessor,
    ComplexChannelProcessor,
    SimpleChannelProcessor,
    ProcessingResult
)

_PROMPTS_FILE = Path(__file__).parent.resolve() / 'ocr_prompts.yml'

class PDFProcessor:
    """Orchestrates page processing across different channel processors for a PDF.

    Loads channel OCR and image description prompts from configuration and routes
    page groups to their corresponding channel processor (Scanned, Complex, or Simple).
    All active channels are processed concurrently.

    Args:
        scanned_processor (ScannedChannelProcessor): Channel processor for scanned pages.
        complex_processor (ComplexChannelProcessor): Channel processor for complex layout or non-English pages.
        simple_processor (SimpleChannelProcessor): Channel processor for simple English pages.

    Raises:
        FileIOError: If prompt template file loading or parsing fails.
    """

    def __init__(
            self, 
            scanned_processor: ScannedChannelProcessor,
            complex_processor: ComplexChannelProcessor,
            simple_processor: SimpleChannelProcessor,
    ):
        try:
            with open(_PROMPTS_FILE, 'r') as f:
                prompts = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise FileIOError(
                f'Failed to read YAML file: {_PROMPTS_FILE}',
                detail=str(e)
            ) from e

        scanned_processor.ocr_system_prompt = prompts['scanned_channel_prompt']
        complex_processor.ocr_system_prompt = prompts['complex_channel_prompt']
        complex_processor.image_desc_prompt = prompts['image_description_prompt']

        self.processors = {
            ProcessingChannel.SCANNED : scanned_processor,
            ProcessingChannel.COMPLEX : complex_processor,
            ProcessingChannel.SIMPLE : simple_processor
        }

    async def process(
            self, 
            doc: pymupdf.Document, 
            page_groups: dict[ProcessingChannel, list[int]]
    ) -> list[ProcessingResult]:
        """Processes classified page groups using their designated channel processors.

        All active channels are processed concurrently via asyncio.gather.

        Args:
            doc (pymupdf.Document): The PyMuPDF PDF document object.
            page_groups (dict[ProcessingChannel, list[int]]): Dictionary mapping processing channels
                to lists of 0-indexed page numbers.

        Returns:
            list[ProcessingResult]: List of processing results produced by active channel processors.
        """
        active_channels = [
            (proc_ch, pages) for proc_ch, pages in page_groups.items() if pages
        ]

        if not active_channels:
            return []

        tasks = [
            self.processors[proc_ch].process(pages=pages, doc=doc)
            for proc_ch, pages in active_channels
        ]

        results = await asyncio.gather(*tasks)
        return list(results)