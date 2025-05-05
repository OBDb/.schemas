from pathlib import Path
import os
import inspect

def extract_make_from_repo_name(repo_name=None):
    """
    Extract the make name from a repository name.

    Args:
        repo_name: Repository name in format "Make-Model". If None, derives from the repository directory.
                  Handles special cases like "Mercedes-Benz-G-Class" where the make name contains hyphens.

    Returns:
        str: The make name or None if not determinable.
    """
    if not repo_name:
        # Get the repository name by traversing up from this file's location
        # until we find a directory with a dash in the name
        file_path = Path(inspect.getframeinfo(inspect.currentframe()).filename)
        current_dir = file_path.parent

        # Walk up the directory tree to find the repository root
        while current_dir.name and '-' not in current_dir.name:
            parent = current_dir.parent
            # Check if we've reached the filesystem root
            if parent == current_dir:
                break
            current_dir = parent

        repo_name = current_dir.name

    # Handle special cases for makes with hyphens in their names
    special_makes_with_hyphens = ["Mercedes-Benz", "Alfa-Romeo", "Aston-Martin", "Land-Rover", "Rolls-Royce"]

    for make in special_makes_with_hyphens:
        if repo_name.startswith(make + "-"):
            return make

    # Extract the make (everything before the first hyphen) for standard cases
    parts = repo_name.split('-')
    if len(parts) > 1:
        return parts[0]

    return None
