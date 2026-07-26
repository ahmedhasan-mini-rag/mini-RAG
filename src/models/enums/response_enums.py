from enum import Enum

class ResponseSignal(str, Enum):
    FILE_VALIDATION_SUCCESS = 'File validated successfully'
    FILE_TYPE_NOT_SUPPORTED = 'File type not supported'
    FILE_SIZE_EXCEEDED = 'File size exceeded'
    FILE_UPLOAD_SUCCESS = 'File(s) upload succeeded'
    FILE_UPLOAD_FAIL = 'File(s) upload failed'
    FILE_NOT_FOUND = 'The requested file(s) not found. Ensure it is uploaded first.'

    PROJECT_NOT_FOUND = 'Project not found, no project with the given id.'

    PROCESSING_SUCCESS = 'File(s) processing succeeded'
    PROCESSING_FAIL = 'File(s) processing failed'

    VECTORDB_INSERTION_SUCCESS = 'Data has been inserted successfully.'
    VECTORDB_INSERTION_FAIL = 'Insertion process failed.'

    VECTORDB_SEARCH_SUCCESS = 'Search process succeeded.'
    VECTORDB_SEARCH_FAIL = 'Search process failed.'

    VECTORDB_COLLECTION_DELETION_SUCCESS = 'Collection deleted successfully.'
    VECTORDB_COLLECTION_DELETION_FAIL = 'Collection deletion failed.'