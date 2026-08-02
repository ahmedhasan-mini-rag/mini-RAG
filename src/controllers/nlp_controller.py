import uuid
from collections.abc import AsyncGenerator

from services.llms.llm_enums import EmbeddingType
from .base_controller import BaseController
from models.schemas import RetrievedDocument, Chunk
from services.llms.templates import load_template

class NLPController(BaseController):
    def __init__(self, chat_client, embedding_client, vectordb_client):
        super().__init__()

        self.chat_client = chat_client
        self.embedding_client = embedding_client
        self.vectordb_client = vectordb_client

    @classmethod
    def create_collection_name(cls, project_name: str) -> str:
        return f'collection_{project_name}'

    async def embed_and_store_chunks(
            self,
            project_name: str,
            chunks_iter: AsyncGenerator[Chunk, None],
            do_reset: bool,
            batch_size: int
    ) -> int:

        collection_name = self.create_collection_name(
            project_name=project_name
        )

        num_inserted = 0
        chunks_batch = {
            'texts': [], 'metadata': [], 'ids': []
        }

        async for chunk in chunks_iter:
            chunks_batch['texts'].append(chunk.chunk_text)
            chunks_batch['ids'].append(
                uuid.uuid5(uuid.NAMESPACE_OID, str(chunk.id))
            )

            metadata = dict(chunk.chunk_metadata) if chunk.chunk_metadata else {}
            metadata['text'] = chunk.chunk_text
            chunks_batch['metadata'].append(metadata)

            if len(chunks_batch['ids']) == batch_size:
                await self._embed_and_store(
                    chunks_batch=chunks_batch,
                    collection_name=collection_name,
                    reset_collection=do_reset
                )

                num_inserted += batch_size
                do_reset = False
                
                chunks_batch['ids'].clear()
                chunks_batch['texts'].clear()
                chunks_batch['metadata'].clear()

        if chunks_batch:
            await self._embed_and_store(
                chunks_batch=chunks_batch,
                collection_name=collection_name,
                reset_collection=do_reset
            )

            num_inserted += len(chunks_batch['ids'])

        return num_inserted

    async def _embed_and_store(
            self, 
            chunks_batch: dict[str, list],
            collection_name: str,
            reset_collection: bool
    ):
        vectors = self.embedding_client.generate_embedding(
            texts=chunks_batch['texts'],
            document_type=EmbeddingType.DOCUMENT
        )

        await self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=len(vectors[0]),
            do_reset=reset_collection
        )

        await self.vectordb_client.insert_vectors(
            collection_name=collection_name,
            vectors=vectors,
            metadata=chunks_batch['metadata'],
            ids=chunks_batch['ids']
        )

    async def search_vectordb_collection(
        self, 
        project_name: str, 
        text: str, 
        top_k: int
    ) -> list[RetrievedDocument]:

        collection_name = self.create_collection_name(
            project_name=project_name
        )

        vector: list[list[float]] = self.embedding_client.generate_embedding(
            texts=[text],
            document_type=EmbeddingType.QUERY
        )

        results = await self.vectordb_client.search_by_vector(
            collection_name=collection_name, 
            vector = vector[0], 
            top_k = top_k
        )

        retrieved = [
            RetrievedDocument(
                text=result['payload']['text'],
                score=result['score']
            )
            for result in results
        ]

        return retrieved

    async def generate_answer(
        self, 
        project_name: str, 
        query: str, 
        n_retrieved_docs: int,
        response_language: str
    ):
        docs = await self.search_vectordb_collection(
            project_name=project_name,
            text=query,
            top_k=n_retrieved_docs
        )
        rag_template = load_template(template_name='rag')

        self.chat_client.system_message = rag_template.format_system_prompt(
            response_language=response_language
        )

        formatted_docs = [
            rag_template.format_document(
                doc_num=i,
                chunk_text=doc.text
            )
            for i, doc in enumerate(docs, 1)
        ]
        formatted_docs = '\n'.join(formatted_docs)

        footer = rag_template.format_footer(user_query=query)

        full_prompt = f'{formatted_docs}\n\n{footer}'

        return self.chat_client.generate_text(prompt=full_prompt)



