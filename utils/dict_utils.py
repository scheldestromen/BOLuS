"""Module with helper functions for dictionaries"""


def check_for_missing_keys(dict_to_check: dict, required_keys: list[str]) -> None:
    """Returns a list of missing keys. Returns an empty list of all keys are present

    Args:
        dict_to_check: dictionary to check
        required_keys: list of required keys"""

    missing_keys = [key for key in required_keys if key not in dict_to_check.keys()]

    if missing_keys:
        raise ValueError(f"Dictionary is missing required keys: {missing_keys}")
