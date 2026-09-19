"""Tests for the NASty REST client boundary."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

MODULE_PATH = Path(__file__).parents[1] / "custom_components" / "nasty" / "api.py"
SPEC = importlib.util.spec_from_file_location("nasty_api", MODULE_PATH)
assert SPEC and SPEC.loader
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("nasty.local", "https://nasty.local"),
        (" https://nasty.local/ ", "https://nasty.local"),
        ("http://10.0.0.5:8080/base/", "http://10.0.0.5:8080/base"),
    ],
)
def test_normalize_url(raw: str, expected: str) -> None:
    assert api.normalize_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "ftp://nasty.local",
        "https://user:password@nasty.local",
        "https://nasty.local?token=secret",
        "https://nasty.local/#fragment",
    ],
)
def test_normalize_url_rejects_unsafe_urls(raw: str) -> None:
    with pytest.raises(ValueError):
        api.normalize_url(raw)


class FakeResponse:
    def __init__(self, status: int, body: Any = None) -> None:
        self.status = status
        self._body = body

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def json(self) -> Any:
        return self._body


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((method, url, kwargs))
        return self.response


@pytest.mark.asyncio
async def test_get_translates_rpc_method_and_authenticates() -> None:
    session = FakeSession(FakeResponse(200, {"hostname": "nasty"}))
    client = api.NastyApiClient(session, "https://nasty.local", "secret")

    assert await client.get("system.info") == {"hostname": "nasty"}
    method, url, kwargs = session.calls[0]
    assert method == "GET"
    assert url == "https://nasty.local/api/v1/system/info"
    assert kwargs["headers"] == {"Authorization": "Bearer secret"}
    assert kwargs["ssl"] is True


@pytest.mark.asyncio
async def test_post_sends_json_body() -> None:
    session = FakeSession(FakeResponse(204))
    client = api.NastyApiClient(session, "https://nasty.local", "secret")

    assert await client.post("vm.stop", id="vm-id") is None
    method, url, kwargs = session.calls[0]
    assert method == "POST"
    assert url == "https://nasty.local/api/v1/vm/stop"
    assert kwargs["json"] == {"id": "vm-id"}


@pytest.mark.asyncio
async def test_authentication_error_is_specific() -> None:
    session = FakeSession(FakeResponse(401, {"error": "invalid token"}))
    client = api.NastyApiClient(session, "https://nasty.local", "secret")

    with pytest.raises(api.NastyAuthenticationError):
        await client.get("system.info")


@pytest.mark.asyncio
async def test_api_error_uses_gateway_message() -> None:
    session = FakeSession(
        FakeResponse(400, {"error": {"code": -32602, "message": "missing field id"}})
    )
    client = api.NastyApiClient(session, "https://nasty.local", "secret")

    with pytest.raises(api.NastyApiError, match="missing field id"):
        await client.post("vm.start")
