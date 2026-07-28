from abc import ABC, abstractmethod

class LLMInterface(ABC):

    @abstractmethod
    def set_chat_model(self, model_id: str):
        ...
    
    @abstractmethod
    def set_embedding_model(self, model_id: str, embedding_size: int):
        ...
    
    @abstractmethod
    def generate_text(
        self, 
        prompt: str, 
        max_output_tokens: int | None = None,
        temperature: float | None = None
    ) -> str:
        ...
    
    @abstractmethod
    def generate_embedding(self, text: str, document_type: str) -> list[float]:
        ...