from .providers import QdrantProvider, PGVectorProvider
from .vectordb_enums import Provider
from utils.config import BASE_DIR, Settings
from exceptions import InvalidConfigError

class VectorDBProviderFactory:
    def __init__(self, pg_client, config: Settings):
        self.pg_client = pg_client
        self.config = config
        self.dbs_repo_path = BASE_DIR / "assets" / "databases"
    
    def create(self, provider: str):
        match provider.lower():

            case Provider.QDRANT:
                dp_path = self._get_db_path(Provider.QDRANT)

                client = QdrantProvider(
                    dp_path=dp_path,
                    similarity_metric=self.config.VECTORDB_SIMILARITY_METRIC,
                )

            case Provider.PGVECTOR:
                client = PGVectorProvider(
                    pg_client=self.pg_client,
                    similarity_metric=self.config.VECTORDB_SIMILARITY_METRIC,
                    index_type=self.config.VECTORDB_INDEX_TYPE,
                    index_building_threshold=self.config.VECTORDB_INDEX_BUILDING_THRESHOLD
                )
            
            case _:
                raise InvalidConfigError(f"Unknown VectorDB provider: '{provider}'")
        
        return client
    
    def _get_db_path(self, dp_name: str) -> str:
        path = self.dbs_repo_path / dp_name

        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        
        return str(path)