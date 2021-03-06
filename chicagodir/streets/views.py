# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
import datetime
import io

import markdown
import redis
from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from rq import Connection, Queue
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from chicagodir.database import db
from chicagodir.directory.forms import StreetListForm
from chicagodir.streets.models import Street, StreetChange
from chicagodir.streets.sorting import streets_sorted
from chicagodir.streets.streetlist import StreetList, StreetListEntry

from .forms import StreetEditForm, StreetSearchForm
from .tasks import (
    calc_successor_info,
    inherit_grid,
    redraw_affected_tags,
    redraw_map_for_street,
    redraw_map_for_streetlist,
    refresh_community_area_tags,
)

blueprint = Blueprint("street", __name__, static_folder="../static")

# lifted from sqlalchemy_utils
# \ is the escape character postgres defaults to
def escape_like(string, escape_char="\\"):
    """
    Escape the string paremeter used in SQL LIKE expressions.

    ::

        from sqlalchemy_utils import escape_like


        query = session.query(User).filter(
            User.name.ilike(escape_like('John'))
        )


    :param string: a string to escape
    :param escape_char: escape character
    """
    return (
        string.replace(escape_char, escape_char * 2)
        .replace("%", escape_char + "%")
        .replace("_", escape_char + "_")
    )


@blueprint.route("/streets", methods=["GET"])
def street_search():
    """Search database for streets."""
    form = StreetSearchForm(request.args)
    if request.query_string and form.validate():
        q = db.session.query(Street)
        if form.year.data:

            year = form.year.data
            first_of_year = datetime.date(month=1, day=1, year=year)
            q = q.filter(
                ((Street.start_date < first_of_year) | (Street.start_date.is_(None)))
                & ((Street.end_date > first_of_year) | (Street.end_date.is_(None)))
            )
        if form.term.data:
            q = q.filter(
                (Street.name.ilike("%" + escape_like(form.term.data) + "%"))
                | (Street.street_id.ilike(escape_like(form.term.data) + "%"))
            )

        results = streets_sorted(q.limit(15).all())
        return jsonify(
            [
                {
                    "name": street.full_name,
                    "id": street.id,
                    "info": street.short_tag(),
                    "label": street.context_info,
                }
                for street in results
            ]
        )


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
            q = q.filter(Street.name.ilike("%" + escape_like(form.name.data) + "%"))

        if form.confirmed.data is not None:

            q = q.filter(Street.confirmed == form.confirmed.data)

        # end filters
        current_streets = streets_sorted(q.all())
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

        with Connection(redis.from_url(current_app.config["REDIS_URL"])):
            q = Queue()
            q.enqueue(refresh_community_area_tags, d.street_id)
            q.enqueue(redraw_map_for_street, d.street_id)
            q.enqueue(calc_successor_info, d.street_id)
            q.enqueue(inherit_grid, d.street_id)
            q.enqueue(redraw_affected_tags, d.street_id)

        return redirect(url_for("street.view_street", tag=tag))
    elif form.is_submitted():
        current_app.logger.warning("submitted but invalid")
    return render_template("streets/street_edit.html", street=d, street_form=form)


@blueprint.route("/streets/list/<int:streetlist_id>/", methods=["GET", "POST"])
def view_streetlist(streetlist_id: int):
    """Viewing a streetlist."""
    try:
        sl = StreetList.query.filter_by(id=streetlist_id).one()
    except NoResultFound:
        abort(404)
    except MultipleResultsFound:
        abort(500)

    return render_template(
        "streets/streetlist_view.html",
        streetlist=sl,
    )


@blueprint.route("/streets/list/new", methods=["GET", "POST"])
@login_required
def new_streetlist():
    """Create a new a streetlist."""
    streetlist = StreetList(name="new streetlist", date=datetime.date.today())
    streetlist.save()
    return redirect(url_for("street.view_streetlist", streetlist_id=streetlist.id))


@blueprint.route("/street/new", methods=["GET", "POST"])
@login_required
def new_street():
    """Create a new a streetlist."""
    street = Street.empty_street()

    street.save()
    return redirect(url_for("street.edit_street", tag=street.street_id))


@blueprint.route("/street/<string:street_id>/regen_id", methods=["GET", "POST"])
@login_required
def regenerate_street_id(street_id: str):
    """Regenerate the street id for this street."""
    """Editing a street."""
    try:
        street = Street.query.filter_by(street_id=street_id).one()
    except NoResultFound:
        abort(404)
    except MultipleResultsFound:
        abort(500)

    street.regenerate_id()

    street.save()
    return redirect(url_for("street.edit_street", tag=street.street_id))


@blueprint.route("/streets/list/<int:streetlist_id>/edit", methods=["GET", "POST"])
@login_required
def edit_streetlist(streetlist_id: int):
    """View a street list associated with a directory."""
    try:
        street_list = StreetList.query.filter_by(id=streetlist_id).one()
    except NoResultFound:
        abort(404)
    except MultipleResultsFound:
        abort(500)

    form = StreetListForm(request.form, obj=street_list)

    # form.set_street_choices(street_choices)

    if form.validate_on_submit():
        form.populate_obj(street_list)

        #  check for new successor street
        if form.new_entry_street.data is not None:
            new_entry = street_list.new_entry(street_id=form.new_entry_street.data)

            new_entry.save()
        street_list.save()
        form = StreetListForm(request.form, obj=street_list)

        with Connection(redis.from_url(current_app.config["REDIS_URL"])):
            q = Queue()
            q.enqueue(redraw_map_for_streetlist, street_list.id)

    return render_template(
        "streets/streetlist_edit.html", streetlist=street_list, street_list_form=form
    )


@blueprint.route(
    "/streets/list/<int:streetlist_id>/edit/remove/<int:entry_id>/", methods=["GET"]
)
@login_required
def remove_street_from_streetlist(streetlist_id: int, entry_id: int):
    """Remove a street from directory streetlist."""
    try:
        entry = StreetListEntry.query.filter_by(id=entry_id).one()
    except NoResultFound:
        abort(404)
    except MultipleResultsFound:
        abort(500)

    if entry is not None:
        entry.delete()
    return redirect(url_for("street.edit_streetlist", streetlist_id=streetlist_id))


@blueprint.route("/streets/lists/", methods=["GET"])
def list_streetlists():
    """Show all the known streetlists."""
    streetlists = sorted(db.session.query(StreetList).all(), key=lambda x: x.date)

    return render_template(
        "streets/streetlist_list.html",
        streetlists=streetlists,
    )


@blueprint.route("/streets/tags/", methods=["GET"])
def list_tags():
    """Show all the known tags."""
    streets_with_tags = (
        db.session.query(Street).filter(Street.tags != None).all()  # noqa
    )

    all_tags = set()
    for street in streets_with_tags:
        all_tags.update(set(street.tags))

    all_tags = sorted(list((all_tags)))
    return render_template(
        "streets/tags_list.html",
        all_tags=all_tags,
    )


@blueprint.route("/streets/tags/<string:tag>/", methods=["GET", "POST"])
def view_tag(tag: str):
    """Viewing a tag."""
    streets = db.session.query(Street).filter(Street.tags.contains([tag])).all()
    if not streets:
        abort(404)

    return render_template(
        "streets/tag_view.html",
        tag=tag,
        streetlist=streets_sorted(streets),
    )


@blueprint.route("/streets/tags/<string:tag>/edit", methods=["GET", "POST"])
def edit_tag(tag: str):
    """Editing a tag."""
    streets = db.session.query(Street).filter(Street.tags.contains([tag])).all()
    if not streets:
        abort(404)

    return render_template(
        "streets/tag_view.html",
        tag=tag,
        streetlist=streets_sorted(streets),
    )


@blueprint.route("/streets/export", methods=["GET"])
def export_streets_csv():
    """Dump csv."""
    sql = """COPY streets to STDIN WITH (FORMAT csv, DELIMITER ',', QUOTE '"', HEADER TRUE)"""
    file = io.StringIO()
    connection = db.get_engine().raw_connection()
    cur = connection.cursor()
    cur.copy_expert(sql, file)
    output = make_response(file.getvalue())
    output.headers["Content-type"] = "text/csv"
    output.headers["Content-Disposition"] = "attachment; filename=export.csv"
    return output
