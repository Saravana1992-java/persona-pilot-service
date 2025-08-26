import time

import aiohttp

from src.config import ic_logging, properties
from src.config.singleton import SingletonMeta


class LLMTokenService(metaclass=SingletonMeta):
    """
    Manages the lifecycle and caching of authentication tokens for Ford's LLM API.

    This service is responsible for obtaining, caching, and refreshing authentication tokens used to authenticate
    requests to Ford's Large Language Model (LLM) API. It ensures that tokens are reused efficiently across requests
    and are refreshed as necessary, minimizing the need for repeated authentication requests.

    Attributes:
        bean_id (str): An identifier for the instance of this class, typically used for logging or debugging purposes.
        app_properties (AppProperties): A configuration object containing properties required for token generation,
        including API endpoint and client credentials.
        token_expiration (float): A timestamp indicating when the current token will expire.
        token (str, optional): The current cached authentication token, if available.

    Methods:
        get_token() -> str:
            Asynchronously obtains a valid authentication token. Returns a cached token if it is still valid,
            otherwise requests a new token from the LLM API and updates the cache.

    Raises:
        aiohttp.ClientError: If there is an issue with the HTTP request to obtain a new token.
    """

    def __init__(self, bean_id, app_properties):
        self.bean_id = bean_id
        self.app_properties = app_properties
        self.token_expiration = 0
        self.token = None

    async def get_token(self):
        token_url = self.app_properties.ford_llm_token_endpoint
        client_id = self.app_properties.ford_llm_client_id
        client_secret = self.app_properties.ford_llm_client_secret
        scope = self.app_properties.ford_llm_scope
        grant_type = self.app_properties.ford_llm_grant_type
        http_proxy = properties.proxy_endpoint
        https_proxy = properties.proxy_endpoint
        # Choose the appropriate proxy based on the URL scheme
        proxy_endpoint = https_proxy if token_url.startswith("https") else http_proxy
        current_time = time.time()
        if self.token and current_time < self.token_expiration:
            ic_logging.get_logger(__name__).info("Token is still valid. Returning cached token.")
            return self.token
        else:
            ic_logging.get_logger(__name__).info("Token is not valid. Creating a new token.")
            async with aiohttp.ClientSession() as session:
                async with session.post(url=token_url, data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": scope,
                    "grant_type": grant_type
                }, proxy=proxy_endpoint) as response:
                    token_data = await response.json()
                    self.token = token_data['access_token']
                    # Assuming token expires in 3600 seconds (1 hour) from now
                    # This value should be adjusted based on the actual token lifetime provided by the API
                    self.token_expiration = current_time + token_data.get('expires_in', 3599)
                    return self.token
