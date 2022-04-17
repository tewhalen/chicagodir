# -*- coding: utf-8 -*-
"""Street forms."""
import datetime

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    Field,
    FieldList,
    Form,
    FormField,
    IntegerField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from wtforms.widgets import TextInput

direction_choices = [("", ""), ("N", "N"), ("S", "S"), ("E", "E"), ("W", "W")]


def int_or_none(x) -> int:
    """Either convert x to an int or return None."""
    try:
        return int(x)
    except TypeError:
        return None
    except ValueError:
        return None


class TagListField(Field):
    """A List of string tags."""

    widget = TextInput()

    def _value(self):
        """Process the data."""
        if self.data:
            return ", ".join(self.data)
        else:
            return ""

    def process_formdata(self, valuelist):
        """Process form data."""
        if valuelist:
            self.data = list({x.strip() for x in valuelist[0].split(",") if x.strip()})
        else:
            self.data = []


year_choices = [(None, "")] + [
    (i, str(i)) for i in reversed(range(1833, datetime.date.today().year + 1))
]


class StreetSearchForm(Form):
    """The form for searching for a street."""

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
    term = StringField("Query", validators=[Optional(), Length(max=40)])


class ChangeForm(Form):
    """The subform for modifying a successor/predecessor change."""

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

    tags = TagListField("Tags")

    new_successor_street_date = DateField("Date of Change", validators=[Optional()])
    new_successor_street_note = StringField("Note", validators=[Optional()])

    new_successor_street = SelectField(
        "Street",
        coerce=int_or_none,
    )

    def set_street_choices(self, street_choices):
        """Set up for proper street choices."""
        for successor in self.successors:
            successor.to_id.choices = street_choices

        self.new_successor_street.choices = [(None, "")] + street_choices
