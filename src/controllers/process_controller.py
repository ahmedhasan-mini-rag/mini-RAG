import os
import logging
from typing import Any
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .base_controller import BaseController
from .project_controller import ProjectController
from models.enums import ProcessingEnums, AssetTypeEnums, ResponseSignal
from models.schemas import Chunk, Project, ProcessRequest, Asset
from models import ChunkModel, AssetModel
from exceptions import (
    FileValidationError, FileNotFoundOnDiskError,
    AssetNotFoundError,
)

logger = logging.getLogger(__name__)

class ProcessController(BaseController):
    def __init__(self, project: Project):
        super().__init__()
        self.project = project
        self.project_path = ProjectController().get_project_path(
            project_name=project.name
        )
    
    def get_file_asset_extension(self, asset_name: str) -> str | None:
        return os.path.splitext(asset_name)[-1]
    
    def get_asset_loader(self, asset_name: str):
        """Return the appropriate file loader. Raises FileValidationError for unsupported types."""
        asset_ext = self.get_file_asset_extension(asset_name)
        asset_path = self.project_path / asset_name

        if asset_ext == ProcessingEnums.TXT:
            loader = TextLoader(asset_path, encoding='utf-8')

        elif asset_ext == ProcessingEnums.PDF:
            loader = PyMuPDFLoader(asset_path)
        
        else:
            raise FileValidationError(
                f"Unsupported file extension '{asset_ext}' for asset '{asset_name}'"
            )

        return loader
    
    def get_file_content(self, asset_name: str) -> list:
        loader = self.get_asset_loader(asset_name=asset_name)

        return loader.load()
    
    def split_file_content(
        self, 
        file_content: list, 
        chunk_size: int, 
        overlap_size: int
    ) -> list:
    
        splitter = RecursiveCharacterTextSplitter(
            chunk_overlap=overlap_size,
            chunk_size=chunk_size,
            length_function=len
        )

        data = [
            (doc.page_content, doc.metadata)
            for doc in file_content
        ]

        file_texts, file_metadata = tuple(zip(*data))

        chunks = splitter.create_documents(
            texts=file_texts,
            metadatas=file_metadata
        )
        return chunks


    async def process_tasks(
        self, 
        process_request: ProcessRequest, 
        chunk_model: ChunkModel,
        asset_model: AssetModel,
    ) -> dict[str, Any]:
    
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
                    file_content = self.get_file_content(asset_name=asset.asset_name)
                    chunks = self.split_file_content(
                        file_content=file_content,
                        chunk_size=chunk_size, 
                        overlap_size=overlap_size
                    )
                    
                except (FileValidationError, OSError) as e:
                    logger.error(
                        f"Error processing asset '{asset.asset_name}': {e}",
                        exc_info=True
                    )
                    continue

                if not chunks:
                    logger.error(
                        f"Error while processing the asset: {asset.asset_name}, " 
                        f"{ResponseSignal.PROCESSING_FAIL}"
                    )
                    continue

                data_chunks = [
                    Chunk(
                        chunk_metadata={'text': chunk.page_content} | chunk.metadata,
                        chunk_order=i,
                        chunk_project_id=self.project.id,
                        chunk_asset_id=asset.id
                    )
                    for i, chunk in enumerate(chunks, 1)
                ]

                all_chunks.extend(data_chunks)
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
