from __future__ import annotations

import json
import shlex
from typing import TYPE_CHECKING
from urllib.parse import urlencode


if TYPE_CHECKING:
    from requestforge.models import HttpRequest


def to_curl(request: HttpRequest) -> str:
    """
    Convert HttpRequest to curl command string.

    Args:
        request: The HTTP request to convert

    Returns:
        curl command string

    Example:
        >>> request = HttpRequest(
        ...     method=HttpMethod.POST,
        ...     url='https://api.example.com/users',
        ...     headers={'Authorization': 'Bearer token'},
        ...     json_data={'name': 'John'},
        ... )
        >>> print(to_curl(request))
        curl -X 'POST' -H 'Authorization: Bearer token' -H 'Content-Type: application/json' --data '{"name": "John"}' 'https://api.example.com/users'
    """
    parts: list[str] = ["curl"]

    # Method
    parts.extend(["-X", shlex.quote(request.method.value)])

    # Headers
    if request.headers:
        for key, value in request.headers.items():
            parts.extend(["-H", shlex.quote(f"{key}: {value}")])

    # Auth
    if request.auth:
        username, password = request.auth
        parts.extend(["-u", shlex.quote(f"{username}:{password}")])

    # Query params
    url = request.url
    if request.params:
        query = urlencode(request.params, doseq=True)
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{query}"

    # JSON body
    if request.json_data is not None:
        if not request.headers or "Content-Type" not in request.headers:
            parts.extend(["-H", shlex.quote("Content-Type: application/json")])

        parts.extend(["--data", shlex.quote(json.dumps(request.json_data))])

    # Form data
    elif request.data is not None:
        parts.extend(
            ["--data", shlex.quote(urlencode(request.data, doseq=True))]
        )

    # Multipart files
    if request.files:
        for field, file_value in request.files.items():
            parts.extend(["-F", shlex.quote(f"{field}=@{file_value}")])

    # Timeout
    if request.timeout is not None:
        parts.extend(["--max-time", str(request.timeout)])

    # URL
    parts.append(shlex.quote(url))

    return " ".join(parts)
