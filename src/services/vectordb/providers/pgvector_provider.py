import uuid
import logging
from dataclasses import dataclass
from collections.abc import Callable
from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from pgvector.sqlalchemy import Vector

from models.schemas import RetrievedDocument
from exceptions import VectorDBServiceError
from ..vectordb_interface import VectorDBInterface
from ..vectordb_enums import SimilarityMetric

@dataclass
class SimilarityMetricInfo:
    symbol: str
    operation: str 
    norm_method: Callable[[float], float]

class PGVectorProvider(VectorDBInterface):
    def __init__(
            self, 
            pg_client: async_sessionmaker, 
            similarity_metric: str, 
            index_type: str,
            index_building_threshold: int
    ):
        self.client = pg_client
        self.sim_metric_info = self._resolve_similarity_metric(similarity_metric)
        self.index_type = index_type
        self.index_building_threshold = index_building_threshold

        self.logger = logging.getLogger(__name__)
        self.get_index_name = lambda collection_name: f'{collection_name}_vector_index'

    async def init_db(self):
        try:
            async with self.client() as session:
                async with session.begin():
                    await session.execute(
                        text("CREATE EXTENSION IF NOT EXISTS vector;")
                    )
        except SQLAlchemyError as e:
            raise VectorDBServiceError(
                "Failed to initialize database",
                detail=str(e)
            ) from e
        
    async def disconnect(self):
        return

    async def collection_exists(self, collection_name: str) -> bool:
        try:
            async with self.client() as session:
                stmt = text("SELECT to_regclass(:collection_name) IS NOT NULL;")
                result = await session.execute(
                    stmt, {'collection_name' : collection_name}
                )
        except SQLAlchemyError as e:
            raise VectorDBServiceError(
                f"Failed to check collection existence for '{collection_name}'",
                detail=str(e)
            ) from e

        return result.scalar()

    async def create_collection(
        self, 
        collection_name: str,
        embedding_size: int,
        do_reset: bool = False
    ) -> bool:

        if not str(embedding_size).isdecimal():
            raise TypeError('"embedding_size" must be an integer.')

        if do_reset:
            await self.delete_collection(collection_name)
        
        if not await self.collection_exists(collection_name):
            try:
                async with self.client() as session:
                    async with session.begin():
                        stmt = text(
                            f'''
                            CREATE TABLE "{collection_name}" (
                            id UUID PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE, 
                            metadata jsonb DEFAULT '{{}}'::jsonb, 
                            vector vector({embedding_size})
                            )
                            '''
                        )

                        await session.execute(stmt)
            except SQLAlchemyError as e:
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

    async def delete_collection(self, collection_name: str) -> bool:
        try:
            async with self.client() as session:
                async with session.begin():
                    stmt = text(f'DROP TABLE IF EXISTS "{collection_name}"')
                    await session.execute(stmt)
        except SQLAlchemyError as e:
            raise VectorDBServiceError(
                f"Failed to delete collection '{collection_name}'",
                detail=str(e)
            ) from e
        
        return True

    async def get_collection_info(self, collection_name: str) -> dict:
        try:
            async with self.client() as session:
                stmt = text("SELECT * FROM pg_tables WHERE tablename = :collection_name")
                info_result = await session.execute(
                stmt, {'collection_name' : collection_name}
            )

            stmt = text(f"SELECT COUNT(*) FROM {collection_name}")
            n_vectors = await session.execute(stmt)

            info = info_result.fetchone()
            if not info:
                return {}

            result = {
                'vectors_count': int(n_vectors.scalar()),
                'info': dict(info._mapping)
            }

            return result

        except SQLAlchemyError as e:
            raise VectorDBServiceError(
                f"Failed to get collection info for '{collection_name}'",
                detail=str(e)
            ) from e

    async def list_collections(self) -> list[str]:
        try:
            async with self.client() as session:
                stmt = text("SELECT tablename FROM pg_tables WHERE tablename LIKE 'collection_%'")
                result = await session.execute(stmt)
                return result.scalars().all()
        except SQLAlchemyError as e:
            raise VectorDBServiceError("Failed to list collections", detail=str(e)) from e

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
        
        data = [
            {'id': uid, 'metadata': meta, 'vector': vec}
            for uid, meta, vec in zip(ids, metadata, vectors)
        ]
        try:
            async with self.client() as session:
                async with session.begin():
                    stmt = text(
                        f'''
                        INSERT INTO "{collection_name}" (id, metadata, vector)
                        VALUES (:id, :metadata, :vector)
                        '''
                    ).bindparams(
                        bindparam('id', type_=PG_UUID),
                        bindparam('metadata', type_=JSONB),
                        bindparam('vector', type_=Vector(len(vectors[0])))
                    )
                    await session.execute(stmt, data)

                    need_index = False
                    count = await session.execute(
                        text(f'SELECT COUNT(*) FROM "{collection_name}"')
                    )
                    if count.scalar() > self.index_building_threshold:
                        need_index = True
        except SQLAlchemyError as e:
            raise VectorDBServiceError(
                f"Failed to insert vectors into '{collection_name}'",
                detail=str(e)
            ) from e

        if need_index and not (await self.vector_index_exists(collection_name)):
            await self.create_vector_index(collection_name=collection_name)
        return True 

    async def search_by_vector(
        self, 
        collection_name: str, 
        vector: list[float], 
        top_k: int
    ) -> list[RetrievedDocument]:

        
        if not await self.collection_exists(collection_name):
            raise VectorDBServiceError(f"Collection '{collection_name}' does not exist")

        try:
            async with self.client() as session:
                stmt = text(
                    f'''
                    SELECT metadata->>'text' AS text, vector {self.sim_metric_info.symbol} :ref_vector AS score
                    FROM {collection_name}
                    ORDER BY score
                    LIMIT :top_k
                    '''
                ).bindparams(
                    bindparam('ref_vector', type_=Vector(len(vector)))
                )

                results = await session.execute(
                    stmt,
                    {'ref_vector': vector, 'top_k': top_k}
                )

                results = results.fetchall()
        except SQLAlchemyError as e:
            raise VectorDBServiceError(
                f"Failed to search in '{collection_name}'",
                detail=str(e)
            ) from e

        return [
            RetrievedDocument(
                text=result.text,
                score=self.sim_metric_info.norm_method(result.score)
            )
            for result in results
        ]

    def _resolve_similarity_metric(self, metric: str) -> SimilarityMetricInfo:
        METRICS_INFO = {
            'dot': {
                'symbol': '<#>', 
                'operation': 'vector_ip_ops', 
                'norm_method': lambda x: -x
            },
            'cosine': {
                'symbol': '<=>', 
                'operation': 'vector_cosine_ops', 
                'norm_method': lambda x: 1-x
            },
            'euclid': {
                'symbol': '<->', 
                'operation': 'vector_l2_ops', 
                'norm_method': lambda x: 1 / (1 + x)
            },
        }

        chosen = METRICS_INFO.get(metric.lower(), None)
        if chosen is None:
            self.logger.warning(
                f"Invalid similarity metric '{metric}'. "
                f"Defaulting to {SimilarityMetric.COSINE}."
            )
            return SimilarityMetricInfo(**METRICS_INFO['cosine'])

        return SimilarityMetricInfo(**chosen)

    async def vector_index_exists(self, collection_name: str) -> bool:
        try:
            async with self.client() as session:
                stmt = text(
                    '''
                    SELECT 1 FROM pg_indexes
                    WHERE tablename = :tablename
                    AND indexname = :indexname
                    '''
                )

                result = await session.execute(
                    stmt,
                    {
                        'tablename': collection_name,
                        'indexname': self.get_index_name(collection_name)
                    }
                )

                return True if result.scalar() is not None else False
        except SQLAlchemyError as e:
            raise VectorDBServiceError(
                f'Failed to search for the index of collection: {collection_name}',
                detail=str(e)
            ) from e

    async def create_vector_index(self, collection_name: str) -> None:
        try:
            async with self.client() as session:
                async with session.begin():
                    index_name = self.get_index_name(collection_name)
                    stmt = text(
                        f'''
                        CREATE INDEX IF NOT EXISTS {index_name}
                        ON {collection_name} USING 
                        {self.index_type} (vector {self.sim_metric_info.operation})
                        '''
                    )

                    await session.execute(stmt)
                    self.logger.info(f"Index '{index_name}' was created successfully.")
        except SQLAlchemyError as e:
            raise VectorDBServiceError(
                f'Failed to create the index for collection: {collection_name}',
                detail=str(e)
            ) from e

    async def reset_vector_index(self, collection_name: str) -> None:
        try:
            async with self.client() as session:
                async with session.begin():
                    index_name = self.get_index_name(collection_name)
                    stmt = text(f'DROP INDEX IF EXISTS {index_name}')
                    await session.execute(stmt)

                    stmt = text(
                        f'''
                        CREATE INDEX {self.get_index_name(collection_name)}
                        ON {collection_name} 
                        USING {self.index_type} (vector {self.sim_metric_info.operation})
                        '''
                    )

                    await session.execute(stmt)
                    self.logger.info(f"Index '{index_name}' was reset successfully.")
        except SQLAlchemyError as e:
            raise VectorDBServiceError(
                f"Failed to reset the index '{index_name}'", detail=str(e)
            ) from e