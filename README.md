# Persona Pilot

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

Access the Swagger UI for detailed API documentation and testing at: <http://localhost:8000/docs>

## Contributing

We welcome contributions! Please open an issue to discuss your proposal before submitting a pull request.
