# -*- coding: utf-8 -*-
"""Street forms."""
from calendar import c
from email.policy import default
from xmlrpc.client import Boolean
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SelectField,
    IntegerField,
    DateField,
    BooleanField,
    TextAreaField,
    FieldList,
    Form,
    FormField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
)

from .models import Street, StreetChange

direction_choices = [("", ""), ("N", "N"), ("S", "S"), ("E", "E"), ("W", "W")]


class ChangeForm(Form):

    date = DateField("Date of Change", validators=[Optional()])
    note = StringField("Note", validators=[Optional()])
    remove = BooleanField("Current", default=False)
    to_id = SelectField(
        "Street",
        coerce=int,
    )
    from_id = SelectField("Street", coerce=int)


class StreetEditForm(FlaskForm):
    """Register form."""

    direction = SelectField("Direction", choices=direction_choices)
    name = StringField("Name", validators=[DataRequired(), Length(max=40)])

    suffix = StringField("Suffix", validators=[Length(max=8)])

    grid_direction = SelectField("Grid Direction", choices=direction_choices)

    grid_location = IntegerField(
        "Grid Location", validators=[Optional(), NumberRange(min=0, max=150000)]
    )

    max_address = IntegerField(
        "Max Address", validators=[Optional(), NumberRange(min=0, max=150000)]
    )
    min_address = IntegerField(
        "Min Address", validators=[Optional(), NumberRange(min=0, max=150000)]
    )

    suffix_direction = SelectField("Suffix Direction", choices=direction_choices)

    start_date = DateField("Start Date", validators=[Optional()])
    end_date = DateField("End Date", validators=[Optional()])
    current = BooleanField("Current", default=True)

    historical_note = TextAreaField("Historical Note")

    successors = FieldList(FormField(ChangeForm))
    confirmed = BooleanField("Confirmed", default=True)
    weird = BooleanField("Weird", default=True)
    skip = BooleanField("Skip", default=True)
