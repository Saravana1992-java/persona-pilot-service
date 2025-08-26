import logging


def get_logger(name):
    """
    Creates or retrieves a logger with the specified name.

    This function configures and returns a logger instance with the given name. If a logger with that name
    already exists, it returns the existing logger. Otherwise, it creates a new logger, sets its level to INFO, and
    adds a StreamHandler to it if it doesn't already have one. The StreamHandler outputs log messages to the console.

    Parameters:
    - name (str): The name of the logger. This can be any string, but it typically corresponds to the module's __name__.

    Returns:
    - logging.Logger: A logger instance configured to log messages at the INFO level and above to the console.

    Example:
        logger = get_logger(name) logger.info("This is an info message")
        This will output: 2021-06-17 14:30:00,000 [INFO] name :: This is an info message
        """

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:  # Check if the logger already has handlers
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s :: %(message)s')

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)

        logger.addHandler(stream_handler)
    return logger
