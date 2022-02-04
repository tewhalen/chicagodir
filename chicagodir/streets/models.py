# -*- coding: utf-8 -*-
"""Street models."""

import re
from sqlalchemy.sql import expression

from chicagodir.database import Column, PkModel, db, reference_col, relationship

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
    return int(text) if text.isdigit() else text


def numeric_split(text):
    """
    split into (numeric)(alpha)
    """
    return re.match(r"(\d+)([^\d\s]+)", text)


def fix_street_type(raw_post_type: str) -> str:
    converted = raw_post_type.strip(".,").upper().strip()
    return post_type_map.get(converted, converted)


def fix_ordinal(text: str) -> str:
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
    street_name = raw_street_name.upper()
    street_name = fix_ordinal(street_name)

    return street_name


def street_title_case(raw_street_name: str) -> str:
    return " ".join(x.capitalize() for x in re.split(r"(\s+)", raw_street_name))


class Street(PkModel):
    """A known historical or current street."""

    __tablename__ = "streets"

    street_id = Column(db.String(25))
    # the full name of the street
    # name = Column(db.String(80), nullable=True)

    # best guesses okay
    start_date = Column(db.Date(), nullable=True, index=True)
    start_date_circa = Column(
        db.Boolean(), nullable=False, server_default=expression.false()
    )
    end_date = Column(db.Date(), nullable=True, index=True)
    end_date_circa = Column(
        db.Boolean(), nullable=False, server_default=expression.false()
    )

    # where on the grid (e.g. Foster is 5200 N)
    grid_location = Column(db.Integer(), nullable=True)
    grid_direction = Column(db.String(2), nullable=True)
    diagonal = Column(db.Boolean(), nullable=False, server_default=expression.false())

    # N S E W
    direction = Column(db.String(3), nullable=True)

    # the bare name
    name = Column(db.String(80), nullable=False, index=True)

    # suffixes
    suffix = Column(db.String(15), nullable=True, index=True)
    suffix_direction = Column(db.String(3), nullable=True)

    # min and max addresses
    min_address = Column(db.Integer(), nullable=True)
    max_address = Column(db.Integer(), nullable=True)

    # whether this is current
    current = Column(
        db.Boolean(), nullable=False, server_default=expression.false(), index=True
    )

    vacated = Column(db.Boolean(), nullable=False, server_default=expression.false())

    # notes on the history
    historical_note = Column(db.Text())

    # other notes
    text = Column(db.Text())

    # checked by a human and fixed
    confirmed = Column(db.Boolean(), nullable=False, server_default=expression.false())

    # something odd about this, doesn't fit schema
    weird = Column(db.Boolean(), nullable=False, server_default=expression.false())

    # this is a bad entry, just skip it
    skip = Column(db.Boolean(), nullable=False, server_default=expression.false())

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<Street({self.name})>"

    @property
    def full_name(self):
        return " ".join(
            [
                self.direction or "",
                street_title_case(self.name),
                self.suffix.capitalize() or "",
                self.suffix_direction or "",
            ]
        )

    @property
    def successors(self):
        return [
            change.to_street
            for change in StreetChange.query.filter(StreetChange.from_id == self.id)
        ]

    @property
    def predecessors(self):
        return [
            change.from_street
            for change in StreetChange.query.filter(StreetChange.to_id == self.id)
        ]

    def short_info(self):
        if not self.current:
            year = ""
            if self.end_date:
                year = self.end_date.year
                if self.end_date_circa:
                    c = "c. "
                else:
                    c = ""
                return "retired {}{}".format(c, year)
            else:
                return "retired"
        else:
            return "current"

    def short_tag(self, suppress_current=True):
        if suppress_current and self.current:
            return ""
        else:
            return "({})".format(self.short_info())

    def retirement_info(self):
        if self.current:
            return ""
        else:
            year = ""
            if self.end_date:
                year = self.end_date.year
            return "Retired {}".format(year)

    def successor_changes(self):
        return StreetChange.query.filter_by(from_id=self.id)

    def predecessor_changes(self):
        return StreetChange.query.filter(StreetChange.to_id == self.id)

    def similar_streets(self):
        return Street.query.filter(
            db.and_(Street.name == self.name, Street.id != self.id)
        )

    @classmethod
    def find_best_street(cls, name, suffix="", direction="", year=None):
        print("looking for", direction, name, suffix, year)
        name = fix_street_name(name)
        matched_streets = Street.query.filter(Street.name == name).all()
        print("found", repr(name), len(matched_streets))
        if len(matched_streets) == 1:
            return matched_streets[0]
        else:
            if suffix:
                matched_streets = list(
                    filter(
                        lambda x: x.suffix == fix_street_type(suffix), matched_streets
                    )
                )
            if len(matched_streets) == 1:
                return matched_streets[0]
            if direction:
                matched_streets = list(
                    filter(lambda x: x.direction == direction, matched_streets)
                )
            if len(matched_streets) == 1:
                return matched_streets[0]
        print("too many:", matched_streets)

    def record_edit(self, user, change: str):
        change_object = StreetEdit(street=self, user=user, note=change)

        change_object.save()


class StreetChange(PkModel):
    """a renaming or other change to a street"""

    __tablename__ = "streetchange"

    type = Column(db.String(12), nullable=True, default="RENAME")

    note = Column(db.Text(), nullable=True)

    from_id = reference_col("streets")
    from_street = relationship("Street", backref="successors", foreign_keys=[from_id])

    to_id = reference_col("streets", nullable=True)
    to_street = relationship("Street", backref="predecessors", foreign_keys=[to_id])

    date = Column(db.Date(), nullable=True)


class StreetEdit(PkModel):
    """tracking user or system changes to a street in this database"""

    __tablename__ = "streets_edits"

    # street edited
    street_id = reference_col("streets")
    street = relationship("Street", backref="edits", foreign_keys=[street_id])

    # user who did the edit
    user_id = reference_col("users")
    user = relationship("User", foreign_keys=[user_id])

    # time of edit
    timestamp = Column(db.DateTime(timezone=True), server_default=db.func.now())

    # note of edit
    note = Column(db.Text())


class StreetList(PkModel):
    """A reference work that has a list of streets extant in a year"""

    __tablename__ = "street_lists"

    name = Column(db.String(80), nullable=False)
    date = Column(db.Date(), nullable=False, index=True)

    url = Column(db.Text())

    # other notes
    text = Column(db.Text())


class StreetListEntry(PkModel):
    __tablename__ = "street_list_entries"

    list_id = reference_col("street_lists")
    list = relationship("StreetList", backref="entries", foreign_keys=[list_id])

    street_id = reference_col("streets", nullable=True)
    street = relationship("Street", foreign_keys=[street_id])
