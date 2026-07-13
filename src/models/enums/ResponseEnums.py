from enum import Enum

class ResponseSignal(Enum):
    FILE_VALIDATION_SUCCESS = 'File validated successfully'
    FILE_TYPE_NOT_SUPPORTED = 'File type not supported'
    FILE_SIZE_EXCEEDED = 'File size exceeded'
    FILE_UPLOAD_SUCCESS = 'File(s) upload succeeded'
    FILE_UPLOAD_FAIL = 'File(s) upload failed'
    PROCESSING_SUCCESS = 'File(s) processing succeeded'
    PROCESSING_FAIL = 'File(s) processing failed'
    FILE_NOT_FOUND = 'The requested file(s) not found. Ensure it is uploaded first.'
    PROJECT_NOT_FOUND = 'Project not found, no project with the given id.'