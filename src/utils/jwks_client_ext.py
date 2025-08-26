from typing import Any, Optional, List

from jwt import PyJWKClient, PyJWK, PyJWKSet

from src.config import ic_logging
from src.exceptions.AppException import InsightException
from src.utils import http_request_utils


class PyJWKClientExt(PyJWKClient):
    def fetch_data(self) -> Any:
        jwk_set: Any = None
        try:
            jwk_set = http_request_utils.get_data(self.uri, headers={}, with_proxy=True)
            ic_logging.get_logger(__name__).debug(f"jwk_set:: {jwk_set}")
            return jwk_set
        except Exception as e:
            raise InsightException(
                403, f'Failed to fetch_data from uri:: {self.uri}. Caused by "{e}"'
            )
        finally:
            if self.jwk_set_cache is not None:
                self.jwk_set_cache.put(jwk_set)

    def get_jwk_set(self, refresh: bool = False) -> PyJWKSet:
        data = None
        if self.jwk_set_cache is not None and not refresh:
            data = self.jwk_set_cache.get()

        if data is None:
            data = self.fetch_data()

        if not isinstance(data, dict):
            raise InsightException(403, "The JWKS endpoint did not return a JSON object")

        return PyJWKSet.from_dict(data)

    def get_signing_keys(self, refresh: bool = False) -> List[PyJWK]:
        jwk_set = self.get_jwk_set(refresh)
        signing_keys = [
            jwk_set_key
            for jwk_set_key in jwk_set.keys
            if jwk_set_key.public_key_use in ["sig", None] and jwk_set_key.key_id
        ]

        if not signing_keys:
            raise InsightException(403, "The JWKS endpoint did not contain any signing keys")

        return signing_keys

    def get_signing_key(self, kid: str) -> PyJWK:
        signing_keys = self.get_signing_keys()
        signing_key = self.match_kid(signing_keys, kid)

        if not signing_key:
            # If no matching signing key from the jwk set, refresh the jwk set and try again.
            signing_keys = self.get_signing_keys(refresh=True)
            signing_key = self.match_kid(signing_keys, kid)

            if not signing_key:
                raise InsightException(403,
                                       f'Unable to find a signing key that matches kid: "{kid}"'
                                       )

        return signing_key

    def get_signing_key_from_jwt(self, token: str) -> PyJWK:
        return super().get_signing_key_from_jwt(token)

    @staticmethod
    def match_kid(signing_keys: List[PyJWK], kid: str) -> Optional[PyJWK]:
        signing_key = None

        for key in signing_keys:
            if key.key_id == kid:
                signing_key = key
                break

        return signing_key
