from .providers import QdrantProvider
from .vectordb_enums import Provider
from utils.config import BASE_DIR
from exceptions import InvalidConfigError

class VectorDBProviderFactory:
    def __init__(self, similarity_metric: str):
        self.similarity_metric = similarity_metric
        self.dbs_repo_path = BASE_DIR / "assets" / "databases"
    
    def create(self, provider: str):
        match provider.lower():
            case Provider.QDRANT:
                dp_path = self._get_db_path(Provider.QDRANT)

                client = QdrantProvider(
                    dp_path=dp_path,
                    similarity_metric=self.similarity_metric
                )
            
            case _:
                raise InvalidConfigError(f"Unknown VectorDB provider: '{provider}'")
        
        return client
    
    def _get_db_path(self, dp_name: str) -> str:
        path = self.dbs_repo_path / dp_name

        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        
        return str(path)