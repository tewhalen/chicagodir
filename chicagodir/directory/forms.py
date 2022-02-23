# -*- coding: utf-8 -*-
"""Street forms."""
import datetime

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    FieldList,
    Form,
    FormField,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional

direction_choices = [("", ""), ("N", "N"), ("S", "S"), ("E", "E"), ("W", "W")]


def int_or_none(x) -> int:
    """Either convert x to an int or return None."""
    try:
        return int(x)
    except TypeError:
        return None
    except ValueError:
        return None


class EntryForm(Form):
    """The subform for modifying a successor/predecessor change."""

    remove = BooleanField("Remove", default=False)
    street_id = SelectField(
        "Street",
        coerce=int,
    )
    # from_id = SelectField("Street", coerce=int)


class StreetListForm(FlaskForm):
    """Form for modifying a street list."""

    name = StringField("Name", validators=[DataRequired(), Length(max=40)])

    date = DateField("Start Date", validators=[Optional()])

    url = StringField("URL", validators=[Optional()])

    entries = FieldList(FormField(EntryForm))

    new_entry_street = SelectField(
        "Street",
        coerce=int_or_none,
    )

    def set_street_choices(self, street_choices):
        """Set up for proper street choices."""
        for entry in self.entries:
            entry.street_id.choices = street_choices

        self.new_entry_street.choices = [(None, "")] + street_choices
