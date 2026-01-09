"""Tests for sync and async stream classes."""

import pytest

from sprites.types import StreamMessage, ServiceLogEvent
from sprites.session import KillStream
from sprites.services import ServiceStream
from sprites.async_checkpoint import AsyncCheckpointStream, AsyncRestoreStream
from sprites.async_session import AsyncKillStream
from sprites.async_services import AsyncServiceStream


# Shared test data
def make_stream_messages():
    """Create test StreamMessage list."""
    return [
        StreamMessage(type="info", data="msg1"),
        StreamMessage(type="info", data="msg2"),
    ]


def make_service_events():
    """Create test ServiceLogEvent list."""
    return [
        ServiceLogEvent(type="started"),
        ServiceLogEvent(type="stdout", data="Hello"),
        ServiceLogEvent(type="exit", exit_code=0),
    ]


# Sync stream tests
class TestSyncStreams:
    """Tests for synchronous stream classes."""

    def test_kill_stream_iteration(self):
        messages = make_stream_messages()
        stream = KillStream(messages)

        result = list(stream)
        assert len(result) == 2
        assert result[0].data == "msg1"
        assert result[1].data == "msg2"

    def test_kill_stream_context_manager(self):
        with KillStream([StreamMessage(type="done")]) as stream:
            result = list(stream)
            assert len(result) == 1

    def test_kill_stream_process_all(self):
        messages = make_stream_messages()
        stream = KillStream(messages)

        collected = []
        stream.process_all(lambda m: collected.append(m.data))
        assert collected == ["msg1", "msg2"]

    def test_service_stream_iteration(self):
        events = make_service_events()
        stream = ServiceStream(events)

        result = list(stream)
        assert len(result) == 3
        assert result[0].type == "started"
        assert result[1].data == "Hello"
        assert result[2].exit_code == 0

    def test_service_stream_context_manager(self):
        with ServiceStream([ServiceLogEvent(type="done")]) as stream:
            result = list(stream)
            assert len(result) == 1


# Async stream tests - parameterized where possible
ASYNC_STREAM_MESSAGE_CLASSES = [
    pytest.param(AsyncCheckpointStream, id="checkpoint"),
    pytest.param(AsyncRestoreStream, id="restore"),
    pytest.param(AsyncKillStream, id="kill"),
]


@pytest.mark.parametrize("StreamClass", ASYNC_STREAM_MESSAGE_CLASSES)
class TestAsyncMessageStreams:
    """Tests for async streams that use StreamMessage."""

    @pytest.mark.asyncio
    async def test_async_iteration(self, StreamClass):
        messages = make_stream_messages()
        stream = StreamClass(messages)

        result = []
        async for msg in stream:
            result.append(msg)

        assert len(result) == 2
        assert result[0].data == "msg1"
        assert result[1].data == "msg2"

    @pytest.mark.asyncio
    async def test_async_context_manager(self, StreamClass):
        async with StreamClass([StreamMessage(type="done")]) as stream:
            result = []
            async for msg in stream:
                result.append(msg)
            assert len(result) == 1


class TestAsyncKillStreamExtra:
    """Additional tests specific to AsyncKillStream."""

    @pytest.mark.asyncio
    async def test_process_all(self):
        messages = make_stream_messages()
        stream = AsyncKillStream(messages)

        collected = []
        await stream.process_all(lambda m: collected.append(m.data))
        assert collected == ["msg1", "msg2"]


class TestAsyncServiceStream:
    """Tests for AsyncServiceStream."""

    @pytest.mark.asyncio
    async def test_async_iteration(self):
        events = make_service_events()
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
        async with AsyncServiceStream([ServiceLogEvent(type="done")]) as stream:
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
