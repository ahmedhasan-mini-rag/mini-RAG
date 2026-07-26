import logging
from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from models import ChunkModel
from models.enums import ResponseSignal
from models.schemas import EmbedRequest, SearchRequest

from controllers import NLPController

nlp_router = APIRouter(
    prefix='/api/v1/nlp',
    tags=['api_v1', 'nlp']
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

    project = await request.app.state.project_model.get_project(
        project_name=project_name,
        create_if_missing=False
    )

    nlp_controller = NLPController(
        chat_client=request.app.state.chat_client,
        embedding_client=request.app.state.embedding_client,
        vectordb_client=request.app.state.vectordb_client
    )

    chunk_model = await ChunkModel.create_instance(
        db_client=request.app.state.db_client
    )

    chunks_iter = await chunk_model.get_project_chunks(
        chunk_project_id=project.id
    )

    BATCH_SIZE = 50

    num_inserted = await nlp_controller.embed_and_store_chunks(
        project_name=project.project_name,
        chunks_iter=chunks_iter,
        do_reset=embed_request.do_reset,
        batch_size=BATCH_SIZE
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            'response': ResponseSignal.VECTORDB_INSERTION_SUCCESS,
            'inserted_vectors' : num_inserted
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
):
    """Perform semantic search against a project's vector database collection.

    Args:
        request (Request): FastAPI request object containing application context.
        project_name (str): Name of the target project.
        search_request (SearchRequest): Search parameters including query text and number of top results to return.

    Returns:
        JSONResponse: Response containing search response signal and the search results.
    """

    project = await request.app.state.project_model.get_project(
        project_name=project_name,
        create_if_missing=False
    )

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