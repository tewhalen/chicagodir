# -*- coding: utf-8 -*-
"""StreetList models."""


from chicagodir.database import Column, PkModel, db, reference_col, relationship
from chicagodir.streets.sorting import street_key


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

    def sorted_entries(self):
        """Return entries sorted as streets."""

        def entry_key(x):
            return street_key(x.street)

        return sorted(self.entries, key=entry_key)

    def sorted_streets(self):
        """Return sorted entries as streets."""
        return [entry.street for entry in self.sorted_entries()]


class StreetListEntry(PkModel):
    """An entry in a list of streets."""

    __tablename__ = "street_list_entries"

    list_id = reference_col("street_lists")
    list = relationship("StreetList", backref="entries", foreign_keys=[list_id])

    street_id = reference_col("streets", nullable=True)
    street = relationship("Street", foreign_keys=[street_id])
