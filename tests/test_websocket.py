"""Tests for WebSocket URL building and protocol handling."""

from unittest.mock import MagicMock

import pytest

from sprites.websocket import build_websocket_url, StreamID


class MockCmd:
    """Mock command for testing URL building."""

    def __init__(
        self,
        sprite_name: str = "test-sprite",
        base_url: str = "https://api.sprites.dev",
        token: str = "test-token",
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        tty: bool = False,
        tty_rows: int = 24,
        tty_cols: int = 80,
        session_id: str | None = None,
    ):
        self.sprite = MagicMock()
        self.sprite.name = sprite_name
        self.sprite.client = MagicMock()
        self.sprite.client.base_url = base_url
        self.sprite.client.token = token

        self.args = args or []
        self.env = env or {}
        self.dir = cwd
        self.tty = tty
        self.tty_rows = tty_rows
        self.tty_cols = tty_cols
        self.session_id = session_id


class TestBuildWebsocketUrl:
    def test_basic_url(self):
        cmd = MockCmd(args=["echo", "hello"])
        url = build_websocket_url(cmd)

        assert url.startswith("wss://api.sprites.dev/v1/sprites/test-sprite/exec?")
        assert "cmd=echo" in url
        assert "cmd=hello" in url
        assert "path=echo" in url
        assert "stdin=true" in url

    def test_http_to_ws_conversion(self):
        cmd = MockCmd(base_url="http://localhost:8080", args=["ls"])
        url = build_websocket_url(cmd)

        assert url.startswith("ws://localhost:8080/")

    def test_https_to_wss_conversion(self):
        cmd = MockCmd(base_url="https://api.sprites.dev", args=["ls"])
        url = build_websocket_url(cmd)

        assert url.startswith("wss://api.sprites.dev/")

    def test_with_environment_variables(self):
        cmd = MockCmd(args=["bash"], env={"FOO": "bar", "BAZ": "qux"})
        url = build_websocket_url(cmd)

        assert "env=FOO%3Dbar" in url
        assert "env=BAZ%3Dqux" in url

    def test_with_working_directory(self):
        cmd = MockCmd(args=["ls"], cwd="/home/user")
        url = build_websocket_url(cmd)

        assert "dir=%2Fhome%2Fuser" in url

    def test_with_tty_enabled(self):
        cmd = MockCmd(args=["bash"], tty=True, tty_rows=40, tty_cols=120)
        url = build_websocket_url(cmd)

        assert "tty=true" in url
        assert "rows=40" in url
        assert "cols=120" in url

    def test_without_tty(self):
        cmd = MockCmd(args=["echo", "test"], tty=False)
        url = build_websocket_url(cmd)

        assert "tty=true" not in url
        assert "rows=" not in url
        assert "cols=" not in url

    def test_attach_to_session(self):
        cmd = MockCmd(session_id="sess_123")
        url = build_websocket_url(cmd)

        assert "/exec/sess_123?" in url
        # Should not include cmd params when attaching
        assert "cmd=" not in url
        assert "path=" not in url

    def test_empty_args(self):
        cmd = MockCmd(args=[])
        url = build_websocket_url(cmd)

        # Should still work, just no cmd params
        assert "stdin=true" in url


class TestStreamID:
    def test_stream_ids(self):
        assert StreamID.STDIN == 0
        assert StreamID.STDOUT == 1
        assert StreamID.STDERR == 2
        assert StreamID.EXIT == 3
        assert StreamID.STDIN_EOF == 4
