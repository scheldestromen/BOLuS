"""Reads and writes data from and to an Excel file"""
from typing import Any
import shutil
from pathlib import Path

from pydantic import BaseModel


def get_list_item_indices(li: list, di: dict) -> dict:
    """
    Function takes a list of strings and a dictionary. The list contains the values from the dictionary.
    The function returns a dictionary with the keys from the dictionary and the index where the
    value can be found in the list.

    Example:
    >>> get_list_item_indices(['derde', 'tweede', 'eerste'], {'first': 'eerste', 'second': 'tweede', 'third': 'derde'})
    {'first': 2, 'second': 1, 'third': 0}
    """
    indices = {}

    for key in di:
        indices[key] = li.index(di[key])

    return indices


def parse_row_instance(sheet: Any, header_row: int, skip_rows: int, col_dict: dict) -> list:
    """
    Reads an Excelsheet. Every row becomes a dictionary with the keys from the col_dict based on the header_row.
    """
    header_list = [cell.value for cell in sheet[header_row]]
    indices = get_list_item_indices(header_list, col_dict)

    rows = []

    for i, row in enumerate(sheet):
        # Skip header
        if i in list(range(skip_rows)):
            continue

        row_dict = {key: row[indices[key]].value for key in col_dict}

        first_header = next(
            header_alias
            for header_alias in col_dict
            if col_dict[header_alias] == header_list[0]
        )

        # If the first cell of the header is empty then we ignore the row
        if row_dict[first_header]:
            rows.append(row_dict)

    return rows


def parse_key_row(sheet: Any, skip_rows: int) -> dict:
    """Parses an Excel worksheet assuming the first column contains a unique key.
    Each row is parsed to a dictionary with as key, the value in the first column and
    as value, the rest of the columns in the row, until the first empty cell was found."""
    row_dict = {}

    for i, row in enumerate(sheet):
        if i in list(range(skip_rows)):  # Skip header
            continue

        # Name is in the first column
        name = row[0].value

        # If a name was filled in, add it to the list
        if not name:
            continue

        if name in row_dict:
            raise ValueError(f"A duplicate name was found: {name}")

        values = []

        # Loop through the values until an empty cell is found
        for cell in row[1:]:
            if cell.value is None:
                break
            values.append(cell.value)

        # Add the name and values to the dictionary
        row_dict[name] = values

    return row_dict
