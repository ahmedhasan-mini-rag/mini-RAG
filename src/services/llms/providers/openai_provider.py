from openai import OpenAI, OpenAIError
import logging
from ..llm_interface import LLMInterface
from exceptions import LLMServiceError, InvalidConfigError

class OpenAIProvider(LLMInterface):
    def __init__(
        self, api_key: str, base_url: str,
        default_max_output_tokens: int = 1200,
        default_max_input_chars: int = 1200,
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

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

        self.logger = logging.getLogger(__name__)
    
    def set_chat_model(self, model_id: str):
        self.chat_model = model_id
    
    def set_embedding_model(self, model_id: str, embedding_size: int | None = None):
        self.embedding_model = model_id
        self.embedding_size = embedding_size

    @property
    def system_message(self) -> str | None:
        return self._system_message

    @system_message.setter
    def system_message(self, message: str | None):
        if message is not None and not isinstance(message, str):
            self.logger.error("system_message must be a string")
            return
        self._system_message = message
    
    def generate_text(
        self, 
        prompt: str, 
        chat_history: list = [], 
        max_output_tokens: int | None = None,
        temperature: float | None = None
    ) -> str:
        if not self.chat_model:
            raise InvalidConfigError("OpenAI chat model not configured")
        
        if len(prompt) > self.default_max_input_chars:
            raise InvalidConfigError(
                f"Prompt too long ({len(prompt)} chars). "
                f"Max allowed: {self.default_max_input_chars}"
            )

        kwargs = {
            "model": self.chat_model,
            "input": prompt,
            "previous_interaction_id": self._previous_interaction_id,
            "temperature": temperature or self.default_temperature,
            "max_output_tokens": max_output_tokens or self.default_max_output_tokens,
        }

        if self._system_message:
            kwargs["system_instruction"] = self._system_message
        
        try:
            response = self.client.responses.create(**kwargs)
        except OpenAIError as e:
            raise LLMServiceError("OpenAI text generation failed", detail=str(e)) from e

        if not response or not response.output_text:
            raise LLMServiceError("OpenAI returned empty response for text generation")
        
        self._previous_interaction_id = response.id

        return response.output_text
    
    def generate_embedding(
        self, 
        texts: list[str], 
        document_type: str = ''
    ) -> list[list[float]]:

        if not self.embedding_model:
            raise InvalidConfigError("OpenAI embedding model not configured")

        kwargs: dict[str, object] = {
            "model": self.embedding_model,
            "input": texts,
        }

        if self.embedding_size:
            kwargs["dimensions"] = self.embedding_size

        try:
            response = self.client.embeddings.create(**kwargs)
        except OpenAIError as e:
            raise LLMServiceError("OpenAI embedding generation failed", detail=str(e)) from e

        if not response or not response.data[0].embedding:
            raise LLMServiceError("OpenAI returned empty response for embedding generation")

        return [item.embedding for item in response.data]