"""Chunking module using *RecursiveCharacterTextSplitter* of langchain_text_splitters library

Receives a unified List[:class:`LoadedDocument`] input from different
loaders and splits every item with the common recursive
chunking way using the ``cl100k_base`` tiktoken tokenizer.
"""

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter, 
    MarkdownHeaderTextSplitter
)
from langchain_core.documents import Document

from ..loaders.schemas import LoadedDocument

def chunk_recursively(
        docs: list[LoadedDocument], 
        chunk_size: int, 
        overlap_size: int,
        split_on_atx_first: bool
) -> list[Document]:

    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",
        chunk_size=chunk_size,
        chunk_overlap=overlap_size,
    )

    if split_on_atx_first:
        md_docs = split_md_headers(docs=docs)
        return splitter.split_documents(md_docs)

    file_texts = [doc.text for doc in docs]
    file_metadata = [doc.metadata.model_dump(exclude_none=True) for doc in docs]

    chunks = splitter.create_documents(
        texts=file_texts,
        metadatas=file_metadata
    )

    return chunks

def split_md_headers(docs: list[LoadedDocument]) -> list[Document]:
    headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
    ("####", "Header 4"),
]
    
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=True
    )
    result = []
    for doc in docs:
        for doc_split in md_splitter.split_text(doc.text):
            doc_split.metadata.update(doc.metadata)
            result.append(doc_split)

    return result
