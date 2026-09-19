"""Asynchronous client for NASty's REST gateway."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout

JsonObject = dict[str, Any]


class NastyApiError(Exception):
    """Base error returned by the NASty API client."""


class NastyAuthenticationError(NastyApiError):
    """The supplied API token was rejected."""


class NastyCannotConnectError(NastyApiError):
    """The NASty appliance could not be reached."""


def normalize_url(url: str) -> str:
    """Normalize an appliance URL and reject unsupported URL shapes."""
    candidate = url.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL must use http or https and include a hostname")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("URL must not contain credentials, a query, or a fragment")
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


class NastyApiClient:
    """Small typed boundary around the appliance REST gateway."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        token: str,
        *,
        verify_ssl: bool = True,
    ) -> None:
        self._session = session
        self.base_url = normalize_url(base_url)
        self._token = token
        self._verify_ssl = verify_ssl

    async def _decode_response(self, response: ClientResponse) -> Any:
        if response.status in {401, 403}:
            raise NastyAuthenticationError("NASty rejected the API token")
        if response.status >= 400:
            try:
                body = await response.json()
                message = body.get("error", {}).get("message")
            except (ClientError, ValueError, TypeError, AttributeError):
                message = None
            raise NastyApiError(message or f"NASty returned HTTP {response.status}")
        if response.status == 204:
            return None
        return await response.json()

    async def request(
        self,
        method: str,
        rpc_method: str,
        *,
        params: JsonObject | None = None,
    ) -> Any:
        """Call one registered RPC method through its REST route."""
        path = rpc_method.replace(".", "/")
        kwargs: dict[str, Any] = {
            "headers": {"Authorization": f"Bearer {self._token}"},
            "ssl": self._verify_ssl,
            "timeout": ClientTimeout(total=30),
        }
        if method == "GET":
            kwargs["params"] = params
        else:
            kwargs["json"] = params
        try:
            async with self._session.request(
                method, f"{self.base_url}/api/v1/{path}", **kwargs
            ) as response:
                return await self._decode_response(response)
        except NastyApiError:
            raise
        except (ClientError, TimeoutError) as error:
            raise NastyCannotConnectError(str(error)) from error

    async def get(self, rpc_method: str, **params: Any) -> Any:
        """Call a read-only NASty method."""
        return await self.request("GET", rpc_method, params=params or None)

    async def post(self, rpc_method: str, **params: Any) -> Any:
        """Call a NASty action method."""
        return await self.request("POST", rpc_method, params=params or None)

    async def get_optional(self, rpc_method: str, default: Any) -> Any:
        """Read an optional subsystem without failing the main coordinator."""
        try:
            return await self.get(rpc_method)
        except NastyApiError:
            return default

    async def validate(self) -> JsonObject:
        """Validate connectivity and return appliance identity."""
        result = await self.get("system.info")
        if not isinstance(result, dict) or not result.get("hostname"):
            raise NastyApiError("system.info returned an invalid response")
        return result
