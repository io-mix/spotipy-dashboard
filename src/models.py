from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    ForeignKey,
    Integer,
    Index,
    UniqueConstraint,
    Date,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class GlobalStat(Base):
    __tablename__ = "global_stats"

    id = Column(Integer, primary_key=True)
    total_tracks = Column(Integer, default=0)
    total_ms = Column(Integer, default=0)


class DailyTrackStat(Base):
    __tablename__ = "daily_track_stats"

    date = Column(Date, primary_key=True, index=True)
    track_id = Column(String, ForeignKey("tracks.id"), primary_key=True, index=True)
    play_count = Column(Integer, default=0)


class DashboardCache(Base):
    __tablename__ = "dashboard_cache"

    id = Column(Integer, primary_key=True)
    data = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)


# prevent expensive "All-Time Favorites" calculations on load
class DashboardSummary(Base):
    __tablename__ = "dashboard_summary"

    id = Column(Integer, primary_key=True)
    time_range = Column(String, unique=True)
    top_song = Column(String)
    top_artist = Column(String)
    top_album = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Track(Base):
    __tablename__ = "tracks"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    artist_name = Column(String, nullable=False, index=True)
    artist_id = Column(String, nullable=False, index=True)
    album_name = Column(String)
    image_url = Column(String)
    duration_ms = Column(Integer)
    release_date = Column(String)
    genres = Column(String)

    play_count = Column(Integer, default=0, index=True)
    # represents the start time of the most recent play
    last_played_at = Column(DateTime, index=True)

    # link to listening history for this track
    history = relationship("ListeningHistory", back_populates="track")
    genre_links = relationship(
        "TrackGenre", back_populates="track", cascade="all, delete-orphan"
    )


class TrackGenre(Base):
    __tablename__ = "track_genres"

    track_id = Column(String, ForeignKey("tracks.id"), primary_key=True)
    genre = Column(String, primary_key=True, index=True)

    track = relationship("Track", back_populates="genre_links")


class ListeningHistory(Base):
    __tablename__ = "listening_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # represents the start time of the track (end_time - duration)
    played_at = Column(DateTime, nullable=False, index=True)
    track_id = Column(String, ForeignKey("tracks.id"), nullable=False, index=True)
    context_type = Column(String)
    context_uri = Column(String)

    # link back to the Track
    track = relationship("Track", back_populates="history")

    # ensure we don't log the exact same play twice
    __table_args__ = (
        UniqueConstraint("played_at", "track_id", name="_played_track_uc"),
    )


# composite index for faster queries on played_at + track_id
Index("idx_played_track", ListeningHistory.played_at, ListeningHistory.track_id)
# covering index for fast time-based aggregations
Index("idx_track_played", ListeningHistory.track_id, ListeningHistory.played_at)
# search optimization index
Index("idx_track_search", Track.name, Track.artist_name, Track.album_name)
# NEW: Index for music profile page to speed up source filtering
Index("idx_context_type", ListeningHistory.context_type)
