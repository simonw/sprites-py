"""Async service management operations for Sprites."""

from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator, Optional

import httpx

from sprites._base import (
    build_auth_headers,
    build_service_payload,
    parse_service_log_events,
    parse_service_with_state,
)
from sprites.exceptions import APIError
from sprites.types import ServiceLogEvent, ServiceWithState

if TYPE_CHECKING:
    from sprites.async_sprite import AsyncSprite


class AsyncServiceStream:
    """An async stream of service operation messages."""

    def __init__(self, messages: list[ServiceLogEvent]):
        """Initialize the async service stream.

        Args:
            messages: Pre-fetched stream messages.
        """
        self._messages = messages
        self._index = 0

    def __aiter__(self) -> AsyncIterator[ServiceLogEvent]:
        """Return async iterator."""
        return self

    async def __anext__(self) -> ServiceLogEvent:
        """Get the next message from the stream."""
        if self._index >= len(self._messages):
            raise StopAsyncIteration
        msg = self._messages[self._index]
        self._index += 1
        return msg

    async def process_all(self, handler: callable) -> None:
        """Process all messages with a handler function asynchronously.

        Args:
            handler: A function that takes a ServiceLogEvent.
        """
        for msg in self._messages:
            handler(msg)

    async def close(self) -> None:
        """Close the stream."""
        pass

    async def __aenter__(self) -> "AsyncServiceStream":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


async def async_list_services(sprite: AsyncSprite) -> list[ServiceWithState]:
    """List all services for a sprite asynchronously.

    Args:
        sprite: The sprite to list services for.

    Returns:
        List of services with their state.

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/services"

    try:
        response = await sprite.client.http_client.get(url)
    except httpx.RequestError as e:
        raise APIError(f"Failed to list services: {e}") from e

    if response.status_code != 200:
        raise APIError(
            f"Failed to list services (status {response.status_code})",
            status_code=response.status_code,
            response=response.text,
        )

    data = response.json()
    return [parse_service_with_state(s) for s in data]


async def async_get_service(sprite: AsyncSprite, name: str) -> ServiceWithState:
    """Get a specific service asynchronously.

    Args:
        sprite: The sprite.
        name: The name of the service.

    Returns:
        The service with its state.

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/services/{name}"

    try:
        response = await sprite.client.http_client.get(url)
    except httpx.RequestError as e:
        raise APIError(f"Failed to get service: {e}") from e

    if response.status_code == 404:
        raise APIError(f"Service not found: {name}", status_code=404)

    if response.status_code != 200:
        raise APIError(
            f"Failed to get service (status {response.status_code})",
            status_code=response.status_code,
            response=response.text,
        )

    return parse_service_with_state(response.json())


async def async_create_service(
    sprite: AsyncSprite,
    name: str,
    cmd: str,
    args: Optional[list[str]] = None,
    needs: Optional[list[str]] = None,
    http_port: Optional[int] = None,
    duration: Optional[float] = None,
) -> AsyncServiceStream:
    """Create or update a service asynchronously.

    Args:
        sprite: The sprite.
        name: The name of the service.
        cmd: The command to run.
        args: Command arguments.
        needs: Services this service depends on.
        http_port: HTTP port the service listens on.
        duration: Monitoring duration in seconds.

    Returns:
        An async stream of service log events.

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/services/{name}"
    if duration:
        url += f"?duration={duration}s"

    payload = build_service_payload(cmd, args, needs, http_port)

    async with httpx.AsyncClient(
        timeout=120.0,
        headers=build_auth_headers(sprite.client.token),
    ) as client:
        try:
            response = await client.put(url, json=payload)
        except httpx.RequestError as e:
            raise APIError(f"Failed to create service: {e}") from e

        if response.status_code == 409:
            raise APIError(
                "Service conflict",
                status_code=409,
                response=response.text,
            )

        if response.status_code != 200:
            raise APIError(
                f"Failed to create service (status {response.status_code})",
                status_code=response.status_code,
                response=response.text,
            )

        return AsyncServiceStream(parse_service_log_events(response.text))


async def async_delete_service(sprite: AsyncSprite, name: str) -> None:
    """Delete a service asynchronously.

    Args:
        sprite: The sprite.
        name: The name of the service.

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/services/{name}"

    try:
        response = await sprite.client.http_client.delete(url)
    except httpx.RequestError as e:
        raise APIError(f"Failed to delete service: {e}") from e

    if response.status_code == 404:
        raise APIError(f"Service not found: {name}", status_code=404)

    if response.status_code == 409:
        raise APIError(
            "Service conflict",
            status_code=409,
            response=response.text,
        )

    if response.status_code not in (200, 204):
        raise APIError(
            f"Failed to delete service (status {response.status_code})",
            status_code=response.status_code,
            response=response.text,
        )


async def async_start_service(
    sprite: AsyncSprite,
    name: str,
    duration: Optional[float] = None,
) -> AsyncServiceStream:
    """Start a service asynchronously.

    Args:
        sprite: The sprite.
        name: The name of the service.
        duration: Monitoring duration in seconds.

    Returns:
        An async stream of service log events.

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/services/{name}/start"
    if duration:
        url += f"?duration={duration}s"

    async with httpx.AsyncClient(
        timeout=120.0,
        headers=build_auth_headers(sprite.client.token),
    ) as client:
        try:
            response = await client.post(url)
        except httpx.RequestError as e:
            raise APIError(f"Failed to start service: {e}") from e

        if response.status_code == 404:
            raise APIError(f"Service not found: {name}", status_code=404)

        if response.status_code != 200:
            raise APIError(
                f"Failed to start service (status {response.status_code})",
                status_code=response.status_code,
                response=response.text,
            )

        return AsyncServiceStream(parse_service_log_events(response.text))


async def async_stop_service(
    sprite: AsyncSprite,
    name: str,
    timeout: Optional[float] = None,
) -> AsyncServiceStream:
    """Stop a service asynchronously.

    Args:
        sprite: The sprite.
        name: The name of the service.
        timeout: Timeout in seconds before force stop.

    Returns:
        An async stream of service log events.

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/services/{name}/stop"
    if timeout:
        url += f"?timeout={timeout}s"

    async with httpx.AsyncClient(
        timeout=120.0,
        headers=build_auth_headers(sprite.client.token),
    ) as client:
        try:
            response = await client.post(url)
        except httpx.RequestError as e:
            raise APIError(f"Failed to stop service: {e}") from e

        if response.status_code == 404:
            raise APIError(f"Service not found: {name}", status_code=404)

        if response.status_code == 409:
            raise APIError(
                "Service not running",
                status_code=409,
                response=response.text,
            )

        if response.status_code != 200:
            raise APIError(
                f"Failed to stop service (status {response.status_code})",
                status_code=response.status_code,
                response=response.text,
            )

        return AsyncServiceStream(parse_service_log_events(response.text))


async def async_signal_service(sprite: AsyncSprite, name: str, signal: str) -> None:
    """Send a signal to a running service asynchronously.

    Args:
        sprite: The sprite.
        name: The name of the service.
        signal: The signal to send (e.g., "SIGTERM", "SIGHUP").

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/services/signal"

    payload = {
        "name": name,
        "signal": signal,
    }

    try:
        response = await sprite.client.http_client.post(url, json=payload)
    except httpx.RequestError as e:
        raise APIError(f"Failed to signal service: {e}") from e

    if response.status_code == 404:
        raise APIError(f"Service not found: {name}", status_code=404)

    if response.status_code == 409:
        raise APIError(
            "Service not running",
            status_code=409,
            response=response.text,
        )

    if response.status_code == 400:
        raise APIError(
            f"Invalid signal: {signal}",
            status_code=400,
            response=response.text,
        )

    if response.status_code not in (200, 204):
        raise APIError(
            f"Failed to signal service (status {response.status_code})",
            status_code=response.status_code,
            response=response.text,
        )
