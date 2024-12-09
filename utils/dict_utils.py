"""Module with helper functions for dictionaries"""
from typing import Any


def check_for_missing_keys(dict_to_check: dict, required_keys: list[str]) -> None:
    """Returns a list of missing keys. Returns an empty list of all keys are present

    Args:
        dict_to_check: dictionary to check
        required_keys: list of required keys"""

    missing_keys = [key for key in required_keys if key not in dict_to_check.keys()]

    if missing_keys:
        raise ValueError(f"Dictionary is missing required keys: {missing_keys}")


def remove_key(d: dict, key: Any):
    """Removes a key from a dictionary and returns the modified dictionary"""
    d.pop(key)
    return d


def group_dicts_by_key(
    dicts: list, group_by_key: str, remove_group_key: bool = True
) -> dict:
    """
    Takes a list of dictionaries and groups them by the specified key. It returns
    a dictionary with the group_by_key as key and the list of dictionaries as value.
    Removal of the group_by_key is optional.

    Args:
        dicts: list of dictionaries.
        group_by_key: key to group by. Must be a key in the dictionaries.
        remove_group_key: Default=True. If True, the group_by_key is removed from the dictionaries.

    Returns:
        grouped_dict: dictionary met dictionaries.

    Example:
        >>> group_dicts_by_key(dicts=[{'a': 1, 'b': 12}, {'a': 1, 'b': 56}, {'a': 2, 'b': 63}], group_by_key='a')
        {1: [{'b': 12}, {'b': 56}], 2: [{'b': 63}]}


    """
    target_keys = set(d[group_by_key] for d in dicts)
    grouped_dict = {k: [d for d in dicts if d[group_by_key] == k] for k in target_keys}

    # De group_by_key verwijderen uit de dictionaries binnen de groep. De group_by_key is nu de key van de grouped_dict
    if remove_group_key:
        for key in grouped_dict:
            group = grouped_dict[key]

            for group_item in group:
                group_item.pop(group_by_key)

    return grouped_dict
