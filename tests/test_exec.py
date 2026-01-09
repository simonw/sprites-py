"""Tests for sync and async command execution."""

from unittest.mock import MagicMock, AsyncMock, patch
import io

import pytest

from sprites import Cmd, CompletedProcess, ExitError, TimeoutError
from sprites.async_exec import AsyncCmd, AsyncCompletedProcess


class TestCompletedProcess:
    def test_basic(self):
        result = CompletedProcess(
            args=["echo", "hello"],
            returncode=0,
            stdout=b"hello\n",
            stderr=b"",
        )
        assert result.args == ["echo", "hello"]
        assert result.returncode == 0
        assert result.stdout == b"hello\n"
        assert result.stderr == b""

    def test_without_output(self):
        result = CompletedProcess(args=["ls"], returncode=0)
        assert result.stdout is None
        assert result.stderr is None


class TestAsyncCompletedProcess:
    def test_basic(self):
        result = AsyncCompletedProcess(
            args=["echo", "hello"],
            returncode=0,
            stdout=b"hello\n",
            stderr=b"",
        )
        assert result.args == ["echo", "hello"]
        assert result.returncode == 0
        assert result.stdout == b"hello\n"
        assert result.stderr == b""


class TestCmd:
    def test_init_basic(self):
        sprite = MagicMock()
        cmd = Cmd(sprite, ["echo", "hello"])

        assert cmd.sprite is sprite
        assert cmd.args == ["echo", "hello"]
        assert cmd.path == "echo"
        assert cmd.env == {}
        assert cmd.dir is None
        assert cmd.tty is False

    def test_init_with_options(self):
        sprite = MagicMock()
        cmd = Cmd(
            sprite,
            ["bash", "-c", "echo test"],
            env={"FOO": "bar"},
            cwd="/home/user",
            tty=True,
            tty_rows=40,
            tty_cols=120,
            timeout=30.0,
        )

        assert cmd.env == {"FOO": "bar"}
        assert cmd.dir == "/home/user"
        assert cmd.tty is True
        assert cmd.tty_rows == 40
        assert cmd.tty_cols == 120
        assert cmd.timeout == 30.0

    def test_init_with_session_id(self):
        sprite = MagicMock()
        cmd = Cmd(sprite, [], session_id="sess_123")

        assert cmd.session_id == "sess_123"
        assert cmd.args == []
        assert cmd.path == ""

    def test_set_tty(self):
        sprite = MagicMock()
        cmd = Cmd(sprite, ["bash"])

        assert cmd.tty is False
        cmd.set_tty(True)
        assert cmd.tty is True

    def test_set_tty_after_started_raises(self):
        sprite = MagicMock()
        cmd = Cmd(sprite, ["bash"])
        cmd._started = True

        with pytest.raises(RuntimeError, match="cannot set TTY after process started"):
            cmd.set_tty(True)

    def test_set_tty_size(self):
        sprite = MagicMock()
        cmd = Cmd(sprite, ["bash"])

        cmd.set_tty_size(50, 200)
        assert cmd.tty_rows == 50
        assert cmd.tty_cols == 200

    def test_exit_code_before_run(self):
        sprite = MagicMock()
        cmd = Cmd(sprite, ["echo"])

        assert cmd.exit_code == -1

    def test_with_stdin_stdout_stderr(self):
        sprite = MagicMock()
        stdin = io.BytesIO(b"input data")
        stdout = io.BytesIO()
        stderr = io.BytesIO()

        cmd = Cmd(
            sprite,
            ["cat"],
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )

        assert cmd.stdin is stdin
        assert cmd.stdout is stdout
        assert cmd.stderr is stderr


class TestAsyncCmd:
    def test_init_basic(self):
        sprite = MagicMock()
        cmd = AsyncCmd(sprite, ["echo", "hello"])

        assert cmd.sprite is sprite
        assert cmd.args == ["echo", "hello"]
        assert cmd.path == "echo"
        assert cmd.env == {}
        assert cmd.dir is None
        assert cmd.tty is False

    def test_init_with_options(self):
        sprite = MagicMock()
        cmd = AsyncCmd(
            sprite,
            ["bash", "-c", "echo test"],
            env={"FOO": "bar"},
            cwd="/home/user",
            tty=True,
            tty_rows=40,
            tty_cols=120,
            timeout=30.0,
        )

        assert cmd.env == {"FOO": "bar"}
        assert cmd.dir == "/home/user"
        assert cmd.tty is True
        assert cmd.tty_rows == 40
        assert cmd.tty_cols == 120
        assert cmd.timeout == 30.0

    def test_set_tty(self):
        sprite = MagicMock()
        cmd = AsyncCmd(sprite, ["bash"])

        assert cmd.tty is False
        cmd.set_tty(True)
        assert cmd.tty is True

    def test_set_tty_after_started_raises(self):
        sprite = MagicMock()
        cmd = AsyncCmd(sprite, ["bash"])
        cmd._started = True

        with pytest.raises(RuntimeError, match="cannot set TTY after process started"):
            cmd.set_tty(True)


class TestExitError:
    def test_basic(self):
        err = ExitError(1)
        assert err.exit_code() == 1
        assert err.returncode == 1
        assert str(err) == "exit status 1"

    def test_with_output(self):
        err = ExitError(1, stdout=b"output", stderr=b"error")
        assert err.stdout == b"output"
        assert err.stderr == b"error"

    def test_with_custom_message(self):
        err = ExitError(1, message="Command failed")
        assert str(err) == "Command failed"


class TestTimeoutError:
    def test_basic(self):
        err = TimeoutError()
        assert str(err) == "command timed out"

    def test_with_timeout_value(self):
        err = TimeoutError("command timed out after 30s", timeout=30.0)
        assert err.timeout == 30.0
