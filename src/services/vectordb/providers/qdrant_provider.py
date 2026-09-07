import logging
import uuid
from exceptions import VectorDBServiceError
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import PointStruct, Distance

from models.schemas import RetrievedDocument
from ..vectordb_interface import VectorDBInterface
from ..vectordb_enums import SimilarityMetric


class QdrantProvider(VectorDBInterface):
    def __init__(self, dp_path: str, similarity_metric: str):
        self.client = AsyncQdrantClient(path=dp_path)
        
        self.logger = logging.getLogger(__name__)
        self.sim_metric = self._resolve_similarity_metric(metric=similarity_metric)

    async def init_db(self):
        return

    async def disconnect(self):
        await self.client.close() 
    
    async def collection_exists(self, collection_name: str) -> bool:
        try:
            return await self.client.collection_exists(collection_name=collection_name)
        except Exception as e:
            raise VectorDBServiceError(
                f"Failed to check collection existence for '{collection_name}'",
                detail=str(e)
            ) from e

    async def delete_collection(self, collection_name: str) -> bool:
        try:
            return await self.client.delete_collection(collection_name=collection_name)
        except Exception as e:
            raise VectorDBServiceError(
                f"Failed to delete collection '{collection_name}'",
                detail=str(e)
            ) from e

    async def create_collection(
        self, 
        collection_name: str,
        embedding_size: int,
        do_reset: bool = False
    ) -> bool:

        if do_reset:
            await self.delete_collection(collection_name)

        if not await self.collection_exists(collection_name):
            try:
                await self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=embedding_size, 
                        distance=self.sim_metric
                    ),
                )
            except Exception as e:
                raise VectorDBServiceError(
                    f"Failed to create collection '{collection_name}'",
                    detail=str(e)
                ) from e
        else:
            self.logger.warning(
                "Trying to create a collection that already exists. "
                "Pass do_reset=True to overwrite it."
            )
            return False
        
        return True

    async def get_collection_info(self, collection_name: str) -> dict:
        try:
            result = await self.client.get_collection(
                collection_name=collection_name
            )
        except Exception as e:
            raise VectorDBServiceError(
                f"Failed to get collection info for '{collection_name}'",
                detail=str(e)
            ) from e

        return result.model_dump()

    async def list_collections(self) -> list[str]:
        try:
            collections = await self.client.get_collections()
        except Exception as e:
            raise VectorDBServiceError("Failed to list collections", detail=str(e)) from e

        return [c.name for c in collections.collections]
    
    async def insert_vectors(
        self, 
        collection_name: str,
        vectors: list[list[float]],
        metadata: list[dict],
        ids: list[uuid.UUID],
    ) -> bool:

        if not await self.collection_exists(collection_name):
            raise VectorDBServiceError(f"Collection '{collection_name}' does not exist")
        
        if not (len(vectors) == len(metadata) == len(ids)):
            raise VectorDBServiceError(
                "Vectors, metadata, and ids must have the same length"
            )
            
        points = [
            PointStruct(
                id=idx,
                vector=vec,
                payload=meta
            )
            for idx, vec, meta in zip(ids, vectors, metadata)
        ]

        try:
            await self.client.upsert(
                collection_name=collection_name,
                points=points
            )
        except Exception as e:
            raise VectorDBServiceError(
                f"Failed to insert vectors into '{collection_name}'",
                detail=str(e)
            ) from e

        return True

    async def search_by_vector(
        self, 
        collection_name: str, 
        vector: list[float], 
        top_k: int
    ) -> list[RetrievedDocument]:

        try:
            search_results = await self.client.query_points(
                collection_name=collection_name,
                query=vector,
                limit=top_k
            )
        except Exception as e:
            raise VectorDBServiceError(
                f"Failed to search in '{collection_name}'",
                detail=str(e)
            ) from e

        return [
            RetrievedDocument(
                text=point.payload.text,            # type: ignore
                score=point.score,
                table_md=point.payload.table_md,    # type: ignore
                img_url=point.payload.img_url       # type: ignore
            ) 
            for point in search_results.points
        ]

    def _resolve_similarity_metric(self, metric: str) -> Distance:
        METRIC_TYPE = {
            'dot': Distance.DOT,
            'cosine': Distance.COSINE,
            'euclid': Distance.EUCLID,
        }

        chosen = METRIC_TYPE.get(metric.lower(), None)
        if chosen is None:
            self.logger.warning(
                f"Invalid similarity metric '{metric}'. "
                f"Defaulting to {SimilarityMetric.COSINE}."
            )
            return METRIC_TYPE['cosine']

        return chosen