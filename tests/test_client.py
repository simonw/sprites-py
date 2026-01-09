"""Tests for SpritesClient and AsyncSpritesClient."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from sprites import AsyncSpritesClient, SpritesClient, SpriteConfig, APIError


class TestSpritesClient:
    def test_init_defaults(self):
        client = SpritesClient("my-token")
        assert client.token == "my-token"
        assert client.base_url == "https://api.sprites.dev"
        assert client.timeout == 30.0

    def test_init_custom_values(self):
        client = SpritesClient(
            "my-token",
            base_url="https://custom.api.dev/",
            timeout=60.0,
        )
        assert client.base_url == "https://custom.api.dev"  # Trailing slash stripped
        assert client.timeout == 60.0

    def test_sprite_returns_sprite_handle(self):
        client = SpritesClient("my-token")
        sprite = client.sprite("test-sprite")
        assert sprite.name == "test-sprite"
        assert sprite.client is client

    def test_context_manager(self):
        with SpritesClient("my-token") as client:
            assert client.token == "my-token"
        # Client should be closed after context exits

    @patch("httpx.Client.post")
    def test_create_sprite_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"name": "new-sprite"}
        mock_post.return_value = mock_response

        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.post = mock_post

        sprite = client.create_sprite("new-sprite")
        assert sprite.name == "new-sprite"
        mock_post.assert_called_once()

    @patch("httpx.Client.post")
    def test_create_sprite_with_config(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"name": "new-sprite"}
        mock_post.return_value = mock_response

        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.post = mock_post

        config = SpriteConfig(ram_mb=512, cpus=2)
        sprite = client.create_sprite("new-sprite", config)

        assert sprite.name == "new-sprite"
        call_args = mock_post.call_args
        assert call_args[1]["json"]["config"]["ram_mb"] == 512
        assert call_args[1]["json"]["config"]["cpus"] == 2

    @patch("httpx.Client.post")
    def test_create_sprite_failure(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.post = mock_post

        with pytest.raises(APIError) as exc_info:
            client.create_sprite("bad-sprite")
        assert exc_info.value.status_code == 400

    @patch("httpx.Client.get")
    def test_get_sprite_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "test-sprite",
            "id": "sp_123",
            "status": "running",
        }
        mock_get.return_value = mock_response

        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.get = mock_get

        sprite = client.get_sprite("test-sprite")
        assert sprite.name == "test-sprite"
        assert sprite.info is not None
        assert sprite.info.id == "sp_123"
        assert sprite.info.status == "running"

    @patch("httpx.Client.get")
    def test_get_sprite_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.get = mock_get

        with pytest.raises(APIError) as exc_info:
            client.get_sprite("nonexistent")
        assert exc_info.value.status_code == 404

    @patch("httpx.Client.delete")
    def test_delete_sprite_success(self, mock_delete):
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_delete.return_value = mock_response

        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.delete = mock_delete

        client.delete_sprite("test-sprite")  # Should not raise
        mock_delete.assert_called_once()

    @patch("httpx.Client.get")
    def test_list_sprites_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sprites": [
                {"name": "sprite1", "id": "sp_1"},
                {"name": "sprite2", "id": "sp_2"},
            ]
        }
        mock_get.return_value = mock_response

        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.get = mock_get

        sprites = client.list_sprites()
        assert len(sprites) == 2
        assert sprites[0].name == "sprite1"
        assert sprites[1].name == "sprite2"

    @patch("httpx.Client.get")
    def test_list_sprites_with_prefix(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sprites": []}
        mock_get.return_value = mock_response

        client = SpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.get = mock_get

        client.list_sprites(prefix="test-")
        call_args = mock_get.call_args
        assert call_args[1]["params"]["prefix"] == "test-"


class TestAsyncSpritesClient:
    def test_init_defaults(self):
        client = AsyncSpritesClient("my-token")
        assert client.token == "my-token"
        assert client.base_url == "https://api.sprites.dev"
        assert client.timeout == 30.0

    def test_init_custom_values(self):
        client = AsyncSpritesClient(
            "my-token",
            base_url="https://custom.api.dev/",
            timeout=60.0,
        )
        assert client.base_url == "https://custom.api.dev"
        assert client.timeout == 60.0

    def test_sprite_returns_async_sprite_handle(self):
        client = AsyncSpritesClient("my-token")
        sprite = client.sprite("test-sprite")
        assert sprite.name == "test-sprite"
        assert sprite.client is client

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        async with AsyncSpritesClient("my-token") as client:
            assert client.token == "my-token"
        # Client should be closed after context exits

    @pytest.mark.asyncio
    async def test_create_sprite_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"name": "new-sprite"}

        client = AsyncSpritesClient("my-token")
        client._http_client = MagicMock()
        client._http_client.post = MagicMock(return_value=mock_response)
        # Make the mock awaitable
        async def mock_post(*args, **kwargs):
            return mock_response
        client._http_client.post = mock_post

        sprite = await client.create_sprite("new-sprite")
        assert sprite.name == "new-sprite"

    @pytest.mark.asyncio
    async def test_create_sprite_failure(self):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"

        client = AsyncSpritesClient("my-token")
        async def mock_post(*args, **kwargs):
            return mock_response
        client._http_client = MagicMock()
        client._http_client.post = mock_post

        with pytest.raises(APIError) as exc_info:
            await client.create_sprite("bad-sprite")
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_sprite_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "test-sprite",
            "id": "sp_123",
            "status": "running",
        }

        client = AsyncSpritesClient("my-token")
        async def mock_get(*args, **kwargs):
            return mock_response
        client._http_client = MagicMock()
        client._http_client.get = mock_get

        sprite = await client.get_sprite("test-sprite")
        assert sprite.name == "test-sprite"
        assert sprite.info is not None
        assert sprite.info.id == "sp_123"

    @pytest.mark.asyncio
    async def test_get_sprite_not_found(self):
        mock_response = MagicMock()
        mock_response.status_code = 404

        client = AsyncSpritesClient("my-token")
        async def mock_get(*args, **kwargs):
            return mock_response
        client._http_client = MagicMock()
        client._http_client.get = mock_get

        with pytest.raises(APIError) as exc_info:
            await client.get_sprite("nonexistent")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_sprite_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 204

        client = AsyncSpritesClient("my-token")
        async def mock_delete(*args, **kwargs):
            return mock_response
        client._http_client = MagicMock()
        client._http_client.delete = mock_delete

        await client.delete_sprite("test-sprite")  # Should not raise

    @pytest.mark.asyncio
    async def test_list_sprites_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sprites": [
                {"name": "sprite1", "id": "sp_1"},
                {"name": "sprite2", "id": "sp_2"},
            ]
        }

        client = AsyncSpritesClient("my-token")
        async def mock_get(*args, **kwargs):
            return mock_response
        client._http_client = MagicMock()
        client._http_client.get = mock_get

        sprites = await client.list_sprites()
        assert len(sprites) == 2
        assert sprites[0].name == "sprite1"
