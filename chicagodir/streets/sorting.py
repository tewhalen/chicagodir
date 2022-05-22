"""Functions related to sorting streets."""

import re

post_type_map = {
    "AY": "AVE",
    "AV": "AVE",
    "AVENUE": "AVE",
    "DRIVE": "DR",
    "PLACE": "PL",
    "COURT": "CT",
    "TERRACE": "TER",
    "TERR": "TER",
    "ROAD": "RD",
    "PARKWAY": "PKWY",
    "SQUARE": "SQ",
    "STREET": "ST",
    "EXPRESSWAY": "EXPY",
    "BOULEVARD": "BLVD",
    "CRESCENT": "CRES",
    "LANE": "LN",
    "PLAZA": "PLZ",
    "HIGHWAY": "HWY",
}


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
    return natural_keys(
        street.name + " " + str(street.suffix or "") + " " + str(street.direction or "")
    )


def streets_sorted(streets):
    """Sort street objects using appropriate key."""
    return sorted(streets, key=street_key)


def numeric_split(text):
    """Use regex to split text into (numeric)(alpha)."""
    return re.match(r"(\d+)([^\d\s]+)", text)


def fix_street_type(raw_post_type: str) -> str:
    """Standardize street type into uppercase abbreviation."""
    converted = raw_post_type.strip(".,").upper().strip()
    return post_type_map.get(converted, converted)


def fix_ordinal(text: str) -> str:
    """Some historical documents have non-standard ordinals and this fixes them.

    23nd -> 23RD
    17th -> 17TH
    2RD -> 2ND
    11nd -> 11TH
    21nd -> 21ST
    etc.
    """
    m = numeric_split(text)
    if not m:
        return text
    number, suffix = m.groups()
    if 3 < int(number) < 20:
        return number + "TH"
    elif number[-1] == "3":
        return number + "RD"
    elif number[-1] == "2":
        return number + "ND"
    elif number[-1] == "1":
        return number + "ST"
    return number + "TH"


def fix_street_name(raw_street_name: str) -> str:
    """Repair potentially weird street names by uppercasing and fixing weird ordinals."""
    street_name = raw_street_name.upper()
    street_name = fix_ordinal(street_name)

    return street_name


def street_title_case(raw_street_name: str) -> str:
    """Put a street name back into title case."""
    return " ".join(x.capitalize() for x in re.split(r"(\s+)", raw_street_name))
