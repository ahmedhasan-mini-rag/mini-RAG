import asyncio
import re
import logging
import base64
from typing import Any
import pymupdf
from openai import AsyncOpenAI

from .channel_processor_interface import ChannelProcessorInterface, ProcessingResult
from .images_storage import R2ImageStorage

logger = logging.getLogger(__name__)

class ComplexChannelProcessor(ChannelProcessorInterface):
    def __init__(
            self, 
            ocr_client: AsyncOpenAI, 
            ocr_model_id: str, 
            dpi: int, 
            semaphore: asyncio.Semaphore,
            r2_bucket_config: dict,
            images_xrefs: list[str]
    ):
        self.ocr_client = ocr_client
        self.ocr_model_id = ocr_model_id
        self.dpi = dpi
        self.semaphore = semaphore
        self.r2_bucket_config = r2_bucket_config
        self.images_xrefs = images_xrefs

        self._image_desc_prompt = None
        self._ocr_system_prompt = None

    @property
    def ocr_system_prompt(self) -> str:
        return self._ocr_system_prompt # type: ignore

    @property
    def image_desc_prompt(self) -> str:
        return self._image_desc_prompt # type: ignore
    
    @ocr_system_prompt.setter
    def ocr_system_prompt(self, value: str):
        if not isinstance(value, str):
            raise ValueError("'ocr_system_prompt' must be a string")
        self._ocr_system_prompt = value

    @image_desc_prompt.setter
    def image_desc_prompt(self, value: str):
        if not isinstance(value, str):
            raise ValueError("'image_desc_prompt' must be a string")

        self._image_desc_prompt = value
    
    async def process(self, pages: list[int], doc: pymupdf.Document) -> ProcessingResult:
        self.r2_img_storage = R2ImageStorage(self.r2_bucket_config)

        ocr_task = asyncio.create_task(self._run_ocr(pages=pages, doc=doc))
        img_task = asyncio.create_task(self._describe_and_upload_images(doc=doc))
        
        mds, imgs_data = await asyncio.gather(ocr_task, img_task)
        
        results = self._post_process_ocr_output(mds=mds)

        return ProcessingResult(
            md_text=results['md_text'],
            tables=results['tables'],
            images=imgs_data
        )

    async def _ocr_single_page(self, page_num: int, doc: pymupdf.Document) -> tuple[int, str]:
        """OCR a single page, returning (page_num, markdown_text, image_xrefs)."""
        page = doc[page_num]

        base64_image = await asyncio.to_thread(self._to_base64, page)

        async with self.semaphore:
            response = await self.ocr_client.chat.completions.create(
                model=self.ocr_model_id,
                temperature=0.1,
                reasoning_effort="none",
                messages=[
                    {
                        "role": "system",
                        "content": self._ocr_system_prompt # type: ignore
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
        
        md = response.choices[0].message.content.strip() # type: ignore
        return page_num, md

    async def _run_ocr(self, pages: list[int], doc: pymupdf.Document) -> list[str]:
        tasks = [self._ocr_single_page(page_num, doc) for page_num in pages]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        # filter out failures
        success_pages, mds = [], []
        for result in raw_results:
            if isinstance(result, Exception):
                logger.warning("Complex OCR failed for a page: %s", result)
                continue
            page_num, md = result # type: ignore
            success_pages.append(page_num)
            mds.append(md)

        failed = [p for p in pages if p not in success_pages]
        if failed:
            logger.warning("Complex channel: OCR failed for pages %s", failed)

        return mds
    
    def _to_base64(self, data: Any) -> str:
        pix = data.get_pixmap(dpi=self.dpi)
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

    async def _describe_and_upload_single_image(self, doc: pymupdf.Document, xref: str) -> tuple[str, str] | None:
        base_img = doc.extract_image(xref)
        if base_img["width"] < 105 or base_img["height"] < 105:
            return None

        img_bytes = base_img["image"]
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")

        img_ext = base_img["ext"].lower()
        if img_ext == 'jpg':
            img_ext = 'jpeg'

        async with self.semaphore:
            response = await self.ocr_client.chat.completions.create(
                model=self.ocr_model_id,
                temperature=0.2,
                reasoning_effort="none",
                messages=[
                    {
                        "role": "system",
                        "content": self._image_desc_prompt # type: ignore
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": "Analyze this image and generate the detailed retrieval description."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{img_ext};base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ]
            )
            
        description = response.choices[0].message.content.strip() # type: ignore

        img_url = await self.r2_img_storage.upload_image(img_bytes, img_ext)

        return img_url, description

    async def _describe_and_upload_images(self, doc: pymupdf.Document) -> dict[str, str]:
        all_xrefs = set()
        for xref_set in self.images_xrefs:
            all_xrefs.update(xref_set)

        tasks = [self._describe_and_upload_single_image(doc, xref) for xref in all_xrefs]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        url_to_desc: dict[str, str] = {}
        for result in raw_results:
            if isinstance(result, Exception):
                logger.warning("Image description failed: %s", result)
                continue
            if result is None:
                continue  # skipped (too small)
            url, description = result # type: ignore
            url_to_desc[url] = description

        failed_xrefs = [
            x for x, r in zip(all_xrefs, raw_results)
            if isinstance(r, Exception)
        ]
        if failed_xrefs:
            logger.warning("Complex channel: image description failed for xrefs %s", failed_xrefs)

        return url_to_desc