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


def int_or_none(x):
    try:
        return int(x)
    except TypeError:
        return None
    except ValueError:
        return None


year_choices = [(None, "")] + [
    (i, str(i)) for i in reversed(range(1833, datetime.date.today().year + 1))
]


class StreetSearchForm(Form):
    name = StringField("Name", validators=[Optional(), Length(max=40)])
    year = SelectField(
        "Year",
        coerce=int_or_none,
        validators=[Optional()],
        choices=year_choices
        # list(reversed(range(1833, datetime.date.today().year + 1))),
        # default=datetime.date.today().year,
    )
    confirmed = BooleanField("Confirmed")


class ChangeForm(Form):

    date = DateField("Date of Change", validators=[Optional()])
    note = StringField("Note", validators=[Optional()])
    remove = BooleanField("Current", default=False)
    to_id = SelectField(
        "Street",
        coerce=int,
    )
    # from_id = SelectField("Street", coerce=int)


class StreetEditForm(FlaskForm):
    """Register form."""

    direction = SelectField("Direction", choices=direction_choices)
    name = StringField("Name", validators=[DataRequired(), Length(max=40)])

    suffix = StringField("Suffix", validators=[Length(max=8)])

    grid_direction = SelectField("Grid Direction", choices=direction_choices)

    grid_location = IntegerField(
        "Grid Location", validators=[Optional(), NumberRange(min=0, max=150000)]
    )
    diagonal = BooleanField("Diagonal")
    max_address = IntegerField(
        "Max Address", validators=[Optional(), NumberRange(min=0, max=1500000)]
    )
    min_address = IntegerField(
        "Min Address", validators=[Optional(), NumberRange(min=0, max=150000)]
    )

    suffix_direction = SelectField("Suffix Direction", choices=direction_choices)

    start_date = DateField("Start Date", validators=[Optional()])
    start_date_circa = BooleanField("circa")

    end_date = DateField("End Date", validators=[Optional()])
    end_date_circa = BooleanField("circa")

    current = BooleanField("Current")
    vacated = BooleanField("Vacated")

    historical_note = TextAreaField("Historical Note")
    text = TextAreaField("Source Notes")
    successors = FieldList(FormField(ChangeForm))
    confirmed = BooleanField("Confirmed")
    weird = BooleanField("Weird")
    skip = BooleanField("Skip")

    new_successor_street_date = DateField("Date of Change", validators=[Optional()])
    new_successor_street_note = StringField("Note", validators=[Optional()])

    new_successor_street = SelectField(
        "Street",
        coerce=int_or_none,
    )
