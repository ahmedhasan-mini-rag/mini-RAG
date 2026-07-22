from google import genai
from google.genai import types
import logging
from ...LLMInterface import LLMInterface
from ...LLMEnums import Role, EmbeddingType
from .embedding_adapter import get_embedding_adapter

class GoogleProvider(LLMInterface):
    def __init__(
        self, api_key: str,
        default_max_output_tokens: int = 1000,
        default_max_input_chars: int = 1500,
        default_temperature: float = 0.5
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

        self.client = genai(api_key=api_key)

        self.logger = logging.getLogger(__name__)
    
    def set_chat_model(self, model_id: str):
        self.chat_model = model_id
    
    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model = model_id
        self.embedding_size = embedding_size
        self._embedding_adapter = get_embedding_adapter(self.client, model_id)

    @property
    def system_message(self) -> str:
        return self._system_message

    @system_message.setter
    def system_message(self, message: str):
        if message is not None and not isinstance(message, str):
            self.logger.error("system_message must be a string")
            return
        self._system_message = message
    
    def generate_text(
        self, 
        prompt: str, 
        chat_history: list = [], 
        max_output_tokens: int = None,
        temperature: float = None
    ):
        if not self.client:
            self.logger.error('Error: the Google client was not set.')
            return None
        
        if not self.chat_model:
            self.logger.error('Error: the Google chat model was not set.')
            return None
        
        if len(prompt) > self.default_max_input_chars:
            self.logger.error(f'Error: the prompt is too long. It should be less than {self.default_max_input_chars} characters.')
            return None
        

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

        response = self.client.interactions.create(**kwargs)

        self._previous_interaction_id = response.id

        if not response or not response.output_text:
            self.logger.error('Error: failed to generate text (provider: google).')
            return None
        
        return response.output_text
    
    def generate_embedding(self, text: str, document_type: str = EmbeddingType.DOCUMENT):
        if not self.client:
            self.logger.error('Error: the Google client was not set.')
            return None
        
        if not self.embedding_model:
            self.logger.error('Error: the Google embedding model was not set.')
            return None

        input_type = self._resolve_document_type(document_type)
        embedding = self._embedding_adapter.embed(text, input_type, self.embedding_size)

        if not embedding:
            self.logger.error('Error: failed to generate embedding (provider: google).')
            return None

        return embedding

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
