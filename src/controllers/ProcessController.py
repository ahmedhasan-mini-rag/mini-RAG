import os
from pathlib import Path
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .BaseController import BaseController
from .ProjectController import ProjectController
from models.enums import ProcessingEnums

class ProcessController(BaseController):
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)
    
    def get_file_extension(self, file_id: str) -> str:
        return os.path.splitext(file_id)[-1]
    
    def get_file_loader(self, file_id: str):
        file_ext = self.get_file_extension(file_id)
        file_path = self.project_path / file_id

        if file_ext == ProcessingEnums.TXT.value:
            loader = TextLoader(file_path, encoding='utf-8')

        elif file_ext == ProcessingEnums.PDF.value:
            loader = PyMuPDFLoader(file_path)
        
        else:
            loader = None

        return loader
    
    def get_file_content(self, file_id: str) -> list:
        loader = self.get_file_loader(file_id=file_id)

        return loader.load()
    
    def process_file_content(self, file_content: list,
                            chunk_size: int, overlap_size: int) -> list:

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
