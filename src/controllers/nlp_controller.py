from tqdm.auto import tqdm

from services.llms.llm_enums import EmbeddingType
from .base_controller import BaseController
from models.schemas import RetrievedDocument, Chunk
from services.llms.templates import load_template
from models import ProjectModel

class NLPController(BaseController):
    def __init__(self, chat_client, embedding_client, vectordb_client):
        super().__init__()

        self.chat_client = chat_client
        self.embedding_client = embedding_client
        self.vectordb_client = vectordb_client

    @classmethod
    def create_collection_name(cls, project_name: str) -> str:
        ProjectModel.validate_project_name(project_name)
        return f'collection_{project_name}'

    async def embed_and_store_chunks(
            self,
            project_name: str,
            chunks: list[Chunk],
            do_reset: bool,
            batch_size: int
    ) -> int:

        collection_name = self.create_collection_name(
            project_name=project_name
        )

        test_vector = self.embedding_client.generate_embedding(
            texts=[chunks[0].chunk_metadata['text']],
            document_type=EmbeddingType.DOCUMENT
        )
        await self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=len(test_vector[0]),
            do_reset=do_reset
        )

        await self.vectordb_client.insert_vectors(
            collection_name=collection_name,
            vectors=test_vector,
            metadata=[chunks[0].chunk_metadata],
            ids=[chunks[0].id]
        )

        num_inserted = 1
        texts, metadata, ids = [], [], []

        progress = tqdm(
            desc=f'Embedding and Storing Chunks for project {project_name}', 
            total=len(chunks)-1, unit='chunks'
        )

        for chunk in chunks[1:]:
            texts.append(chunk.chunk_metadata['text'])
            ids.append(chunk.id)
            metadata.append(chunk.chunk_metadata)

            if len(ids) == batch_size:
                vectors = self.embedding_client.generate_embedding(
                    texts=texts,
                    document_type=EmbeddingType.DOCUMENT
                )

                await self.vectordb_client.insert_vectors(
                    collection_name=collection_name,
                    vectors=vectors,
                    metadata=metadata,
                    ids=ids,
                )

                num_inserted += batch_size
                
                ids.clear()
                texts.clear()
                metadata.clear()

                progress.update(batch_size)

        if ids:
            vectors = self.embedding_client.generate_embedding(
                texts=texts,
                document_type=EmbeddingType.DOCUMENT
            )

            await self.vectordb_client.insert_vectors(
                collection_name=collection_name,
                vectors=vectors,
                metadata=metadata,
                ids=ids,
            )

            num_inserted += len(ids)
            progress.update(len(ids))
        
        progress.close()

        return num_inserted

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

        return results

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



