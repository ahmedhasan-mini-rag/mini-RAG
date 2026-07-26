from enum import Enum

class Provider(str, Enum):
    QDRANT = "qdrant"

class SimilarityMetric(str, Enum):
    COSINE = "cosine"
    DOT = "dot"
    EUCLID = "euclid"