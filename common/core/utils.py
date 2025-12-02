import json
import random
import re
import string
from datetime import timedelta, datetime
from functools import lru_cache, wraps
from collections import defaultdict


def randomword(length):
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))


def is_json(value):
    if not value:
        return False
    if not isinstance(value, str):
        return False
    try:
        json.loads(value)
    except ValueError:
        return False
    return True


def timed_lru_cache(seconds: int, maxsize: int = 128):
    def wrapper_cache(func):
        func = lru_cache(maxsize=maxsize)(func)
        func.lifetime = timedelta(seconds=seconds)
        func.expiration = datetime.utcnow() + func.lifetime

        @wraps(func)
        def wrapped_func(*args, **kwargs):
            if datetime.utcnow() >= func.expiration:
                func.cache_clear()
                func.expiration = datetime.utcnow() + func.lifetime

            return func(*args, **kwargs)

        return wrapped_func

    return wrapper_cache


def to_title_case(snake_case_string):
    # Split the string by underscores and capitalize each word
    words = snake_case_string.split("_")
    title_words = [word.capitalize() for word in words]

    # Join the words to form the title case string
    title_case_string = "".join(title_words)

    return title_case_string


def merge_dicts_of_lists(dict1, dict2):
    merged_dict = defaultdict(list)  # Initialize merged_dict as a defaultdict

    for key, value in dict1.items():
        merged_dict[key].extend(value)  # Add values from dict1 to merged_dict

    for key, value in dict2.items():
        merged_dict[key].extend(value)  # Add values from dict2 to merged_dict

    return merged_dict


def format_sf(text, suffix=None, safe=False):
    # Handle empty or None input
    if not text or not isinstance(text, str):
        return "unnamed_column"

    # Remove any double quotes
    text = re.sub(r'"+', "", text)

    # Strip leading/trailing whitespace
    text = text.strip()

    # If empty after stripping, return a default name
    if not text:
        return "unnamed_column"

    # Check if text starts with a digit BEFORE any other processing
    starts_with_digit = text[0].isdigit()

    # Check for special characters
    has_special_chars = re.search(r"[^0-9a-zA-Z_. ]", text)

    if has_special_chars:
        text = re.sub(r"[^0-9a-zA-Z]+", "_", text) if safe else f'"{text}"'
    else:
        text = re.sub(r"\W+", "_", text)

    # Add prefix if starts with digit (only for unquoted identifiers)
    # Quoted identifiers can start with digits in Snowflake
    if starts_with_digit and not text.startswith('"'):
        text = f"n_{text}"

    # Add suffix if provided
    if suffix:
        text = f"{text}{suffix}"

    # Convert to lowercase and strip leading/trailing whitespace
    result = text.lower().strip()

    # Strip trailing underscores
    result = result.rstrip("_")

    # Only strip leading underscores if the result would still be valid
    # (i.e., doesn't start with a digit after stripping)
    if result.startswith("_"):
        # Check what's after the leading underscores
        stripped = result.lstrip("_")
        # Only strip if the result is not empty and doesn't start with a digit
        if stripped and not stripped[0].isdigit():
            result = stripped
        # If it would start with a digit after stripping underscores, add n_ prefix
        elif stripped and stripped[0].isdigit():
            result = f"n_{stripped}"
        # If stripping would leave empty string, keep the underscores
        elif not stripped:
            pass  # keep result as is (with underscores)

    # Final check: if result is empty or invalid, return a default
    if not result or result == '""':
        return "unnamed_column"

    return result
