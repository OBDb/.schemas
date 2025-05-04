from pathlib import Path
import os

def extract_make_from_repo_name(repo_name=None):
    """
    Extract the make name from a repository name.

    Args:
        repo_name: Repository name in format "Make-Model". If None, uses current directory.
                  Handles special cases like "Mercedes-Benz-G-Class" where the make name contains hyphens.

    Returns:
        str: The make name or None if not determinable.
    """
    if not repo_name:
        # Get the repository name from the current working directory path
        repo_name = Path(os.getcwd()).parts[-1]

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
