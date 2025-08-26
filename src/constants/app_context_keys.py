from enum import Enum


class AppContextKeys(Enum):
    """
    Defines keys used to access various components within the application context.

    This enumeration provides a centralized definition of keys that are used to retrieve specific components from the
    application context. These components can include properties settings, data sources, services, and more,
    facilitating a structured and consistent access pattern across the application.

    Attributes:
        app_properties (Enum): Key for accessing application properties.
        async_cloud_sql_datasource (Enum): Key for accessing the asynchronous Cloud SQL data source.
        async_job_handler (Enum): Key for accessing the asynchronous job handler.
        vertex_ai_embeddings (Enum): Key for accessing Vertex AI embeddings service.
        insights_service (Enum): Key for accessing insights service.
        async_es (Enum): Key for accessing asynchronous Elasticsearch operations.
        elastic_service (Enum): Key for accessing Elasticsearch service.
        llm_token_service (Enum): Key for accessing LLM token service.
        llm_service (Enum): Key for accessing LLM service.
        data_service (Enum): Key for accessing general data service.
    """
    app_properties = 1
    async_cloud_sql_datasource = 2
    async_job_handler = 3
    vertex_ai_embeddings = 4
    insights_service = 5
    async_es = 6
    elastic_service = 7
    llm_token_service = 8
    llm_service = 9
    data_service = 10
    chat_service = 11
