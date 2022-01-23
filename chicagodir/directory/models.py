# -*- coding: utf-8 -*-
"""Directory models."""
from ast import Add
import datetime as dt
from email.policy import default

from chicagodir.database import Column, PkModel, db, reference_col, relationship
from chicagodir.extensions import bcrypt
from chicagodir.streets.models import Street


def get_all_jobs():
    return (
        db.session.query(Entry.profession, db.func.count(Entry.id))
        .group_by(Entry.profession)
        .order_by(db.func.count(Entry.id).desc())
    )


class Directory(PkModel):
    """A directory stored in the app."""

    __tablename__ = "directories"
    name = Column(db.String(80), unique=True, nullable=False)
    year = Column(db.Integer(), nullable=False)
    tag = Column(db.String(15), unique=True, nullable=False)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<Dir({self.year}|{self.name!r})>"

    def new_page(self, csv_output):
        new_page_num = csv_output[0]["page"]
        # check to see if page already exists
        existing_page = Page.query.filter(
            db.and_(Page.number == new_page_num, Page.directory == self)
        ).one_or_none()
        if existing_page:
            db.session.delete(existing_page)
        new_page = Page(number=new_page_num, directory=self)
        new_page.save()
        i = 0
        rows = []
        for row in csv_output:
            new_entry = Entry(page_id=new_page.id)
            new_entry.first_name = row["FirstName"]
            new_entry.last_name = row["LastName"]
            new_entry.middle_name = row["MiddleName"]
            new_entry.profession = row["Profession"]
            new_entry.widow = bool(row["Widow"])
            new_entry.home_address = HomeAddress(
                number=row["HomeAddressNumber"],
                street_name_pre_directional=row["HomeAddressStreetNamePreDirectional"],
                street_name_pre_type=row["HomeAddressStreetNamePreType"],
                street_name=row["HomeAddressStreetName"],
                street_name_post_type=row["HomeAddressStreetNamePostType"],
                subaddress_type=row["HomeAddressSubaddressType"],
                subaddress_identifier=row["HomeAddressSubaddressIdentifier"],
                building_name=row["HomeAddreessBuildingName"],
                place_name=row["HomeAddressPlaceName"],
                dir_entry=new_entry,
            )
            new_entry.home_address.save()
            new_entry.home_address.find_street()
            new_entry.work_address = WorkAddress(
                number=row["WorkAddressNumber"],
                street_name_pre_directional=row["WorkAddressStreetNamePreDirectional"],
                street_name_pre_type=row["WorkAddressStreetNamePreType"],
                street_name=row["WorkAddressStreetName"],
                street_name_post_type=row["WorkAddressStreetNamePostType"],
                subaddress_type=row["WorkAddressSubaddressType"],
                subaddress_identifier=row["WorkAddressSubaddressIdentifier"],
                building_name=row["WorkAddressBuildingName"],
                dir_entry=new_entry,
            )
            new_entry.work_address.save()
            new_entry.work_address.find_street()
            rows.append(new_entry)
            new_entry.save()
            i += 1
        return i


class Page(PkModel):
    """A page of a directory."""

    __tablename__ = "pages"
    number = Column(db.Integer(), nullable=False)
    directory_id = reference_col(
        "directories",
    )
    directory = relationship("Directory", backref="pages")


class Address(PkModel):

    __tablename__ = "d_address"

    type_ = db.Column(db.String(20), nullable=False)

    __mapper_args__ = {"polymorphic_on": type_}

    number_prefix = Column(db.String(), default="")
    number = Column(db.Integer())
    number_suffix = Column(db.String(), default="")
    street_name_pre_directional = Column(db.String(), default="")
    street_name_pre_type = Column(db.String(), default="")
    street_name = Column(db.String(), default="")
    street_name_post_type = Column(db.String(), default="")
    subaddress_type = Column(db.String(), default="")
    subaddress_identifier = Column(db.String(), default="")
    building_name = Column(db.String(), default="")
    place_name = Column(db.String(), default="")
    corner_of = Column(db.String(), default="")

    street_id = reference_col("streets", nullable=True)
    street = relationship("Street", foreign_keys=[street_id])

    def find_street(self):
        self.street = Street.find_best_street(
            name=self.street_name,
            suffix=self.street_name_post_type,
            direction=self.street_name_pre_directional,
            year=self.dir_entry.page.directory.year,
        )
        return self.street

    def render(self):
        return " ".join(
            map(
                str,
                [
                    self.number_prefix,
                    self.number,
                    self.number_suffix,
                    self.street_name_pre_directional,
                    self.street_name_pre_type,
                    self.street_name,
                    self.street_name_post_type,
                    self.subaddress_type,
                    self.subaddress_identifier,
                    self.building_name,
                    self.place_name,
                    self.corner_of,
                ],
            )
        )


class HomeAddress(Address):
    __mapper_args__ = {"polymorphic_identity": "home"}


class WorkAddress(Address):
    __mapper_args__ = {"polymorphic_identity": "work"}


class Entry(PkModel):
    """A directory entry."""

    __tablename__ = "entries"
    ocr_id = Column(db.String(20))
    # bbox = Column(db.String())

    page_id = reference_col("pages")
    page = relationship("Page", backref="entries")

    first_name = Column(db.String())
    last_name = Column(db.String())
    middle_name = Column(db.String())
    suffix_generational = Column(db.String())
    title = Column(db.String())
    spouse_name = Column(db.String())
    profession = Column(db.String())
    widow = Column(db.Boolean())
    company_name = Column(db.String())

    work_address_id = reference_col("d_address", nullable=True)
    work_address = relationship(
        "WorkAddress",
        backref=db.backref("dir_entry", uselist=False),
        foreign_keys=[work_address_id],
        uselist=False,
    )

    home_address_id = reference_col("d_address", nullable=True)
    home_address = relationship(
        "HomeAddress",
        backref=db.backref("dir_entry", uselist=False),
        foreign_keys=[home_address_id],
        uselist=False,
    )

    telephone_number = Column(db.String())

    # bookkeeping

    # checked by a human and fixed
    confirmed = Column(db.Boolean(), default=False)

    # something odd about this, doesn't fit schema
    weird = Column(db.Boolean(), default=False)

    # this is a bad entry, just skip it
    skip = Column(db.Boolean(), default=False)
