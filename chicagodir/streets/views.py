# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
import datetime
import re

import markdown
from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from chicagodir.database import db
from chicagodir.streets.models import Street, StreetChange

from .forms import StreetEditForm, StreetSearchForm


def atoi(text):
    """Convert text to an integer if possible, else return the string."""
    return int(text) if text.isdigit() else text


def natural_keys(text):
    """For use in sorting numeric and text stuff naturally, build keys.

    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    """
    return [atoi(c) for c in re.split(r"(\d+)", text)]


def street_key(street: Street):
    """Given a street object, return an appropriate sorting key."""
    return natural_keys(street.name + " " + street.suffix + " " + street.direction)


def streets_sorted(streets):
    """Sort street objects using appropriate key."""
    return sorted(streets, key=street_key)


blueprint = Blueprint("street", __name__, static_folder="../static")


@blueprint.route("/streets", methods=["GET"])
def street_search():
    """Search database for streets."""


@blueprint.route("/street/", methods=["GET", "POST"])
def street_listing():
    """Show all the known streets."""
    form = StreetSearchForm(request.args)
    year_str = "as of today"
    if request.query_string and form.validate():
        q = db.session.query(Street)
        if form.year.data:

            year = form.year.data
            first_of_year = datetime.date(month=1, day=1, year=year)
            q = q.filter(
                ((Street.start_date < first_of_year) | (Street.start_date.is_(None)))
                & ((Street.end_date > first_of_year) | (Street.end_date.is_(None)))
            )
            year_str = "as of {}".format(str(year))

        if form.name.data:
            q = q.filter(Street.name.ilike("%" + form.name.data + "%"))

        if form.confirmed.data is not None:

            q = q.filter(Street.confirmed == form.confirmed.data)

        # end filters
        current_streets = sorted(
            q.all(),
            key=street_key,
        )
        current_app.logger.info(form.confirmed.data)

    else:
        current_streets = streets_sorted(
            db.session.query(Street).filter(Street.current.is_(True)).all()
        )
    total_count = len(current_streets)
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
        total_count=total_count,
    )


@blueprint.route(
    "/street/by_tag/<string:tag>",
    methods=[
        "GET",
    ],
)
def streets_by_tag(tag: str):
    """Show all the known streets."""
    form = StreetSearchForm(request.args)
    current_streets = streets_sorted(
        db.session.query(Street).filter(Street.tags.contains([tag]))
    )
    total_count = len(current_streets)

    street_groups = []
    for i in range(0, len(current_streets), 100):
        street_groups.append(current_streets[i : i + 100])
    # street_groups = itertools.zip_longest(current_streets * 100)
    return render_template(
        "streets/street_listing.html",
        current_streets=street_groups,
        search_form=form,
        year_str="tagged '{}'".format(tag),
        total_count=total_count,
    )


@blueprint.route(
    "/street/missing_start/",
    methods=[
        "GET",
    ],
)
def missing_start():
    """Show all the known streets."""
    form = StreetSearchForm(request.args)
    current_streets = streets_sorted(
        db.session.query(Street).filter(Street.start_date.is_(None)).all()
    )
    total_count = len(current_streets)

    street_groups = []
    for i in range(0, len(current_streets), 100):
        street_groups.append(current_streets[i : i + 100])
    # street_groups = itertools.zip_longest(current_streets * 100)
    return render_template(
        "streets/street_listing.html",
        current_streets=street_groups,
        search_form=form,
        year_str="missing start year",
        total_count=total_count,
    )


@blueprint.route(
    "/street/missing_end/",
    methods=[
        "GET",
    ],
)
def missing_end():
    """Show all the known streets that are not current but have no end date."""
    form = StreetSearchForm(request.args)
    current_streets = streets_sorted(
        db.session.query(Street)
        .filter((Street.end_date.is_(None)) & (Street.current.is_not(True)))
        .all()
    )
    total_count = len(current_streets)

    street_groups = []
    for i in range(0, len(current_streets), 100):
        street_groups.append(current_streets[i : i + 100])
    # street_groups = itertools.zip_longest(current_streets * 100)
    return render_template(
        "streets/street_listing.html",
        current_streets=street_groups,
        search_form=form,
        year_str="missing retirement year",
        total_count=total_count,
    )


@blueprint.route("/street/<string:tag>/", methods=["GET", "POST"])
def view_street(tag: str):
    """Let's look at a historical street."""
    try:
        d = Street.query.filter_by(street_id=tag).one()
    except NoResultFound:
        abort(404)
    except MultipleResultsFound:
        abort(500)
    return render_template(
        "streets/street_index.html",
        street=d,
        source_notes=markdown.markdown(d.text.replace("\t", "")),
    )


def remove_successor(street, change_to_remove):
    """Remove an association to a successor street."""
    street.record_edit(
        current_user,
        "removed sucessor {} ({})".format(
            change_to_remove.to_street.full_name, change_to_remove.to_street.street_id
        ),
    )
    change_to_remove.to_street.record_edit(
        current_user,
        "removed predecessor {} ({})".format(street.full_name, street.street_id),
    )
    change_to_remove.delete()


def add_successor(street, new_successor):
    """Record the addition of a new successor."""
    street.record_edit(
        current_user,
        "added successor {} ({})".format(
            new_successor.to_street.full_name, new_successor.to_street.street_id
        ),
    )
    new_successor.to_street.record_edit(
        current_user,
        "added predecessor {} ({})".format(street.full_name, street.street_id),
    )


@blueprint.route("/street/<string:tag>/edit", methods=["GET", "POST"])
@login_required
def edit_street(tag: str):
    """Editing a street."""
    try:
        d = Street.query.filter_by(street_id=tag).one()
    except NoResultFound:
        abort(404)
    except MultipleResultsFound:
        abort(500)

    # WTForms is weird when the method is GET
    if request.method != "GET":
        form = StreetEditForm(request.form, obj=d)
    else:
        form = StreetEditForm(None, obj=d)

    # set up street choices
    street_choices = [
        (street.id, street.full_name)
        for street in streets_sorted(d.contemporary_streets())
    ]
    form.set_street_choices(street_choices)

    if form.validate_on_submit():
        form.populate_obj(d)

        # remove successor streets marked for deletion
        for to_remove in [x for x in d.successors if x.remove]:
            remove_successor(d, to_remove)

        #  check for new successor street
        if form.new_successor_street.data is not None:
            new_successor = StreetChange(
                from_id=d.id,
                to_id=form.new_successor_street.data,
                date=form.new_successor_street_date.data,
                note=form.new_successor_street_note.data,
            )
            new_successor.save()
            add_successor(d, new_successor)

        d.record_changes(current_user)

        d.save()
        return redirect(url_for("street.view_street", tag=tag))
    elif form.is_submitted():
        current_app.logger.warning("submitted but invalid")
    return render_template("streets/street_edit.html", street=d, street_form=form)
