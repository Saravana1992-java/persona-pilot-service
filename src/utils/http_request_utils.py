import requests

from src.config import properties, ic_logging
from src.exceptions.AppException import InsightException


def get_data(uri: str, headers, with_proxy: bool = True):
    try:
        if with_proxy:
            http_proxy = properties.proxy_endpoint
            proxies = {"http": http_proxy, "https": http_proxy}
            response = requests.get(url=uri, headers=headers, proxies=proxies)
        else:
            response = requests.get(url=uri, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        ic_logging.get_logger(__name__).exception(e)
        raise InsightException(
            401, f'Failed to get_data from uri:: {uri}. Caused by "{e}"'
        )
