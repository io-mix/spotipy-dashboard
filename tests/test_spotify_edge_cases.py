import pytest
from unittest.mock import patch, MagicMock
from spotify_service import SpotifyService
from models import GlobalStat, Track
from sqlalchemy import select
from tests.conftest import MockSessionLocal


@pytest.mark.asyncio
async def test_auth_flow_methods():
    # test auth url generation and code parsing
    with patch("spotify_service.SpotifyOAuth") as mock_oauth:
        mock_instance = mock_oauth.return_value
        mock_instance.get_authorize_url.return_value = "http://spotify.com/auth"
        mock_instance.parse_response_code.return_value = "code123"

        service = SpotifyService()
        assert service.get_auth_url() == "http://spotify.com/auth"

        # valid code
        assert service.complete_auth("http://localhost/?code=code123") is True
        # invalid code
        mock_instance.parse_response_code.return_value = None
        assert service.complete_auth("http://localhost/?error=access_denied") is False


@pytest.mark.asyncio
async def test_sync_missing_metadata(db_session):
    # test sync with missing images and short release dates
    with patch(
        "spotify_service.AsyncSessionLocal", return_value=MockSessionLocal(db_session)
    ), patch("spotify_service.spotipy.Spotify"), patch(
        "spotify_service.SpotifyOAuth"
    ) as mock_oauth:

        mock_oauth.return_value.cache_handler.get_cached_token.return_value = {
            "access_token": "t"
        }
        service = SpotifyService()

        api_data = {
            "items": [
                {
                    "track": {
                        "id": "t_edge",
                        "name": "edge",
                        "duration_ms": 100,
                        "artists": [{"id": "a1", "name": "art"}],
                        "album": {
                            "name": "alb",
                            "images": [],  # empty images
                            "release_date": "1994",  # year only
                        },
                    },
                    "played_at": "2025-01-01T12:00:00.000Z",
                }
            ]
        }
        service.sp.current_user_recently_played.return_value = api_data
        service.sp.artists.return_value = {"artists": [{"id": "a1", "genres": []}]}

        count = await service.sync_recently_played()
        assert count == 1

        # verify track was saved with null image
        res = await db_session.execute(select(Track).filter_by(id="t_edge"))
        track = res.scalar()
        assert track.image_url is None
        assert track.release_date == "1994"


@pytest.mark.asyncio
async def test_global_stats_accumulation(db_session):
    # verify global stats update correctly across multiple syncs
    with patch(
        "spotify_service.AsyncSessionLocal", return_value=MockSessionLocal(db_session)
    ), patch("spotify_service.spotipy.Spotify"), patch(
        "spotify_service.SpotifyOAuth"
    ) as mock_oauth:

        mock_oauth.return_value.cache_handler.get_cached_token.return_value = {
            "access_token": "t"
        }
        service = SpotifyService()
        service.sp.artists.return_value = {"artists": [{"id": "a1", "genres": []}]}

        # sync 1 track
        service.sp.current_user_recently_played.return_value = {
            "items": [
                {
                    "track": {
                        "id": "1",
                        "name": "s",
                        "duration_ms": 1000,
                        "artists": [{"id": "a1", "name": "a"}],
                        "album": {"name": "al", "images": [], "release_date": "2025"},
                    },
                    "played_at": "2025-01-01T10:00:00Z",
                }
            ]
        }
        await service.sync_recently_played()

        # sync another track
        service.sp.current_user_recently_played.return_value = {
            "items": [
                {
                    "track": {
                        "id": "2",
                        "name": "s",
                        "duration_ms": 2000,
                        "artists": [{"id": "a1", "name": "a"}],
                        "album": {"name": "al", "images": [], "release_date": "2025"},
                    },
                    "played_at": "2025-01-01T11:00:00Z",
                }
            ]
        }
        await service.sync_recently_played()

        res = await db_session.execute(select(GlobalStat))
        g = res.scalar()
        assert g.total_tracks == 2
        assert g.total_ms == 3000
