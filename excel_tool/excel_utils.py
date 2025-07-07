"""Reads and writes data from and to an Excel file"""

from typing import Any


def get_list_item_indices(li: list[str], di: dict[str, str]) -> dict[str, int]:
    """
    Function takes a list of strings and a dictionary. The list contains the values from the dictionary.
    The function returns a dictionary with the keys from the dictionary and the index where the
    value can be found in the list.

    Example:
    >>> get_list_item_indices(['derde', 'tweede', 'eerste'], {'first': 'eerste', 'second': 'tweede', 'third': 'derde'})
    {'first': 2, 'second': 1, 'third': 0}
    """
    indices: dict[str, int] = {}

    for key in di:
        indices[key] = li.index(di[key])

    return indices


def parse_row_instance(
    sheet: Any, header_row: int, skip_rows: int, col_dict: dict[str, str] | None = None
) -> list[dict[str, Any]]:
    """
    Reads an Excelsheet. Every row becomes a dictionary with the keys from the col_dict based on the header_row.
    """

    header_list = [cell.value for cell in sheet[header_row]]

    # Check if the column names are unique (there could be None column names, but this is allowed)
    header_list_check = [header for header in header_list if header is not None]

    if len(set(header_list_check)) != len(header_list_check):
        raise ValueError(f"Duplicate names found in the column row of sheet '{sheet.title}'.\n"
                         "Please ensure all column names are unique.")

    if col_dict is not None:
        indices = get_list_item_indices(header_list, col_dict)
    else:
        indices = None

    rows: list[dict[str, Any]] = []

    for i, row in enumerate(sheet):
        # Skip header
        if i in list(range(skip_rows)):
            continue

        if indices is not None:
            row_dict = {key: row[indices[key]].value for key in col_dict}

            first_header = next(
                header_alias
                for header_alias in col_dict
                if col_dict[header_alias] == header_list[0]
            )

        else:
            row_dict = {key: cell.value for key, cell in zip(header_list, row) if key is not None}
            first_header = header_list[0]

        # If the first cell of the header is empty then we ignore the row
        if row_dict[first_header]:
            rows.append(row_dict)

    return rows


def parse_row_instance_remainder(
    sheet: Any, header_row: int, skip_rows: int, col_dict: dict[str, str], key_remainder: str
) -> list:
    """
    Reads an Excelsheet. Every row becomes a dictionary with the keys from the col_dict based on the header_row.
    The columns for which the column name is not present in col_dict are parsed to the dictionary with key key_remainder.
    The values are read from the i + 1 column, where i is the position of the most right column, upto the
    first empty cell.
    """
    header_list = [cell.value for cell in sheet[header_row]]
    indices = get_list_item_indices(header_list, col_dict)
    max_index = max(indices.values())

    rows = []

    for i, row in enumerate(sheet):
        # Skip header
        if i in list(range(skip_rows)):
            continue

        row_dict = {key: row[indices[key]].value for key in col_dict}

        other = []

        # Loop through the values until an empty cell is found
        for cell in row[max_index + 1 :]:
            if cell.value is None or cell.value == "":
                break
            other.append(cell.value)

        row_dict[key_remainder] = other

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
    as value, the rest of the columns in the row, until the first empty cell was found.
    """
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
            raise ValueError(
                f"A duplicate name was found: `{name}` in sheet {sheet.name}"
            )

        values = []

        # Loop through the values until an empty cell is found
        for cell in row[1:]:
            if cell.value is None or cell.value == "":
                break
            values.append(cell.value)

        # Add the name and values to the dictionary
        row_dict[name] = values

    return row_dict


def parse_key_value_cols(
    sheet: Any,
    header_row: int,
    skip_rows: int,
    key_col: str,
    value_col: str,
    col_dict: dict,
    key_dict: dict,
) -> dict:
    """Parses an Excel worksheet in which a column contains the keys and another column contains
    the values. The key value pairs are assumed to be on the same row, but don't have to
    be adjacent.

    Args:
        sheet: Excel worksheet
        header_row: number of the header row
        skip_rows: number of rows to skip
        key_col: name (alias) of the column containing the keys
        value_col: name (alias) of the column containing the values
        col_dict: dictionary with the column alias as key and the actual column name
          as value
        key_dict: dictionary with the key alias as key and the actual key as value"""

    header_list = [cell.value for cell in sheet[header_row]]
    indices = get_list_item_indices(header_list, col_dict)

    sheet_dict = {}

    for i, row in enumerate(sheet):
        # Skip header
        if i in list(range(skip_rows)):
            continue

        key = row[indices[key_col]].value
        value = row[indices[value_col]].value

        if key in sheet_dict.keys():
            raise ValueError(
                f"A duplicate key was found: `{key}` in sheet {sheet.name}"
            )

        # If the key is not None then it is assigned
        if key is not None:
            sheet_dict[key_dict[key]] = value

    return sheet_dict
