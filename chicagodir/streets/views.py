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
    abort,
)
from flask_login import login_required, login_user, logout_user, current_user
from chicagodir.database import db
from chicagodir.extensions import login_manager
from chicagodir.streets.models import Street, StreetEdit, StreetChange
from chicagodir.utils import flash_errors
from .forms import StreetEditForm, StreetSearchForm
from sqlalchemy import inspect
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

import markdown
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


def streets_sorted(streets):
    return sorted(streets, key=street_key)


blueprint = Blueprint("street", __name__, static_folder="../static")


@blueprint.route("/street/", methods=["GET", "POST"])
def street_listing():
    """Show all the known streets."""
    form = StreetSearchForm(request.args)
    year_str = "today"
    if request.query_string and form.validate():
        q = db.session.query(Street)
        if form.year.data:

            year = form.year.data
            first_of_year = datetime.date(month=1, day=1, year=year)
            q = q.filter(
                ((Street.start_date < first_of_year) | (Street.start_date == None))
                & ((Street.end_date > first_of_year) | (Street.end_date == None))
            )
            year_str = str(year)

        if form.name.data:
            q = q.filter(Street.name.ilike("%" + form.name.data + "%"))

        if form.confirmed.data != None:

            q = q.filter(Street.confirmed == form.confirmed.data)

        # end filters
        current_streets = sorted(
            q.all(),
            key=street_key,
        )
        current_app.logger.info(form.confirmed.data)

    else:
        current_streets = streets_sorted(
            db.session.query(Street).filter(Street.current == True).all()
        )

    street_groups = []
    for i in range(0, len(current_streets), 100):
        street_groups.append(current_streets[i : i + 100])
    # street_groups = itertools.zip_longest(current_streets * 100)
    return render_template(
        "streets/street_listing.html",
        current_streets=street_groups,
        # withdrawn_streets=Street.query.filter_by(current=False).all(),
        search_form=form,
        year_str=year_str,
    )


@blueprint.route("/street/year/<int:year>", methods=["GET", "POST"])
def street_listing_by_year(year):
    """Show all the known streets."""

    first_of_year = datetime.date(month=1, day=1, year=year)

    current_streets = streets_sorted(
        db.session.query(Street)
        .filter(
            ((Street.start_date < first_of_year) | (Street.start_date == None))
            & ((Street.end_date > first_of_year) | (Street.end_date == None))
        )
        .all()
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
    try:
        d = Street.query.filter_by(street_id=tag).first_or_404()
    except NoResultFound:
        abort(404)
    except MultipleResultsFound:
        abort(500)
    return render_template(
        "streets/street_index.html",
        street=d,
        source_notes=markdown.markdown(d.text.replace("\t", "")),
    )


@blueprint.route("/street/<string:tag>/edit", methods=["GET", "POST"])
@login_required
def edit_street(tag: str):
    try:
        d = Street.query.filter_by(street_id=tag).one()
    except NoResultFound:
        abort(404)
    except MultipleResultsFound:
        abort(500)

    if request.method != "GET":
        form = StreetEditForm(request.form, obj=d)
    else:
        form = StreetEditForm(None, obj=d)

    if d.end_date is None:

        street_choices = [
            (street.id, street.full_name)
            for street in streets_sorted(db.session.query(Street).all())
        ]
    else:
        street_choices = [
            (street.id, street.full_name)
            for street in streets_sorted(
                db.session.query(Street)
                .filter(
                    ((Street.start_date < d.end_date) | (Street.start_date == None))
                )
                .all()
            )
        ]
    for successor in form.successors:
        successor.to_id.choices = street_choices

    form.new_successor_street.choices = [(None, "")] + street_choices

    if form.validate_on_submit():
        form.populate_obj(d)

        changes = {}
        # remove successor streets marked for deletion
        for to_remove in [x for x in d.successors if x.remove]:
            d.record_edit(
                current_user,
                "removed sucessor {} ({})".format(
                    to_remove.to_street.full_name, to_remove.to_street.street_id
                ),
            )
            to_remove.delete()

        #  check for new successor street
        if form.new_successor_street.data is not None:
            new_successor = StreetChange(
                from_id=d.id,
                to_id=form.new_successor_street.data,
                date=form.new_successor_street_date.data,
                note=form.new_successor_street_note.data,
            )
            new_successor.save()
            d.record_edit(
                current_user,
                "added successor {} ({})".format(
                    new_successor.to_street.full_name, new_successor.to_street.street_id
                ),
            )

        for attr in inspect(d).attrs:
            if attr.history.has_changes():
                changes[attr.key] = attr.history.added
        if changes:
            d.record_edit(current_user, str(changes))
            current_app.logger.info(changes)
        d.save()
        return redirect(url_for("street.view_street", tag=tag))
    elif form.is_submitted():
        current_app.logger.warning("submitted but invalid")
    return render_template("streets/street_edit.html", street=d, street_form=form)
