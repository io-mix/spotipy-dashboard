import pytest
from unittest.mock import patch
from spotify_service import SpotifyService
from tests.conftest import MockSessionLocal


@pytest.mark.asyncio
async def test_sync_recently_played_idempotency(db_session):
    # setup mocks
    with patch(
        "spotify_service.AsyncSessionLocal", return_value=MockSessionLocal(db_session)
    ), patch("spotify_service.spotipy.Spotify") as mock_spotify, patch(
        "spotify_service.SpotifyOAuth"
    ) as mock_oauth:

        mock_oauth_instance = mock_oauth.return_value
        mock_oauth_instance.cache_handler.get_cached_token.return_value = {
            "access_token": "test"
        }

        service = SpotifyService()
        service.auth_manager = mock_oauth_instance

        # static api response
        api_data = {
            "items": [
                {
                    "track": {
                        "id": "t1",
                        "name": "song",
                        "duration_ms": 1000,
                        "artists": [{"id": "a1", "name": "artist"}],
                        "album": {
                            "name": "album",
                            "images": [],
                            "release_date": "2025",
                        },
                    },
                    "played_at": "2025-01-01T12:00:00.000Z",
                }
            ]
        }

        service.sp.current_user_recently_played.return_value = api_data
        service.sp.artists.return_value = {"artists": [{"id": "a1", "genres": ["pop"]}]}

        # first sync: should add 1
        count1 = await service.sync_recently_played()
        assert count1 == 1

        # second sync with same data: should add 0
        count2 = await service.sync_recently_played()
        assert count2 == 0
