"""
Tests for utility functions.
    - curl command generation
    - Various request types
"""

from requestforge.utils import to_curl
from requestforge.models import HttpMethod, HttpRequest


class TestToCurl:
    """
    Test to_curl utility function.

    Output Example:
    curl -X 'POST' \
      -H 'Authorization: Bearer token' \
      -H 'Content-Type: application/json' \
      --data '{"name": "John"}' \
      'https://api.example.com/users?notify=true'
    """

    def test_simple_get_request(self):
        """Test converting simple GET request to curl (Basic GET → curl)."""
        request = HttpRequest(
            method=HttpMethod.GET,
            url="https://api.example.com/users",
        )

        curl_cmd = to_curl(request)

        assert "curl" in curl_cmd
        assert "GET" in curl_cmd
        assert "api.example.com/users" in curl_cmd

    def test_post_with_json(self):
        """Test POST request with JSON (POST + JSON + headers)."""
        request = HttpRequest(
            method=HttpMethod.POST,
            url="https://api.example.com/users",
            json_data={"name": "John", "email": "john@example.com"},
            headers={"Authorization": "Bearer token"},
        )

        curl_cmd = to_curl(request)

        assert "POST" in curl_cmd
        assert "Authorization" in curl_cmd
        assert "Bearer token" in curl_cmd
        assert "--data" in curl_cmd
        assert "name" in curl_cmd

    def test_post_with_form_data(self):
        """Test POST request with form data (POST + form data)."""
        request = HttpRequest(
            method=HttpMethod.POST,
            url="https://api.example.com/login",
            data={"username": "user", "password": "pass"},
        )

        curl_cmd = to_curl(request)

        assert "POST" in curl_cmd
        assert "--data" in curl_cmd

    def test_request_with_query_params(self):
        """Test request with query parameters (URL with ?params)."""
        request = HttpRequest(
            method=HttpMethod.GET,
            url="https://api.example.com/users",
            params={"page": 1, "limit": 10},
        )

        curl_cmd = to_curl(request)

        assert "page" in curl_cmd
        assert "limit" in curl_cmd

    def test_request_with_auth(self):
        """Test request with basic auth (-u user:pass)."""
        request = HttpRequest(
            method=HttpMethod.GET,
            url="https://api.example.com/users",
            auth=("user", "password"),
        )

        curl_cmd = to_curl(request)

        assert "-u" in curl_cmd
        assert "user:password" in curl_cmd

    def test_request_with_timeout(self):
        """Test request with timeout (--max-time)."""
        request = HttpRequest(
            method=HttpMethod.GET,
            url="https://api.example.com/users",
            timeout=30.0,
        )

        curl_cmd = to_curl(request)

        assert "--max-time" in curl_cmd
        assert "30" in curl_cmd

    def test_request_with_files(self):
        """Test request with file upload (-F file=@path)."""
        request = HttpRequest(
            method=HttpMethod.POST,
            url="https://api.example.com/upload",
            files={"file": "/path/to/file.txt"},
        )

        curl_cmd = to_curl(request)

        assert "-F" in curl_cmd
        assert "file" in curl_cmd

    def test_multiple_headers(self):
        """Test request with multiple headers (Multiple -H)."""
        request = HttpRequest(
            method=HttpMethod.GET,
            url="https://api.example.com/users",
            headers={
                "Authorization": "Bearer token",
                "X-Custom-Header": "value",
                "X-Request-ID": "123",
            },
        )

        curl_cmd = to_curl(request)

        assert "Authorization" in curl_cmd
        assert "X-Custom-Header" in curl_cmd
        assert "X-Request-ID" in curl_cmd

    def test_complex_request(self):
        """Test complex request with multiple features (All features combined)."""
        request = HttpRequest(
            method=HttpMethod.POST,
            url="https://api.example.com/users",
            headers={"Authorization": "Bearer token"},
            json_data={"name": "John"},
            params={"notify": "true"},
            timeout=60.0,
        )

        curl_cmd = to_curl(request)

        assert "POST" in curl_cmd
        assert "Authorization" in curl_cmd
        assert "notify" in curl_cmd
        assert "--data" in curl_cmd
        assert "--max-time" in curl_cmd
