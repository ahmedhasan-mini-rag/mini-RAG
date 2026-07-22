from abc import ABC, abstractmethod

class VectorDBInterface(ABC):
    
    @abstractmethod
    def create_collection(
        self, 
        collection_name: str,
        embedding_size: int,
        do_reset: bool = False
    ) -> bool:
        ...
    
    @abstractmethod
    def get_collection_info(self, collection_name: str) -> dict:
        ...

    @abstractmethod
    def list_collections(self) -> list[str]:
        ...
    
    @abstractmethod
    def delete_collection(self, collection_name: str) -> bool:
        ...

    @abstractmethod
    def collection_exists(self, collection_name: str) -> bool:
        ...
    
    @abstractmethod
    def insert_vector(
        self, 
        collection_name: str,
        vector: list[float],
        metadata: dict,
        vector_id: int | str,
    ) -> bool:
        ...
    
    @abstractmethod
    def insert_vectors(
        self, 
        collection_name: str,
        vectors: list[list[float]],
        texts: list[str],
        metadata: list[dict],
        batch_size: int = 100
    ) -> bool:
        ...

    @abstractmethod
    def search_by_vector(
        self, 
        collection_name: str, 
        vector: list[float], 
        top_k: int
    ) -> list[dict]:
        ...