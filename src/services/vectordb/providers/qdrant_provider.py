from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct
import logging

from ..VectorDBInterface import VectorDBInterface
from .. VectorDBEnums import SimilarityMetric

class QdrantProvider(VectorDBInterface):
    def __init__(self, dp_path: str, similarity_metric: str):
        self.client = QdrantClient(url=dp_path)
        
        if similarity_metric.lower() == SimilarityMetric.DOT:
            self.sim_metric = SimilarityMetric.DOT
        else:
            self.sim_metric = SimilarityMetric.COSINE
        
        self.logger = logging.getLogger(__name__)

    def collection_exists(self, collection_name: str) -> bool:
        return self.client.collection_exists(collection_name=collection_name)

    def delete_collection(self, collection_name: str) -> bool:
        return self.client.delete_collection(collection_name=collection_name)

    def create_collection(
        self, 
        collection_name: str,
        embedding_size: int,
        do_reset: bool = False
    ) -> bool:

        if do_reset:
            self.delete_collection(collection_name)
        
        if not self.collection_exists(collection_name):
            try:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=embedding_size, 
                        distance=self.sim_metric
                    ),
                )
            except Exception as e:
                self.logger.error(f"Error while trying to create a collection: {e}")
                return False
        else:
            self.logger.warning(
                "Trying to create a collection that already exists. "
                "Pass do_reset=True to overwrite it."
            )
            return False
        
        return True

    def get_collection_info(self, collection_name: str) -> dict:
        return self.client.get_collection(
            collection_name=collection_name
        ).model_dump()

    def list_collections(self) -> list[str]:
        collections = self.client.get_collections()
        return [c.name for c in collections.collections]
    
    def insert_vector(
        self, 
        collection_name: str,
        vector: list[float],
        metadata: dict,
        vector_id: int | str
    ) -> bool:

        if not self.collection_exists(collection_name):
            self.logger.error(f"Collection '{collection_name}' does not exist.")
            return False
        
        try:
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=vector_id,
                        vector=vector,
                        payload=metadata
                    )
                ]
            )
        except Exception as e:
            self.logger.error(f"Error while trying to insert a single vector: {e}")
            return False

        return True

    def insert_vectors(
        self, 
        collection_name: str,
        vectors: list[list[float]],
        metadata: list[dict],
        ids: list[int | str],
        batch_size: int = 100,
    ) -> bool:

        if len(vectors) != len(metadata) != len(ids):
            self.logger.error("Vectors, metadata, and ids must have the same length.")
            return False
        
        for i in range(0, len(vectors), batch_size):
            j = i+batch_size

            batch_vectors = vectors[i : j]
            batch_metadata = metadata[i : j]
            batch_ids = ids[i : j]
            
            points = [
                PointStruct(
                    id=batch_ids[k],
                    vector=batch_vectors[k],
                    payload=batch_metadata[k]
                )

                for k in range(len(batch_ids))
            ]

            try:
                self.client.upsert(
                    collection_name=collection_name,
                    points=points
                )
            except Exception as e:
                self.logger.error(f"Error while trying to insert multiple vectors in a batch: {e}")
                return False

        return True

    def search_by_vector(
        self, 
        collection_name: str, 
        vector: list[float], 
        top_k: int
    ) -> list[dict]:

        try:
            search_results = self.client.query_points(
                collection_name=collection_name,
                query=vector,
                limit=top_k
            )
        except Exception as e:
            self.logger.error(f"Error while trying to search for similar vectors: {e}")
            return []

        return [point.model_dump() for point in search_results.points]