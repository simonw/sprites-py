"""Async command execution for Sprites."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, BinaryIO, Callable

from sprites.exceptions import ExitError, TimeoutError

if TYPE_CHECKING:
    from sprites.async_sprite import AsyncSprite


@dataclass
class AsyncCompletedProcess:
    """Result of a completed async command (mirrors subprocess.CompletedProcess)."""

    args: list[str]
    returncode: int
    stdout: bytes | None = None
    stderr: bytes | None = None


class AsyncCmd:
    """Represents an async command to be run on a sprite.

    This class provides a native async interface for command execution.
    """

    def __init__(
        self,
        sprite: AsyncSprite,
        args: list[str],
        *,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        stdin: BinaryIO | None = None,
        stdout: BinaryIO | None = None,
        stderr: BinaryIO | None = None,
        tty: bool = False,
        tty_rows: int = 24,
        tty_cols: int = 80,
        session_id: str | None = None,
        timeout: float | None = None,
    ):
        """Initialize an async command.

        Args:
            sprite: The sprite to execute the command on.
            args: Command and arguments (args[0] is the command name).
            env: Environment variables to set.
            cwd: Working directory for the command.
            stdin: File-like object to read stdin from.
            stdout: File-like object to write stdout to.
            stderr: File-like object to write stderr to.
            tty: Enable TTY/pseudo-terminal mode.
            tty_rows: Terminal height (rows).
            tty_cols: Terminal width (columns).
            session_id: Attach to existing session instead of creating new one.
            timeout: Command timeout in seconds.
        """
        self.sprite = sprite
        self.args = args
        self.path = args[0] if args else ""
        self.env = env or {}
        self.dir = cwd
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.tty = tty
        self.tty_rows = tty_rows
        self.tty_cols = tty_cols
        self.session_id = session_id
        self.timeout = timeout

        # Internal state
        self._started = False
        self._finished = False
        self._exit_code = -1
        self._text_message_handler: Callable[[bytes], None] | None = None
        self._capture_stdout = False
        self._capture_stderr = False
        self._stdout_data: bytes = b""
        self._stderr_data: bytes = b""

    def set_tty(self, enable: bool) -> None:
        """Enable or disable TTY mode."""
        if self._started:
            raise RuntimeError("cannot set TTY after process started")
        self.tty = enable

    def set_tty_size(self, rows: int, cols: int) -> None:
        """Set terminal size."""
        self.tty_rows = rows
        self.tty_cols = cols

    async def run(self) -> None:
        """Start command and wait for completion asynchronously.

        Raises:
            ExitError: If the command exits with non-zero status.
            TimeoutError: If the command times out.
        """
        code = await self._run_async()
        if code != 0:
            raise ExitError(code, self._stdout_data, self._stderr_data)

    async def output(self) -> bytes:
        """Run command and return stdout asynchronously.

        Returns:
            The stdout output from the command.

        Raises:
            ExitError: If the command exits with non-zero status.
            TimeoutError: If the command times out.
            RuntimeError: If stdout is already set.
        """
        if self.stdout is not None:
            raise RuntimeError("stdout already set")

        self._capture_stdout = True
        code = await self._run_async()

        if code != 0:
            raise ExitError(code, self._stdout_data, self._stderr_data)

        return self._stdout_data

    async def combined_output(self) -> bytes:
        """Run command and return combined stdout/stderr asynchronously.

        Returns:
            The combined stdout and stderr output.

        Raises:
            ExitError: If the command exits with non-zero status.
            TimeoutError: If the command times out.
            RuntimeError: If stdout or stderr is already set.
        """
        if self.stdout is not None:
            raise RuntimeError("stdout already set")
        if self.stderr is not None:
            raise RuntimeError("stderr already set")

        self._capture_stdout = True
        self._capture_stderr = True
        code = await self._run_async()

        # For combined output, merge stdout and stderr
        combined = self._stdout_data + self._stderr_data

        if code != 0:
            raise ExitError(code, combined, b"")

        return combined

    async def _run_async(self) -> int:
        """Run the command asynchronously and return exit code."""
        if self._started:
            raise RuntimeError("command already started")
        self._started = True

        try:
            from sprites.websocket import run_ws_command_async

            if self.timeout is not None and self.timeout > 0:
                try:
                    async with asyncio.timeout(self.timeout):
                        return await run_ws_command_async(self)
                except asyncio.TimeoutError:
                    raise TimeoutError(
                        f"command timed out after {self.timeout}s", timeout=self.timeout
                    ) from None
            else:
                return await run_ws_command_async(self)
        finally:
            self._finished = True

    @property
    def exit_code(self) -> int:
        """Return exit code or -1 if not finished."""
        return self._exit_code


async def async_run(
    sprite: AsyncSprite,
    *args: str,
    capture_output: bool = False,
    timeout: float | None = None,
    check: bool = False,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
    tty: bool = False,
    tty_rows: int = 24,
    tty_cols: int = 80,
) -> AsyncCompletedProcess:
    """Run a command on the sprite asynchronously.

    Args:
        sprite: The sprite to execute on.
        *args: Command and arguments.
        capture_output: Capture stdout and stderr.
        timeout: Timeout in seconds.
        check: Raise ExitError if command returns non-zero.
        env: Environment variables.
        cwd: Working directory.
        tty: Enable TTY mode.
        tty_rows: Terminal rows.
        tty_cols: Terminal columns.

    Returns:
        AsyncCompletedProcess with results.

    Raises:
        ExitError: If check=True and command returns non-zero.
        TimeoutError: If command times out.
    """
    cmd = AsyncCmd(
        sprite,
        list(args),
        env=env,
        cwd=cwd,
        tty=tty,
        tty_rows=tty_rows,
        tty_cols=tty_cols,
        timeout=timeout,
    )

    if capture_output:
        cmd._capture_stdout = True
        cmd._capture_stderr = True

    code = await cmd._run_async()

    result = AsyncCompletedProcess(
        args=list(args),
        returncode=code,
        stdout=cmd._stdout_data if capture_output else None,
        stderr=cmd._stderr_data if capture_output else None,
    )

    if check and code != 0:
        raise ExitError(code, result.stdout or b"", result.stderr or b"")

    return result
