"""Functions related to sorting streets."""

import re


def atoi(text):
    """Convert text to an integer if possible, else return the string."""
    return int(text) if text.isdigit() else text


def natural_keys(text):
    """For use in sorting numeric and text stuff naturally, build keys.

    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    """
    return [atoi(c) for c in re.split(r"(\d+)", text)]


def street_key(street):
    """Given a street object, return an appropriate sorting key."""
    return natural_keys(street.name + " " + street.suffix + " " + street.direction)


def streets_sorted(streets):
    """Sort street objects using appropriate key."""
    return sorted(streets, key=street_key)
