"""Module with helper functions for lists"""


def check_list_of_dicts_for_duplicate_values(dict_list: list[dict], key: str) -> None:
    """Checks for duplicate values at the specified key.

    The list should contain dictionaries with the specified key. The function
    checks if the all the values at the specified key are unique. If not, an error is
    raised.

    Args:
        dict_list: list of dictionaries, which all contain the specified key
        key: key to check for duplicates"""

    if len(set([d[key] for d in dict_list])) != len(dict_list):
        raise ValueError(f"List contains duplicate values at the specified key {key}."
                         f"This is not allowed.")
