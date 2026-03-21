class MessageStrings:
    AUTH_EXPIRED = "Spotify Authentication Expired. Please check your terminal to re-authenticate and refresh the page."
    SYNC_COMPLETE_NEW = "Sync Complete: {count} new tracks logged."
    SYNC_COMPLETE_NONE = "Sync Complete: No new tracks found."
    SYNC_BACKGROUND = "Background Sync: {count} new tracks logged."
    STATUS_OK = "OK"
    STATUS_UNAUTHENTICATED = "UNAUTHENTICATED"
    STATUS_ERROR = "ERROR"
    AUTH_REQUIRED_KEY = "SPOTIFY_AUTH_REQUIRED"
    SYNC_ERROR_PREFIX = "Sync Error: {error}"
    HEALTH_ERROR_PREFIX = "Failed to write health status: {error}"
    BG_SYNC_ERROR_PREFIX = "Background sync error: {error}"

    # view errors
    VIEW_NOT_IMPLEMENTED = "{view} not implemented for {mode}."

    # backup logs
    BACKUP_START = (
        "Starting backup to {path}. Note: This may temporarily lock the database."
    )
    BACKUP_SUCCESS = "Atomic backup created: {filename}"
    BACKUP_ROTATE = "Removed old backup: {filename}"
    BACKUP_FAILED = "Backup failed: {error}"
    BACKUP_INIT_FAILED = "Backup initialization failed: {error}"

    # auth dialog messages
    AUTH_INVALID_URL = "Invalid URL. Please make sure you copied the entire link."
    AUTH_SUCCESS = "Authentication successful! Syncing now..."
