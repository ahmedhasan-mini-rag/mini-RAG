import logging
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from models import ChunkModel
from models.enums import ResponseSignal
from models.schemas import EmbedRequest, SearchRequest
from controllers import NLPController
from worker.tasks.embed_project_chunks import process
from worker.task_utils.idempotency_manager import IdempotencyManager

nlp_router = APIRouter(
    prefix='/api/nlp',
    tags=['nlp']
)

logger = logging.getLogger(__name__)

@nlp_router.post('/embed/{project_name}')
async def embed_project_chunks(
    request: Request, 
    project_name: str,
    embed_request: EmbedRequest,
) -> JSONResponse:
    """Generate vector embeddings for project text chunks and store them in the vector database.

    Args:
        request (Request): FastAPI request object containing application context.
        project_name (str): Name of the target project.
        embed_request (EmbedRequest): Configuration for embedding generation (e.g., reset flag).

    Returns:
        JSONResponse: Response containing vector DB insertion signal and count of inserted vectors.
    """
    idempotency_manager = IdempotencyManager(db_client=request.app.state.db_client)

    task_args = {
        'project_name': project_name,
        'do_reset': embed_request.do_reset
    }

    task = process.delay(
        project_name=project_name,
        do_reset=embed_request.do_reset
    )

    _ = await idempotency_manager.create_task_record(
        task_args=task_args,
        task_name=process.name, # type: ignore
        celery_id=task.id
    )

    return JSONResponse(
        content={
            'response' : ResponseSignal.TASK_IN_PROGRESS,
            'task_id' : task.id
        }
    )

@nlp_router.delete('/delete/{project_name}')
async def delete_project_collection(request: Request, project_name: str) -> JSONResponse:
    """Clear all vector embeddings for a project from the vector database.

    Args:
        request (Request): FastAPI request object containing application context.
        project_name (str): Name of the target project.

    Returns:
        JSONResponse: Response containing vector DB deletion signal and status.
    """
    
    collection_name = NLPController.create_collection_name(project_name=project_name)
    await request.app.state.vectordb_client.delete_collection(collection_name=collection_name)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'response': ResponseSignal.VECTORDB_COLLECTION_DELETION_SUCCESS
        }
    )

@nlp_router.get('/info/{project_name}')
async def get_project_collection_info(request: Request, project_name: str) -> JSONResponse:
    """Retrieve metadata and status details for a project's vector database collection.

    Args:
        request (Request): FastAPI request object containing application context.
        project_name (str): Name of the target project.

    Returns:
        JSONResponse: Response containing vector database collection information.
    """

    collection_name = NLPController.create_collection_name(project_name=project_name)
    info = await request.app.state.vectordb_client.get_collection_info(
        collection_name=collection_name
    )

    return JSONResponse(content=info)

@nlp_router.post('/search/{project_name}')
async def search_collection(
    request: Request, 
    project_name: str,
    search_request: SearchRequest,
) -> JSONResponse:
    """Perform semantic search against a project's vector database collection.

    Args:
        request (Request): FastAPI request object containing application context.
        project_name (str): Name of the target project.
        search_request (SearchRequest): Search parameters including query text and number of top results to return.

    Returns:
        JSONResponse: Response containing search response signal and the search results.
    """

    nlp_controller = NLPController(
        chat_client=request.app.state.chat_client,
        embedding_client=request.app.state.embedding_client,
        vectordb_client=request.app.state.vectordb_client
    )

    search_results = await nlp_controller.search_vectordb_collection(
        project_name=project_name,
        text=search_request.text,
        top_k=search_request.top_k
    )

    # convert to dicts
    response_result = [
        search_result.__dict__ 
        for search_result in search_results
    ]

    return JSONResponse(
        content={
            'response': ResponseSignal.VECTORDB_SEARCH_SUCCESS,
            'search_results': response_result
        }
    )

@nlp_router.post('/answer/{project_name}')
async def answer_query(
    request: Request, 
    project_name: str,
    search_request: SearchRequest,
) -> JSONResponse:

    nlp_controller = NLPController(
        chat_client=request.app.state.chat_client,
        embedding_client=request.app.state.embedding_client,
        vectordb_client=request.app.state.vectordb_client
    )

    answer = await nlp_controller.generate_answer(
        project_name=project_name,
        query=search_request.text,
        n_retrieved_docs=search_request.top_k,
        response_language=search_request.response_language
    )

    return JSONResponse(
        content={
            'response': ResponseSignal.RAG_ANSWER_SUCCESS,
            'answer': answer
        }
    )

