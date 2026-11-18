"""
Timestamp utilities for message formatting and synchronization.
"""

from datetime import datetime, timezone
from typing import Optional


def get_utc_now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def format_display_time(iso_or_str: Optional[str] = None) -> str:
    """
    Formats a timestamp string or current time into a clean [HH:MM] display format.
    
    Args:
        iso_or_str: An ISO formatted timestamp string, standard datetime string, or None for now.
        
    Returns:
        Formatted string like "[14:35]".
    """
    if not iso_or_str:
        return datetime.now().strftime("[%H:%M]")
    
    # Try parsing common formats
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(iso_or_str, fmt)
            # If naive, treat as local or UTC
            return dt.strftime("[%H:%M]")
        except ValueError:
            continue
            
    # Fallback to taking time slice if string contains 'T' or space
    if " " in iso_or_str:
        parts = iso_or_str.split(" ")
        if len(parts) > 1 and ":" in parts[1]:
            return f"[{parts[1][:5]}]"
    elif "T" in iso_or_str:
        parts = iso_or_str.split("T")
        if len(parts) > 1 and ":" in parts[1]:
            return f"[{parts[1][:5]}]"
            
    return f"[{iso_or_str[:5]}]"


def get_current_timestamp_str() -> str:
    """Returns formatted current local timestamp 'YYYY-MM-DD HH:MM:SS'."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
