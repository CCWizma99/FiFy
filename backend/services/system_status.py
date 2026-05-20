"""
backend/services/system_status.py
Tracks system-wide alerts and errors like API quota limits.
"""
from datetime import datetime, timedelta, timezone

class SystemStatus:
    def __init__(self):
        self._quota_error = None
        self._retry_after = None

    def report_quota_error(self, message: str, retry_seconds: int = 60):
        self._quota_error = message
        self._retry_after = datetime.now(timezone.utc) + timedelta(seconds=retry_seconds)

    def get_quota_status(self):
        if self._retry_after and datetime.now(timezone.utc) > self._retry_after:
            self._quota_error = None
            self._retry_after = None
        
        return {
            "error": self._quota_error,
            "retry_after": self._retry_after.isoformat() if self._retry_after else None,
            "is_blocked": self._quota_error is not None
        }

    def clear_quota_error(self):
        self._quota_error = None
        self._retry_after = None

system_status = SystemStatus()
