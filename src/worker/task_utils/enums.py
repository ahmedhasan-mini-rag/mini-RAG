from enum import Enum

class TaskService(str, Enum):
    DB_CLIENT = 'db_client'
    _DB_ENGINE = 'db_engine' # ships with DB_CLIENT for ease of connection dispose
    CHAT_CLIENT = 'chat_client'
    EMBEDDING_CLIENT = 'embedding_client'
    VECTORDB_CLIENT = 'vectordb_client'

class TaskState(str, Enum):
    PENDING = 'pending'
    STARTED = 'started'
    SUCCESS = 'success'
    FAILURE = 'failure'