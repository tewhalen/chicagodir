# -*- coding: utf-8 -*-
"""Street models."""

import re

from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import expression
import datetime

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
    """Convert text to an integer if possible."""
    return int(text) if text.isdigit() else text


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


class Street(PkModel):
    """A known historical or current street."""

    __tablename__ = "streets"

    street_id = Column(db.String(25), index=True)
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

    # text-based tags

    tags = Column(ARRAY(db.String))

    # checked by a human and fixed
    confirmed = Column(db.Boolean(), nullable=False, server_default=expression.false())

    # something odd about this, doesn't fit schema
    weird = Column(db.Boolean(), nullable=False, server_default=expression.false())

    # this is a bad entry, just skip it
    skip = Column(db.Boolean(), nullable=False, server_default=expression.false())

    __table_args__ = (db.Index("idx_streets_name_suff", "name", "suffix"),)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<Street({self.name})>"

    @property
    def full_name(self) -> str:
        """The full name of the street."""
        return " ".join(
            [
                self.direction or "",
                street_title_case(self.name),
                self.suffix.capitalize() or "",
                self.suffix_direction or "",
            ]
        )

    @property
    def short_name(self) -> str:
        """Name without directional prefix."""
        return " ".join(
            [
                street_title_case(self.name),
                self.suffix.capitalize() or "",
            ]
        )

    def find_current_successors(self, n=0):
        """Follow the chain of street changes all the way to the end."""
        if n > 5:
            # don't recurse more than 5 times
            return set()
        elif self.current:
            return {street}
        else:
            found = set()
            for street in street.successor_streets:
                found = found.union(street.find_current_successors(n + 1))
            return found

    @property
    def successor_streets(self) -> "list[Street]":
        """A list of successor streets."""
        return [change.to_street for change in self.successor_changes()]

    def single_successor(self):
        """If this is succeeded by a single street, return its name and suffix."""
        # FIX ME this query is slow to run 1000s of times
        q = (
            db.session.query(Street.name, Street.suffix)
            .filter(StreetChange.from_id == self.id)
            .join(StreetChange, Street.id == StreetChange.to_id)
            .group_by(Street.name, Street.suffix)
            .all()
        )

        if len(q) == 1:
            return "{} {}".format(
                street_title_case(q[0].name.title()), q[0].suffix.capitalize()
            )
        else:
            return None

    @property
    def predecessors(self) -> "list[Street]":
        """A list of predecessor streets."""
        return [change.from_street for change in self.predecessor_changes()]

    def short_info(self) -> str:
        """Short text for after the name of a street to indicate historical status/context."""
        if not self.current:
            if self.vacated:
                status = "vacated"
            else:
                status = "retired"
                name = self.single_successor()
                if name:
                    status = "→ {}".format(name)

            year = ""
            if self.end_date:
                year = self.end_date.year
                if self.end_date_circa:
                    c = "c."
                else:
                    c = ""
                return "{} {}{}".format(status, c, year)
            else:
                return status
        else:
            return "current"

    def short_tag(self, suppress_current=True) -> str:
        """Possible short tag for after the name of a street to indicate historical status/context."""

        if suppress_current and self.current:
            return ""
        else:
            return "({})".format(self.short_info())

    def retirement_info(self) -> str:
        """Short bit of info indicating the retired/vacated status of a street."""
        if self.current:
            return ""

        if self.vacated:
            status = "Vacated"
        else:
            status = "Retired"
        if self.end_date:
            year = self.end_date.year
            if self.end_date_circa:
                c = "c."
            else:
                c = ""
            return "{} {}{}".format(status, c, year)
        else:
            return status

    def successor_changes(self):
        """Query the sucessor associations."""
        return StreetChange.query.filter_by(from_id=self.id)

    def predecessor_changes(self):
        """Query the prdececssor associations."""
        return StreetChange.query.filter(StreetChange.to_id == self.id)

    def similar_streets(self):
        """Find similarly-named streets."""
        return Street.query.filter(
            db.and_(Street.name == self.name, Street.id != self.id)
        )

    def contemporary_streets(self):
        """Other streets which are extant at the time of this street."""
        q = db.session.query(Street)
        if self.end_date is not None:
            q.filter(
                ((Street.start_date <= self.end_date) | (Street.start_date.is_(None)))
            )
        if self.start_date is not None:
            q.filter(
                ((Street.end_date >= self.start_date) | (Street.end_date.is_(None)))
            )
        return q.all()

    @classmethod
    def streets_given_date(cls, date):
        """Given a date, find all contemporaneous streets."""
        q = db.session.query(Street)
        if date is not None:
            q.filter(((Street.start_date <= date) | (Street.start_date.is_(None))))
            q.filter(((Street.end_date >= date) | (Street.end_date.is_(None))))
        return q.all()

    @classmethod
    def find_best_street(cls, name, suffix="", direction="", year=None):
        """Given details, find the one matching street, if any."""
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
        """Record that an edit has been made to this street by a user."""
        change_object = StreetEdit(street=self, user=user, note=change)

        change_object.save()

    def data_issues(self) -> list:
        """Report out the data issues with this street that a user might like to fix."""
        issues = []
        if not self.confirmed:
            issues.append(
                {
                    "issue": "unconfirmed",
                    "icon": "far fa-question-circle",
                    "level": "info",
                }
            )
        if not self.current and self.end_date is None:
            issues.append(
                {
                    "issue": "no end date",
                    "icon": "far fa-calendar-times",
                    "level": "warning",
                }
            )
        if self.start_date is None:
            issues.append(
                {
                    "issue": "no start date",
                    "icon": "far fa-calendar-times",
                    "level": "warning",
                }
            )
        if not self.current and not self.successors and not self.vacated:
            issues.append(
                {
                    "issue": "no sucessors and not vacated",
                    "icon": "fas fa-code-branch",
                    "level": "warning",
                }
            )
        if self.weird:
            issues.append(
                {
                    "issue": "marked as weird",
                    "icon": "fas fa-asterisk",
                    "level": "danger",
                }
            )
        if not self.min_address or not self.max_address:
            issues.append(
                {
                    "issue": "missing min/max addresses",
                    "icon": "fas fa-map-marked-alt",
                    "level": "warning",
                }
            )
        if not self.grid_location and not self.diagonal:
            issues.append(
                {
                    "issue": "missing grid location",
                    "icon": "fas fa-border-none",
                    "level": "warning",
                }
            )

        return issues

    def record_changes(self, current_user):
        """Inspect using sqlalchemy and record changes."""
        changes = {}

        for attr in inspect(self).attrs:
            if attr.history.has_changes():
                changes[attr.key] = attr.history.added
        if changes:
            self.record_edit(current_user, str(changes))

    @property
    def timestamp(self):
        q = db.select(db.func.max(StreetEdit.timestamp).label("timestamp")).filter(
            StreetEdit.street_id == self.id
        )
        row = db.session.execute(q).one()
        if row:
            return row["timestamp"]
        else:
            return datetime.datetime.now()


class StreetChange(PkModel):
    """An association between two streets indicating a renaming or other change."""

    __tablename__ = "streetchange"

    type = Column(db.String(12), nullable=True, default="RENAME")

    note = Column(db.Text(), nullable=True)

    from_id = reference_col("streets", column_kwargs={"index": True})
    from_street = relationship("Street", backref="successors", foreign_keys=[from_id])

    to_id = reference_col("streets", nullable=True, column_kwargs={"index": True})
    to_street = relationship("Street", backref="predecessors", foreign_keys=[to_id])

    date = Column(db.Date(), nullable=True)


class StreetEdit(PkModel):
    """A record of a user or system edit to a street in this database."""

    __tablename__ = "streets_edits"

    # street edited
    street_id = reference_col("streets", column_kwargs={"index": True})
    street = relationship("Street", backref="edits", foreign_keys=[street_id])

    # user who did the edit
    user_id = reference_col("users")
    user = relationship("User", foreign_keys=[user_id])

    # time of edit
    timestamp = Column(db.DateTime(timezone=True), server_default=db.func.now())

    # note of edit
    note = Column(db.Text())


class StreetList(PkModel):
    """A reference work that has a list of streets extant in a year."""

    __tablename__ = "street_lists"

    name = Column(db.String(80), nullable=False)
    date = Column(db.Date(), nullable=False, index=True)

    url = Column(db.Text())

    # other notes
    text = Column(db.Text())

    def new_entry(self, street_id):
        """Add an entry to the streetlist."""
        return StreetListEntry(list_id=self.id, street_id=street_id)


class StreetListEntry(PkModel):
    """An entry in a list of streets."""

    __tablename__ = "street_list_entries"

    list_id = reference_col("street_lists")
    list = relationship("StreetList", backref="entries", foreign_keys=[list_id])

    street_id = reference_col("streets", nullable=True)
    street = relationship("Street", foreign_keys=[street_id])
