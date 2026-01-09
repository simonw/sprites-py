"""Tests for shared base utilities."""

from datetime import datetime, timezone

import pytest

from sprites._base import (
    build_auth_headers,
    build_network_policy_payload,
    build_service_payload,
    build_sprite_create_payload,
    parse_checkpoint,
    parse_checkpoint_list,
    parse_datetime,
    parse_network_policy,
    parse_ndjson_stream_messages,
    parse_service_log_events,
    parse_service_with_state,
    parse_session,
    parse_session_list,
    parse_sprite_info,
    parse_sprite_list,
)
from sprites.types import NetworkPolicy, PolicyRule, SpriteConfig


class TestBuildAuthHeaders:
    def test_basic_token(self):
        headers = build_auth_headers("my-token")
        assert headers == {"Authorization": "Bearer my-token"}

    def test_empty_token(self):
        headers = build_auth_headers("")
        assert headers == {"Authorization": "Bearer "}


class TestBuildSpriteCreatePayload:
    def test_name_only(self):
        payload = build_sprite_create_payload("my-sprite", None)
        assert payload == {"name": "my-sprite"}

    def test_with_config(self):
        config = SpriteConfig(ram_mb=512, cpus=2, region="ord", storage_gb=10)
        payload = build_sprite_create_payload("my-sprite", config)
        assert payload == {
            "name": "my-sprite",
            "config": {
                "ram_mb": 512,
                "cpus": 2,
                "region": "ord",
                "storage_gb": 10,
            },
        }

    def test_with_partial_config(self):
        config = SpriteConfig(ram_mb=256)
        payload = build_sprite_create_payload("my-sprite", config)
        assert payload == {
            "name": "my-sprite",
            "config": {"ram_mb": 256},
        }


class TestParseSpriteInfo:
    def test_full_response(self):
        data = {
            "name": "test-sprite",
            "id": "sp_123",
            "status": "running",
            "url": "https://test-sprite.sprites.dev",
            "primary_region": "ord",
        }
        info = parse_sprite_info(data, "fallback-name")
        assert info.name == "test-sprite"
        assert info.id == "sp_123"
        assert info.status == "running"
        assert info.url == "https://test-sprite.sprites.dev"
        assert info.region == "ord"

    def test_minimal_response(self):
        data = {}
        info = parse_sprite_info(data, "fallback-name")
        assert info.name == "fallback-name"
        assert info.id is None
        assert info.status is None


class TestParseSpriteList:
    def test_multiple_sprites(self):
        data = {
            "sprites": [
                {"name": "sprite1", "id": "sp_1", "status": "running"},
                {"name": "sprite2", "id": "sp_2", "status": "stopped"},
            ]
        }
        sprites = parse_sprite_list(data)
        assert len(sprites) == 2
        assert sprites[0].name == "sprite1"
        assert sprites[1].name == "sprite2"

    def test_empty_list(self):
        data = {"sprites": []}
        sprites = parse_sprite_list(data)
        assert len(sprites) == 0


class TestParseCheckpoint:
    def test_full_checkpoint(self):
        data = {
            "id": "cp_123",
            "create_time": "2024-01-15T10:30:00Z",
            "comment": "test checkpoint",
            "history": ["cp_122", "cp_121"],
        }
        checkpoint = parse_checkpoint(data)
        assert checkpoint.id == "cp_123"
        assert checkpoint.comment == "test checkpoint"
        assert checkpoint.history == ["cp_122", "cp_121"]


class TestParseCheckpointList:
    def test_multiple_checkpoints(self):
        data = [
            {"id": "cp_1", "create_time": "2024-01-15T10:00:00Z"},
            {"id": "cp_2", "create_time": "2024-01-15T11:00:00Z"},
        ]
        checkpoints = parse_checkpoint_list(data)
        assert len(checkpoints) == 2
        assert checkpoints[0].id == "cp_1"
        assert checkpoints[1].id == "cp_2"


class TestParseNdjsonStreamMessages:
    def test_multiple_messages(self):
        text = '{"type": "info", "data": "Starting..."}\n{"type": "done"}\n'
        messages = parse_ndjson_stream_messages(text)
        assert len(messages) == 2
        assert messages[0].type == "info"
        assert messages[0].data == "Starting..."
        assert messages[1].type == "done"

    def test_empty_lines(self):
        text = '{"type": "info"}\n\n{"type": "done"}\n'
        messages = parse_ndjson_stream_messages(text)
        assert len(messages) == 2

    def test_invalid_json_skipped(self):
        text = '{"type": "info"}\ninvalid json\n{"type": "done"}\n'
        messages = parse_ndjson_stream_messages(text)
        assert len(messages) == 2


class TestParseDatetime:
    def test_valid_datetime(self):
        result = parse_datetime("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_none_input(self):
        result = parse_datetime(None)
        assert result is None

    def test_empty_string(self):
        result = parse_datetime("")
        assert result is None

    def test_invalid_format(self):
        result = parse_datetime("not a date")
        assert result is None


class TestParseSession:
    def test_full_session(self):
        data = {
            "id": "sess_123",
            "command": "bash",
            "workdir": "/home/user",
            "created": "2024-01-15T10:00:00Z",
            "bytes_per_second": 100,
            "is_active": True,
            "last_activity": "2024-01-15T10:05:00Z",
            "tty": True,
        }
        session = parse_session(data)
        assert session.id == "sess_123"
        assert session.command == "bash"
        assert session.workdir == "/home/user"
        assert session.bytes_per_second == 100
        assert session.is_active is True
        assert session.tty is True


class TestParseSessionList:
    def test_multiple_sessions(self):
        data = {
            "sessions": [
                {"id": "sess_1", "command": "bash", "workdir": "/", "created": "2024-01-15T10:00:00Z"},
                {"id": "sess_2", "command": "python", "workdir": "/app", "created": "2024-01-15T11:00:00Z"},
            ]
        }
        sessions = parse_session_list(data)
        assert len(sessions) == 2
        assert sessions[0].id == "sess_1"
        assert sessions[1].id == "sess_2"


class TestParseNetworkPolicy:
    def test_with_rules(self):
        data = {
            "rules": [
                {"domain": "*.example.com", "action": "allow"},
                {"domain": "*.blocked.com", "action": "deny"},
            ]
        }
        policy = parse_network_policy(data)
        assert len(policy.rules) == 2
        assert policy.rules[0].domain == "*.example.com"
        assert policy.rules[0].action == "allow"

    def test_empty_rules(self):
        data = {"rules": []}
        policy = parse_network_policy(data)
        assert len(policy.rules) == 0


class TestBuildNetworkPolicyPayload:
    def test_with_rules(self):
        policy = NetworkPolicy(
            rules=[
                PolicyRule(domain="*.example.com", action="allow"),
                PolicyRule(domain="*.blocked.com", action="deny"),
            ]
        )
        payload = build_network_policy_payload(policy)
        assert len(payload["rules"]) == 2
        assert payload["rules"][0]["domain"] == "*.example.com"
        assert payload["rules"][0]["action"] == "allow"

    def test_filters_none_values(self):
        policy = NetworkPolicy(
            rules=[PolicyRule(domain="*.example.com")]
        )
        payload = build_network_policy_payload(policy)
        assert "action" not in payload["rules"][0]


class TestParseServiceWithState:
    def test_with_state(self):
        data = {
            "name": "web",
            "cmd": "python",
            "args": ["-m", "http.server"],
            "needs": ["db"],
            "http_port": 8000,
            "state": {
                "name": "web",
                "status": "running",
                "pid": 1234,
                "started_at": "2024-01-15T10:00:00Z",
                "restart_count": 2,
            },
        }
        svc = parse_service_with_state(data)
        assert svc.service.name == "web"
        assert svc.service.cmd == "python"
        assert svc.service.args == ["-m", "http.server"]
        assert svc.service.needs == ["db"]
        assert svc.service.http_port == 8000
        assert svc.state is not None
        assert svc.state.status == "running"
        assert svc.state.pid == 1234
        assert svc.state.restart_count == 2

    def test_without_state(self):
        data = {"name": "web", "cmd": "python"}
        svc = parse_service_with_state(data)
        assert svc.service.name == "web"
        assert svc.state is None


class TestParseServiceLogEvents:
    def test_multiple_events(self):
        text = '{"type": "stdout", "data": "Hello"}\n{"type": "exit", "exit_code": 0}\n'
        events = parse_service_log_events(text)
        assert len(events) == 2
        assert events[0].type == "stdout"
        assert events[0].data == "Hello"
        assert events[1].type == "exit"
        assert events[1].exit_code == 0


class TestBuildServicePayload:
    def test_minimal(self):
        payload = build_service_payload("python", None, None, None)
        assert payload == {"cmd": "python"}

    def test_full(self):
        payload = build_service_payload(
            "python",
            ["-m", "http.server"],
            ["db"],
            8000,
        )
        assert payload == {
            "cmd": "python",
            "args": ["-m", "http.server"],
            "needs": ["db"],
            "http_port": 8000,
        }
