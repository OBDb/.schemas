from typing import Any, Dict, List, Optional

# Filters are open-ended, so conflicts are checked over every model year a
# vehicle could plausibly have.
MODEL_YEARS = range(1980, 2101)

OPTIONAL_FIELDS = ("eax", "rax", "filter")


def filter_matches(filter_obj: Optional[Dict[str, Any]], year: int) -> bool:
    """Whether a filterObject admits a model year, as Pelican reads it.

    from < to is a range, from > to is everything outside the gap between
    them, and years adds single years. No filter, or one with no fields,
    admits every year.
    """
    if not filter_obj:
        return True
    from_val = filter_obj.get("from")
    to_val = filter_obj.get("to")
    if from_val is not None and to_val is not None:
        if from_val < to_val:
            if from_val <= year <= to_val:
                return True
        elif year >= from_val or year <= to_val:
            return True
    elif to_val is not None:
        if year <= to_val:
            return True
    elif from_val is not None:
        if year >= from_val:
            return True
    return year in (filter_obj.get("years") or [])


def specificity(entry: Dict[str, Any]) -> int:
    """How many of eax, rax and filter an entry sets; the highest match wins."""
    return sum(1 for field in OPTIONAL_FIELDS if field in entry)


def _addresses_overlap(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Whether one command could match both entries' addresses."""
    if a["hdr"] != b["hdr"]:
        return False
    for field in ("eax", "rax"):
        if field in a and field in b and a[field] != b[field]:
            return False
    return True


def find_ecu_conflicts(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Pairs of entries that name different types for one command in one year.

    An entry setting more of eax, rax and filter overrides a broader one, so
    only equally specific entries can conflict.
    """
    conflicts = []
    for i, a in enumerate(entries):
        for b in entries[i + 1:]:
            if a["type"] == b["type"] or specificity(a) != specificity(b):
                continue
            if not _addresses_overlap(a, b):
                continue
            year = next(
                (y for y in MODEL_YEARS
                 if filter_matches(a.get("filter"), y) and filter_matches(b.get("filter"), y)),
                None,
            )
            if year is not None:
                conflicts.append({"entry": a, "conflicting_entry": b, "year": year})
    return conflicts


def describe_entry(entry: Dict[str, Any]) -> str:
    address = ".".join(entry[field] for field in ("hdr", "eax", "rax") if field in entry)
    return f"{address} ({entry['type']})"
