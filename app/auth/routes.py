from flask import current_app, redirect, session, url_for

from ..models import Person, db
from . import auth_bp, oauth


@auth_bp.route("/login/<provider>")
def login(provider):
    if provider not in ("google", "discord"):
        return redirect(url_for("main.index"))

    client = oauth.create_client(provider)
    if client is None:
        return (
            f"Provedor '{provider}' ainda não configurado "
            f"(faltam as credenciais no .env — veja o README).",
            400,
        )

    redirect_uri = url_for("auth.callback", provider=provider, _external=True)
    return client.authorize_redirect(redirect_uri)


@auth_bp.route("/callback/<provider>")
def callback(provider):
    client = oauth.create_client(provider)
    if client is None:
        return redirect(url_for("main.index"))

    token = client.authorize_access_token()

    # --- A CORREÇÃO É AQUI ---
    # Garante que o campo token_type exista e seja 'Bearer'
    token['token_type'] = 'Bearer'
    # -------------------------

    if provider == "google":
        # Google geralmente funciona bem assim, mas se der erro no Google tbm,
        # pode manter a linha acima antes desse if.
        userinfo = token.get("userinfo") or {}
        provider_id = str(userinfo["sub"])
        email = userinfo.get("email")
        name = userinfo.get("name") or email or "Sem nome"
        photo = userinfo.get("picture")
    else:  # discord
        profile = client.get("users/@me", token=token).json()
        provider_id = str(profile["id"])
        email = profile.get("email")
        name = profile.get("global_name") or profile.get("username") or "Sem nome"
        avatar = profile.get("avatar")
        photo = (
            f"https://cdn.discordapp.com/avatars/{provider_id}/{avatar}.png"
            if avatar
            else "https://cdn.discordapp.com/embed/avatars/0.png"
        )

    person = Person.query.filter_by(auth_provider=provider, provider_user_id=provider_id).first()

    if person is None:
        # primeiro login dessa pessoa: cria o registro e puxa nome/foto reais.
        # depois disso, quem manda no nome/foto é o admin (não sobrescreve mais sozinho).
        person = Person(
            auth_provider=provider,
            provider_user_id=provider_id,
            name=name,
            photo_url=photo,
            email=email,
        )
        db.session.add(person)
    else:
        person.email = email or person.email

    is_admin_email = bool(email) and email.lower() in current_app.config["ADMIN_EMAILS"]
    is_admin_discord = provider == "discord" and provider_id in current_app.config["ADMIN_DISCORD_IDS"]
    if is_admin_email or is_admin_discord:
        person.is_admin = True

    db.session.commit()

    session["person_id"] = person.id
    return redirect(url_for("main.index"))


@auth_bp.route("/logout")
def logout():
    session.pop("person_id", None)
    return redirect(url_for("main.index"))
