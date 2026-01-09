"""Shared base utilities for sync and async Sprites SDK implementations."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sprites.types import (
    Checkpoint,
    NetworkPolicy,
    PolicyRule,
    Service,
    ServiceLogEvent,
    ServiceState,
    ServiceWithState,
    Session,
    SpriteInfo,
    StreamMessage,
)

# Default configuration
DEFAULT_BASE_URL = "https://api.sprites.dev"
DEFAULT_TIMEOUT = 30.0
CREATE_TIMEOUT = 120.0  # Sprite creation can take longer


def build_auth_headers(token: str) -> dict[str, str]:
    """Build authorization headers for API requests."""
    return {"Authorization": f"Bearer {token}"}


def build_sprite_create_payload(name: str, config: Any | None) -> dict[str, Any]:
    """Build payload for sprite creation."""
    payload: dict[str, Any] = {"name": name}
    if config:
        cfg: dict[str, Any] = {}
        if config.ram_mb is not None:
            cfg["ram_mb"] = config.ram_mb
        if config.cpus is not None:
            cfg["cpus"] = config.cpus
        if config.region is not None:
            cfg["region"] = config.region
        if config.storage_gb is not None:
            cfg["storage_gb"] = config.storage_gb
        if cfg:
            payload["config"] = cfg
    return payload


def parse_sprite_info(data: dict[str, Any], name: str) -> SpriteInfo:
    """Parse SpriteInfo from API response."""
    return SpriteInfo(
        name=data.get("name", name),
        id=data.get("id"),
        status=data.get("status"),
        url=data.get("url"),
        region=data.get("primary_region"),
    )


def parse_sprite_list(data: dict[str, Any]) -> list[SpriteInfo]:
    """Parse sprite list from API response."""
    sprites_data = data.get("sprites", [])
    sprites = []
    for s in sprites_data:
        sprites.append(SpriteInfo(
            name=s.get("name", ""),
            id=s.get("id"),
            status=s.get("status"),
            url=s.get("url"),
        ))
    return sprites


def parse_checkpoint(data: dict[str, Any]) -> Checkpoint:
    """Parse Checkpoint from API response."""
    return Checkpoint(
        id=data.get("id", ""),
        create_time=datetime.fromisoformat(data.get("create_time", "").replace("Z", "+00:00")),
        comment=data.get("comment"),
        history=data.get("history"),
    )


def parse_checkpoint_list(data: list[dict[str, Any]]) -> list[Checkpoint]:
    """Parse checkpoint list from API response."""
    return [parse_checkpoint(item) for item in data]


def parse_ndjson_stream_messages(text: str) -> list[StreamMessage]:
    """Parse NDJSON text into StreamMessage objects."""
    messages = []
    for line in text.split("\n"):
        if line.strip():
            try:
                data = json.loads(line)
                messages.append(
                    StreamMessage(
                        type=data.get("type", ""),
                        data=data.get("data"),
                        error=data.get("error"),
                    )
                )
            except json.JSONDecodeError:
                pass
    return messages


def parse_datetime(dt_str: str | None) -> datetime | None:
    """Parse ISO datetime string, returning None if invalid."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_session(data: dict[str, Any]) -> Session:
    """Parse Session from API response."""
    created_str = data.get("created", "")
    created = datetime.now()
    if created_str:
        try:
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        except ValueError:
            pass

    return Session(
        id=data.get("id", ""),
        command=data.get("command", ""),
        workdir=data.get("workdir", ""),
        created=created,
        bytes_per_second=int(data.get("bytes_per_second", 0)),
        is_active=data.get("is_active", False),
        last_activity=parse_datetime(data.get("last_activity")),
        tty=data.get("tty", False),
    )


def parse_session_list(data: dict[str, Any]) -> list[Session]:
    """Parse session list from API response."""
    sessions_data = data.get("sessions", [])
    return [parse_session(s) for s in sessions_data]


def parse_network_policy(data: dict[str, Any]) -> NetworkPolicy:
    """Parse NetworkPolicy from API response."""
    rules = []
    for rule_data in data.get("rules", []):
        rule = PolicyRule(
            domain=rule_data.get("domain"),
            action=rule_data.get("action"),
            include=rule_data.get("include"),
        )
        rules.append(rule)
    return NetworkPolicy(rules=rules)


def build_network_policy_payload(policy: NetworkPolicy) -> dict[str, Any]:
    """Build payload for network policy update."""
    return {
        "rules": [
            {
                k: v
                for k, v in {
                    "domain": rule.domain,
                    "action": rule.action,
                    "include": rule.include,
                }.items()
                if v is not None
            }
            for rule in policy.rules
        ]
    }


def parse_service_with_state(data: dict[str, Any]) -> ServiceWithState:
    """Parse ServiceWithState from API response."""
    # Parse service definition
    service = Service(
        name=data.get("name", ""),
        cmd=data.get("cmd", ""),
        args=data.get("args", []),
        needs=data.get("needs", []),
        http_port=data.get("http_port"),
    )

    # Parse state if present
    state = None
    state_data = data.get("state")
    if state_data:
        state = ServiceState(
            name=state_data.get("name", ""),
            status=state_data.get("status", "unknown"),
            pid=state_data.get("pid"),
            started_at=parse_datetime(state_data.get("started_at")),
            next_restart_at=parse_datetime(state_data.get("next_restart_at")),
            error=state_data.get("error"),
            restart_count=state_data.get("restart_count", 0),
        )

    return ServiceWithState(service=service, state=state)


def parse_service_log_events(text: str) -> list[ServiceLogEvent]:
    """Parse NDJSON text into ServiceLogEvent objects."""
    messages = []
    for line in text.split("\n"):
        if line.strip():
            try:
                data = json.loads(line)
                messages.append(
                    ServiceLogEvent(
                        type=data.get("type", ""),
                        data=data.get("data"),
                        exit_code=data.get("exit_code"),
                        timestamp=data.get("timestamp"),
                        log_files=data.get("log_files"),
                    )
                )
            except json.JSONDecodeError:
                pass
    return messages


def build_service_payload(
    cmd: str,
    args: list[str] | None,
    needs: list[str] | None,
    http_port: int | None,
) -> dict[str, Any]:
    """Build payload for service creation."""
    payload: dict[str, Any] = {"cmd": cmd}
    if args:
        payload["args"] = args
    if needs:
        payload["needs"] = needs
    if http_port is not None:
        payload["http_port"] = http_port
    return payload
