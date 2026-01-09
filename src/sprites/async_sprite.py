"""AsyncSprite class representing a remote sprite instance with async operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, AsyncIterator, BinaryIO

from sprites.async_exec import AsyncCmd, AsyncCompletedProcess, async_run
from sprites.types import SpriteInfo

if TYPE_CHECKING:
    from sprites.client import AsyncSpritesClient
    from sprites.types import Checkpoint, NetworkPolicy, ServiceWithState, Session


@dataclass
class AsyncSprite:
    """Represents a sprite instance with async operations."""

    name: str
    client: AsyncSpritesClient
    info: SpriteInfo | None = None

    def command(
        self,
        *args: str,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        stdin: BinaryIO | None = None,
        stdout: BinaryIO | None = None,
        stderr: BinaryIO | None = None,
        tty: bool = False,
        tty_rows: int = 24,
        tty_cols: int = 80,
        timeout: float | None = None,
    ) -> AsyncCmd:
        """Create an async command to run on this sprite.

        Args:
            *args: Command and arguments (first arg is the command name).
            env: Environment variables to set.
            cwd: Working directory for the command.
            stdin: File-like object to read stdin from.
            stdout: File-like object to write stdout to.
            stderr: File-like object to write stderr to.
            tty: Enable TTY/pseudo-terminal mode.
            tty_rows: Terminal height (rows).
            tty_cols: Terminal width (columns).
            timeout: Command timeout in seconds.

        Returns:
            An AsyncCmd object that can be used to execute the command.
        """
        return AsyncCmd(
            sprite=self,
            args=list(args),
            env=env,
            cwd=cwd,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            tty=tty,
            tty_rows=tty_rows,
            tty_cols=tty_cols,
            timeout=timeout,
        )

    async def run(
        self,
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
        """Run a command and wait for completion asynchronously.

        Args:
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
        """
        return await async_run(
            self,
            *args,
            capture_output=capture_output,
            timeout=timeout,
            check=check,
            env=env,
            cwd=cwd,
            tty=tty,
            tty_rows=tty_rows,
            tty_cols=tty_cols,
        )

    def attach_session(
        self,
        session_id: str,
        *,
        stdin: BinaryIO | None = None,
        stdout: BinaryIO | None = None,
        stderr: BinaryIO | None = None,
        timeout: float | None = None,
    ) -> AsyncCmd:
        """Attach to an existing session asynchronously.

        Args:
            session_id: The ID of the session to attach to.
            stdin: File-like object to read stdin from.
            stdout: File-like object to write stdout to.
            stderr: File-like object to write stderr to.
            timeout: Command timeout in seconds.

        Returns:
            An AsyncCmd object for the attached session.
        """
        return AsyncCmd(
            sprite=self,
            args=[],
            session_id=session_id,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            timeout=timeout,
        )

    async def delete(self) -> None:
        """Delete this sprite."""
        await self.client.delete_sprite(self.name)

    async def destroy(self) -> None:
        """Destroy this sprite (alias for delete)."""
        await self.delete()

    # Checkpoint operations

    async def list_checkpoints(self, history_filter: str = "") -> list[Checkpoint]:
        """List all checkpoints for this sprite.

        Args:
            history_filter: Optional filter for checkpoint history.

        Returns:
            List of checkpoint objects.
        """
        from sprites.async_checkpoint import async_list_checkpoints

        return await async_list_checkpoints(self, history_filter)

    async def get_checkpoint(self, checkpoint_id: str) -> Checkpoint:
        """Get a specific checkpoint.

        Args:
            checkpoint_id: The ID of the checkpoint.

        Returns:
            The checkpoint object.
        """
        from sprites.async_checkpoint import async_get_checkpoint

        return await async_get_checkpoint(self, checkpoint_id)

    async def create_checkpoint(self, comment: str = "") -> AsyncIterator:
        """Create a new checkpoint.

        Args:
            comment: Optional comment for the checkpoint.

        Returns:
            An async iterator of checkpoint creation messages.
        """
        from sprites.async_checkpoint import async_create_checkpoint

        return await async_create_checkpoint(self, comment)

    async def restore_checkpoint(self, checkpoint_id: str) -> AsyncIterator:
        """Restore a checkpoint.

        Args:
            checkpoint_id: The ID of the checkpoint to restore.

        Returns:
            An async iterator of restore messages.
        """
        from sprites.async_checkpoint import async_restore_checkpoint

        return await async_restore_checkpoint(self, checkpoint_id)

    # Network policy operations

    async def get_network_policy(self) -> NetworkPolicy:
        """Get the current network policy.

        Returns:
            The network policy for this sprite.
        """
        from sprites.async_policy import async_get_network_policy

        return await async_get_network_policy(self)

    async def update_network_policy(self, policy: NetworkPolicy) -> None:
        """Update the network policy.

        Args:
            policy: The new network policy to set.
        """
        from sprites.async_policy import async_update_network_policy

        await async_update_network_policy(self, policy)

    # Session operations

    async def list_sessions(self) -> list[Session]:
        """List active sessions for this sprite.

        Returns:
            List of active sessions.
        """
        from sprites.async_session import async_list_sessions

        return await async_list_sessions(self)

    async def kill_session(
        self,
        session_id: str,
        signal: str = "SIGTERM",
        timeout: int = 10,
    ) -> AsyncIterator:
        """Kill a session.

        Args:
            session_id: The ID of the session to kill.
            signal: The signal to send (default: SIGTERM).
            timeout: Timeout in seconds before force kill (default: 10).

        Returns:
            An async iterator of kill progress messages.
        """
        from sprites.async_session import async_kill_session

        return await async_kill_session(self, session_id, signal, timeout)

    # Service operations

    async def list_services(self) -> list[ServiceWithState]:
        """List all services for this sprite.

        Returns:
            List of services with their state.
        """
        from sprites.async_services import async_list_services

        return await async_list_services(self)

    async def get_service(self, name: str) -> ServiceWithState:
        """Get a specific service.

        Args:
            name: The name of the service.

        Returns:
            The service with its state.
        """
        from sprites.async_services import async_get_service

        return await async_get_service(self, name)

    async def create_service(
        self,
        name: str,
        cmd: str,
        args: list[str] | None = None,
        needs: list[str] | None = None,
        http_port: int | None = None,
        duration: float | None = None,
    ) -> AsyncIterator:
        """Create or update a service.

        Args:
            name: The name of the service.
            cmd: The command to run.
            args: Command arguments.
            needs: Services this service depends on.
            http_port: HTTP port the service listens on.
            duration: Monitoring duration in seconds.

        Returns:
            An async iterator of service log events.
        """
        from sprites.async_services import async_create_service

        return await async_create_service(self, name, cmd, args, needs, http_port, duration)

    async def delete_service(self, name: str) -> None:
        """Delete a service.

        Args:
            name: The name of the service.
        """
        from sprites.async_services import async_delete_service

        await async_delete_service(self, name)

    async def start_service(
        self,
        name: str,
        duration: float | None = None,
    ) -> AsyncIterator:
        """Start a service.

        Args:
            name: The name of the service.
            duration: Monitoring duration in seconds.

        Returns:
            An async iterator of service log events.
        """
        from sprites.async_services import async_start_service

        return await async_start_service(self, name, duration)

    async def stop_service(
        self,
        name: str,
        timeout: float | None = None,
    ) -> AsyncIterator:
        """Stop a service.

        Args:
            name: The name of the service.
            timeout: Timeout in seconds before force stop.

        Returns:
            An async iterator of service log events.
        """
        from sprites.async_services import async_stop_service

        return await async_stop_service(self, name, timeout)

    async def signal_service(self, name: str, signal: str) -> None:
        """Send a signal to a running service.

        Args:
            name: The name of the service.
            signal: The signal to send (e.g., "SIGTERM", "SIGHUP").
        """
        from sprites.async_services import async_signal_service

        await async_signal_service(self, name, signal)
