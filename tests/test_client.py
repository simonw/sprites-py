"""Tests for SpritesClient and AsyncSpritesClient."""

from unittest.mock import MagicMock, AsyncMock

import pytest

from sprites import AsyncSpritesClient, SpritesClient, SpriteConfig, APIError


# Shared test data
CLIENT_INIT_CASES = [
    ("defaults", "my-token", {}, "https://api.sprites.dev", 30.0),
    ("custom", "my-token", {"base_url": "https://custom.api.dev/", "timeout": 60.0},
     "https://custom.api.dev", 60.0),
]


def make_mock_response(status_code: int, json_data: dict | None = None, text: str = ""):
    """Create a mock HTTP response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = text
    if json_data is not None:
        mock.json.return_value = json_data
    return mock


# Parametrized tests for initialization (shared between sync/async)
@pytest.mark.parametrize("name,token,kwargs,expected_url,expected_timeout", CLIENT_INIT_CASES)
class TestClientInit:
    def test_sync_client_init(self, name, token, kwargs, expected_url, expected_timeout):
        client = SpritesClient(token, **kwargs)
        assert client.token == token
        assert client.base_url == expected_url
        assert client.timeout == expected_timeout

    def test_async_client_init(self, name, token, kwargs, expected_url, expected_timeout):
        client = AsyncSpritesClient(token, **kwargs)
        assert client.token == token
        assert client.base_url == expected_url
        assert client.timeout == expected_timeout


class TestSpritesClient:
    def test_sprite_returns_sprite_handle(self):
        client = SpritesClient("my-token")
        sprite = client.sprite("test-sprite")
        assert sprite.name == "test-sprite"
        assert sprite.client is client

    def test_context_manager(self):
        with SpritesClient("my-token") as client:
            assert client.token == "my-token"

    def test_create_sprite_success(self):
        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.post.return_value = make_mock_response(201, {"name": "new-sprite"})

        sprite = client.create_sprite("new-sprite")
        assert sprite.name == "new-sprite"

    def test_create_sprite_with_config(self):
        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.post.return_value = make_mock_response(201, {"name": "new-sprite"})

        config = SpriteConfig(ram_mb=512, cpus=2)
        sprite = client.create_sprite("new-sprite", config)

        assert sprite.name == "new-sprite"
        call_args = client._http_client.post.call_args
        assert call_args[1]["json"]["config"]["ram_mb"] == 512
        assert call_args[1]["json"]["config"]["cpus"] == 2

    def test_create_sprite_failure(self):
        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.post.return_value = make_mock_response(400, text="Bad request")

        with pytest.raises(APIError) as exc_info:
            client.create_sprite("bad-sprite")
        assert exc_info.value.status_code == 400

    def test_get_sprite_success(self):
        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.get.return_value = make_mock_response(
            200, {"name": "test-sprite", "id": "sp_123", "status": "running"}
        )

        sprite = client.get_sprite("test-sprite")
        assert sprite.name == "test-sprite"
        assert sprite.info is not None
        assert sprite.info.id == "sp_123"

    def test_get_sprite_not_found(self):
        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.get.return_value = make_mock_response(404)

        with pytest.raises(APIError) as exc_info:
            client.get_sprite("nonexistent")
        assert exc_info.value.status_code == 404

    def test_delete_sprite_success(self):
        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.delete.return_value = make_mock_response(204)

        client.delete_sprite("test-sprite")  # Should not raise

    def test_list_sprites_success(self):
        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.get.return_value = make_mock_response(
            200, {"sprites": [{"name": "sprite1"}, {"name": "sprite2"}]}
        )

        sprites = client.list_sprites()
        assert len(sprites) == 2
        assert sprites[0].name == "sprite1"

    def test_list_sprites_with_prefix(self):
        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.get.return_value = make_mock_response(200, {"sprites": []})

        client.list_sprites(prefix="test-")
        call_args = client._http_client.get.call_args
        assert call_args[1]["params"]["prefix"] == "test-"


class TestAsyncSpritesClient:
    def test_sprite_returns_async_sprite_handle(self):
        client = AsyncSpritesClient("my-token")
        sprite = client.sprite("test-sprite")
        assert sprite.name == "test-sprite"
        assert sprite.client is client

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        async with AsyncSpritesClient("my-token") as client:
            assert client.token == "my-token"

    @pytest.mark.asyncio
    async def test_create_sprite_success(self):
        client = AsyncSpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.post = AsyncMock(
            return_value=make_mock_response(201, {"name": "new-sprite"})
        )

        sprite = await client.create_sprite("new-sprite")
        assert sprite.name == "new-sprite"

    @pytest.mark.asyncio
    async def test_create_sprite_failure(self):
        client = AsyncSpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.post = AsyncMock(
            return_value=make_mock_response(400, text="Bad request")
        )

        with pytest.raises(APIError) as exc_info:
            await client.create_sprite("bad-sprite")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_sprite_success(self):
        client = AsyncSpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.get = AsyncMock(
            return_value=make_mock_response(
                200, {"name": "test-sprite", "id": "sp_123", "status": "running"}
            )
        )

        sprite = await client.get_sprite("test-sprite")
        assert sprite.name == "test-sprite"
        assert sprite.info is not None
        assert sprite.info.id == "sp_123"

    @pytest.mark.asyncio
    async def test_get_sprite_not_found(self):
        client = AsyncSpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.get = AsyncMock(return_value=make_mock_response(404))

        with pytest.raises(APIError) as exc_info:
            await client.get_sprite("nonexistent")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_sprite_success(self):
        client = AsyncSpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.delete = AsyncMock(return_value=make_mock_response(204))

        await client.delete_sprite("test-sprite")  # Should not raise

    @pytest.mark.asyncio
    async def test_list_sprites_success(self):
        client = AsyncSpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.get = AsyncMock(
            return_value=make_mock_response(
                200, {"sprites": [{"name": "sprite1"}, {"name": "sprite2"}]}
            )
        )

        sprites = await client.list_sprites()
        assert len(sprites) == 2
        assert sprites[0].name == "sprite1"
