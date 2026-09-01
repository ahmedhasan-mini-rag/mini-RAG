"""PDF loader using *pymupdf*."""

from __future__ import annotations

import time
import asyncio
import uuid
import logging
from pathlib import Path
import pymupdf
from openai import AsyncOpenAI

from .base import BaseLoader, register_loader
from .schemas import LoadedDocument
from exceptions import FileIOError
from ..pdf_pipeline import classify_doc_pages, PDFProcessor
from ..pdf_pipeline.channel_processors import *
from ..pdf_pipeline.enums import ProcessingChannel
from .schemas import ProcessingOutputType, DocumentMetaData
from utils.config import get_settings

logger = logging.getLogger(__name__)


@register_loader('.pdf')
class PdfLoader(BaseLoader):
    async def load(self, file_path: Path) -> list[LoadedDocument]:
        settings = get_settings()

        try:
            with pymupdf.open(file_path) as pdf:
                page_groups = classify_doc_pages(
                    doc=pdf,
                    text_max_limit=settings.SCANNED_PAGE_TEXT_MAX_LIMIT,
                    ratio_min_limit=settings.SCANNED_PAGE_MIN_RATIO_LIMIT
                )

                images_xrefs = [
                    {img[0] for img in pdf[page_num].get_images()} 
                    for page_num in page_groups[ProcessingChannel.COMPLEX]
                ]
                ch_proc = self._prepare_channel_processors(settings, images_xrefs)
                pdf_proc = PDFProcessor(**ch_proc)
                # print(f'page_groups: {page_groups}\n')

                proc_results = await pdf_proc.process(
                    doc=pdf, 
                    page_groups=page_groups,
                )

                metadata_template = DocumentMetaData(
                    source = str(file_path),
                    format = ".pdf",
                    total_pages = len(pdf),
                )

                output = self._normalize_output(
                    proc_results=proc_results,
                    proc_pages=tuple(page_groups.values()),
                    metadata_template=metadata_template
                )

                return output
        except Exception as exc:
            img_names = []
            for xref in images_xrefs:
                base_img = pdf.extract_image(xref)

                img_ext = base_img["ext"].lower()
                if img_ext == 'jpg':
                    img_ext = 'jpeg'
                
                img_names.append(
                    {
                        'key': R2ImageStorage.create_image_name(
                                    img_bytes=base_img["image"],
                                    img_ext=img_ext
                                )
                    }
                )
            
            delete_payload = {
                "Objects": img_names,
                "Quiet": True
            }

            r2_img_storage = R2ImageStorage(r2_config=settings.r2_bucket_config)
            await r2_img_storage.delete_images(delete_payload)

            logger.info('Orphan images were deleted form the R2 bucket '
                        f'upon processing failure of the file "{file_path.name}"')

            raise FileIOError(
                f"Failed to extract text from PDF '{file_path.name}'",
                detail=str(exc),
            ) from exc

    def _normalize_output(
            self, 
            proc_results: list[ProcessingResult], 
            proc_pages: tuple[list[int], ...],
            metadata_template: DocumentMetaData
    ) -> list[LoadedDocument]:
        
        output = []
        for result, pages in zip(proc_results, proc_pages):
            if len(result.md_text) != len(pages):
                logger.warning(
                    f'Potential problem: length of resulting md_text({len(result.md_text)})' 
                    f'is expected to match the length of processed pages({len(pages)})'
                )

            # text
            for i, text in enumerate(result.md_text):
                cur_metadata = metadata_template.model_copy()
                cur_metadata.doc_type = ProcessingOutputType.TEXT
                cur_metadata.page = pages[i]

                output.append(
                    LoadedDocument(
                        text=text,
                        metadata=cur_metadata
                    )
                )

            # images
            for url, desc in result.images.items():
                cur_metadata = metadata_template.model_copy()
                cur_metadata.doc_type = ProcessingOutputType.IMAGE
                cur_metadata.img_url = url

                output.append(
                    LoadedDocument(
                        text=desc,
                        metadata=cur_metadata
                    )
                )

            # tables
            for page_tables in result.tables:
                for table in page_tables:
                    cur_metadata = metadata_template.model_copy()
                    cur_metadata.doc_type = ProcessingOutputType.TABLE
                    cur_metadata.table_md = table['markdown']

                    output.append(
                        LoadedDocument(
                            text=table['description'],
                            metadata=cur_metadata
                        )
                    )
        
        return output

    def _prepare_channel_processors(self, settings, images_xrefs) -> dict:
        ocr_client = AsyncOpenAI(
            base_url=settings.OCR_MODEL_URL,
            api_key=settings.OCR_MODEL_API_KEY
        )

        semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_VLM_CALLS)

        return {
            'scanned_processor': ScannedChannelProcessor(
                ocr_client=ocr_client,
                ocr_model_id=settings.OCR_MODEL_ID,
                dpi=settings.CONVERSION_DPI,
                semaphore=semaphore
            ),
            'complex_processor': ComplexChannelProcessor(
                ocr_client=ocr_client,
                ocr_model_id=settings.OCR_MODEL_ID,
                dpi=settings.CONVERSION_DPI,
                semaphore=semaphore,
                r2_bucket_config=settings.r2_bucket_config,
                images_xrefs=images_xrefs
            ),
            'simple_processor': SimpleChannelProcessor()
        }