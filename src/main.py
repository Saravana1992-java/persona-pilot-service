import asyncio
import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from typing import Annotated

from elasticsearch import NotFoundError, UnsupportedProductError, ConflictError, BadRequestError, \
    AuthenticationException, AuthorizationException
from fastapi import FastAPI, Request, HTTPException, Depends, APIRouter, Path, Query, Body
from fastapi.exceptions import RequestValidationError, ResponseValidationError, ValidationException
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError
from starlette.responses import JSONResponse, Response

from src import app_context
from src.config import ic_logging
from src.constants.app_context_keys import AppContextKeys
from src.constants.job_statuses import JobStatus
from src.exceptions.AppException import InsightException
from src.models.api_response import ApiResponse
from src.models.insights_search_request import InsightsSearchRequest
from src.models.talk_insights_request import TalkInsightsRequest
from src.models.vector_search_request import VectorSearchRequest
from src.services.data_service import DataService
from src.utils import jwt_utils


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the beans
    await app_context.init()
    yield
    # Clean up the connections and release the resources
    await app_context.cleanup()


adfs_auth = HTTPBearer(scheme_name="ADFS_Auth",
                       bearerFormat="JWT",
                       description="Get ADFS access_token from insights catalogue ui and use it here.")

host = "localhost"
scheme = "http"
port = "8001"
base_path = "/ai-resume-toolkit"

# Context variable to store token per request
sub: ContextVar[str] = ContextVar("sub", default="")
uid: ContextVar[str] = ContextVar("uid", default="")
user_name: ContextVar[str] = ContextVar("user_name", default="")

app = FastAPI(title="AI Toolkit for Resume Crafting and Knowledge Validation",
              description="",
              version="1.0.0",
              contact={
                  "name": "Saravana manikandan S",
                  "url": "www.linkedin.com/in/saravanamanikandan-s-23935670",
                  "email": "sarvanamani1992@gmail.com",
              },
              lifespan=lifespan,
              root_path=base_path)


@app.middleware("http")
async def security_filter(request: Request, call_next):
    global host, scheme, port
    start_time = time.time()
    scheme = request.url.scheme
    host = request.url.hostname
    path = request.url.path
    port = request.url.port
    ic_logging.get_logger(__name__).info(f"scheme::{scheme}")
    ic_logging.get_logger(__name__).info(f"hostname::{host}")
    ic_logging.get_logger(__name__).info(f"port::{port}")
    ic_logging.get_logger(__name__).info(f"path::{path}")
    whitelist_paths = ["/ai-resume-toolkit/docs", "/ai-resume-toolkit/openapi.json", "/ai-resume-toolkit/favicon.ico"]
    # Whitelist Swagger paths
    if path in whitelist_paths:
        response = await call_next(request)
    else:
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(status_code=403, detail="No Authorization found in header.")
        try:
            # Extract bearer and token value
            scheme, token = authorization.strip().split(" ")
            if scheme.lower() != "bearer":
                raise HTTPException(status_code=403, detail="Invalid Authorization scheme.")
            app_properties = await app_context.get(AppContextKeys.app_properties)
            verified_claims = jwt_utils.validate_jwt_token(token, app_properties.audience)
            sub.set(verified_claims['sub'])
            uid.set(verified_claims['uid'])
            user_name.set(verified_claims['fordDisplayName'])
        except InsightException as e:
            raise HTTPException(status_code=401, detail=e.message)
        response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time}s"
    return response


def custom_openapi():
    global host, port
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        contact=app.contact,
        routes=app.routes,
    )
    openapi_schema["openapi"] = "3.0.0"  # Set OpenAPI version to 3.0.0
    openapi_schema["components"]["securitySchemes"] = {
        adfs_auth.scheme_name: {
            "type": "http",
            "scheme": adfs_auth.model.scheme,
            "bearerFormat": adfs_auth.model.bearerFormat
        }
    }
    openapi_schema["security"] = [{adfs_auth.scheme_name: []}]
    # Add current host name to servers
    ic_logging.get_logger(__name__).info("MTD:custom_openapi::hostname::" + host)
    protocol = "http" if host == "localhost" else "https"
    port = ":8001" if host == "localhost" else ""
    openapi_schema["servers"] = [{"url": f"{protocol}://{host}{port}{base_path}"}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

key_query: str = Query(
    title="Resume ID to get downloadable resume",
    description="Resume ID to get downloadable resume. Example: 1800000112",
    default=None,
    regex=r"^\d{1,20}$",
    json_schema_extra={"x-42c-sample": "1800000112"}
)

index_path: str = Path(title="Index name to perform operations on Elastic Search",
                       description="Index name to perform operations on Elastic Search. Example: resumes_dev",
                       default=...,
                       min_length=3,
                       max_length=30,
                       regex="^[a-z0-9_]+$",
                       json_schema_extra={"x-42c-sample": "resumes_dev"})

responses = {
    200: {"description": "Success",
          "model": ApiResponse},
    204: {"description": "No Content"},
    400: {"description": "Bad Request",
          "model": ApiResponse},
    401: {"description": "Unauthorized",
          "model": ApiResponse},
    403: {"description": "Forbidden",
          "model": ApiResponse},
    404: {"description": "Not Found",
          "model": ApiResponse},
    406: {"description": "Not Acceptable",
          "model": ApiResponse},
    422: {"description": "Unable to process the request",
          "model": ApiResponse},
    429: {"description": "Too Many Requests",
          "model": ApiResponse},
    500: {"description": "Internal Server Error",
          "model": ApiResponse},
    "default": {"description": "Sorry, something went wrong",
                "model": ApiResponse}
}

router = APIRouter(
    prefix="/api/v1",
    tags=["v1"],
    responses=responses,
)


@router.get(path='/resume',
            summary="Fetch downloadable resume based on a given resume id.",
            description="Fetch downloadable resume based on a given resume id.",
            response_description="A response object containing the status code, message, and data related to the "
                                 "fetched resume.",
            response_model=ApiResponse,
            operation_id="get_api_v1_resume",
            responses=responses)
async def get_api_resume_v1(credentials: Annotated[HTTPAuthorizationCredentials, Depends(adfs_auth)],
                            key: str = key_query):
    data_service: DataService = await app_context.get(AppContextKeys.data_service)
    try:
        key = int(key) if key is not None else None
    except ValueError as e:
        raise InsightException(status_code=404, message="Value error: " + str(e))
    insights = await data_service.fetch_insights(key)
    status = 200
    return JSONResponse(status_code=status,
                        media_type="application/json",
                        content=ApiResponse(status_code=status, message="Success",
                                            data=insights.to_dict()).model_dump())


@router.put(path='/index/{index}/search/v1',
            summary="Retrieves insights & summary for a specific index with enhanced search capabilities.",
            description="This endpoint performs a semantic search within a specified index of the Insights Catalog. It "
                        "uses advanced algorithms to understand the intent of the search query, providing more  "
                        "relevant results based on the context of the query, rather than relying solely on keyword "
                        "matching.",
            response_description="A response object containing the status code, message, and data related to the "
                                 "fetched insights. The data includes a list of insights that match the search "
                                 "criteria, along with pagination information.",
            response_model=ApiResponse,
            operation_id="get_api_insights_index_search_v1",
            responses=responses)
async def get_api_insights_index__search_v1(credentials: Annotated[HTTPAuthorizationCredentials, Depends(adfs_auth)],
                                            vector_search_request:
                                            VectorSearchRequest = Body(default=...,
                                                                       title="Query criteria for semantic search",
                                                                       description="Query criteria for semantic "
                                                                                   "search"),
                                            index: str = index_path):
    cdsid = get_cdsid()
    logged_in_user_name = get_user_name()

    # Semantic search based on query
    request = InsightsSearchRequest.to_instance(index=index, cdsid=cdsid, logged_in_user_name=logged_in_user_name,
                                                vector_search_request=vector_search_request)
    data_service = await app_context.get(AppContextKeys.data_service)
    summary_search_response = await data_service.search_insights_v2(request)
    if summary_search_response is None:
        summary_search_response = {}
    status = 200
    return JSONResponse(status_code=status, media_type="application/json",
                        content=ApiResponse(status_code=status, message="Success",
                                            data=summary_search_response).model_dump())


@router.put(path='/index/{index}',
            summary="Updates or inserts a single record into the specified index in Elastic Search. If a key is "
                    "provided, the specific record associated with that key is updated. If no key is provided, "
                    "bulk insert will be performed from PGSQL by ENV.",
            description="Updates or inserts a single record into the specified index in Elastic Search. If a key is "
                        "provided, the specific record associated with that key is updated. bulk insert will be "
                        "performed from PGSQL by ENV.",
            response_description="A response object containing the status code, message, and data related to the "
                                 "operation. For successful operations, the status code will be 202 (Accepted), "
                                 "and the data will include information about the job initiated to perform the sync "
                                 "operation.",
            response_model=ApiResponse,
            operation_id="put_api_insights_index_key_v1",
            responses=responses)
async def put_api_insights_index_key_v1(credentials: Annotated[HTTPAuthorizationCredentials, Depends(adfs_auth)],
                                        index: str = index_path,
                                        key: str = key_query,
                                        sync_option: str = Query(
                                            title="The sync option to sync PGSQL & Elastic search",
                                            description="The sync option to sync PGSQL & Elastic search. "
                                                        "Example: [insert, upsert, bulk_insert]",
                                            default=...,
                                            min_length=3,
                                            max_length=20,
                                            regex="^[a-z_]+$",
                                            json_schema_extra={"x-42c-sample": "insert"})):
    job_id = int(time.time() * 1000)
    async_job_handler = await app_context.get(AppContextKeys.async_job_handler)
    await async_job_handler.register(job_id=job_id, name="sync", status=JobStatus.IN_PROGRESS.name)
    try:
        try:
            key = int(key) if key is not None else None
        except ValueError as e:
            raise InsightException(status_code=404, message="Value error: " + str(e))
        data_service = await app_context.get(AppContextKeys.data_service)
        loop = asyncio.get_running_loop()
        loop.create_task(data_service.process_sync(job_id, key, index, sync_option))
        job_history = await async_job_handler.get(job_id)
        status = 202
        return JSONResponse(status_code=status,
                            media_type="application/json",
                            content=ApiResponse(status_code=status, message="Accepted", data=job_history).model_dump())
    except InsightException as e:
        await async_job_handler.update(job_id=job_id, status=JobStatus.FAILED.name, data={"error": str(e)})
        status = 500
        return JSONResponse(status_code=status,
                            media_type="application/json",
                            content=ApiResponse(status_code=status, message=str(e)).model_dump())


@router.put(path='/index/{index}/summary/reactions/{key}/v1',
            summary="Updates or inserts a user reaction such as like or dislike for AI Summary.",
            description="Updates or inserts a user reaction such as like or dislike for AI Summary.",
            response_description="A response object containing the status code, message, and data related to the "
                                 "operation. For successful operations, the status code will be 200 (Ok), "
                                 "and the data will include information about the summary cache ",
            response_model=ApiResponse,
            operation_id="put_api_insights_index_summary_reactions_v1",
            responses=responses)
async def put_api_insights_index_summary_reactions_v1(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(adfs_auth)],
        index: str = index_path,
        key: str = Path(title="AI summary cache key",
                        description="AI summary cache key. Example: 1800000112",
                        default=...,
                        regex=r"^\d{1,20}$",
                        json_schema_extra={"x-42c-sample": "1800000112"}),
        reaction: str = Query(
            title="User Reaction to the Generated AI Summary. Ex: [like or dislike]",
            description="User Reaction to the Generated AI Summary.",
            default=...,
            min_length=3,
            max_length=10,
            regex="^[a-z]+$",
            json_schema_extra={"x-42c-sample": "like"})):
    cdsid = get_cdsid()
    logged_in_user_name = get_user_name()
    data_service = await app_context.get(AppContextKeys.data_service)
    response = await data_service.update_user_reaction(key=key, index=index, user_reaction=reaction, cdsid=cdsid,
                                                       logged_in_user_name=logged_in_user_name)
    status = 200
    return JSONResponse(status_code=status,
                        media_type="application/json",
                        content=ApiResponse(status_code=status, message="Success", data=response).model_dump())


@router.delete(path='/index/{index}/v1',
               summary="Deletes a single insight record by its key within a specified index, or deletes the entire "
                       "index if no key is provided.",
               description="This endpoint allows for the deletion of insights data within the Elastic Search. "
                           "If a key is specified, only the record associated with that key is deleted. If no key "
                           "is provided, the entire index specified will be deleted, removing all records within it.",
               response_description="A response object containing the status code and message related to the "
                                    "operation. For successful deletion of a record or index, the status code will be "
                                    "204 (No Content).",
               response_model=ApiResponse,
               operation_id="delete_api_insights_index_key_v1",
               responses=responses)
async def delete_api_insights__index___key__v1(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(adfs_auth)],
        index: str = index_path,
        key: str = key_query):
    try:
        key = int(key) if key is not None else None
    except ValueError as e:
        raise InsightException(status_code=404, message="Value error: " + str(e))
    data_service = await app_context.get(AppContextKeys.data_service)
    await data_service.delete_insight(index, key)
    status = 204
    return Response(status_code=status)


@router.get(path='/embeddings/v1',
            summary="Fetches the embeddings for a given sentence & task type. This endpoint is designed to return "
                    "embeddings that represent the semantic meaning of the input sentence or are tailored for a "
                    "specific task type.",
            description="Fetches the embeddings for a given sentence & task type. This endpoint is designed to return "
                        "embeddings that represent the semantic meaning of the input sentence or are tailored for a "
                        "specific task type.",
            response_description="A response object containing the status code, message, and data related to the "
                                 "fetched embeddings. The data includes the embeddings array along with any "
                                 "additional relevant information.",
            response_model=ApiResponse,
            operation_id="get_api_insights_embeddings_v1",
            responses=responses)
async def get_api_insights_embeddings_v1(credentials: Annotated[HTTPAuthorizationCredentials, Depends(adfs_auth)],
                                         sentence: str =
                                         Query(
                                             title="The sentence for which embeddings are to be fetched.",
                                             description="The sentence for which embeddings are to be fetched. "
                                                         "Example: Blue cruise",
                                             default=...,
                                             min_length=3,
                                             max_length=10000,
                                             regex=r"([a-zA-Z0-9-._!\"`'#%&,:;<>=@{}~\$\(\)\*\+\/\\\?\[\]\^\|]+|[\.\^\$\*\+\?\{\}\[\]\\\|\(\)])",
                                             json_schema_extra={"x-42c-sample": "Blue Cruise"}),
                                         task_type: str = Query(
                                             title="The Task Type to create a embeddings",
                                             description="The Task Type to create a embeddings. "
                                                         "Example: [RETRIEVAL_QUERY, RETRIEVAL_DOCUMENT, "
                                                         "SEMANTIC_SIMILARITY, FACT_VERIFICATION]",
                                             default=...,
                                             min_length=10,
                                             max_length=50,
                                             regex="^[A-Z_]+$",
                                             json_schema_extra={"x-42c-sample": "SEMANTIC_SIMILARITY"})):
    data_service = await app_context.get(AppContextKeys.data_service)
    embeddings = await data_service.get_embeddings(sentence, task_type)
    status = 200
    return JSONResponse(status_code=status,
                        media_type="application/json",
                        content=ApiResponse(status_code=status, message="Success", data=embeddings).model_dump())


@router.get(path='/jobs/{job_id}/v1',
            summary="Retrieves the status and details of a specific job by its job ID. This endpoint is useful for "
                    "tracking the progress or result of asynchronous operations initiated by other API endpoints.",
            description="Retrieves the status and details of a specific job by its job ID. This endpoint is useful for "
                        "tracking the progress or result of asynchronous operations initiated by other API endpoints.",
            response_description="A response object containing the status code, message, and data related to the "
                                 "requested job. The data includes job details such as job ID, name, status, and any "
                                 "relevant data associated with the job.",
            response_model=ApiResponse,
            operation_id="get_api_insights_job_id_v1",
            responses=responses)
async def get_api_insights__job_id__v1(credentials: Annotated[HTTPAuthorizationCredentials, Depends(adfs_auth)],
                                       job_id: str = Path(title="The job id to fetch the job details",
                                                          description="The job id to fetch the job details. "
                                                                      "Example: 1800000112",
                                                          default=...,
                                                          regex=r"^\d{1,20}$",
                                                          json_schema_extra={"x-42c-sample": "1800000112"})):
    async_job_handler = await app_context.get(AppContextKeys.async_job_handler)
    if job_id is None:
        raise InsightException(status_code=400, message="Job ID is required.")
    try:
        job_id = int(job_id) if job_id is not None else None
    except ValueError as e:
        raise InsightException(status_code=404, message="Value error: " + str(e))
    insights_dict = await async_job_handler.get(job_id)
    status = 200
    return JSONResponse(status_code=status,
                        media_type="application/json",
                        content=ApiResponse(status_code=status, message="Success", data=insights_dict).model_dump())


@router.delete(path='/jobs/v1',
               summary="Deletes a specific job by its job ID. This will remove all the jobs from the system and "
                       "any associated data if job ID not provided",
               description="Deletes a specific job by its job ID. This will remove all the jobs from the system and "
                           "any associated data if job ID not provided",
               response_description="No Content",
               response_model=ApiResponse,
               operation_id="delete_api_insights_jobs_v1",
               responses=responses)
async def delete_api_insights_jobs_v1(credentials: Annotated[HTTPAuthorizationCredentials, Depends(adfs_auth)],
                                      job_id: str = Query(title="The job id to fetch the job details",
                                                          description="The job id to fetch the job details. "
                                                                      "Example: 123456",
                                                          default=None,
                                                          regex=r"^\d{1,20}$",
                                                          json_schema_extra={"x-42c-sample": "1800000112"})):
    async_job_handler = await app_context.get(AppContextKeys.async_job_handler)
    try:
        job_id = int(job_id) if job_id is not None else None
    except ValueError as e:
        raise InsightException(status_code=404, message="Value error: " + str(e))
    await async_job_handler.remove(job_id)
    status = 204
    return Response(status_code=status)


@router.post(path='/chat/v1',
             summary="Analyze document and answer questions.",
             description="Analyze a document and answer any questions asked by a user through a chatbox.",
             response_description="Response object containing the status code, message, and data related to the insight",
             response_model=ApiResponse,
             operation_id="post_insight_chat_v1",
             responses=responses)
async def post_insight_chat_v1(credentials: Annotated[HTTPAuthorizationCredentials, Depends(adfs_auth)],
                               talk_insight_request: TalkInsightsRequest = Body(...)):
    data_service = await app_context.get(AppContextKeys.data_service)
    chat_response = await data_service.chat_process(talk_insight_request.gcs_path, talk_insight_request.user_question)
    status = 200
    return JSONResponse(status_code=status,
                        media_type="application/json",
                        content=ApiResponse(status_code=status, message="Success",
                                            data={"message": chat_response}).model_dump())


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [{"field": err["loc"][-1], "message": err["msg"]} for err in exc.errors()]
    return JSONResponse(
        status_code=400,
        media_type="application/json",
        content={"status_code": 400, "message": "Request Validation Error", "data": {"errors": errors}}
    )


@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(request: Request, exc: ResponseValidationError):
    errors = [{"field": err["loc"][-1], "message": err["msg"]} for err in exc.errors()]
    return JSONResponse(
        status_code=500,
        media_type="application/json",
        content={"status_code": 500, "message": "Response Validation Error", "data": {"errors": errors}}
    )


@app.exception_handler(ValidationException)
async def request_validation_exception_handler(request: Request, exc: ValidationException):
    errors = [{"field": err["loc"][-1], "message": err["msg"]} for err in exc.errors()]
    return JSONResponse(
        status_code=400,
        media_type="application/json",
        content={"status_code": 400, "message": "Validation Exception", "data": {"errors": errors}}
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    errors = [{"field": err["loc"][-1], "message": err["msg"]} for err in exc.errors()]
    return JSONResponse(
        status_code=400,
        media_type="application/json",
        content={"status_code": 400, "message": "Validation Error", "data": {"errors": errors}}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, e: Exception):
    ic_logging.get_logger(__name__).exception(e)
    if isinstance(e, ValidationError):
        status = 400
        return JSONResponse(
            status_code=status,
            media_type="application/json",
            content=ApiResponse(status_code=status, message=str(e)).model_dump())
    if isinstance(e, RequestValidationError):
        status = 400
        return JSONResponse(
            status_code=status,
            media_type="application/json",
            content=ApiResponse(status_code=status, message=str(e)).model_dump())
    elif isinstance(e, ResponseValidationError):
        status = 500
        return JSONResponse(
            status_code=status,
            media_type="application/json",
            content=ApiResponse(status_code=status, message=str(e)).model_dump())
    elif isinstance(e, HTTPException):
        status = e.status_code if e.status_code else 400
        message = e.detail if e.detail else "HTTP Validation Error"
        return JSONResponse(status_code=status,
                            media_type="application/json",
                            content=ApiResponse(status_code=status, message=message).model_dump())
    elif isinstance(e, ValueError):
        status = 404
        message = "Value Error: " + str(e) if str(e) else "Value Error"
        return JSONResponse(
            status_code=status,
            media_type="application/json",
            content=ApiResponse(status_code=status, message=message).model_dump()
        )
    elif isinstance(e, KeyError):
        status = 404
        message = "Key Error:  " + str(e) if str(e) else "Key Error"
        return JSONResponse(
            status_code=status,
            media_type="application/json",
            content=ApiResponse(status_code=status, message=message).model_dump()
        )
    elif isinstance(e, InsightException):
        status = e.status_code
        return JSONResponse(status_code=status,
                            media_type="application/json",
                            content=ApiResponse(status_code=status, message=e.message).model_dump())
    elif isinstance(e, UnsupportedProductError):
        status = e.status_code
        return JSONResponse(status_code=status,
                            media_type="application/json",
                            content=ApiResponse(status_code=status, message=e.error).model_dump())
    elif isinstance(e, NotFoundError):
        status = e.status_code
        return JSONResponse(status_code=status,
                            media_type="application/json",
                            content=ApiResponse(status_code=status, message=e.error).model_dump())
    elif isinstance(e, ConflictError):
        status = e.status_code
        return JSONResponse(status_code=status,
                            media_type="application/json",
                            content=ApiResponse(status_code=status, message=e.error).model_dump())
    elif isinstance(e, BadRequestError):
        status = e.status_code
        return JSONResponse(status_code=status,
                            media_type="application/json",
                            content=ApiResponse(status_code=status, message=e.error).model_dump())
    elif isinstance(e, AuthenticationException):
        status = e.status_code
        return JSONResponse(status_code=status,
                            media_type="application/json",
                            content=ApiResponse(status_code=status, message=e.error).model_dump())
    elif isinstance(e, AuthorizationException):
        status = e.status_code
        return JSONResponse(status_code=status,
                            media_type="application/json",
                            content=ApiResponse(status_code=status, message=e.error).model_dump())
    else:
        status = 500
        message = str(e) if str(e) else "Internal Server Error"
        return JSONResponse(status_code=status,
                            media_type="application/json",
                            content=ApiResponse(status_code=status, message=message).model_dump())


def get_cdsid() -> str:
    cdsid = sub.get()
    if cdsid is None:
        raise HTTPException(status_code=403, detail="cdsid is not available in request context.")
    return cdsid


def get_user_name() -> str:
    logged_in_user_name = user_name.get()
    if logged_in_user_name is None:
        raise HTTPException(status_code=403, detail="fordDisplayName is not available in request context.")
    return logged_in_user_name


app.include_router(router)
