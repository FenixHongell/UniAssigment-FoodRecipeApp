from datetime import datetime, timezone

def format_timestamp(ts):
    """
    Formats a given timestamp to a human-readable relative time description. If the
    timestamp is `None`, the function returns "Unknown". The function computes the
    difference between the current time and the provided timestamp in minutes, hours,
    or days and returns a suitable string representation of the elapsed time.

    For example:
    - Returns "just now" for timestamps less than a minute ago.
    - Returns "X minutes ago" for timestamps within the last hour.
    - Returns "X hours ago" for timestamps within the last 24 hours.
    - Returns "X days ago" for timestamps older than 24 hours.

    :param ts: The input timestamp in seconds since the epoch as a float or None.
    :type ts: float
    :return: A string describing the relative time elapsed since the provided timestamp,
        e.g., "just now", "5 minutes ago", "2 hours ago", or "Unknown" if the timestamp is None.
    :rtype: str
    """
    # Dont want to disable an entire page just because of a single timestamp
    if ts is None:
        return "Unknown"

    now = datetime.now(timezone.utc)
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    diff = now - dt
    m = int(diff.total_seconds() // 60)
    if m < 1:
        return "just now"
    if m < 60:
        return f"{m} minute{'s' if m != 1 else ''} ago"
    h = m // 60
    if h < 24:
        return f"{h} hour{'s' if h != 1 else ''} ago"
    d = h // 24
    return f"{d} day{'s' if d != 1 else ''} ago"
