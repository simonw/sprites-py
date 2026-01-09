"""Async checkpoint operations for Sprites."""

from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

import httpx

from sprites._base import (
    build_auth_headers,
    parse_checkpoint,
    parse_checkpoint_list,
    parse_ndjson_stream_messages,
)
from sprites.exceptions import APIError
from sprites.types import Checkpoint, StreamMessage

if TYPE_CHECKING:
    from sprites.async_sprite import AsyncSprite


class AsyncCheckpointStream:
    """An async stream of checkpoint creation messages."""

    def __init__(self, messages: list[StreamMessage]):
        """Initialize the async checkpoint stream.

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

    async def close(self) -> None:
        """Close the stream."""
        pass

    async def __aenter__(self) -> "AsyncCheckpointStream":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


class AsyncRestoreStream:
    """An async stream of checkpoint restore messages."""

    def __init__(self, messages: list[StreamMessage]):
        """Initialize the async restore stream.

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

    async def close(self) -> None:
        """Close the stream."""
        pass

    async def __aenter__(self) -> "AsyncRestoreStream":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()


async def async_list_checkpoints(
    sprite: AsyncSprite, history_filter: str = ""
) -> list[Checkpoint]:
    """List all checkpoints for a sprite asynchronously.

    Args:
        sprite: The sprite to list checkpoints for.
        history_filter: Optional filter for checkpoint history.

    Returns:
        List of checkpoint objects.

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/checkpoints"
    if history_filter:
        url += f"?history={history_filter}"

    try:
        response = await sprite.client.http_client.get(url)
    except httpx.RequestError as e:
        raise APIError(f"Failed to list checkpoints: {e}") from e

    if response.status_code != 200:
        raise APIError(
            f"Failed to list checkpoints (status {response.status_code})",
            status_code=response.status_code,
            response=response.text,
        )

    return parse_checkpoint_list(response.json())


async def async_get_checkpoint(sprite: AsyncSprite, checkpoint_id: str) -> Checkpoint:
    """Get a specific checkpoint asynchronously.

    Args:
        sprite: The sprite.
        checkpoint_id: The ID of the checkpoint.

    Returns:
        The checkpoint object.

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/checkpoints/{checkpoint_id}"

    try:
        response = await sprite.client.http_client.get(url)
    except httpx.RequestError as e:
        raise APIError(f"Failed to get checkpoint: {e}") from e

    if response.status_code != 200:
        raise APIError(
            f"Failed to get checkpoint (status {response.status_code})",
            status_code=response.status_code,
            response=response.text,
        )

    return parse_checkpoint(response.json())


async def async_create_checkpoint(
    sprite: AsyncSprite, comment: str = ""
) -> AsyncCheckpointStream:
    """Create a new checkpoint asynchronously.

    Args:
        sprite: The sprite to checkpoint.
        comment: Optional comment for the checkpoint.

    Returns:
        An async stream of checkpoint creation messages.

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/checkpoint"

    payload = {}
    if comment:
        payload["comment"] = comment

    # Use a separate async client for streaming with no timeout
    async with httpx.AsyncClient(
        timeout=None,
        headers=build_auth_headers(sprite.client.token),
    ) as client:
        try:
            response = await client.post(
                url, json=payload, headers={"Content-Type": "application/json"}
            )
        except httpx.RequestError as e:
            raise APIError(f"Failed to create checkpoint: {e}") from e

        if response.status_code != 200:
            raise APIError(
                f"Failed to create checkpoint (status {response.status_code})",
                status_code=response.status_code,
                response=response.text,
            )

        messages = parse_ndjson_stream_messages(response.text)
        return AsyncCheckpointStream(messages)


async def async_restore_checkpoint(
    sprite: AsyncSprite, checkpoint_id: str
) -> AsyncRestoreStream:
    """Restore a checkpoint asynchronously.

    Args:
        sprite: The sprite to restore.
        checkpoint_id: The ID of the checkpoint to restore.

    Returns:
        An async stream of restore messages.

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/checkpoints/{checkpoint_id}/restore"

    # Use a separate async client for streaming with no timeout
    async with httpx.AsyncClient(
        timeout=None,
        headers=build_auth_headers(sprite.client.token),
    ) as client:
        try:
            response = await client.post(url)
        except httpx.RequestError as e:
            raise APIError(f"Failed to restore checkpoint: {e}") from e

        if response.status_code != 200:
            raise APIError(
                f"Failed to restore checkpoint (status {response.status_code})",
                status_code=response.status_code,
                response=response.text,
            )

        messages = parse_ndjson_stream_messages(response.text)
        return AsyncRestoreStream(messages)
