"""
Custom exception hierarchy for mini-RAG.

All application-specific exceptions inherit from MiniRAGError,
allowing the global FastAPI exception handler in main.py to
map each family to the correct HTTP status code.

Hierarchy
---------
MiniRAGError
├── NotFoundError
│   ├── ProjectNotFoundError
│   ├── AssetNotFoundError
│   └── FileNotFoundOnDiskError
├── ValidationError
│   ├── FileValidationError
│   └── InvalidConfigError
├── DatabaseError
│   ├── DatabaseWriteError
│   └── DatabaseReadError
├── ServiceError
│   ├── LLMServiceError
│   └── VectorDBServiceError
└── FileIOError
"""


class MiniRAGError(Exception):
    """Root exception for all mini-RAG application errors."""

    def __init__(self, message: str = "An unexpected error occurred", detail: str | None = None):
        self.message = message
        self.detail = detail
        super().__init__(message)

# Source not found 

class NotFoundError(MiniRAGError):
    """Base class for all "resource not found" errors."""


class ProjectNotFoundError(NotFoundError):
    """Raised when a requested project does not exist."""


class AssetNotFoundError(NotFoundError):
    """Raised when a requested asset does not exist."""


class FileNotFoundOnDiskError(NotFoundError):
    """Raised when an asset's backing file is missing from the filesystem."""


# Validation and bad input 

class ValidationError(MiniRAGError):
    """Base class for input validation failures."""


class FileValidationError(ValidationError):
    """Raised when an uploaded file fails type or size checks."""


class InvalidConfigError(ValidationError):
    """Raised for invalid configuration (unknown provider, bad metric, etc.)."""


# Database errors 

class DatabaseError(MiniRAGError):
    """Base class for all MongoDB operation failures."""


class DatabaseWriteError(DatabaseError):
    """Raised when a database insert/update/delete fails."""


class DatabaseReadError(DatabaseError):
    """Raised when a database query fails."""


# External service errors 

class ServiceError(MiniRAGError):
    """Base class for external service (LLM, VectorDB) failures."""


class LLMServiceError(ServiceError):
    """Raised when an LLM provider call fails."""


class VectorDBServiceError(ServiceError):
    """Raised when a vector database operation fails."""


# File I O errors 

class FileIOError(MiniRAGError):
    """Raised when a filesystem read/write operation fails."""
