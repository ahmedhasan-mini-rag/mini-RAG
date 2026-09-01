import asyncio
import re
import logging
import pymupdf
import base64
from openai import AsyncOpenAI
from .channel_processor_interface import ChannelProcessorInterface, ProcessingResult

logger = logging.getLogger(__name__)

class ScannedChannelProcessor(ChannelProcessorInterface):
    def __init__(self, ocr_client: AsyncOpenAI, ocr_model_id: str, dpi: int, semaphore: asyncio.Semaphore):
        self.ocr_client = ocr_client
        self.ocr_model_id = ocr_model_id
        self.dpi = dpi
        self.semaphore = semaphore

        self._ocr_system_prompt = None

    @property
    def ocr_system_prompt(self) -> str:
        return self._ocr_system_prompt # type: ignore

    @ocr_system_prompt.setter
    def ocr_system_prompt(self, value: str):
        if not isinstance(value, str):
            raise ValueError("'ocr_system_prompt' must be a string")

        self._ocr_system_prompt = value

    async def process(self, pages: list[int], doc: pymupdf.Document) -> ProcessingResult:
        extracted_mds = await self._run_ocr(pages=pages, doc=doc)
        results = self._post_process_ocr_output(mds=extracted_mds)

        return ProcessingResult(
            md_text=results['md_text'],
            tables=results['tables']
        )

    async def _ocr_single_page(self, page_num: int, doc: pymupdf.Document) -> tuple[int, str]:
        """OCR a single page, returning (page_num, markdown_text)."""
        page = doc[page_num]
        base64_image = await asyncio.to_thread(self._page_to_base64, page)

        async with self.semaphore:
            response = await self.ocr_client.chat.completions.create(
                model=self.ocr_model_id,
                temperature=0.1,
                reasoning_effort="none",
                messages=[
                    {
                        "role": "system",
                        "content": self._ocr_system_prompt # type:ignore
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Convert this page into Markdown format following the instructions."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ]
            )

        page_content = response.choices[0].message.content.strip() # type: ignore
        return page_num, page_content

    async def _run_ocr(self, pages: list[int], doc: pymupdf.Document) -> list[str]:
        tasks = [self._ocr_single_page(page_num, doc) for page_num in pages]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Preserve page order; filter out failures
        ordered: dict[int, str] = {}
        for result in raw_results:
            if isinstance(result, Exception):
                logger.warning("Scanned OCR failed for a page: %s", result)
                continue
            page_num, content = result # type: ignore
            ordered[page_num] = content

        failed = [p for p in pages if p not in ordered]
        if failed:
            logger.warning("Scanned channel: OCR failed for pages %s", failed)

        return list(ordered.values())

    def _page_to_base64(self, page: pymupdf.Page) -> str:
        pix = page.get_pixmap(dpi=self.dpi)
        img_bytes = pix.tobytes("png")
        return base64.b64encode(img_bytes).decode("utf-8")

    def _post_process_ocr_output(self, mds: list[str]) -> dict[str, list]:
        results = {
            'md_text' : [],
            'tables' : []
        }

        def remove_tables(match):
            cur_tables.append(dict(
                zip(('description', 'markdown'), match.groups())
            ))
            return ""
        
        for md in mds:
            cur_tables = []
            stripped_md = re.sub(
                self._SCANNED_TABLES_REGEX, remove_tables, md, 
                flags=re.DOTALL | re.IGNORECASE
            )

            results["md_text"].append(stripped_md)
            results["tables"].append(cur_tables)

        return results
