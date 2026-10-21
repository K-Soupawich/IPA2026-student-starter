import requests

def error(code):
    return {"status": "error", "result": code}

def map_exception(exc):
    if isinstance(exc, PermissionError):
        return error("authentication_failed")
    if isinstance(
        exc,
        (
            ConnectionError,
            TimeoutError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ),
    ):
        return error("connection_failed")
    return error("backend_failed")
