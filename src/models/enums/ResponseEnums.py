from enum import Enum

class ResponseSignal(Enum):
    FILE_VALIDATION_SUCCESS = 'File validated successfully'
    FILE_TYPE_NOT_SUPPORTED = 'File type not supported'
    FILE_SIZE_EXCEEDED = 'File size exceeded'
    FILE_UPLOAD_SUCCESS = 'File upload succeeded'
    FILE_UPLOAD_FAIL = 'File upload failed'
    PROCESSING_SUCCESS = 'File processing succeeded'
    PROCESSING_FAIL = 'File processing failed'
    FILE_NOT_FOUND = 'The requested file not found. Ensure it is uploaded first.'