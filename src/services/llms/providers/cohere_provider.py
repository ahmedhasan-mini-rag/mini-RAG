from cohere import ClientV2
import logging
from ..LLMInterface import LLMInterface
from ..LLMEnums import Role, EmbeddingType

class CohereProvider(LLMInterface):
    def __init__(
        self, api_key: str,
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

        self.client = ClientV2(api_key=api_key)

        self.logger = logging.getLogger(__name__)
    
    def set_chat_model(self, model_id: str):
        self.chat_model = model_id
    
    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model = model_id
        self.embedding_size = embedding_size
    
    def generate_text(
        self, 
        prompt: str, 
        chat_history: list = [], 
        max_output_tokens: int = None,
        temperature: float = None
    ):
        if not self.client:
            self.logger.error('Error: the Cohere client was not set.')
            return None
        
        if not self.chat_model:
            self.logger.error('Error: the Cohere chat model was not set.')
            return None
        
        if len(prompt) > self.default_max_input_chars:
            self.logger.error(f'Error: the prompt is too long. It should be less than {self.default_max_input_chars} characters.')
            return None
        
        chat_history.append(
            {
                "role": Role.USER,
                "content": prompt
            }
        )

        response = self.client.chat(
            model=self.chat_model,
            messages=chat_history,
            max_tokens=max_output_tokens or self.default_max_output_tokens,
            temperature=temperature or self.default_temperature,
        )

        if not response or not response.message.content[0].text:
            self.logger.error('Error: failed to generate text (provider: cohere).')
            return None
        
        return response.message.content[0].text

    def generate_embedding(
        self, 
        text: str, 
        document_type: str = EmbeddingType.DOCUMENT
    ) -> list[float]:
    
        if not self.client:
            self.logger.error('Error: the Cohere client was not set.')
            return None
        
        if not self.embedding_model:
            self.logger.error('Error: the Cohere embedding model was not set.')
            return None

        input_type = self._resolve_document_type(document_type)

        kwargs = {
            "model": self.embedding_model,
            "texts": [text],
            "input_type": input_type
        }

        if self.embedding_size:
            kwargs["output_dimension"] = self.embedding_size

        response = self.client.embed(**kwargs)

        if not response or not response.embeddings.float[0]:
            self.logger.error('Error: failed to generate embedding (provider: cohere).')
            return None

        return response.embeddings.float[0]
    
    def _resolve_document_type(self, document_type: str) -> EmbeddingType:
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