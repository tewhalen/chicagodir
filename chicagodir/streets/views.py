# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required, login_user, logout_user, current_user
from chicagodir.database import db
from chicagodir.extensions import login_manager
from chicagodir.streets.models import Street, StreetEdit
from chicagodir.utils import flash_errors
from .forms import StreetEditForm
from sqlalchemy import inspect

import itertools

import os
import re
import csv
import datetime


def atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    """
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    """
    return [atoi(c) for c in re.split(r"(\d+)", text)]


def street_key(street: Street):
    return natural_keys(street.name + " " + street.suffix + " " + street.direction)


blueprint = Blueprint("street", __name__, static_folder="../static")


@blueprint.route("/street/", methods=["GET", "POST"])
def street_listing():
    """Show all the known streets."""
    current_streets = sorted(Street.query.filter_by(current=True).all(), key=street_key)
    street_groups = []
    for i in range(0, len(current_streets), 100):
        street_groups.append(current_streets[i : i + 100])
    # street_groups = itertools.zip_longest(current_streets * 100)
    return render_template(
        "streets/street_listing.html",
        current_streets=street_groups,
        withdrawn_streets=Street.query.filter_by(current=False).all(),
    )


@blueprint.route("/street/year/<int:year>", methods=["GET", "POST"])
def street_listing_by_year(year):
    """Show all the known streets."""

    first_of_year = datetime.date(month=1, day=1, year=year)

    current_streets = sorted(
        db.session.query(Street)
        .filter(
            ((Street.start_date < first_of_year) | (Street.start_date == None))
            & ((Street.end_date > first_of_year) | (Street.end_date == None))
        )
        .all(),
        key=street_key,
    )

    street_groups = []
    for i in range(0, len(current_streets), 100):
        street_groups.append(current_streets[i : i + 100])
    # street_groups = itertools.zip_longest(current_streets * 100)
    return render_template(
        "streets/street_by_year.html",
        current_streets=street_groups,
    )


@blueprint.route("/street/<string:tag>/", methods=["GET", "POST"])
def view_street(tag: str):
    d = Street.query.filter_by(street_id=tag).one()
    return render_template("streets/street_index.html", street=d)


@blueprint.route("/street/<string:tag>/edit", methods=["GET", "POST"])
@login_required
def edit_street(tag: str):
    d = Street.query.filter_by(street_id=tag).one()

    form = StreetEditForm(request.form, obj=d)
    for successor in form.successors:
        successor.to_id.choices = [
            (street.id, street.full_name) for street in db.session.query(Street).all()
        ]

    if form.validate_on_submit():
        form.populate_obj(d)

        changes = {}
        for attr in inspect(d).attrs:
            if attr.history.has_changes():
                changes[attr.key] = attr.history.added
        if changes:
            change_object = StreetEdit(street=d, user=current_user, note=str(changes))
            change_object.save()
            current_app.logger.info(changes)
        d.save()
        return redirect(url_for("street.view_street", tag=tag))
    elif form.is_submitted():
        current_app.logger.warning("submitted but invalid")
    return render_template("streets/street_edit.html", street=d, street_form=form)
