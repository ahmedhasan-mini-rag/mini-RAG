from enum import Enum

class Provider(str, Enum):
    OPENAI = "openai"
    COHERE = "cohere"
    GOOGLE = "google"

# used for cohere only currently
class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class CohereEmbeddingType(str, Enum):
    SEARCH_DOCUMENT = "search_document"
    SEARCH_QUERY = "search_query"

class GoogleEmbeddingType(str, Enum):
    DOCUMENT = "document"
    QUERY = "query"
