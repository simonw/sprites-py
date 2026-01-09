"""Sprites SDK - Python client for remote command execution on Sprites."""

# Sync client and sprite
# Async client and sprite
from sprites.async_checkpoint import (
    AsyncCheckpointStream,
    AsyncRestoreStream,
)
from sprites.async_exec import AsyncCmd, AsyncCompletedProcess, async_run
from sprites.async_services import AsyncServiceStream
from sprites.async_session import AsyncKillStream
from sprites.async_sprite import AsyncSprite
from sprites.client import AsyncSpritesClient, SpritesClient
from sprites.exceptions import APIError, ExitError, TimeoutError
from sprites.exec import Cmd, CompletedProcess, run
from sprites.services import ServiceStream
from sprites.session import KillStream
from sprites.sprite import Sprite
from sprites.types import (
    Checkpoint,
    NetworkPolicy,
    PolicyRule,
    Service,
    ServiceLogEvent,
    ServiceState,
    ServiceWithState,
    Session,
    SpriteConfig,
    SpriteInfo,
    StreamMessage,
    URLSettings,
)

__all__ = [
    # Sync Client
    "SpritesClient",
    "Sprite",
    # Async Client
    "AsyncSpritesClient",
    "AsyncSprite",
    # Sync Command execution
    "Cmd",
    "CompletedProcess",
    "run",
    # Async Command execution
    "AsyncCmd",
    "AsyncCompletedProcess",
    "async_run",
    # Exceptions
    "ExitError",
    "APIError",
    "TimeoutError",
    # Configuration
    "SpriteConfig",
    "SpriteInfo",
    "URLSettings",
    # Checkpoints
    "Checkpoint",
    "StreamMessage",
    # Sync Streams
    "KillStream",
    "ServiceStream",
    # Async Streams
    "AsyncCheckpointStream",
    "AsyncRestoreStream",
    "AsyncKillStream",
    "AsyncServiceStream",
    # Network policy
    "NetworkPolicy",
    "PolicyRule",
    # Sessions
    "Session",
    # Services
    "Service",
    "ServiceState",
    "ServiceWithState",
    "ServiceLogEvent",
]

__version__ = "0.1.0"
