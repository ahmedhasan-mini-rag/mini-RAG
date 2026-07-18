from openai import OpenAI
import logging
from ..LLMInterface import LLMInterface

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
        max_output_tokens: int = None,
        temperature: float = None
    ):
        if not self.client:
            self.logger.error('Error: the OpenAI client was not set.')
            return None
        
        if not self.chat_model:
            self.logger.error('Error: the OpenAI chat model was not set.')
            return None
        
        if len(prompt) > self.default_max_input_chars:
            self.logger.error(f'Error: the prompt is too long. It should be less than {self.default_max_input_chars} characters.')
            return None

        kwargs = {
            "model": self.chat_model,
            "input": prompt,
            "previous_interaction_id": self._previous_interaction_id,
            "temperature": temperature or self.default_temperature,
            "max_output_tokens": max_output_tokens or self.default_max_output_tokens,
        }

        if self._system_message:
            kwargs["system_instruction"] = self._system_message
        
        response = self.client.responses.create(**kwargs)

        if not response or not response.output_text:
            self.logger.error('Error: failed to generate text (provider: openai).')
            return None
        
        self._previous_interaction_id = response.id

        return response.output_text
    
    def generate_embedding(self, text: str, document_type: str = None):
        if not self.client:
            self.logger.error('Error: the OpenAI client was not set.')
            return None
        
        if not self.embedding_model:
            self.logger.error('Error: the OpenAI embedding model was not set.')
            return None

        kwargs = {
            "model": self.embedding_model,
            "input": text,
        }

        if self.embedding_size:
            kwargs["dimensions"] = self.embedding_size

        response = self.client.embeddings.create(**kwargs)

        if not response or not response.data[0].embedding:
            self.logger.error('Error: failed to generate embedding (provider: openai).')
            return None

        return response.data[0].embedding