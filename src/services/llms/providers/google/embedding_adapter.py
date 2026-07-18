from abc import ABC, abstractmethod
from google import genai
from google.genai import types
from ...LLMEnums import GoogleEmbeddingType


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
    def embed(self, text: str, document_type: GoogleEmbeddingType,
              embedding_size: int) -> list[float]:
        ...


class ConfigBasedAdapter(EmbeddingAdapter):
    """For gemini-embedding-001, text-embedding-004/005, etc.

    Uses EmbedContentConfig(task_type=...) to specify the task.
    """

    _TASK_MAP = {
        GoogleEmbeddingType.DOCUMENT: "RETRIEVAL_DOCUMENT",
        GoogleEmbeddingType.QUERY:    "QUESTION_ANSWERING",
    }

    def embed(self, text, document_type, embedding_size):
        task = self._TASK_MAP.get(document_type, "RETRIEVAL_DOCUMENT")
        res = self.client.models.embed_content(
            model=self.model_id,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task,
                output_dimensionality=embedding_size,
            ),
        )
        return res.embeddings[0].values


class InlineTaskAdapter(EmbeddingAdapter):
    """For gemini-embedding-2 and newer multimodal models.

    Uses inline text prefix formatting per Google's official docs:
    - Queries:   f"task: question answering | query: {text}"
    - Documents: f"title: none | text: {text}"
    """

    def embed(self, text, document_type, embedding_size):
        if document_type == GoogleEmbeddingType.QUERY:
            formatted = f"task: question answering | query: {text}"
        else:
            # Document storage — uses the title/text format per Google docs.
            # "none" is the placeholder when no title is available.
            formatted = f"title: none | text: {text}"

        res = self.client.models.embed_content(
            model=self.model_id,
            contents=formatted,
            config=types.EmbedContentConfig(
                output_dimensionality=embedding_size,
            ),
        )
        return res.embeddings[0].values


def get_embedding_adapter(client: genai.Client, model_id: str) -> EmbeddingAdapter:
    """Factory: inspects model name and returns the correct adapter."""
    if "embedding-2" in model_id.lower():
        return InlineTaskAdapter(client, model_id)
    return ConfigBasedAdapter(client, model_id)
