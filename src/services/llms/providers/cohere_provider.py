from cohere import ClientV2
from cohere.core import ApiError as CohereApiError
import logging
from ..llm_interface import LLMInterface
from ..llm_enums import Role, EmbeddingType
from exceptions import LLMServiceError, InvalidConfigError

class CohereProvider(LLMInterface):
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

        self._system_message = None
        self._chat_history = [{}]

        self.client = ClientV2(api_key=api_key)

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
        self._chat_history[0] = {
            'role': Role.SYSTEM, 'content': message
        }
    
    def set_chat_model(self, model_id: str):
        self.chat_model = model_id
    
    def set_embedding_model(self, model_id: str, embedding_size: int | None):
        self.embedding_model = model_id
        self.embedding_size = embedding_size
    
    def generate_text(
        self, 
        prompt: str, 
        max_output_tokens: int | None = None,
        temperature: float | None = None
    ) -> str:
        if not self.chat_model:
            raise InvalidConfigError("Cohere chat model not configured")
        
        if len(prompt) > self.default_max_input_chars:
            raise InvalidConfigError(
                f"Prompt too long ({len(prompt)} chars). "
                f"Max allowed: {self.default_max_input_chars}"
            )

        self._update_chat_history(role = Role.USER, content = prompt)
        
        try:
            response = self.client.chat(
                model=self.chat_model,
                messages=self._chat_history,
                max_tokens=max_output_tokens or self.default_max_output_tokens,
                temperature=temperature or self.default_temperature,
            )
        except CohereApiError as e:
            raise LLMServiceError("Cohere text generation failed", detail=str(e)) from e

        if not response or not response.message.content[0].text:
            raise LLMServiceError("Cohere returned empty response for text generation")
        
        self._update_chat_history(
            role = Role.ASSISTANT, 
            content = response.message.content[0].text
        )

        return self._chat_history[-1]['content']

    def generate_embedding(
        self, 
        texts: list[str], 
        document_type: str = EmbeddingType.DOCUMENT
    ) -> list[list[float]]:
    
        if not self.embedding_model:
            raise InvalidConfigError("Cohere embedding model not configured")

        input_type = self._resolve_document_type(document_type)

        kwargs = {
            "model": self.embedding_model,
            "texts": texts,
            "input_type": input_type
        }

        if self.embedding_size:
            kwargs["output_dimension"] = self.embedding_size

        try:
            response = self.client.embed(**kwargs)
        except CohereApiError as e:
            raise LLMServiceError("Cohere embedding generation failed", detail=str(e)) from e

        if not response or not response.embeddings.float:
            raise LLMServiceError("Cohere returned empty response for embedding generation")

        return response.embeddings.float
    
    def _resolve_document_type(self, document_type: str) -> str:
        """Map a raw string to the EmbeddingType enum with a safe default."""

        TASK_MAP = {
            EmbeddingType.DOCUMENT: "search_document",
            EmbeddingType.QUERY:    "search_query",
        }

        task = TASK_MAP.get(document_type, None)

        if task is None:
            self.logger.warning(
                f"Invalid document type '{document_type}'. "
                f"Defaulting to {EmbeddingType.DOCUMENT}."
            )
            return TASK_MAP[EmbeddingType.DOCUMENT]

        return task

    def _update_chat_history(self, role: Role, content: str):
        self._chat_history.append(
            {
                'role': role,
                'content': content
            }
        )