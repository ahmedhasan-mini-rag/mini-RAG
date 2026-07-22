from .providers import QdrantProvider
from .VectorDBEnums import Provider
from utils.config import BASE_DIR

class VectorDBProviderFactory:
    def __init__(self, similarity_metric: str):
        self.similarity_metric = similarity_metric
        self.dbs_repo_path = BASE_DIR / "assets" / "databases"
    
    def create(self, provider: str):
        match provide.lower():
            case Provider.QDRANT:
                dp_path = self._get_db_path(Provider.QDRANT)

                client = QdrantProvider(
                    dp_path=dp_path,
                    similarity_metric=self.similarity_metric
                )
            
            case _:
                client = None
            
        return client
    
    def _get_db_path(dp_name: str) -> str:
        path = self.dbs_repo_path / dp_name

        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        
        return str(path)