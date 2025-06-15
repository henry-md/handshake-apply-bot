import functools
import time
import logging
from datetime import timedelta

def format_duration(seconds):
    """
    Format duration in seconds to a human-readable string using timedelta.
    Only includes non-zero values in the output.
    """
    delta = timedelta(seconds=seconds)
    total_seconds = int(delta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60 + (delta.microseconds / 1000000)

    parts = []
    if hours > 0:
        parts.append(f"{hours} hr{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} min{'s' if minutes != 1 else ''}")
    if seconds > 0 or not parts:  # Include seconds if it's the only non-zero value
        parts.append(f"{seconds:.2f} sec{'s' if seconds != 1 else ''}")
    
    return ", ".join(parts)

def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        duration = end - start
        formatted_duration = format_duration(duration)
        logging.info(f"⏱️ {func.__name__} took {formatted_duration}")
        return result
    return wrapper