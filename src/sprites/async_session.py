"""Async session management operations for Sprites."""

from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

import httpx

from sprites._base import (
    build_auth_headers,
    parse_ndjson_stream_messages,
    parse_session_list,
)
from sprites.exceptions import APIError
from sprites.types import Session, StreamMessage

if TYPE_CHECKING:
    from sprites.async_sprite import AsyncSprite


class AsyncKillStream:
    """An async stream of session kill progress messages."""

    def __init__(self, messages: list[StreamMessage]):
        """Initialize the async kill stream.

        Args:
            messages: Pre-fetched stream messages.
        """
        self._messages = messages
        self._index = 0

    def __aiter__(self) -> AsyncIterator[StreamMessage]:
        """Return async iterator."""
        return self

    async def __anext__(self) -> StreamMessage:
        """Get the next message from the stream."""
        if self._index >= len(self._messages):
            raise StopAsyncIteration
        msg = self._messages[self._index]
        self._index += 1
        return msg

    async def process_all(self, handler: callable) -> None:
        """Process all messages with a handler function asynchronously.

        Args:
            handler: A function that takes a StreamMessage.
        """
        for msg in self._messages:
            handler(msg)

    async def close(self) -> None:
        """Close the stream."""
        pass

    async def __aenter__(self) -> "AsyncKillStream":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


async def async_list_sessions(sprite: AsyncSprite) -> list[Session]:
    """List active sessions for a sprite asynchronously.

    Args:
        sprite: The sprite to list sessions for.

    Returns:
        List of active sessions.

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/exec"

    try:
        response = await sprite.client.http_client.get(url)
    except httpx.RequestError as e:
        raise APIError(f"Failed to list sessions: {e}") from e

    if response.status_code != 200:
        raise APIError(
            f"Failed to list sessions (status {response.status_code})",
            status_code=response.status_code,
            response=response.text,
        )

    return parse_session_list(response.json())


async def async_kill_session(
    sprite: AsyncSprite,
    session_id: str,
    signal: str = "SIGTERM",
    timeout: int = 10,
) -> AsyncKillStream:
    """Kill a session asynchronously.

    Args:
        sprite: The sprite.
        session_id: The ID of the session to kill.
        signal: The signal to send (default: SIGTERM).
        timeout: Timeout in seconds before force kill (default: 10).

    Returns:
        An async stream of kill progress messages.

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/exec/{session_id}/kill"

    payload = {
        "signal": signal,
        "timeout": timeout,
    }

    # Use a separate async client for streaming with extended timeout
    async with httpx.AsyncClient(
        timeout=120.0,
        headers=build_auth_headers(sprite.client.token),
    ) as client:
        try:
            response = await client.post(url, json=payload)
        except httpx.RequestError as e:
            raise APIError(f"Failed to kill session: {e}") from e

        if response.status_code != 200:
            raise APIError(
                f"Failed to kill session (status {response.status_code})",
                status_code=response.status_code,
                response=response.text,
            )

        messages = parse_ndjson_stream_messages(response.text)
        return AsyncKillStream(messages)
