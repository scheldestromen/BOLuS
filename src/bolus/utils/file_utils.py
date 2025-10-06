from pathlib import Path


def get_files_by_extension(
    directory: str, file_ext: str, search_sub_dir: bool = False
) -> list[dict[str, str]]:
    """
    Searches through a directory for files with the specified file extension.

    Args:
      directory (str): Path to the folder (may contain subfolders).
      file_ext (str): File extension (without or without dot).
      search_sub_dir (bool): Whether to search subdirectories as well. Default is False.

    Returns:
      list[dict[str, str]]: List of dictionaries with 'name' and 'path' keys.
    """

    dir_path = Path(directory)

    # Validate inputs
    if not dir_path.exists() or not dir_path.is_dir():
        raise ValueError(f"Invalid directory: {directory}")

    if not file_ext:
        raise ValueError("File extension cannot be empty")

    file_ext = file_ext.lstrip(".").casefold()  # Normalize extension

    file_list = []
    search_func = dir_path.rglob if search_sub_dir else dir_path.glob

    for file in search_func(f"*.{file_ext}"):
        file_list.append({"name": file.name, "path": str(file)})

    return file_list
