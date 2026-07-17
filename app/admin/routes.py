import os
import cloudinary
import cloudinary.uploader
from functools import wraps
from flask import Blueprint, render_template, session, redirect, url_for, abort, request
from ..models import Person, Edition, CategoryTemplate, EditionCategory, Nomination, Vote, StoryProgress, db
from datetime import datetime

# --- Configuração do Cloudinary ---
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# --- Helpers e Utils ---
def salvar_imagem_base64(b64_string):
    if not b64_string or 'base64' not in b64_string:
        return None
    try:
        # Envia a foto do seu painel direto para os servidores do Cloudinary
        upload_result = cloudinary.uploader.upload(b64_string)

        # Pega a URL segura (https) que o Cloudinary gerou e salva no seu banco de dados
        return upload_result.get("secure_url")
    except Exception as e:
        print(f"Erro ao subir para o Cloudinary: {e}")
        return None


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "person_id" not in session:
            return redirect(url_for("auth.login", provider="google"))

        person = Person.query.get(session["person_id"])

        # Se a pessoa sumiu do banco de dados (cookie fantasma), limpa a sessão e manda logar de novo
        if not person:
            session.clear()
            return redirect(url_for("auth.login", provider="google"))

        if not person.is_admin:
            abort(403)

        return f(*args, **kwargs)

    return decorated_function


# --- Rotas do Dashboard e Pessoas ---
@admin_bp.route("/")
@admin_required
def dashboard():
    person = Person.query.get(session["person_id"])
    return render_template("admin/dashboard.html", admin_user=person, pessoas_count=Person.query.count(),
                           templates_count=CategoryTemplate.query.count(),
                           edicoes=Edition.query.order_by(Edition.year.desc()).all())


@admin_bp.route("/pessoas", methods=["GET", "POST"])
@admin_required
def pessoas():
    if request.method == "POST":
        nome = request.form.get("nome")
        foto_b64 = request.form.get("foto_b64")
        foto_url = salvar_imagem_base64(foto_b64)
        if nome:
            db.session.add(Person(name=nome, photo_url=foto_url, is_manual=True))
            db.session.commit()
            return redirect(url_for('admin.pessoas'))

    todas = Person.query.order_by(Person.name).all()
    part = {}
    for p in todas:
        anos = db.session.query(Edition.year) \
            .join(EditionCategory, EditionCategory.edition_id == Edition.id) \
            .join(Nomination, Nomination.edition_category_id == EditionCategory.id) \
            .filter(Nomination.person_id == p.id) \
            .distinct() \
            .order_by(Edition.year.desc()) \
            .all()
        part[p.id] = [ano[0] for ano in anos]

    return render_template("admin/pessoas.html", admin_user=Person.query.get(session["person_id"]), pessoas=todas,
                           participacoes=part)


@admin_bp.route("/pessoas/editar/<int:pessoa_id>", methods=["POST"])
@admin_required
def editar_pessoa(pessoa_id):
    p = Person.query.get_or_404(pessoa_id)
    p.name = request.form.get("nome", p.name)
    foto_url = salvar_imagem_base64(request.form.get("foto_b64"))
    if foto_url: p.photo_url = foto_url
    db.session.commit()
    return redirect(url_for('admin.pessoas'))


@admin_bp.route("/pessoas/excluir/<int:pessoa_id>", methods=["POST"])
@admin_required
def excluir_pessoa(pessoa_id):
    p = Person.query.get_or_404(pessoa_id)

    # 1. Apaga todos os votos que a pessoa deu ou recebeu
    Vote.query.filter((Vote.voter_id == pessoa_id) | (Vote.nominee_id == pessoa_id)).delete()

    # 2. Apaga todas as indicações dessa pessoa nas categorias
    Nomination.query.filter_by(person_id=pessoa_id).delete()

    # 3. Apaga o progresso da cerimônia (caso ela tenha)
    StoryProgress.query.filter_by(person_id=pessoa_id).delete()

    # 4. Agora sim, com tudo limpo, apaga a pessoa
    db.session.delete(p)
    db.session.commit()

    return redirect(url_for('admin.pessoas'))


# --- Rotas de Templates (Biblioteca) ---
@admin_bp.route("/templates", methods=["GET", "POST"])
@admin_required
def templates_list():
    if request.method == "POST":
        db.session.add(CategoryTemplate(name=request.form.get("nome"), description=request.form.get("descricao")))
        db.session.commit()
        return redirect(url_for('admin.templates_list'))
    return render_template("admin/templates_list.html", admin_user=Person.query.get(session["person_id"]),
                           templates=CategoryTemplate.query.order_by(CategoryTemplate.name).all())


@admin_bp.route("/templates/editar/<int:template_id>", methods=["POST"])
@admin_required
def editar_template(template_id):
    t = CategoryTemplate.query.get_or_404(template_id)
    t.name, t.description = request.form.get("nome"), request.form.get("descricao")
    db.session.commit()
    return redirect(url_for('admin.templates_list'))


@admin_bp.route("/templates/excluir/<int:template_id>", methods=["POST"])
@admin_required
def excluir_template(template_id):
    db.session.delete(CategoryTemplate.query.get_or_404(template_id))
    db.session.commit()
    return redirect(url_for('admin.templates_list'))


# --- Rotas de Temporadas e Categorias ---
@admin_bp.route("/temporadas", methods=["GET", "POST"])
@admin_required
def temporadas():
    if request.method == "POST":
        try:
            db.session.add(Edition(year=int(request.form.get("ano"))))
            db.session.commit()
        except:
            db.session.rollback()
        return redirect(url_for('admin.temporadas'))
    return render_template("admin/temporadas.html", admin_user=Person.query.get(session["person_id"]),
                           edicoes=Edition.query.order_by(Edition.year.desc()).all())


@admin_bp.route("/temporadas/excluir/<int:edition_id>", methods=["POST"])
@admin_required
def excluir_temporada(edition_id):
    edicao = Edition.query.get_or_404(edition_id)
    categorias = EditionCategory.query.filter_by(edition_id=edicao.id).all()
    for cat in categorias:
        Nomination.query.filter_by(edition_category_id=cat.id).delete()
        db.session.delete(cat)
    db.session.delete(edicao)
    db.session.commit()
    return redirect(url_for('admin.temporadas'))


@admin_bp.route("/temporadas/<int:edition_id>")
@admin_required
def edicao_painel(edition_id):
    edicao = Edition.query.get_or_404(edition_id)
    categorias = EditionCategory.query.filter_by(edition_id=edition_id).all()

    indicados_dict = {}
    for cat in categorias:
        noms = Nomination.query.filter_by(edition_category_id=cat.id).all()
        indicados_dict[cat.id] = []
        for n in noms:
            p = Person.query.get(n.person_id)
            if p:
                indicados_dict[cat.id].append({'nom_id': n.id, 'person': p})

    return render_template(
        "admin/edicao_painel.html",
        admin_user=Person.query.get(session["person_id"]),
        edicao=edicao,
        categorias=categorias,
        all_templates=CategoryTemplate.query.all(),
        all_people=Person.query.order_by(Person.name).all(),
        indicados=indicados_dict
    )


@admin_bp.route("/temporadas/<int:edition_id>/importar", methods=["POST"])
@admin_required
def importar_categorias(edition_id):
    for t_id in request.form.getlist("template_ids"):
        temp = CategoryTemplate.query.get(t_id)
        if temp: db.session.add(EditionCategory(edition_id=edition_id, name=temp.name, description=temp.description))
    db.session.commit()
    return redirect(url_for('admin.edicao_painel', edition_id=edition_id))


@admin_bp.route("/temporadas/<int:edition_id>/criar-categoria", methods=["POST"])
@admin_required
def criar_categoria_zero(edition_id):
    db.session.add(EditionCategory(edition_id=edition_id, name=request.form.get("nome"),
                                   description=request.form.get("descricao")))
    db.session.commit()
    return redirect(url_for('admin.edicao_painel', edition_id=edition_id))


@admin_bp.route("/categoria/<int:cat_id>/editar", methods=["POST"])
@admin_required
def editar_categoria(cat_id):
    cat = EditionCategory.query.get_or_404(cat_id)
    cat.name, cat.description = request.form.get("nome"), request.form.get("descricao")
    db.session.commit()
    return redirect(url_for('admin.edicao_painel', edition_id=cat.edition_id))


@admin_bp.route("/categoria/<int:cat_id>/excluir", methods=["POST"])
@admin_required
def excluir_categoria(cat_id):
    cat = EditionCategory.query.get_or_404(cat_id)
    Nomination.query.filter_by(edition_category_id=cat.id).delete()
    db.session.delete(cat)
    db.session.commit()
    return redirect(url_for('admin.edicao_painel', edition_id=cat.edition_id))


@admin_bp.route("/categoria/<int:cat_id>/indicado/adicionar", methods=["POST"])
@admin_required
def adicionar_indicado(cat_id):
    person_ids = request.form.getlist("person_id")
    categoria = EditionCategory.query.get_or_404(cat_id)

    if person_ids:
        for p_id in person_ids:
            existe = Nomination.query.filter_by(edition_category_id=cat_id, person_id=p_id).first()
            if not existe:
                nova_indicacao = Nomination(edition_category_id=cat_id, person_id=p_id)
                db.session.add(nova_indicacao)
        db.session.commit()

    return redirect(url_for('admin.edicao_painel', edition_id=categoria.edition_id))


@admin_bp.route("/indicado/<int:nom_id>/excluir", methods=["POST"])
@admin_required
def excluir_indicado(nom_id):
    nom = Nomination.query.get_or_404(nom_id)
    categoria = EditionCategory.query.get(nom.edition_category_id)
    eid = categoria.edition_id
    db.session.delete(nom)
    db.session.commit()
    return redirect(url_for('admin.edicao_painel', edition_id=eid))


@admin_bp.route("/categoria/<int:cat_id>/duplicar", methods=["POST"])
@admin_required
def duplicar_categoria(cat_id):
    cat_original = EditionCategory.query.get_or_404(cat_id)

    nova_cat = EditionCategory(
        edition_id=cat_original.edition_id,
        name=f"{cat_original.name} (Cópia)",
        description=cat_original.description
    )
    db.session.add(nova_cat)
    db.session.commit()

    Nomination.query.filter_by(edition_category_id=nova_cat.id).delete()
    db.session.commit()

    noms_originais = Nomination.query.filter_by(edition_category_id=cat_original.id).all()
    for nom in noms_originais:
        nova_nom = Nomination(
            edition_category_id=nova_cat.id,
            person_id=nom.person_id
        )
        db.session.add(nova_nom)

    db.session.commit()
    return redirect(url_for('admin.edicao_painel', edition_id=cat_original.edition_id))


@admin_bp.route("/temporadas/<int:edition_id>/configurar", methods=["POST"])
@admin_required
def configurar_temporada(edition_id):
    edicao = Edition.query.get_or_404(edition_id)
    edicao.state = request.form.get("state", edicao.state)

    def parse_dt(dt_str):
        if dt_str:
            return datetime.strptime(dt_str, '%Y-%m-%dT%H:%M')
        return None

    edicao.voting_start = parse_dt(request.form.get("voting_start"))
    edicao.voting_end = parse_dt(request.form.get("voting_end"))
    edicao.presentation_date = parse_dt(request.form.get("presentation_date"))

    db.session.commit()
    return redirect(url_for('admin.edicao_painel', edition_id=edicao.id))


@admin_bp.route("/pessoas/toggle-admin/<int:pessoa_id>", methods=["POST"])
@admin_required
def toggle_admin(pessoa_id):
    p = Person.query.get_or_404(pessoa_id)

    # Trava de segurança: Você não pode remover o próprio cargo de Admin
    if p.id != session["person_id"]:
        p.is_admin = not p.is_admin
        db.session.commit()

    return redirect(url_for('admin.pessoas'))