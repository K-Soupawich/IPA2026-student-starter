import requests
from ncclient.operations import TimeoutExpiredError
from ncclient.transport.errors import (
    AuthenticationError,
    SessionCloseError,
    SSHError,
)


def error(code):
    return {"status": "error", "result": code}

def map_exception(exc):
    if isinstance(exc, ( PermissionError, AuthenticationError)):
        return error("authentication_failed")
    if isinstance(
        exc,
        (
            ConnectionError,
            TimeoutError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            SSHError,
            SessionCloseError,
            TimeoutExpiredError,
        ),
    ):
        return error("connection_failed")
    return error("backend_failed")
