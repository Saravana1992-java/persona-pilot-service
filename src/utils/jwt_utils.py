import jwt

from src.config import ic_logging
from src.exceptions.AppException import InsightException
from src.utils import http_request_utils
from src.utils.jwks_client_ext import PyJWKClientExt


def validate_jwt_token(token: str, aud: str):
    try:
        signing_key = get_signing_key(token)
        # Decode the JWT token using the public key to validate the claims and signature
        options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_nbf": True,
            "verify_iat": True,
            "verify_aud": True
        }
        try:
            verified_claims = jwt.decode(jwt=token,
                                         key=signing_key.key,
                                         algorithms=["RS256"],
                                         audience=aud,
                                         options=options)
            ic_logging.get_logger(__name__).debug(f"verified_claims:: {verified_claims}")
        except Exception as e:
            raise InsightException(401, f"UnAuthorised: {e}")
        return verified_claims
    except jwt.ExpiredSignatureError:
        raise InsightException(401, "Token has expired")
    except jwt.InvalidTokenError as e:
        raise InsightException(401, f"Invalid token: {e}")


def get_signing_key(token: str):
    # Decode the JWT token header to extract the kid
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header['kid']

    # Decode the JWT token claims without verifying the signature to extract the iss
    unverified_claims = jwt.decode(token, options={"verify_signature": False}, algorithms=["RS256"])
    iss = unverified_claims['iss']

    # Fetch the public key using the kid and iss
    open_id_config_url = f"{iss}/.well-known/openid-configuration"
    ic_logging.get_logger(__name__).info(f"open_id_config_url:: {open_id_config_url}")
    response = http_request_utils.get_data(open_id_config_url, headers={}, with_proxy=True)
    jwks_uri = response['jwks_uri']
    ic_logging.get_logger(__name__).info(f"jwks_uri:: {jwks_uri}")

    jwks_client = PyJWKClientExt(jwks_uri)
    signing_key = jwks_client.get_signing_key(kid)
    return signing_key
