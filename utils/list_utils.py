"""Module with helper functions for lists"""


def check_list_of_dicts_for_duplicate_values(dict_list: list[dict], key: str) -> None:
    """Checks for duplicate values at the specified key.

    The list should contain dictionaries with the specified key. The function
    checks if the all the values at the specified key are unique. If not, an error is
    raised.

    Args:
        dict_list: list of dictionaries, which all contain the specified key
        key: key to check for duplicates"""

    values = [d[key] for d in dict_list]
    duplicates = [value for value in values if values.count(value) > 1]
    duplicates = list(set(duplicates))

    if duplicates:
        raise ValueError(
            f"List contains duplicate values at the specified key '{key}'. "
            f"This is not allowed. \nThe duplicates are: {', '.join(duplicates)}."
        )


def unique_in_order(lst: list) -> list:
    """Returns a list of unique items in the order they appear in the list

    Args:
        lst: list of items

    Returns:
        unique: list of unique items"""

    seen = set()
    unique = []

    for item in lst:
        if item not in seen:
            unique.append(item)
            seen.add(item)

    return unique


def get_list_item_indices(li: list[str], di: dict[str, str]) -> dict[str, int]:
    """
    Functie neemt een list met strings en een dictionary. De list bevat de values uit dictionary. De functie geeft een
    dictionary met als keys de keys uit opgegeven dictionary 'di' en als value de index waar deze key in de opgegeven
    list 'li' gevonden kan worden.

    Example:
    >>> get_list_item_indices(['derde', 'tweede', 'eerste'], {'first': 'eerste', 'second': 'tweede', 'third': 'derde'})
    {'first': 2, 'second': 1, 'third': 0}

    """
    indices: dict[str, int] = {}

    for key in di:
        indices[key] = li.index(di[key])

    return indices
