# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
import csv

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from chicagodir.directory.models import Directory, Page, get_all_jobs

blueprint = Blueprint("dir", __name__, static_folder="../static")


@blueprint.route("/dir/", methods=["GET", "POST"])
def directory_listing():
    """Show all the directories."""

    return render_template("dir/direct_listing.html", directories=Directory.query.all())


@blueprint.route("/jobs/", methods=["GET", "POST"])
def profession_listing():
    """Show all the known professions."""

    return render_template("dir/job_listing.html", jobs=get_all_jobs())


@blueprint.route("/dir/new", methods=["GET", "POST"])
@login_required
def new_directory():
    """Show all the directories."""
    d = Directory(name="Lakeside Directory", year="1911", tag="lakeside-1911")
    d.save()
    return redirect("/dir/")


@blueprint.route("/dir/<string:tag>/", methods=["GET", "POST"])
def view_directory(tag: str):
    d = Directory.query.filter_by(tag=tag).one()
    return render_template("dir/direct_index.html", directory=d)


@blueprint.route("/dir/<string:tag>/p/<int:page>", methods=["GET", "POST"])
def view_page(tag: str, page: int):
    d = Directory.query.filter_by(tag=tag).one()
    page = Page.query.filter_by(directory_id=d.id, number=page).first()
    return render_template("dir/page_listing.html", directory=d, page=page)


@blueprint.route("/dir/<string:tag>/p/<int:page_id>/fix", methods=["GET", "POST"])
def fix_page(tag: str, page_id: int):
    d = Directory.query.filter_by(tag=tag).one()
    page = Page.query.filter_by(directory_id=d.id, number=page_id).first()
    for entry in page.entries:
        if entry.home_address:
            if entry.home_address.find_street():
                entry.save()
    return redirect(url_for("dir.view_page", tag=tag, page=page_id))


@blueprint.route("/dir/<string:tag>/page/upload", methods=["GET", "POST"])
@login_required
def upload_csv(tag: str):
    d = Directory.query.filter_by(tag=tag).one()
    if request.method == "POST":
        # check if the post request has the file part
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files["file"]
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        if file:
            csv_output = d.new_page(
                list(csv.DictReader(x.decode() for x in file.stream))
            )
        else:
            csv_output = []
    return render_template("dir/new_page.html", csv_output=csv_output, directory=d)
