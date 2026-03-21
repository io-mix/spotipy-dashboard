import pytest
from unittest.mock import patch
from spotify_service import SpotifyService
from tests.conftest import MockSessionLocal


@pytest.mark.asyncio
async def test_sync_recently_played(db_session):
    # mock spotipy and db session
    with patch(
        "spotify_service.AsyncSessionLocal", return_value=MockSessionLocal(db_session)
    ), patch("spotify_service.spotipy.Spotify") as mock_spotify, patch(
        "spotify_service.SpotifyOAuth"
    ) as mock_oauth:

        # setup mock auth to bypass cache check
        mock_oauth_instance = mock_oauth.return_value
        mock_oauth_instance.cache_handler.get_cached_token.return_value = {
            "access_token": "test"
        }

        service = SpotifyService()
        service.auth_manager = mock_oauth_instance

        # mock api response
        service.sp.current_user_recently_played.return_value = {
            "items": [
                {
                    "track": {
                        "id": "t1",
                        "name": "test song",
                        "duration_ms": 1000,
                        "artists": [{"id": "a1", "name": "test artist"}],
                        "album": {
                            "name": "test album",
                            "images": [],
                            "release_date": "2025",
                        },
                    },
                    "played_at": "2025-01-01T12:00:00.000Z",
                }
            ]
        }
        service.sp.artists.return_value = {"artists": [{"id": "a1", "genres": ["pop"]}]}

        # run sync
        count = await service.sync_recently_played()

        # verify 1 track added
        assert count == 1
