import os

from elasticsearch import AsyncElasticsearch

from src.config import properties, ic_logging
from src.constants.app_context_keys import AppContextKeys
from src.datasource.async_sql_datasource import AsyncCloudSQLDataSource
from src.handlers.async_job_handler import AsyncJobHandler
from src.services.ai.embedding_service import VertexTextEmbeddingService
from src.services.ai.llm_service import LLMService
from src.services.ai.llm_token_service import LLMTokenService
from src.services.chat_service import ChatService
from src.services.data_service import DataService
from src.services.elastic_service import ElasticService
from src.services.resume_service import InsightsService

app_context = {}


async def register(name, value):
    app_register = await get_valid_registration_id(name)
    key = app_register.value
    if key in app_context:
        raise ValueError(f"Key {key} already exists in application context.")
    app_context[key] = value


async def get_valid_registration_id(name) -> AppContextKeys:
    try:
        return AppContextKeys[name]
    except KeyError:
        raise KeyError(f"Key {name} could not be registered.")


async def get(key: AppContextKeys):
    return app_context.get(key.value)


async def remove(key: AppContextKeys):
    return await app_context.pop(key.value)


async def remove_all():
    return app_context.clear()


async def init_services():
    try:
        app_properties = properties.prop(bean_id=AppContextKeys.app_properties.name)
        async_cloud_sql_datasource = AsyncCloudSQLDataSource(bean_id=AppContextKeys.async_cloud_sql_datasource.name,
                                                             app_properties=app_properties)
        async_job_handler = AsyncJobHandler(bean_id=AppContextKeys.async_job_handler.name)
        vertex_ai_embeddings = VertexTextEmbeddingService(bean_id=AppContextKeys.vertex_ai_embeddings.name)
        insights_service = InsightsService(bean_id=AppContextKeys.insights_service.name,
                                           app_properties=app_properties, datasource=async_cloud_sql_datasource)

        llm_token_service = LLMTokenService(bean_id=AppContextKeys.llm_token_service.name,
                                            app_properties=app_properties)
        llm_service = LLMService(bean_id=AppContextKeys.llm_service.name, llm_token_service=llm_token_service)
        async_es = AsyncElasticsearch(hosts=app_properties.es_url, api_key=app_properties.api_key)
        elastic_service = ElasticService(bean_id=AppContextKeys.elastic_service.name,
                                         async_es=async_es, vertex_text_embedding_service=vertex_ai_embeddings)
        chat_service = ChatService(bean_id=AppContextKeys.chat_service.name, app_properties=app_properties)
        data_service = DataService(bean_id=AppContextKeys.data_service.name,
                                   async_job_handler=async_job_handler,
                                   insight_service=insights_service,
                                   vertex_text_embedding_service=vertex_ai_embeddings,
                                   elastic_service=elastic_service,
                                   llm_service=llm_service,
                                   chat_service=chat_service)

        services = list((app_properties, async_cloud_sql_datasource, async_job_handler, vertex_ai_embeddings,
                         insights_service, async_es, elastic_service, llm_token_service, llm_service, data_service,
                         chat_service))

        for service in services:
            if isinstance(service, AsyncElasticsearch):
                await register(AppContextKeys.async_es.name, async_es)
            else:
                await register(service.bean_id, service)

    except Exception as e:
        ic_logging.get_logger(__name__).exception(f"Error initializing services: {e}")
        raise e


async def init():
    """
    Initializes the application context by setting up various services and configurations.

    This method performs the following steps:
    1. Retrieves the GCP environment variable and logs it.
    2. Initializes all required services including database connections, job handlers, AI services, and Elasticsearch.
    3. Registers each service in the application context for global access.
    4. Specifically fetches and stores an authentication token for the LLM service.

    Raises:
        Exception: If any error occurs during the initialization of services, it is logged and then raised to halt the
        application startup.
    """
    ic_logging.get_logger(__name__).info("Initializing application context ...")
    ic_logging.get_logger("google.cloud.sql.connector")
    env = os.environ['ENV']
    ic_logging.get_logger(__name__).info(f"env:: {env}")
    await init_services()

    # initialize
    llm_token_service = await get(AppContextKeys.llm_token_service)
    if isinstance(llm_token_service, LLMTokenService):
        await llm_token_service.get_token()

    ic_logging.get_logger(__name__).info("application context initialized successfully ...")


async def cleanup():
    """
    Cleans up resources and connections upon application shutdown.

    This method is responsible for gracefully shutting down and releasing resources associated with the application.
    It performs the following operations:
    1. Closes the connection to the Cloud SQL database.
    2. Performs cleanup operations for the asynchronous job handler.
    3. Closes the connection to Elasticsearch.
    4. Removes all registered services from the application context.

    """
    ic_logging.get_logger(__name__).info("cleanup begins ...")
    async_cloud_sql_datasource = await get(AppContextKeys.async_cloud_sql_datasource)
    if isinstance(async_cloud_sql_datasource, AsyncCloudSQLDataSource):
        await async_cloud_sql_datasource.cleanup()

    async_job_handler = await get(AppContextKeys.async_job_handler)
    if isinstance(async_job_handler, AsyncJobHandler):
        await async_job_handler.cleanup()

    async_es = await get(AppContextKeys.async_es)
    if isinstance(async_es, AsyncElasticsearch):
        await async_es.close()

    await remove_all()
    
    ic_logging.get_logger(__name__).info("cleanup completed ...")
