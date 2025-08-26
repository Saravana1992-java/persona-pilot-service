import asyncio
import os
from io import StringIO

import pandas as pd
from dateutil.parser import parse
from google.cloud.sql.connector import Connector
from pandas import DataFrame
from sqlalchemy import text

from src.config import ic_logging
from src.config import properties
from src.constants.envs import Env
from src.datasource.async_sql_datasource import AsyncSQLDataSource
from src.exceptions.AppException import AppException


class ResumeService:
    """
    Manages the retrieval and processing of resume data from various sources.

    This service is responsible for fetching and processing the resume data either from a database, depending on the
    environment configuration. It supports operations such as fetching resume by key, preprocessing data for
    consistency.

    Attributes:
        bean_id (str): An identifier for the instance of this class, typically used for logging or debugging purposes.
        app_properties (dict): A dictionary containing application properties and configurations.
        datasource (AsyncCloudSQLDataSource): The datasource object used for database operations.

    Methods:
        get_resume(key: str) -> DataFrame:
            Fetches resume data based on the provided key.
        fetch_data_from_db(key: str) -> DataFrame:
            Fetches resume data from the database based on the provided key. Returns a pandas DataFrame containing
            the fetched data.
        preprocess_data(data: DataFrame) -> DataFrame:
            Preprocesses the fetched data for consistency, such as filling missing values and formatting dates.
            Returns the preprocessed DataFrame.
        pre_process_array_data(data: DataFrame) -> DataFrame:
            Further processes data columns that contain array-like data stored as strings, converting them into actual
            lists. Returns the processed DataFrame.
        fetch_data_from_csv() -> DataFrame:
            Fetches resume data from a CSV file. This method is typically used in local development environments.
            Returns a pandas DataFrame containing the data.

    Raises:
        AppException: Custom exception class used to handle various error scenarios encountered during
        the data fetching and processing operations.
    """

    def __init__(self, bean_id, app_properties, datasource: AsyncSQLDataSource):
        self.bean_id = bean_id
        self.app_properties = app_properties
        self.datasource = datasource

    async def get_resume(self, key):
        if Env.LOCAL.name == properties.env:
            return await self.fetch_data_from_csv()
        else:
            return await self.fetch_data_from_db(key)

    async def fetch_data_from_db(self, key):
        ic_logging.get_logger(__name__).info("Connect Database to create data frame!!!")
        query = properties.get_resume_pages_by_user_permission_query
        params = {'userid': None, 'offset': None, 'page_size': None}
        if key:
            query = f"{query} where key = {key}"

        loop = asyncio.get_running_loop()
        async with Connector(loop=loop) as connector:
            pool = await self.datasource.init_connection_pool(connector)
            async with pool.connect() as connection:
                result = await connection.execute(text(query), params)
                results = result.fetchall()
                if not results:
                    ic_logging.get_logger(__name__).error("No data returned from the query.")
                    raise AppException(404, "No data returned from the query.")
                else:
                    ic_logging.get_logger(__name__).info(f"Number of rows returned: {len(results)}")
                    columns = result.keys()  # This gets the column names from the result
                    # Convert results to DataFrame
                    data = pd.DataFrame(results, columns=columns)
                    return data
            await pool.dispose()

    @staticmethod
    async def preprocess_data(data: DataFrame) -> DataFrame:
        data.fillna("", inplace=True)

        data = await ResumeService.pre_process_date_data(data)

        data = await ResumeService.pre_process_audit_date_data(data)

        data = await ResumeService.pre_process_string_data(data)

        data = await ResumeService.pre_process_array_data(data)

        data = await ResumeService.pre_process_file_paths(data)
        return data

    @staticmethod
    async def pre_process_string_data(data: DataFrame) -> DataFrame:
        columns_to_process = ['title', 'description']
        for column in columns_to_process:
            if column in data.columns:
                data[column] = data[column].apply(lambda x: x if isinstance(x, str) and x.strip() else "")
        return data

    @staticmethod
    async def pre_process_date_data(data: DataFrame) -> DataFrame:
        columns_to_process = ['publication_date']
        for column in columns_to_process:
            if column in data.columns:
                data[column] = data[column].apply(lambda x: '' if x is None else str(x))
        return data

    @staticmethod
    async def pre_process_audit_date_data(data: DataFrame) -> DataFrame:
        columns_to_process = ['created_datetime', 'updated_datetime']
        for column in columns_to_process:
            if column in data.columns:
                data[column] = data[column].apply(
                    lambda x: '' if x is None or pd.isna(x) else str(parse(str(x)).strftime('%Y-%m-%d %H:%M:%S')))
        return data

    @staticmethod
    async def pre_process_array_data(data: DataFrame) -> DataFrame:
        columns_to_process = ['finding', 'created_by', 'created_by_cdsid', 'updated_by', 'updated_by_cdsid', 'authors',
                              'authors_cdsid', 'draft_viewers', 'draft_viewers_cdsid', 'regions', 'classifications',
                              'keywords']
        for column in columns_to_process:
            if column in data.columns:
                data[column] = data[column].apply(
                    lambda x: [item.strip() for item in x.split(',')] if isinstance(x, str) and x.strip() else [])
        return data

    @staticmethod
    async def pre_process_file_paths(data: DataFrame) -> DataFrame:
        columns_to_process = ['file_path', 'thumbnail_image_file_path']
        for column in columns_to_process:
            if column in data.columns:
                data[column] = data[column].apply(
                    lambda x: [item.strip() for item in x.split('|')] if isinstance(x, str) and x.strip() else [])
        return data

    async def fetch_data_from_csv(self):
        script_dir = os.path.dirname(__file__)
        data_file_path = os.path.join(script_dir, self.app_properties.data_file)

        if not os.path.isfile(data_file_path):
            ic_logging.get_logger(__name__).error(f"File {data_file_path} does not exist.")
            raise AppException(404, f"File {data_file_path} does not exist.")

        async def read_file_async(path):
            loop = asyncio.get_running_loop()
            with open(path, 'r', encoding='utf-8') as file:
                return await loop.run_in_executor(None, file.read)

        try:
            data_str = await read_file_async(data_file_path)
            data = pd.read_csv(StringIO(data_str))

            if data.shape[0] == 0:
                ic_logging.get_logger(__name__).info("No data returned from the query.")
                raise AppException(404, "No data returned from the query.")
            else:
                return data
        except Exception as e:
            ic_logging.get_logger(__name__).exception(f"Error reading data from CSV: {e}")
            raise AppException(500, f"Error reading data from CSV: {e}")
