from enum import Enum

class Provider(str, Enum):
    QDRANT = "qdrant"
    PGVECTOR = 'pgvector'

class SimilarityMetric(str, Enum):
    COSINE = "cosine"
    DOT = "dot"
    EUCLID = "euclid"

class IndexAlgorithm(str, Enum):
    HNSW = "hnsw"
    IVFFLAT = "ivfflat"