"""
Datetime utilities for the HQT trading system.

This module provides timezone-aware datetime utilities for market session
detection, bar time calculations, and trading day counting.

All internal times are stored in UTC. Market hours are based on Forex 24/5
schedule (Sunday 5pm EST - Friday 5pm EST).
"""

from datetime import datetime, timedelta, timezone
from enum import IntEnum
from typing import Literal

import pytz


class Timeframe(IntEnum):
    """Timeframe enum with values in minutes."""

    M1 = 1
    M5 = 5
    M15 = 15
    M30 = 30
    H1 = 60
    H4 = 240
    D1 = 1440
    W1 = 10080
    MN1 = 43200  # Approximate (30 days)


# Market timezone (Eastern Time)
MARKET_TZ = pytz.timezone("America/New_York")

# Forex market hours (Sunday 5pm EST - Friday 5pm EST)
MARKET_OPEN_WEEKDAY = 6  # Sunday
MARKET_OPEN_HOUR = 17  # 5pm
MARKET_CLOSE_WEEKDAY = 4  # Friday
MARKET_CLOSE_HOUR = 17  # 5pm


def utc_now() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.

    Returns:
        Timezone-aware datetime in UTC

    Example:
        ```python
        from hqt.foundation.utils import utc_now

        now = utc_now()
        print(f"Current UTC time: {now}")
        print(f"Is aware: {now.tzinfo is not None}")  # True
        ```
    """
    return datetime.now(timezone.utc)


def is_market_open(dt: datetime | None = None) -> bool:
    """
    Check if the Forex market is open at the given time.

    Forex market is open 24/5 from Sunday 5pm EST to Friday 5pm EST.

    Args:
        dt: Datetime to check (UTC). If None, uses current time.

    Returns:
        True if market is open, False otherwise

    Example:
        ```python
        from hqt.foundation.utils import is_market_open, utc_now

        # Check current time
        if is_market_open():
            print("Market is open!")

        # Check specific time
        from datetime import datetime, timezone
        dt = datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)
        if is_market_open(dt):
            print("Market was open at that time")
        ```
    """
    if dt is None:
        dt = utc_now()

    # Convert to market timezone (EST)
    if dt.tzinfo is None:
        # Assume UTC if naive
        dt = dt.replace(tzinfo=timezone.utc)

    market_time = dt.astimezone(MARKET_TZ)

    # Check if weekend
    weekday = market_time.weekday()
    hour = market_time.hour

    # Saturday is closed
    if weekday == 5:
        return False

    # Sunday: open from 5pm onwards
    if weekday == 6:
        return hour >= MARKET_OPEN_HOUR

    # Monday-Thursday: open 24 hours
    if weekday < 4:
        return True

    # Friday: open until 5pm
    if weekday == 4:
        return hour < MARKET_CLOSE_HOUR

    return False


def align_to_bar(
    dt: datetime,
    timeframe: Timeframe | int,
    mode: Literal["floor", "ceil"] = "floor",
) -> datetime:
    """
    Align datetime to the nearest bar boundary.

    Args:
        dt: Datetime to align (must be timezone-aware)
        timeframe: Timeframe in minutes (Timeframe enum or int)
        mode: Alignment mode - "floor" (round down) or "ceil" (round up)

    Returns:
        Aligned datetime (preserves timezone)

    Raises:
        ValueError: If dt is timezone-naive or timeframe is invalid

    Example:
        ```python
        from hqt.foundation.utils import align_to_bar, Timeframe
        from datetime import datetime, timezone

        dt = datetime(2024, 1, 15, 14, 37, 23, tzinfo=timezone.utc)

        # Align to M15 bar (floor)
        aligned = align_to_bar(dt, Timeframe.M15, mode="floor")
        print(aligned)  # 2024-01-15 14:30:00+00:00

        # Align to H1 bar (ceil)
        aligned = align_to_bar(dt, Timeframe.H1, mode="ceil")
        print(aligned)  # 2024-01-15 15:00:00+00:00
        ```
    """
    if dt.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware")

    # Get timeframe in minutes
    if isinstance(timeframe, Timeframe):
        minutes = timeframe.value
    else:
        minutes = int(timeframe)

    if minutes <= 0:
        raise ValueError(f"Timeframe must be positive, got {minutes}")

    # Convert to UTC for calculations
    utc_dt = dt.astimezone(timezone.utc)

    # Calculate total minutes since epoch
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    total_minutes = int((utc_dt - epoch).total_seconds() / 60)

    # Align to bar boundary
    if mode == "floor":
        aligned_minutes = (total_minutes // minutes) * minutes
    elif mode == "ceil":
        aligned_minutes = ((total_minutes + minutes - 1) // minutes) * minutes
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'floor' or 'ceil'")

    # Convert back to datetime
    aligned_utc = epoch + timedelta(minutes=aligned_minutes)

    # Preserve original timezone
    return aligned_utc.astimezone(dt.tzinfo)


def next_bar_time(dt: datetime, timeframe: Timeframe | int) -> datetime:
    """
    Calculate the start time of the next bar.

    Args:
        dt: Current datetime (must be timezone-aware)
        timeframe: Timeframe in minutes (Timeframe enum or int)

    Returns:
        Start time of next bar (preserves timezone)

    Raises:
        ValueError: If dt is timezone-naive or timeframe is invalid

    Example:
        ```python
        from hqt.foundation.utils import next_bar_time, Timeframe
        from datetime import datetime, timezone

        dt = datetime(2024, 1, 15, 14, 37, 23, tzinfo=timezone.utc)

        # Get next M15 bar
        next_m15 = next_bar_time(dt, Timeframe.M15)
        print(next_m15)  # 2024-01-15 14:45:00+00:00

        # Get next H1 bar
        next_h1 = next_bar_time(dt, Timeframe.H1)
        print(next_h1)  # 2024-01-15 15:00:00+00:00
        ```
    """
    # Align to current bar, then add one timeframe
    current_bar = align_to_bar(dt, timeframe, mode="floor")

    # Get timeframe in minutes
    if isinstance(timeframe, Timeframe):
        minutes = timeframe.value
    else:
        minutes = int(timeframe)

    return current_bar + timedelta(minutes=minutes)


def trading_days_between(
    start_dt: datetime,
    end_dt: datetime,
    include_start: bool = True,
    include_end: bool = True,
) -> int:
    """
    Count the number of trading days between two dates.

    A trading day is any day when the market is open at any point during the day.
    For Forex, this excludes Saturdays.

    Args:
        start_dt: Start datetime (must be timezone-aware)
        end_dt: End datetime (must be timezone-aware)
        include_start: Include start date in count
        include_end: Include end date in count

    Returns:
        Number of trading days

    Raises:
        ValueError: If datetimes are timezone-naive or start > end

    Example:
        ```python
        from hqt.foundation.utils import trading_days_between
        from datetime import datetime, timezone

        start = datetime(2024, 1, 15, tzinfo=timezone.utc)  # Monday
        end = datetime(2024, 1, 19, tzinfo=timezone.utc)    # Friday

        # Count trading days (Mon-Fri = 5 days)
        days = trading_days_between(start, end)
        print(days)  # 5

        # Exclude endpoints
        days = trading_days_between(start, end, include_start=False, include_end=False)
        print(days)  # 3 (Tue, Wed, Thu)
        ```
    """
    if start_dt.tzinfo is None or end_dt.tzinfo is None:
        raise ValueError("Both datetimes must be timezone-aware")

    if start_dt > end_dt:
        raise ValueError("start_dt must be <= end_dt")

    # Convert to market timezone
    start_market = start_dt.astimezone(MARKET_TZ)
    end_market = end_dt.astimezone(MARKET_TZ)

    # Get date components
    start_date = start_market.date()
    end_date = end_market.date()

    # Count trading days
    count = 0
    current_date = start_date

    while current_date <= end_date:
        # Skip start date if not included
        if current_date == start_date and not include_start:
            current_date += timedelta(days=1)
            continue

        # Skip end date if not included
        if current_date == end_date and not include_end:
            break

        # Check if trading day (not Saturday)
        weekday = current_date.weekday()
        if weekday != 5:  # Not Saturday
            count += 1

        current_date += timedelta(days=1)

    return count


def get_session_name(dt: datetime | None = None) -> str:
    """
    Get the trading session name for a given time.

    Forex has three major sessions: Asian, European (London), and American (New York).

    Args:
        dt: Datetime to check (UTC). If None, uses current time.

    Returns:
        Session name: "asian", "european", "american", or "closed"

    Example:
        ```python
        from hqt.foundation.utils import get_session_name, utc_now

        session = get_session_name()
        print(f"Current session: {session}")

        # Check specific time
        from datetime import datetime, timezone
        dt = datetime(2024, 1, 15, 14, 0, tzinfo=timezone.utc)
        session = get_session_name(dt)
        print(f"Session at {dt}: {session}")
        ```
    """
    if dt is None:
        dt = utc_now()

    if not is_market_open(dt):
        return "closed"

    # Convert to UTC if not already
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    hour = dt.hour

    # Session times in UTC (approximate):
    # Asian: 00:00 - 09:00 UTC (Tokyo 09:00-18:00 JST)
    # European: 07:00 - 16:00 UTC (London 08:00-17:00 GMT)
    # American: 12:00 - 21:00 UTC (New York 07:00-16:00 EST)

    if 0 <= hour < 7:
        return "asian"
    elif 7 <= hour < 12:
        return "european"
    elif 12 <= hour < 21:
        return "american"
    else:
        return "asian"


def is_dst(dt: datetime) -> bool:
    """
    Check if daylight saving time is active in the market timezone.

    Args:
        dt: Datetime to check (must be timezone-aware)

    Returns:
        True if DST is active, False otherwise

    Raises:
        ValueError: If dt is timezone-naive

    Example:
        ```python
        from hqt.foundation.utils import is_dst
        from datetime import datetime, timezone

        # Summer time (DST active)
        summer = datetime(2024, 7, 15, tzinfo=timezone.utc)
        print(is_dst(summer))  # True

        # Winter time (DST inactive)
        winter = datetime(2024, 1, 15, tzinfo=timezone.utc)
        print(is_dst(winter))  # False
        ```
    """
    if dt.tzinfo is None:
        raise ValueError("Datetime must be timezone-aware")

    # Convert to market timezone
    market_time = dt.astimezone(MARKET_TZ)

    # Check if DST is active
    return bool(market_time.dst())
