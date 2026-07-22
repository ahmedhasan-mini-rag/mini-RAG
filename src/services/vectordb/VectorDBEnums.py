from enum import Enum

class Provider(Enum, str):
    QDRANT = "qdrant"

class SimilarityMetric(Enum, str):
    COSINE = "cosine"
    DOT = "dot"
    # EUCLID = "euclid"