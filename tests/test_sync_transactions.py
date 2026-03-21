import pytest
from unittest.mock import patch
from spotify_service import SpotifyService
from models import Track, ListeningHistory
from sqlalchemy import select
from tests.conftest import MockSessionLocal


@pytest.mark.asyncio
async def test_sync_rollback_on_error(db_session):
    # verify that if an error occurs mid-sync, no data is committed
    with patch(
        "spotify_service.AsyncSessionLocal", return_value=MockSessionLocal(db_session)
    ), patch("spotify_service.spotipy.Spotify") as mock_sp, patch(
        "spotify_service.SpotifyOAuth"
    ) as mock_oauth:

        mock_oauth.return_value.cache_handler.get_cached_token.return_value = {
            "access_token": "t"
        }
        service = SpotifyService()

        # mock api to return one valid track
        mock_sp.return_value.current_user_recently_played.return_value = {
            "items": [
                {
                    "track": {
                        "id": "fail_track",
                        "name": "s",
                        "duration_ms": 100,
                        "artists": [{"id": "a1", "name": "a"}],
                        "album": {"name": "al", "images": [], "release_date": "2025"},
                    },
                    "played_at": "2025-01-01T12:00:00Z",
                }
            ]
        }

        # force an error during artist genre fetching (which happens after track processing)
        mock_sp.return_value.artists.side_effect = Exception("Database simulated crash")

        # run sync
        await service.sync_recently_played()

        # verify rollback: track should NOT be in database
        res = await db_session.execute(select(Track).filter_by(id="fail_track"))
        assert res.scalar() is None

        res_h = await db_session.execute(select(ListeningHistory))
        assert len(res_h.scalars().all()) == 0
