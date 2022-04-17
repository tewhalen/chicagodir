# -*- coding: utf-8 -*-
"""Street forms."""

from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, StringField
from wtforms.validators import DataRequired, Length, Optional

direction_choices = [("", ""), ("N", "N"), ("S", "S"), ("E", "E"), ("W", "W")]


def int_or_none(x) -> int:
    """Either convert x to an int or return None."""
    try:
        return int(x)
    except TypeError:
        return None
    except ValueError:
        return None


class StreetListForm(FlaskForm):
    """Form for modifying a street list."""

    name = StringField("Name", validators=[DataRequired(), Length(max=40)])

    date = DateField("Start Date", validators=[Optional()])

    url = StringField("URL", validators=[Optional()])

    # entries = FieldList(FormField(EntryForm))

    new_entry_street = IntegerField(
        "Street",
    )
