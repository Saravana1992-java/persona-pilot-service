import asyncpg
from google.cloud.sql.connector import Connector
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import properties


class AsyncSQLDataSource:
    """
    Manages asynchronous connections to a SQL database using SQLAlchemy and asyncpg.

    This class is responsible for creating and managing a pool of connections to a specified SQL instance.
    It utilizes SQLAlchemy's create_async_engine for asynchronous ORM operations and asyncpg for lower-level database
    interactions. The class provides methods to initialize the connection pool and to clean up resources.

    Attributes:
        bean_id (str): An identifier for the instance of this class, typically used for logging or debugging.
        app_properties (object): An object containing configuration properties for the database connection, including
        instance name, database user, password, database name, IP type, and driver.

    Methods:
        init_connection_pool(connector: Connector): Asynchronously initializes the connection pool for the database
        using the provided SQL Connector. Returns the connection pool object.
        cleanup(): Asynchronously disposes of the connection pool, releasing all resources.
    """

    def __init__(self, bean_id, app_properties):
        self.bean_id = bean_id
        self.connection_pool = None
        self.app_properties = app_properties
        self.instance_connection_string = (self.app_properties.pgsql_project_id
                                           + ":" + self.app_properties.pgsql_region +
                                           ":" + self.app_properties.pgsql_instance)
        self.user = self.app_properties.pgsql_user
        self.password = self.app_properties.pgsql_password
        self.db = self.app_properties.pgsql_db
        self.ip_type = properties.pgsql_ip_type
        self.driver = properties.pgsql_driver

    async def init_connection_pool(self, connector: Connector):
        """
        Asynchronously initializes the connection pool for the SQL database.

        This method sets up a connection pool to the specified SQL instance. It leverages asyncpg for database
        connections and SQLAlchemy for asynchronous ORM operations.
        The connection pool allows for efficient management of database connections in an asynchronous environment.

        Parameters:
            connector (Connector):

        Returns:
            The initialized connection pool object, ready for use in database operations.

        Raises:
            ConnectionError: If there is an issue establishing the connection to the SQL database.
        """

        async def get_asyncpg_connection() -> asyncpg.Connection:
            asyncpg_connection: asyncpg.Connection = await connector.connect_async(
                instance_connection_string=self.instance_connection_string,
                driver=self.driver,
                user=self.user,
                password=self.password,
                db=self.db,
                ip_type=self.ip_type
            )
            return asyncpg_connection

        self.connection_pool = create_async_engine(
            url="postgresql+asyncpg://",
            async_creator=get_asyncpg_connection,
        )
        return self.connection_pool

    async def cleanup(self):
        """
        Asynchronously disposes of the connection pool, releasing all resources.

        This method is responsible for properly disposing of the connection pool associated with the SQL
        database. It ensures that all connections are closed and resources are released in an orderly fashion,
        preventing resource leaks and ensuring the application can cleanly disconnect from the database.

        Raises:
            Exception: If an error occurs during the disposal of the connection pool.
        """
        if self.connection_pool:
            await self.connection_pool.dispose()
