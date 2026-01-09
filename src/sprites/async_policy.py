"""Async network policy operations for Sprites."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from sprites._base import build_network_policy_payload, parse_network_policy
from sprites.exceptions import APIError
from sprites.types import NetworkPolicy

if TYPE_CHECKING:
    from sprites.async_sprite import AsyncSprite


async def async_get_network_policy(sprite: AsyncSprite) -> NetworkPolicy:
    """Get the current network policy for a sprite asynchronously.

    Args:
        sprite: The sprite to get the policy for.

    Returns:
        The network policy.

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/policy/network"

    try:
        response = await sprite.client.http_client.get(url)
    except httpx.RequestError as e:
        raise APIError(f"Failed to get network policy: {e}") from e

    if response.status_code != 200:
        raise APIError(
            f"Failed to get network policy (status {response.status_code})",
            status_code=response.status_code,
            response=response.text,
        )

    return parse_network_policy(response.json())


async def async_update_network_policy(
    sprite: AsyncSprite, policy: NetworkPolicy
) -> None:
    """Update the network policy for a sprite asynchronously.

    Args:
        sprite: The sprite to update.
        policy: The new network policy.

    Raises:
        APIError: If the API call fails.
    """
    url = f"{sprite.client.base_url}/v1/sprites/{sprite.name}/policy/network"
    payload = build_network_policy_payload(policy)

    try:
        response = await sprite.client.http_client.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
    except httpx.RequestError as e:
        raise APIError(f"Failed to update network policy: {e}") from e

    if response.status_code == 400:
        raise APIError(
            f"Invalid policy: {response.text}",
            status_code=400,
            response=response.text,
        )

    if response.status_code != 204:
        raise APIError(
            f"Failed to update network policy (status {response.status_code})",
            status_code=response.status_code,
            response=response.text,
        )
