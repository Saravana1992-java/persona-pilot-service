class AppException(Exception):
    """
        Custom exception class for handling app-related errors.

        This exception is raised when an error specific to the resume processing or retrieval occurs. It allows for
        more granular error handling and can be used to communicate specific error messages and status codes back to
        the client.

        Attributes:
            status_code (int): The HTTP status code associated with the error.
            message (str): A detailed error message describing the cause of the error.
        """
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(self.status_code, self.message)
