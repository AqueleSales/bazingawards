from flask import Flask

from .auth import auth_bp, oauth
from .config import Config
from .main import main_bp
from .models import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    oauth.init_app(app)
    _register_oauth_providers(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    return app


def _register_oauth_providers(app):
    """Só registra um provedor se as credenciais dele existirem no .env.
    Sem isso, /auth/login/<provider> avisa que falta configurar."""

    if app.config.get("GOOGLE_CLIENT_ID") and app.config.get("GOOGLE_CLIENT_SECRET"):
        oauth.register(
            name="google",
            client_id=app.config["GOOGLE_CLIENT_ID"],
            client_secret=app.config["GOOGLE_CLIENT_SECRET"],
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    if app.config.get("DISCORD_CLIENT_ID") and app.config.get("DISCORD_CLIENT_SECRET"):
        oauth.register(
            name="discord",
            client_id=app.config["DISCORD_CLIENT_ID"],
            client_secret=app.config["DISCORD_CLIENT_SECRET"],
            access_token_url="https://discord.com/api/oauth2/token",
            authorize_url="https://discord.com/api/oauth2/authorize",
            api_base_url="https://discord.com/api/",
            client_kwargs={"scope": "identify email"},
        )
