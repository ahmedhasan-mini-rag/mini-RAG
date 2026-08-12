from abc import ABC, abstractmethod
import uuid

class VectorDBInterface(ABC):

    @abstractmethod
    async def init_db(self):
        ...

    @abstractmethod
    async def disconnect(self):
        ...
    
    @abstractmethod
    async def collection_exists(self, collection_name: str) -> bool:
        ...
    
    @abstractmethod
    async def create_collection(
        self, 
        collection_name: str,
        embedding_size: int,
        do_reset: bool = False
    ) -> bool:
        ...
    
    @abstractmethod
    async def get_collection_info(self, collection_name: str) -> dict:
        ...

    @abstractmethod
    async def list_collections(self) -> list[str]:
        ...
    
    @abstractmethod
    async def delete_collection(self, collection_name: str) -> bool:
        ...
    
    @abstractmethod
    async def insert_vectors(
        self, 
        collection_name: str,
        vectors: list[list[float]],
        metadata: list[dict],
        ids: list[uuid.UUID]
    ) -> bool:
        ...

    @abstractmethod
    async def search_by_vector(
        self, 
        collection_name: str, 
        vector: list[float], 
        top_k: int
    ) -> list[dict]:
        ...

    def _resolve_similarity_metric(self, metric: str):
        ...