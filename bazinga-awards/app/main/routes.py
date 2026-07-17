from datetime import datetime
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from sqlalchemy import func
from ..models import Edition, EditionCategory, Nomination, Vote, Person, StoryProgress, db

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    user = Person.query.get(session.get("person_id")) if "person_id" in session else None
    edicao = Edition.query.order_by(Edition.year.desc()).first()

    edicoes_passadas = Edition.query.filter(Edition.state == 'FINISHED').order_by(Edition.year.desc()).all()

    historico_premios = []
    total_trofeus = 0
    if user:
        todas_edicoes = Edition.query.order_by(Edition.year.desc()).all()
        for ed in todas_edicoes:
            if ed.state == 'FINISHED':
                vitorias = 0
                for cat in EditionCategory.query.filter_by(edition_id=ed.id).all():
                    votos = db.session.query(Vote.nominee_id, func.count(Vote.id).label('total')).filter(
                        Vote.edition_category_id == cat.id).group_by(Vote.nominee_id).order_by(
                        func.count(Vote.id).desc()).all()
                    if votos and votos[0].nominee_id == user.id:
                        vitorias += 1

                if vitorias > 0:
                    historico_premios.append({'ano': ed.year, 'trofeus': f"{vitorias} 🏆"})
                    total_trofeus += vitorias
            else:
                foi_indicado = Nomination.query.join(EditionCategory).filter(EditionCategory.edition_id == ed.id,
                                                                             Nomination.person_id == user.id).first()
                if foi_indicado:
                    historico_premios.append({'ano': ed.year, 'trofeus': "..."})

    # SE NÃO EXISTIR TEMPORADA NENHUMA, ELE RENDERIZA O LOBBY MESMO ASSIM!
    if not edicao:
        return render_template("index.html", edicao=None, status_real='NO_EDITION', user=user, categorias=[],
                               indicados={}, meus_votos={}, next_date=None, evento_timer="",
                               edicoes_passadas=edicoes_passadas, historico_premios=historico_premios,
                               total_trofeus=total_trofeus)

    agora = datetime.now()

    if edicao.state != 'FINISHED':
        if edicao.state == 'ANNOUNCED' and edicao.voting_start and agora >= edicao.voting_start:
            edicao.state = 'VOTING'
            db.session.commit()
        elif edicao.state == 'VOTING' and edicao.voting_end and agora >= edicao.voting_end:
            edicao.state = 'CLOSED'
            db.session.commit()
        elif edicao.state == 'CLOSED' and edicao.presentation_date and agora >= edicao.presentation_date:
            edicao.state = 'REVEALING'
            db.session.commit()
        elif edicao.state == 'REVEALING' and edicao.presentation_date and (
                agora - edicao.presentation_date).total_seconds() >= 86400:
            edicao.state = 'FINISHED'
            db.session.commit()

    next_date = None
    evento_timer = ""
    if edicao.state == 'ANNOUNCED' and edicao.voting_start:
        next_date = edicao.voting_start.isoformat()
        evento_timer = "As urnas abrem em"
    elif edicao.state == 'VOTING' and edicao.voting_end:
        next_date = edicao.voting_end.isoformat()
        evento_timer = "A votação encerra em"
    elif edicao.state == 'CLOSED' and edicao.presentation_date:
        next_date = edicao.presentation_date.isoformat()
        evento_timer = "A Cerimônia começa em"

    meus_votos = {v.edition_category_id: v.nominee_id for v in
                  Vote.query.filter_by(voter_id=user.id).all()} if user else {}

    categorias = EditionCategory.query.filter_by(edition_id=edicao.id).all()
    indicados = {
        cat.id: [Person.query.get(n.person_id) for n in Nomination.query.filter_by(edition_category_id=cat.id).all() if
                 Person.query.get(n.person_id)] for cat in categorias}

    return render_template("index.html", edicao=edicao, status_real=edicao.state, user=user, categorias=categorias,
                           indicados=indicados, meus_votos=meus_votos, next_date=next_date, evento_timer=evento_timer,
                           edicoes_passadas=edicoes_passadas, historico_premios=historico_premios,
                           total_trofeus=total_trofeus)


@main_bp.route("/atualizar_nome", methods=["POST"])
def atualizar_nome():
    if "person_id" not in session: return jsonify({"success": False}), 401
    user = Person.query.get(session["person_id"])
    novo_nome = request.form.get("novo_nome")
    if user and novo_nome and novo_nome.strip() != "":
        user.name = novo_nome.strip()
        db.session.commit()
    return redirect(url_for("main.index"))


@main_bp.route("/votar", methods=["POST"])
def votar():
    if "person_id" not in session: return jsonify({"success": False}), 401
    dados = request.get_json()
    voto_antigo = Vote.query.filter_by(edition_category_id=dados.get("categoria_id"),
                                       voter_id=session["person_id"]).first()
    if voto_antigo:
        voto_antigo.nominee_id = dados.get("nominee_id")
    else:
        db.session.add(Vote(edition_category_id=dados.get("categoria_id"), voter_id=session["person_id"],
                            nominee_id=dados.get("nominee_id")))
    db.session.commit()
    return jsonify({"success": True})


@main_bp.route("/cerimonia")
def cerimonia():
    if "person_id" not in session: return redirect(url_for("auth.login", provider="google"))
    edicao = Edition.query.order_by(Edition.year.desc()).first()
    if not edicao or edicao.state not in ['REVEALING', 'FINISHED']: return redirect(url_for("main.index"))

    progresso = StoryProgress.query.filter_by(person_id=session["person_id"], edition_id=edicao.id).first()
    if not progresso:
        progresso = StoryProgress(person_id=session["person_id"], edition_id=edicao.id, current_step=0)
        db.session.add(progresso)
        db.session.commit()

    ranking_dados = []
    for cat in EditionCategory.query.filter_by(edition_id=edicao.id).order_by(EditionCategory.order_index,
                                                                              EditionCategory.id).all():
        votos = db.session.query(Vote.nominee_id, func.count(Vote.id).label('total')).filter(
            Vote.edition_category_id == cat.id).group_by(Vote.nominee_id).order_by(func.count(Vote.id).desc()).all()
        ranking_dados.append({"id": cat.id, "nome": cat.name, "descricao": cat.description,
                              "podio": [{"id": p.id, "nome": p.name, "foto": p.photo_url, "votos": v.total} for v in
                                        votos if (p := Person.query.get(v.nominee_id))]})

    return render_template("cerimonia.html", edicao=edicao, ranking=ranking_dados, step_atual=progresso.current_step)


@main_bp.route("/cerimonia/salvar_progresso", methods=["POST"])
def salvar_progresso():
    if "person_id" in session and (progresso := StoryProgress.query.filter_by(person_id=session["person_id"],
                                                                              edition_id=Edition.query.order_by(
                                                                                      Edition.year.desc()).first().id).first()):
        progresso.current_step = request.get_json().get("step", 0)
        db.session.commit()
    return jsonify({"success": True})


@main_bp.route("/resultados/<int:year>")
def resultados_temporada(year):
    edicao = Edition.query.filter_by(year=year, state='FINISHED').first()
    if not edicao: return redirect(url_for("main.index"))

    ranking_dados = []
    for cat in EditionCategory.query.filter_by(edition_id=edicao.id).order_by(EditionCategory.order_index,
                                                                              EditionCategory.id).all():
        votos = db.session.query(Vote.nominee_id, func.count(Vote.id).label('total')).filter(
            Vote.edition_category_id == cat.id).group_by(Vote.nominee_id).order_by(func.count(Vote.id).desc()).all()
        ranking_dados.append({"nome": cat.name, "descricao": cat.description,
                              "podio": [{"nome": p.name, "foto": p.photo_url, "votos": v.total} for v in votos if
                                        (p := Person.query.get(v.nominee_id))]})

    return render_template("resultados.html", edicao=edicao, ranking=ranking_dados)