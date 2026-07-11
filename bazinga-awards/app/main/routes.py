from flask import render_template, session

from ..models import Person
from . import main_bp


@main_bp.route("/")
def index():
    person = None
    if "person_id" in session:
        person = Person.query.get(session["person_id"])
    return render_template("index.html", person=person)
