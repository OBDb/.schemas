import os
import re

class YearRange:
    """A class to represent and compare year ranges from filenames."""

    def __init__(self, filename: str):
        self.filename = filename
        self.start_year = None
        self.end_year = None
        self.single_year = None
        self._parse_filename(filename)

    def _parse_filename(self, filename: str):
        """Parse a filename to extract year range information."""
        # Remove file extension
        basename = os.path.basename(filename)
        name_part = os.path.splitext(basename)[0]

        # YYYY-YYYY.json (year range)
        range_match = re.match(r'^(\d{4})-(\d{4})$', name_part)
        if range_match:
            self.start_year = int(range_match.group(1))
            self.end_year = int(range_match.group(2))
            return

        # Default: Consider as default.json or fallback case
        self.start_year = 0
        self.end_year = 9999  # Far future

    def contains_year(self, year: int) -> bool:
        """Check if this range contains the specified year."""
        if self.start_year is None or self.end_year is None:
            return False
        return self.start_year <= year <= self.end_year

    def __str__(self) -> str:
        if self.single_year is not None:
            return f"{self.single_year} ({self.filename})"
        if self.start_year == 0 and self.end_year == 9999:
            return f"default ({self.filename})"
        return f"{self.start_year}-{self.end_year} ({self.filename})"
