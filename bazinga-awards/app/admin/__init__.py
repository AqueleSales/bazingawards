from flask import Blueprint

main_bp = Blueprint("main", __name__)

from . import routes  # noqa: E402,F401


# No seu arquivo principal de criação do app (provavelmente onde tem db.init_app),
# você precisará registrar esse blueprint:
# app.register_blueprint(admin_bp)