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
from flask_login import login_required, login_user, logout_user

from chicagodir.extensions import login_manager
from chicagodir.public.forms import LoginForm
from chicagodir.streets.models import Street
from chicagodir.user.forms import RegisterForm
from chicagodir.user.models import User
from chicagodir.utils import flash_errors

blueprint = Blueprint("public", __name__, static_folder="../static")


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.get_by_id(int(user_id))


@blueprint.route("/", methods=["GET", "POST"])
def home():
    """Home page."""
    form = LoginForm(request.form)
    current_app.logger.info("Hello from the home page!")
    # Handle logging in
    if request.method == "POST":
        if form.validate_on_submit():
            login_user(form.user)
            flash("You are logged in.", "success")
            redirect_url = request.args.get("next") or url_for("user.members")
            return redirect(redirect_url)
        else:
            flash_errors(form)
    return render_template("public/home.html", form=form)


@blueprint.route("/logout/")
@login_required
def logout():
    """Logout."""
    logout_user()
    flash("You are logged out.", "info")
    return redirect(url_for("public.home"))


@blueprint.route("/register/", methods=["GET", "POST"])
def register():
    """Register new user."""
    form = RegisterForm(request.form)
    if form.validate_on_submit():
        User.create(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            active=True,
        )
        flash("Thank you for registering. You can now log in.", "success")
        return redirect(url_for("public.home"))
    else:
        flash_errors(form)
    return render_template("public/register.html", form=form)


@blueprint.route("/about/")
def about():
    """About page."""
    form = LoginForm(request.form)
    return render_template("public/about.html", form=form)


@blueprint.route("/help_out/")
def help_out():
    """About page."""
    form = LoginForm(request.form)
    missing_end_dates = Street.query.filter_by(end_date=None, current=False).count()
    missing_start_dates = Street.query.filter_by(start_date=None).count()
    missing_grid_location = Street.query.filter_by(
        grid_location=None, current=True
    ).count()
    unchecked_streets = Street.query.filter_by(confirmed=False).count()

    return render_template(
        "public/help_out.html",
        form=form,
        missing_end_dates=missing_end_dates,
        missing_start_dates=missing_start_dates,
        missing_grid_location=missing_grid_location,
        unchecked_streets=unchecked_streets,
    )
