# Insights Catalog Elasticsearch

This project is an advanced Insights Catalog system designed to manage and query (**_kNN_**) insights data efficiently
using
**Vertex AI** (**_text-embedding-004_**) embeddings in Elasticsearch vector database. It is built with **_Asynchronous_
**
programming
using **_Python & FastAPI_**, offering a robust concurrent API solution for insights data handling, including fetching,
synchronizing, searching and deleting operations.
The system integrates with **Ford's Large Language Model** (**_LLM_**) API for advanced search **summarization** for the
search
results being retrieved for the user's query.

## Key Components

- **DataService**: Central to the application, it orchestrates various operations on insights data, leveraging other
  services for comprehensive data management.
- **ElasticService**: Provides asynchronous Elasticsearch operations, enabling efficient data indexing, searching,
  and management.
- **InsightsService**: Focuses on asynchronous data retrieving and processing from Cloud SQL, ensuring data
  consistency and availability.
- **LLMService**: Focuses on advanced search summarization by natural language processing and semantic understanding
  capabilities.
- **Exception Handling**: Utilizes custom exceptions for precise error management, enhancing the robustness of
  the application.

## Features

- Asynchronous data handling for improved performance.
- Integration with Ford's LLM API for advanced data processing.
- Comprehensive insights data management including CRUD operations and synchronization with external systems.
- Semantic search capabilities through Elasticsearch.
- Custom exception handling for granular error management.

## Local Setup

1. Clone the repository:
    ```bash
    git clone git@github.ford.com:VDCC/insights-elastic-search.git
    ```
2. Set environment variables:
    ```bash
    export PYTHONUNBUFFERED=1
    export ENV=DEV
    ```
3. Build the application:
    ```bash
    .\local_setup.bat
    ```
4. Run the application with file change detection:
    ```bash
    .\.venv\Scripts\python.exe -m uvicorn src.main:app --reload
    ```

## API Documentation

Access the Swagger UI for detailed API documentation and testing at: http://localhost:8000/docs

## Contributing

We welcome contributions! Please open an issue to discuss your proposal before submitting a pull request.
