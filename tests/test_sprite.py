"""Tests for Sprite and AsyncSprite classes."""

from unittest.mock import MagicMock, AsyncMock
import io

import pytest

from sprites import Sprite, Cmd
from sprites.async_sprite import AsyncSprite
from sprites.async_exec import AsyncCmd


# Parametrize tests that work identically for both sprite types
SPRITE_CONFIGS = [
    pytest.param(Sprite, Cmd, id="sync"),
    pytest.param(AsyncSprite, AsyncCmd, id="async"),
]


@pytest.mark.parametrize("SpriteClass,CmdClass", SPRITE_CONFIGS)
class TestSpriteShared:
    """Tests that apply to both Sprite and AsyncSprite."""

    def test_init(self, SpriteClass, CmdClass):
        client = MagicMock()
        sprite = SpriteClass(name="test-sprite", client=client)

        assert sprite.name == "test-sprite"
        assert sprite.client is client
        assert sprite.info is None

    def test_init_with_info(self, SpriteClass, CmdClass):
        client = MagicMock()
        info = MagicMock()
        sprite = SpriteClass(name="test-sprite", client=client, info=info)

        assert sprite.info is info

    def test_command_returns_correct_type(self, SpriteClass, CmdClass):
        client = MagicMock()
        sprite = SpriteClass(name="test-sprite", client=client)

        cmd = sprite.command("echo", "hello")

        assert isinstance(cmd, CmdClass)
        assert cmd.args == ["echo", "hello"]
        assert cmd.sprite is sprite

    def test_command_with_options(self, SpriteClass, CmdClass):
        client = MagicMock()
        sprite = SpriteClass(name="test-sprite", client=client)

        stdin = io.BytesIO()
        stdout = io.BytesIO()
        stderr = io.BytesIO()

        cmd = sprite.command(
            "bash", "-c", "echo test",
            env={"FOO": "bar"},
            cwd="/home/user",
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            tty=True,
            tty_rows=40,
            tty_cols=120,
            timeout=30.0,
        )

        assert cmd.args == ["bash", "-c", "echo test"]
        assert cmd.env == {"FOO": "bar"}
        assert cmd.dir == "/home/user"
        assert cmd.stdin is stdin
        assert cmd.stdout is stdout
        assert cmd.stderr is stderr
        assert cmd.tty is True
        assert cmd.tty_rows == 40
        assert cmd.tty_cols == 120
        assert cmd.timeout == 30.0

    def test_attach_session(self, SpriteClass, CmdClass):
        client = MagicMock()
        sprite = SpriteClass(name="test-sprite", client=client)

        cmd = sprite.attach_session("sess_123")

        assert isinstance(cmd, CmdClass)
        assert cmd.session_id == "sess_123"
        assert cmd.args == []


class TestSpriteSync:
    """Sync-specific sprite tests."""

    def test_delete_calls_client(self):
        client = MagicMock()
        sprite = Sprite(name="test-sprite", client=client)

        sprite.delete()

        client.delete_sprite.assert_called_once_with("test-sprite")

    def test_destroy_calls_delete(self):
        client = MagicMock()
        sprite = Sprite(name="test-sprite", client=client)

        sprite.destroy()

        client.delete_sprite.assert_called_once_with("test-sprite")


class TestAsyncSpriteAsync:
    """Async-specific sprite tests."""

    @pytest.mark.asyncio
    async def test_delete_calls_client(self):
        client = MagicMock()
        client.delete_sprite = AsyncMock()
        sprite = AsyncSprite(name="test-sprite", client=client)

        await sprite.delete()

        client.delete_sprite.assert_called_once_with("test-sprite")

    @pytest.mark.asyncio
    async def test_destroy_calls_delete(self):
        client = MagicMock()
        client.delete_sprite = AsyncMock()
        sprite = AsyncSprite(name="test-sprite", client=client)

        await sprite.destroy()

        client.delete_sprite.assert_called_once_with("test-sprite")
