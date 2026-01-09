"""WebSocket protocol handler for Sprites command execution."""

from __future__ import annotations

import asyncio
import json
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Callable, Protocol
from urllib.parse import urlencode

import websockets
from websockets.exceptions import ConnectionClosed

if TYPE_CHECKING:
    from sprites.async_exec import AsyncCmd
    from sprites.exec import Cmd


class StreamID(IntEnum):
    """Stream identifiers for the binary protocol."""

    STDIN = 0
    STDOUT = 1
    STDERR = 2
    EXIT = 3
    STDIN_EOF = 4


# WebSocket keepalive timeouts (matching Go SDK)
WS_PING_INTERVAL = 15  # seconds
WS_PONG_WAIT = 45  # seconds


class CmdLike(Protocol):
    """Protocol for command-like objects (both sync Cmd and AsyncCmd)."""

    sprite: Any
    args: list[str]
    env: dict[str, str]
    dir: str | None
    stdin: Any
    stdout: Any
    stderr: Any
    tty: bool
    tty_rows: int
    tty_cols: int
    session_id: str | None
    _text_message_handler: Callable[[bytes], None] | None
    _capture_stdout: bool
    _capture_stderr: bool
    _stdout_data: bytes
    _stderr_data: bytes


def build_websocket_url(cmd: CmdLike) -> str:
    """Build the WebSocket URL with query parameters."""
    base_url = cmd.sprite.client.base_url

    # Convert HTTP(S) to WS(S)
    if base_url.startswith("https"):
        base_url = "wss" + base_url[5:]
    elif base_url.startswith("http"):
        base_url = "ws" + base_url[4:]

    # Build path
    if cmd.session_id:
        path = f"/v1/sprites/{cmd.sprite.name}/exec/{cmd.session_id}"
    else:
        path = f"/v1/sprites/{cmd.sprite.name}/exec"

    # Build query params
    params: list[tuple[str, str]] = []

    # Command args (only for new commands)
    if not cmd.session_id:
        for arg in cmd.args:
            params.append(("cmd", arg))
        if cmd.args:
            params.append(("path", cmd.args[0]))

    # Environment variables
    for key, value in cmd.env.items():
        params.append(("env", f"{key}={value}"))

    # Working directory
    if cmd.dir:
        params.append(("dir", cmd.dir))

    # TTY settings
    if cmd.tty:
        params.append(("tty", "true"))
        params.append(("rows", str(cmd.tty_rows)))
        params.append(("cols", str(cmd.tty_cols)))

    # Stdin indicator - always true for now
    params.append(("stdin", "true"))

    query = urlencode(params)
    return f"{base_url}{path}?{query}"


class WSCommand:
    """WebSocket command execution handler."""

    def __init__(self, cmd: CmdLike):
        """Initialize a WebSocket command handler.

        Args:
            cmd: The Cmd or AsyncCmd instance to execute.
        """
        self.cmd = cmd
        self.ws: websockets.WebSocketClientProtocol | None = None
        self.exit_code = -1
        self.started = False
        self.done = False
        self._is_attach = cmd.session_id is not None
        self.text_message_handler: Callable[[bytes], None] | None = None
        self._stdout_buffer: bytearray = bytearray()
        self._stderr_buffer: bytearray = bytearray()
        self._io_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the WebSocket connection."""
        if self.started:
            raise RuntimeError("already started")
        self.started = True

        url = build_websocket_url(self.cmd)
        headers = {"Authorization": f"Bearer {self.cmd.sprite.client.token}"}

        self.ws = await websockets.connect(
            url,
            additional_headers=headers,
            ping_interval=WS_PING_INTERVAL,
            ping_timeout=WS_PONG_WAIT,
            max_size=10 * 1024 * 1024,  # 10MB max message size
        )

        # When attaching to an existing session, wait for session_info to determine TTY mode
        if self._is_attach:
            await self._wait_for_session_info()

        # Start I/O loop in background
        self._io_task = asyncio.create_task(self._run_io())

    async def _wait_for_session_info(self) -> None:
        """Wait for session_info message when attaching."""
        if self.ws is None:
            raise RuntimeError("WebSocket not connected")

        try:
            async with asyncio.timeout(10):
                async for message in self.ws:
                    if isinstance(message, str):
                        try:
                            info = json.loads(message)
                            if info.get("type") == "session_info":
                                self.cmd.tty = info.get("tty", False)
                                if self.text_message_handler:
                                    self.text_message_handler(message.encode())
                                return
                        except json.JSONDecodeError:
                            pass
                        # Pass other text messages to handler
                        if self.text_message_handler:
                            self.text_message_handler(message.encode())
        except asyncio.TimeoutError:
            raise RuntimeError("timeout waiting for session_info") from None

    async def _run_io(self) -> None:
        """Main I/O loop."""
        if self.ws is None:
            return

        try:
            # Handle stdin in background if provided
            stdin_task: asyncio.Task[None] | None = None
            if self.cmd.stdin is not None:
                stdin_task = asyncio.create_task(self._copy_stdin())
            else:
                # Send EOF immediately if no stdin
                await self._send_stdin_eof()

            # Process incoming messages
            async for message in self.ws:
                await self._handle_message(message)

        except ConnectionClosed as e:
            # Normal closure - extract exit code from close code if available
            if e.code == 1000:  # Normal closure
                if self.exit_code < 0:
                    self.exit_code = 0
        except Exception:
            pass
        finally:
            self.done = True
            if stdin_task is not None:
                stdin_task.cancel()
                try:
                    await stdin_task
                except asyncio.CancelledError:
                    pass

    async def _handle_message(self, message: str | bytes) -> None:
        """Handle incoming WebSocket message."""
        if self.cmd.tty:
            # TTY mode
            if isinstance(message, str):
                # Text message - control/notification
                if self.text_message_handler:
                    self.text_message_handler(message.encode())
            else:
                # Binary - raw terminal data
                self._stdout_buffer.extend(message)
                if self.cmd.stdout is not None:
                    self.cmd.stdout.write(message)
        else:
            # Non-TTY mode - stream-based protocol
            if isinstance(message, str):
                # Text messages are control/notifications
                if self.text_message_handler:
                    self.text_message_handler(message.encode())
                return

            if not message:
                return

            stream_id = message[0]
            payload = message[1:]

            if stream_id == StreamID.STDOUT:
                self._stdout_buffer.extend(payload)
                if self.cmd.stdout is not None:
                    self.cmd.stdout.write(payload)
            elif stream_id == StreamID.STDERR:
                self._stderr_buffer.extend(payload)
                if self.cmd.stderr is not None:
                    self.cmd.stderr.write(payload)
            elif stream_id == StreamID.EXIT:
                self.exit_code = payload[0] if payload else 0
                if self.ws:
                    await self.ws.close()

    async def _copy_stdin(self) -> None:
        """Copy data from stdin to WebSocket."""
        if self.cmd.stdin is None:
            return

        try:
            loop = asyncio.get_event_loop()
            while True:
                # Read stdin in executor to avoid blocking
                data = await loop.run_in_executor(None, self.cmd.stdin.read, 4096)
                if not data:
                    break
                await self._write_stdin(data)
            await self._send_stdin_eof()
        except Exception:
            pass

    async def _write_stdin(self, data: bytes) -> None:
        """Write data to stdin stream."""
        if self.ws is None:
            return

        if self.cmd.tty:
            await self.ws.send(data)
        else:
            message = bytes([StreamID.STDIN]) + data
            await self.ws.send(message)

    async def _send_stdin_eof(self) -> None:
        """Send stdin EOF marker."""
        if self.ws is None:
            return

        if not self.cmd.tty:
            await self.ws.send(bytes([StreamID.STDIN_EOF]))

    async def resize(self, cols: int, rows: int) -> None:
        """Send resize control message."""
        if not self.cmd.tty or self.ws is None:
            return
        msg = json.dumps({"type": "resize", "cols": cols, "rows": rows})
        await self.ws.send(msg)

    async def wait(self) -> int:
        """Wait for command to complete and return exit code."""
        if self._io_task is not None:
            await self._io_task
        return self.exit_code

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self.ws is not None:
            await self.ws.close()
            self.ws = None

    def get_stdout(self) -> bytes:
        """Get the accumulated stdout buffer."""
        return bytes(self._stdout_buffer)

    def get_stderr(self) -> bytes:
        """Get the accumulated stderr buffer."""
        return bytes(self._stderr_buffer)


async def run_ws_command(cmd: "Cmd") -> int:
    """Run a sync Cmd via WebSocket and return exit code.

    Args:
        cmd: The command to execute (sync Cmd from exec module).

    Returns:
        The exit code of the command.
    """
    ws_cmd = WSCommand(cmd)
    ws_cmd.text_message_handler = cmd._text_message_handler

    await ws_cmd.start()
    exit_code = await ws_cmd.wait()

    # Copy buffered output if cmd is capturing
    if cmd._capture_stdout:
        cmd._stdout_data = ws_cmd.get_stdout()
    if cmd._capture_stderr:
        cmd._stderr_data = ws_cmd.get_stderr()

    return exit_code


async def run_ws_command_async(cmd: "AsyncCmd") -> int:
    """Run an AsyncCmd via WebSocket and return exit code.

    Args:
        cmd: The async command to execute (AsyncCmd from async_exec module).

    Returns:
        The exit code of the command.
    """
    ws_cmd = WSCommand(cmd)
    ws_cmd.text_message_handler = cmd._text_message_handler

    await ws_cmd.start()
    exit_code = await ws_cmd.wait()

    # Copy buffered output if cmd is capturing
    if cmd._capture_stdout:
        cmd._stdout_data = ws_cmd.get_stdout()
    if cmd._capture_stderr:
        cmd._stderr_data = ws_cmd.get_stderr()

    return exit_code
