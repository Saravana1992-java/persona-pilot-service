import json

import aiohttp

from src.config import ic_logging, properties
from src.exceptions.AppException import InsightException
from src.services.ai.llm_token_service import LLMTokenService


class LLMService:
    """
    Provides services for interacting with Ford's Large Language Model (LLM) API.

    This class encapsulates the functionality required to communicate with Ford's LLM API, including summarizing
    documents based on a query. It leverages an asynchronous HTTP client for API communication and handles token
    management for authentication.

    Attributes:
        bean_id (str): An identifier for the instance of this class, typically used for logging or debugging purposes.
        llm_token_service (LLMTokenService): A service responsible for fetching and managing authentication tokens
        for the LLM API.

    Methods:
        summarize(query: str, documents: str) -> str:
            Asynchronously requests a summary from the LLM API based on the provided query and documents. Returns a
            detailed summary as a string.

    Raises:
        InsightException: If the LLM API request fails or returns an error status code.
    """

    def __init__(self, bean_id, llm_token_service: LLMTokenService):
        self.bean_id = bean_id
        self.llm_token_service = llm_token_service

    async def summarize(self, query, documents):
        prompt = (f"You are a highly skilled AI trained in language comprehension and summarization. "
                  f"I would like you to understand the user's topic: '{query}' and summarize the following "
                  f"json document into a concise abstract paragraph about the topic without exceeding 150 words. Aim "
                  f"to retain the most important points, providing a coherent and readable summary that could help the "
                  f"users to understand the main points in the document without needing to read the entire document. "
                  f"Always take extra steps to look into publicly available resources to enhance a summarization about "
                  f"the topic with more suitable points. If the provided document does not contain the information "
                  f"needed to summarize the topic or having totally irrelevant information about the topic then simply "
                  f"write: {properties.insufficient_information_reply} Please avoid unnecessary details or tangential "
                  f"points such as from document, The provided document and so on. Start the paragraph always with the "
                  f"topic followed by the summary. For example, if the topic is 'Artificial Intelligence' then start "
                  f"the paragraph with Artificial Intelligence (AI) is a field of study that involves building "
                  f"machines and computers that can mimic human intelligence. "
                  f"\n json document: {documents}")

        messages = [
            {
                "role": "system",
                "content": properties.summary_context
            },
            {
                "role": "user",
                "content": prompt
            },
        ]

        content = await self.connect_llm(messages)
        return content

    async def extract_keywords(self, query):
        messages = [
            {
                "role": "system",
                "content": properties.keyword_extraction_context
            },
            {
                "role": "user",
                "content": query
            },
        ]
        content = await self.connect_llm(messages)
        if content:
            ic_logging.get_logger(__name__).info(f"content: {content}")
            arr = json.loads(content)
            return ' '.join(map(str, arr["keywords"]))
        return None

    async def analyse_user_queries(self, user_query, query_cache):
        messages = [
            {
                "role": "system",
                "content": properties.analyse_user_query_prompt
            },
            {
                "role": "user",
                "content": f"1. {user_query}\n" + f"2. {query_cache}\n"
            },
        ]
        content = await self.connect_llm(messages)
        if content:
            ic_logging.get_logger(__name__).info(f"content: {content}")
            return content
        return None

    async def connect_llm(self, messages):
        api_endpoint = "https://api.pd01i.gcp.ford.com/fordllmapi/api/v1/chat/completions"
        token = await self.llm_token_service.get_token()
        ic_logging.get_logger(__name__).info(f"Requesting Ford LLM api_endpoint. {api_endpoint}")
        async with aiohttp.ClientSession() as session:
            async with session.post(api_endpoint,
                                    headers={"Authorization": f"Bearer {token}"},
                                    json={"model": "gpt-4",
                                          "messages": messages,
                                          }) as response:
                if response.status == 200:
                    ic_logging.get_logger(__name__).info(f"Request to Ford LLM Completed. {api_endpoint}")
                    content = await response.json()
                    return content["choices"][0]["message"]["content"]
                else:
                    error_message = (f"Request to Ford LLM failed with status code: {response.status} and "
                                     f"response: {await response.json()}")
                    ic_logging.get_logger(__name__).error(error_message)
                    raise InsightException(response.status, error_message)
