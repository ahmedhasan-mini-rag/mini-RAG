from google import genai
from google.genai import types, errors as genai_errors
import logging
from ...llm_interface import LLMInterface
from ...llm_enums import Role, EmbeddingType
from .embedding_adapter import get_embedding_adapter
from exceptions import LLMServiceError, InvalidConfigError

class GoogleProvider(LLMInterface):
    def __init__(
        self, api_key: str,
        default_max_output_tokens: int,
        default_max_input_chars: int,
        default_temperature: float
    ):

        self.default_max_output_tokens = default_max_output_tokens
        self.default_max_input_chars = default_max_input_chars
        self.default_temperature = default_temperature

        self.chat_model = None
        self.embedding_model = None
        self.embedding_size = None

        self._previous_interaction_id = None
        self._system_message = None
        self._embedding_adapter = None

        self.client = genai.Client(api_key=api_key)

        self.logger = logging.getLogger(__name__)
    
    @property
    def system_message(self) -> str | None:
        return self._system_message

    @system_message.setter
    def system_message(self, message: str):
        if message is not None and not isinstance(message, str):
            self.logger.error("system_message must be a string")
            return
        self._system_message = message
    
    def set_chat_model(self, model_id: str):
        self.chat_model = model_id
    
    def set_embedding_model(self, model_id: str, embedding_size: int | None):
        self.embedding_model = model_id
        self.embedding_size = embedding_size
        self._embedding_adapter = get_embedding_adapter(self.client, model_id)
    
    def generate_text(
        self, 
        prompt: str, 
        max_output_tokens: int | None = None,
        temperature: float | None = None
    ) -> str:
        if not self.chat_model:
            raise InvalidConfigError("Google chat model not configured")
        
        if len(prompt) > self.default_max_input_chars:
            raise InvalidConfigError(
                f"Prompt too long ({len(prompt)} chars). "
                f"Max allowed: {self.default_max_input_chars}"
            )

        kwargs = {
            "model": self.chat_model,
            "input": prompt,
            "previous_interaction_id": self._previous_interaction_id,
            "generation_config": {
                "max_output_tokens" : max_output_tokens or self.default_max_output_tokens,
                "temperature" : temperature or self.default_temperature,
            }
        }
        
        if self._system_message:
            kwargs["system_instruction"] = self._system_message

        try:
            response = self.client.interactions.create(**kwargs)
        except genai_errors.APIError as e:
            raise LLMServiceError("Google text generation failed", detail=str(e)) from e

        self._previous_interaction_id = response.id

        if not response or not response.output_text:
            raise LLMServiceError("Google returned empty response for text generation")
        
        return response.output_text
    
    def generate_embedding(
        self, 
        texts: list[str], 
        document_type: str = EmbeddingType.DOCUMENT
    ) -> list[list[float]]:

        if not self.embedding_model:
            raise InvalidConfigError("Google embedding model not configured")

        input_type = self._resolve_document_type(document_type)

        try:
            embeddings = self._embedding_adapter.embed(
                texts, input_type, self.embedding_size
            )
        except genai_errors.APIError as e:
            raise LLMServiceError(
                "Google embedding generation failed", detail=str(e)
            ) from e

        if not embeddings:
            raise LLMServiceError("Google returned empty response for embedding generation")

        return embeddings

    def _resolve_document_type(self, document_type: str) -> EmbeddingType:
        """Map a raw string to the EmbeddingType enum with a safe default."""
        try:
            return EmbeddingType(document_type.lower())
        except ValueError:
            self.logger.warning(
                f"Invalid document type '{document_type}'. "
                f"Defaulting to {EmbeddingType.DOCUMENT}."
            )
            return EmbeddingType.DOCUMENT
