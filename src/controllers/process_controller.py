import os
import logging
import time
from typing import Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .base_controller import BaseController
from .project_controller import ProjectController
from models.enums import AssetTypeEnums, ResponseSignal
from models.schemas import Chunk, Project, ProcessRequest, Asset
from models import ChunkModel, AssetModel
from ingestion.loaders import load_file
from ingestion.chunkers.recursive_chunking import chunk_recursively
from ingestion.loaders.schemas import LoadedDocument
from ingestion.loaders.schemas import ProcessingOutputType
from exceptions import (
    FileValidationError, FileNotFoundOnDiskError,
    AssetNotFoundError, FileIOError,
)

logger = logging.getLogger(__name__)

class ProcessController(BaseController):
    def __init__(self, project: Project):
        super().__init__()
        self.project = project
        self.project_path = ProjectController().get_project_path(
            project_name=project.name
        )
    
    async def get_file_content(self, asset_name: str) -> list[LoadedDocument]:
        """Extract content from an asset file using the loader pipeline."""
        asset_path = self.project_path / asset_name
        return await load_file(asset_path)

    async def process_tasks(
        self, 
        process_request: ProcessRequest, 
        chunk_model: ChunkModel,
        asset_model: AssetModel,
    ) -> dict[str, Any]:

        gs = time.perf_counter()
        kwargs = {
            'chunk_size': process_request.chunk_size,
            'overlap_size': process_request.overlap_size,
            'chunk_model': chunk_model,
        }

        if process_request.asset_name:
            logger.info(f"processing single file: {process_request.asset_name}")

            try:
                asset = await asset_model.get_asset(
                    asset_project_id=self.project.id,
                    asset_name=process_request.asset_name
                )
            except AssetNotFoundError:
                logger.error(f"Asset '{process_request.asset_name}' not found in the database.")
                return {
                    'processed_files': 0,
                    'inserted_chunks': 0,
                    'failed_files': 1,
                    'files_not_found': [process_request.asset_name]
                }
            
            assets = [asset]

        else:
            logger.info(f"processing all assets of project '{self.project.name}'")
            assets = await asset_model.get_project_assets(
                asset_project_id=self.project.id, 
                asset_type=AssetTypeEnums.FILE
            )

        n_chunks, n_files_proc, not_found = await self.process_files(
            assets=assets, **kwargs
        )

        ge = time.perf_counter()
        print(f'total time: {ge-gs}')
        return {
            'processed_files': n_files_proc,
            'inserted_chunks': n_chunks,
            'failed_files': len(assets) - n_files_proc,
            'files_not_found': not_found
        }

    async def process_files(
        self, 
        assets: list[Asset], 
        chunk_size: int, 
        overlap_size: int,
        chunk_model: ChunkModel,
    ) -> tuple[int, int, list[str]]:

            not_found = []
            all_chunks = []
            n_chunks, n_files_proc = 0, 0

            for asset in assets:
                try:
                    self.validate_existence(asset)
                except FileNotFoundOnDiskError:
                    not_found.append(asset.asset_name)
                    continue
                
                try:
                    file_content = await self.get_file_content(asset_name=asset.asset_name)
                    ext = os.path.splitext(asset.asset_name)

                    # process text docs
                    text_docs = [
                        doc for doc in file_content
                        if doc.metadata.doc_type == ProcessingOutputType.TEXT
                    ]
                    text_chunks = chunk_recursively(
                        docs=text_docs,
                        chunk_size=chunk_size, 
                        overlap_size=overlap_size,
                        split_on_atx_first=(ext == '.pdf')
                    )
                    
                except (FileValidationError, FileIOError, OSError) as e:
                    logger.error(
                        f"Error processing asset '{asset.asset_name}': {e}",
                        exc_info=True
                    )
                    continue

                if not text_chunks:
                    logger.error(
                        f"Error while processing the asset: {asset.asset_name}, " 
                        f"{ResponseSignal.PROCESSING_FAIL}"
                    )
                    continue

                chunks = [
                    Chunk(
                        chunk_metadata={'text': chunk.page_content} | chunk.metadata,
                        chunk_project_id=self.project.id,
                        chunk_asset_id=asset.id
                    )
                    for chunk in text_chunks
                ]

                # add non-text docs
                chunks.extend([
                    Chunk(
                        chunk_metadata={'text': doc.text} | doc.metadata.model_dump(exclude_none=True),
                        chunk_project_id=self.project.id,
                        chunk_asset_id=asset.id
                    )
                    for doc in file_content
                    if doc.metadata.doc_type != ProcessingOutputType.TEXT
                ])

                all_chunks.extend(chunks)
                n_files_proc += 1

            if all_chunks:
                n_chunks = await chunk_model.insert_multiple_chunks(chunks=all_chunks)

            logger.info(
                f"Batch complete: processed {n_files_proc}/{len(assets)} files, "
                f"inserted {n_chunks} chunks, {len(not_found)} not found."
            )

            return n_chunks, n_files_proc, not_found

    def validate_existence(self, asset: Asset) -> None:
        """Raise FileNotFoundOnDiskError if the asset file doesn't exist on disk."""
        if not self.check_file_exists(self.project.name, asset.asset_name):
            raise FileNotFoundOnDiskError(
                f"File '{asset.asset_name}' not found on disk for project '{self.project.name}'"
            )
