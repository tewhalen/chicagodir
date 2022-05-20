# -*- coding: utf-8 -*-
"""Street models."""

import base64
import datetime
import logging
import re
import uuid

from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
from sqlalchemy import ForeignKey, func, inspect
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import expression

from chicagodir.database import Column, PkModel, db, reference_col, relationship
from chicagodir.streets.geodata import clip_by_address
from chicagodir.streets.sorting import (
    fix_street_name,
    fix_street_type,
    street_title_case,
)
from chicagodir.streets.streetlist import StreetListEntry


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

    successor_name = Column(db.String(80), nullable=True)

    # add geometry
    geom = Column(Geometry("GEOMETRY", srid=3435))

    __table_args__ = (db.Index("idx_streets_name_suff", "name", "suffix"),)

    @classmethod
    def empty_street(cls):
        """Generate a new empty street with a unique street id."""
        new_id = (
            base64.urlsafe_b64encode(uuid.uuid1().bytes).rstrip(b"=").decode("ascii")
        )
        return cls(
            street_id=new_id,
            name="** new street **",
            suffix="",
            skip=True,
        )

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
                (self.suffix or "").capitalize(),
                self.suffix_direction or "",
            ]
        ).strip()

    @property
    def short_name(self) -> str:
        """Name without directional prefix."""
        return " ".join(
            [
                street_title_case(self.name),
                (self.suffix or "").capitalize(),
            ]
        )

    def find_current_successors(self, n=0):
        """Follow the chain of street changes all the way to the end."""
        if n > 5:
            # don't recurse more than 5 times
            return set()
        elif self.current:
            return {self}
        else:
            found = set()
            for street in self.successor_streets:
                found = found.union(street.find_current_successors(n + 1))
            return found

    @property
    def successor_streets(self) -> "list[Street]":
        """A list of successor streets."""
        return [change.to_street for change in self.successor_changes()]

    def full_geometry(self):
        """Return the geometry of this street if known, or of all successor streets, or none."""
        if self.geom:
            return self.geom
        else:
            return (
                db.session.query(func.ST_SetSRID(func.ST_Union(Street.geom), 3435))
                .filter(Street.id.in_([street.id for street in self.successor_streets]))
                .scalar()
            )

    def specific_geometry(self):
        """Return the geometry of this street.
        Either known (and stored) or calculated, based on using successor streets and known grid locations."""
        if self.geom:
            return self.geom
        else:
            current_streets = self.find_current_successors()
            if not current_streets:
                return None

            elif (
                (len(current_streets) == 1)
                and self.min_address
                and self.max_address
                and next(iter(current_streets)).direction
            ):
                fg = self.full_geometry()
                if fg is None:
                    return None
                else:
                    return clip_by_address(
                        fg,
                        next(iter(current_streets)).direction,
                        self.min_address,
                        self.max_address,
                    )

    def best_geometry(self):
        """Return either the specific geometry or the full geometry."""
        return self.specific_geometry() or self.full_geometry()

    def calculate_single_successor(self):
        """If this is succeeded by a single street, store its name and suffix."""
        # FIX ME this query is slow to run 1000s of times
        q = (
            db.session.query(Street.name, Street.suffix)
            .filter(StreetChange.from_id == self.id)
            .join(StreetChange, Street.id == StreetChange.to_id)
            .group_by(Street.name, Street.suffix)
            .all()
        )

        if len(q) == 1:
            self.successor_name = "{} {}".format(
                street_title_case(q[0].name.title()), q[0].suffix.capitalize()
            )

    def get_grid_location_from_successors(self):
        """Figure out our grid location based on our successor streets."""
        if self.diagonal or self.grid_direction or self.grid_location:
            return
        successors = self.find_current_successors()
        directions = {x.grid_direction for x in successors}
        directions.discard(None)
        if len(directions) == 1:
            self.grid_direction = directions.pop()
        locations = {x.grid_location for x in successors}
        locations.discard(None)
        if len(locations) == 1:
            self.grid_location = locations.pop()
        if any(x.diagonal for x in successors):
            self.diagonal = True

    @property
    def predecessors(self) -> "list[Street]":
        """A list of predecessor streets."""
        return [change.from_street for change in self.predecessor_changes()]

    def grid_info(self) -> str:
        """Return short text indicating grid position."""
        if self.diagonal:
            return "diag"
        elif self.grid_direction and self.grid_location:
            return "{}{}".format(self.grid_location, self.grid_direction)
        else:
            return ""

    def short_info(self) -> str:
        """Short text for after the name of a street to indicate historical status/context."""
        if not self.current:
            if self.vacated:
                status = "vacated"
            else:
                status = "retired"
                if self.successor_name:
                    status = "→ {}".format(self.successor_name)

            end_date_info = self.end_date_info()
            if end_date_info:
                return "{} {}".format(status, end_date_info)
            else:
                return status
        else:
            return "current"

    def end_date_info(self) -> str:
        """Return some info about the end date of the street."""
        if self.end_date:
            year = self.end_date.year
            if self.end_date_circa:
                c = "c."
            else:
                c = ""
            return "{}{}".format(c, year)
        else:
            return ""

    def start_date_info(self) -> str:
        """Return some info about the start date of the street."""
        if self.start_date:
            year = self.start_date.year
            if self.start_date_circa:
                c = "c."
            else:
                c = ""
            return "{}{}".format(c, year)
        else:
            return ""

    def year_range(self) -> tuple[int]:
        """Return a range of years that this street was valid between."""
        early, late = 1830, datetime.date.today().year
        if self.start_date:
            early = self.start_date.year

        if self.end_date:
            late = self.end_date.year
        return (early, late)

    @property
    def context_info(self) -> str:
        """Returns a lengthy street name + info to contexualize the street."""
        return self.full_name + " " + self.grid_info() + " " + self.short_tag()

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
    def timestamp(self) -> datetime.datetime:
        """Return the timestamp of latest edit to this street."""
        q = db.select(db.func.max(StreetEdit.timestamp).label("timestamp")).filter(
            StreetEdit.street_id == self.id
        )
        row = db.session.execute(q).one()
        if row:
            return row["timestamp"]
        else:
            return datetime.datetime.now()

    def street_lists(self) -> list:
        """Return list of street lists in which this street appears."""
        results = (
            db.session.query(StreetListEntry)
            .filter(StreetListEntry.street_id == self.id)
            .all()
        )
        return sorted([entry.list for entry in results], key=lambda x: x.date)

    def regenerate_id(self):
        """Change the street_id of this street to reflect the new name."""
        i = 0
        while (
            db.session.query(Street)
            .filter(Street.street_id == "{:.8}_{:02}".format(self.name, i))
            .first()
        ):
            i += 1
        self.street_id = "{:.8}_{:02}".format(self.name, i)

    def stored_maps(self):
        """Return the list of stored maps that this street might appear on."""
        early, late = self.year_range()
        q = (
            db.session.query(StoredMap)
            .filter(StoredMap.year >= early)
            .filter(StoredMap.year <= late)
            .filter(func.ST_Intersects(StoredMap.geom, self.best_geometry()))
        )
        return q.all()


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


class StoredMap(PkModel):
    """A map with geometry."""

    __tablename__ = "stored_map"
    name = Column(db.String(80), nullable=False)
    year = Column(db.Integer(), nullable=False, index=True)

    url = Column(db.Text())

    # other notes
    text = Column(db.Text())
    geom = Column(Geometry("GEOMETRY", srid=3435))
