import pytest
from sqlalchemy.exc import IntegrityError
from models import Track, ListeningHistory
from datetime import datetime


@pytest.mark.asyncio
async def test_listening_history_unique_constraint(db_session):
    # create dummy track
    track = Track(id="t1", name="song", artist_name="artist", artist_id="a1")
    db_session.add(track)
    await db_session.commit()

    played_time = datetime(2025, 1, 1, 12, 0, 0)

    # insert first play
    play1 = ListeningHistory(track_id="t1", played_at=played_time)
    db_session.add(play1)
    await db_session.commit()

    # attempt duplicate play at exact same time
    play2 = ListeningHistory(track_id="t1", played_at=played_time)
    db_session.add(play2)

    # should raise integrity error due to unique constraint
    with pytest.raises(IntegrityError):
        await db_session.commit()
