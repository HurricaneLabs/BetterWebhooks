import sys
import os
import time
import hashlib
import hmac
from base64 import b64decode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from loguru import logger

HASH_FUNCTION_MAP = {
    "sha1": hashlib.sha1,
    "sha256": hashlib.sha256,
    "sha512": hashlib.sha512,
}


def get_hmac_headers(
    body: bytes,
    hmac_secret: str,
    hmac_hash_function: str,
    hmac_digest_type: str,
    hmac_sig_header: str,
    hmac_time_header: str,
):
    """
    Given the final JSON
    """
    headers = {}

    # If the user sets a timestamp header, we
    # 1. Save the timestamp
    # 2. Add it to the request headers
    # 3. Append the timestamp to the body so it's calculated as part of the signature
    if hmac_time_header:
        timestamp = str(time.time())
        headers[hmac_time_header] = timestamp
        body += timestamp.encode()


    from base64 import b64encode
    secret_bytes = hmac_secret.encode("utf-8")
    logger.info(HASH_FUNCTION_MAP.get(hmac_hash_function))

    hashed = hmac.new(secret_bytes, body, HASH_FUNCTION_MAP.get(hmac_hash_function))

    if hmac_digest_type == "b64":
        digest = b64encode(hashed.digest())
    elif hmac_digest_type == "hex":
        digest = hashed.hexdigest()
    else:
        raise ValueError(f"Unknown digest type: {hmac_digest_type}")

    headers[hmac_sig_header] = digest

    return headers
