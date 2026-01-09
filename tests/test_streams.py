"""Tests for sync and async stream classes."""

import pytest

from sprites.types import StreamMessage, ServiceLogEvent
from sprites.session import KillStream
from sprites.services import ServiceStream
from sprites.async_checkpoint import AsyncCheckpointStream, AsyncRestoreStream
from sprites.async_session import AsyncKillStream
from sprites.async_services import AsyncServiceStream


class TestKillStream:
    def test_iteration(self):
        messages = [
            StreamMessage(type="info", data="Sending signal"),
            StreamMessage(type="info", data="Process terminated"),
        ]
        stream = KillStream(messages)

        result = list(stream)
        assert len(result) == 2
        assert result[0].type == "info"
        assert result[0].data == "Sending signal"

    def test_context_manager(self):
        messages = [StreamMessage(type="done")]
        with KillStream(messages) as stream:
            result = list(stream)
            assert len(result) == 1

    def test_process_all(self):
        messages = [
            StreamMessage(type="info", data="msg1"),
            StreamMessage(type="info", data="msg2"),
        ]
        stream = KillStream(messages)

        collected = []
        stream.process_all(lambda m: collected.append(m.data))

        assert collected == ["msg1", "msg2"]


class TestServiceStream:
    def test_iteration(self):
        events = [
            ServiceLogEvent(type="started"),
            ServiceLogEvent(type="stdout", data="Hello"),
            ServiceLogEvent(type="exit", exit_code=0),
        ]
        stream = ServiceStream(events)

        result = list(stream)
        assert len(result) == 3
        assert result[0].type == "started"
        assert result[1].data == "Hello"
        assert result[2].exit_code == 0

    def test_context_manager(self):
        events = [ServiceLogEvent(type="done")]
        with ServiceStream(events) as stream:
            result = list(stream)
            assert len(result) == 1


class TestAsyncCheckpointStream:
    @pytest.mark.asyncio
    async def test_async_iteration(self):
        messages = [
            StreamMessage(type="info", data="Creating checkpoint"),
            StreamMessage(type="done"),
        ]
        stream = AsyncCheckpointStream(messages)

        result = []
        async for msg in stream:
            result.append(msg)

        assert len(result) == 2
        assert result[0].type == "info"
        assert result[1].type == "done"

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        messages = [StreamMessage(type="done")]
        async with AsyncCheckpointStream(messages) as stream:
            result = []
            async for msg in stream:
                result.append(msg)
            assert len(result) == 1


class TestAsyncRestoreStream:
    @pytest.mark.asyncio
    async def test_async_iteration(self):
        messages = [
            StreamMessage(type="info", data="Restoring"),
            StreamMessage(type="done"),
        ]
        stream = AsyncRestoreStream(messages)

        result = []
        async for msg in stream:
            result.append(msg)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        messages = [StreamMessage(type="done")]
        async with AsyncRestoreStream(messages) as stream:
            result = []
            async for msg in stream:
                result.append(msg)
            assert len(result) == 1


class TestAsyncKillStream:
    @pytest.mark.asyncio
    async def test_async_iteration(self):
        messages = [
            StreamMessage(type="info", data="Sending signal"),
            StreamMessage(type="done"),
        ]
        stream = AsyncKillStream(messages)

        result = []
        async for msg in stream:
            result.append(msg)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_process_all(self):
        messages = [
            StreamMessage(type="info", data="msg1"),
            StreamMessage(type="info", data="msg2"),
        ]
        stream = AsyncKillStream(messages)

        collected = []
        await stream.process_all(lambda m: collected.append(m.data))

        assert collected == ["msg1", "msg2"]


class TestAsyncServiceStream:
    @pytest.mark.asyncio
    async def test_async_iteration(self):
        events = [
            ServiceLogEvent(type="started"),
            ServiceLogEvent(type="stdout", data="Hello"),
            ServiceLogEvent(type="exit", exit_code=0),
        ]
        stream = AsyncServiceStream(events)

        result = []
        async for event in stream:
            result.append(event)

        assert len(result) == 3
        assert result[0].type == "started"
        assert result[1].data == "Hello"
        assert result[2].exit_code == 0

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        events = [ServiceLogEvent(type="done")]
        async with AsyncServiceStream(events) as stream:
            result = []
            async for event in stream:
                result.append(event)
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_process_all(self):
        events = [
            ServiceLogEvent(type="stdout", data="line1"),
            ServiceLogEvent(type="stdout", data="line2"),
        ]
        stream = AsyncServiceStream(events)

        collected = []
        await stream.process_all(lambda e: collected.append(e.data))

        assert collected == ["line1", "line2"]
