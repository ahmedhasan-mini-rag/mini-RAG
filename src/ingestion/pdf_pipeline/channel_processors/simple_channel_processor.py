import asyncio
import pymupdf
import pymupdf4llm

from .channel_processor_interface import ChannelProcessorInterface, ProcessingResult


class SimpleChannelProcessor(ChannelProcessorInterface):
    
    async def process(self, pages: list[int], doc: pymupdf.Document) -> ProcessingResult:
        pages_data = await asyncio.to_thread(
            pymupdf4llm.to_markdown,
            doc=doc,
            pages=pages,
            page_chunks=True,
            use_ocr=False
        )

        md_text = [page['text'] for page in pages_data] # type: ignore
        return ProcessingResult(md_text=md_text)
