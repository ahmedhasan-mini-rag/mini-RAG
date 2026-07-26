from abc import ABC, abstractmethod
from google import genai
from google.genai import types, errors as genai_errors
from ...llm_enums import EmbeddingType
from exceptions import LLMServiceError


class EmbeddingAdapter(ABC):
    """Abstraction over Google's embedding API version differences.

    V1 models (gemini-embedding-001, text-embedding-004/005) use
    EmbedContentConfig(task_type=...) to specify the task.

    V2 models (gemini-embedding-2+) use inline text prefix formatting.
    """

    def __init__(self, client: genai.Client, model_id: str):
        self.client = client
        self.model_id = model_id

    @abstractmethod
    def embed(self, texts: list[str], document_type: EmbeddingType, 
                embedding_size: int) -> list[list[float]]:
        ...


class ConfigBasedAdapter(EmbeddingAdapter):
    """For gemini-embedding-001, text-embedding-004/005, etc.

    Uses EmbedContentConfig(task_type=...) to specify the task.
    """

    _TASK_MAP = {
        EmbeddingType.DOCUMENT: "RETRIEVAL_DOCUMENT",
        EmbeddingType.QUERY:    "QUESTION_ANSWERING",
    }

    def embed(self, texts, document_type, embedding_size):
        task = self._TASK_MAP.get(document_type, "RETRIEVAL_DOCUMENT")

        try:
            response = self.client.models.embed_content(
                model=self.model_id,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task,
                    output_dimensionality=embedding_size,
                ),
            )
        except genai_errors.APIError as e:
            raise LLMServiceError("Google embedding generation failed", detail=str(e)) from e
    
        return [embedding.values for embedding in response.embeddings]


class InlineTaskAdapter(EmbeddingAdapter):
    """For gemini-embedding-2 and newer multimodal models.

    Uses inline text prefix formatting per Google's official docs:
    - Queries:   f"task: question answering | query: {text}"
    - Documents: f"title: none | text: {text}"
    """

    def embed(self, texts, document_type, embedding_size):
        if document_type == EmbeddingType.QUERY:
            formatted = [
                f"task: question answering | query: {text}" for text in texts
            ]
        else:
            formatted = [
                f"title: none | text: {text}" for text in texts
            ]

        try:
            response = self.client.models.embed_content(
                model=self.model_id,
                contents=formatted,
                config=types.EmbedContentConfig(
                    output_dimensionality=embedding_size,
                ),
            )
        except genai_errors.APIError as e:
            raise LLMServiceError("Google embedding generation failed", detail=str(e)) from e

        return [embedding.values for embedding in response.embeddings]


def get_embedding_adapter(client: genai.Client, model_id: str) -> EmbeddingAdapter:
    """Factory: inspects model name and returns the correct adapter."""
    if "embedding-2" in model_id.lower():
        return InlineTaskAdapter(client, model_id)
    return ConfigBasedAdapter(client, model_id)
