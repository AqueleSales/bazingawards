from datetime import datetime
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from ..models import Edition, EditionCategory, Nomination, Vote, Person, db

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    # Pega a edição mais recente criada (Ex: 2026)
    edicao = Edition.query.order_by(Edition.year.desc()).first()

    if not edicao:
        return "O Admin ainda não criou nenhuma temporada. Volte mais tarde!"

    # --- A MÁGICA DO TEMPO REAL ---
    agora = datetime.now()
    status_dinamico = edicao.state

    if edicao.voting_start and edicao.voting_end:
        if agora < edicao.voting_start:
            status_dinamico = "ANNOUNCED"
        elif edicao.voting_start <= agora <= edicao.voting_end:
            status_dinamico = "VOTING"
        elif agora > edicao.voting_end and (not edicao.presentation_date or agora < edicao.presentation_date):
            status_dinamico = "CLOSED"
        elif edicao.presentation_date and agora >= edicao.presentation_date:
            status_dinamico = "REVEALING"

    # --- DADOS DO USUÁRIO LOGADO ---
    user = None
    meus_votos = {}
    if "person_id" in session:
        user = Person.query.get(session["person_id"])
        if user:
            # Puxa no banco tudo que ele já votou pra marcar os cards de verde
            votos_db = Vote.query.filter_by(voter_id=user.id).all()
            meus_votos = {v.edition_category_id: v.nominee_id for v in votos_db}

    # --- DADOS DA CATEGORIA E INDICADOS ---
    categorias = EditionCategory.query.filter_by(edition_id=edicao.id).all()
    indicados = {}
    for cat in categorias:
        noms = Nomination.query.filter_by(edition_category_id=cat.id).all()
        indicados[cat.id] = []
        for n in noms:
            p = Person.query.get(n.person_id)
            if p:
                indicados[cat.id].append(p)

    return render_template(
        "index.html",
        edicao=edicao,
        status_real=status_dinamico,
        user=user,
        categorias=categorias,
        indicados=indicados,
        meus_votos=meus_votos
    )


# --- ROTA INVISÍVEL PARA SALVAR O VOTO SEM RECARREGAR A PÁGINA ---
@main_bp.route("/votar", methods=["POST"])
def votar():
    if "person_id" not in session:
        return jsonify({"success": False, "error": "Você precisa estar logado para votar!"}), 401

    dados = request.get_json()
    cat_id = dados.get("categoria_id")
    nominee_id = dados.get("nominee_id")
    user_id = session["person_id"]

    # Procura se o cara já tinha votado nessa categoria
    voto_antigo = Vote.query.filter_by(edition_category_id=cat_id, voter_id=user_id).first()

    if voto_antigo:
        # Troca o voto
        voto_antigo.nominee_id = nominee_id
    else:
        # Cria voto novo
        novo_voto = Vote(edition_category_id=cat_id, voter_id=user_id, nominee_id=nominee_id)
        db.session.add(novo_voto)

    db.session.commit()
    return jsonify({"success": True})