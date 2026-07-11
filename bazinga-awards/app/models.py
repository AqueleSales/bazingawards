from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Person(db.Model):
    """Alguém do grupo. Pode estar 'ligado' a uma conta real (Google/Discord)
    ou ser só um cadastro manual feito pelo admin (sem login ainda)."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    photo_url = db.Column(db.String(500))

    auth_provider = db.Column(db.String(20))  # 'google' | 'discord' | None (manual)
    provider_user_id = db.Column(db.String(120))
    email = db.Column(db.String(255))

    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_manual = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("auth_provider", "provider_user_id", name="uq_person_provider"),
    )

    def __repr__(self):
        return f"<Person {self.id} {self.name!r}>"


class Edition(db.Model):
    """Uma temporada (2026, 2027...). O estado controla o que o admin
    pode fazer e o que os usuários enxergam."""

    # announced -> setup -> voting -> blackout -> revealing -> archived
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, unique=True, nullable=False)
    state = db.Column(db.String(20), default="announced", nullable=False)
    premiere_at = db.Column(db.DateTime)  # data/hora marcada pro admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Edition {self.year} {self.state}>"


class CategoryTemplate(db.Model):
    """Biblioteca reutilizável de categorias. O admin monta uma vez,
    e reaproveita (copia/duplica) nas próximas temporadas."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CategoryTemplate {self.name!r}>"


class TemplateNominee(db.Model):
    """Pessoas padrão salvas num template, pra 'duplicar categoria'
    já trazer a lista de gente junto."""

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey("category_template.id"), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=False)
    order_index = db.Column(db.Integer, default=0)


class EditionCategory(db.Model):
    """Uma categoria dentro de uma temporada específica (pode ter
    vindo de um template ou sido criada na hora)."""

    id = db.Column(db.Integer, primary_key=True)
    edition_id = db.Column(db.Integer, db.ForeignKey("edition.id"), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey("category_template.id"))
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    order_index = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<EditionCategory {self.name!r} edition={self.edition_id}>"


class Nomination(db.Model):
    """Quem tá concorrendo em qual categoria, naquela temporada."""

    id = db.Column(db.Integer, primary_key=True)
    edition_category_id = db.Column(db.Integer, db.ForeignKey("edition_category.id"), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=False)
    order_index = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.UniqueConstraint("edition_category_id", "person_id", name="uq_nomination_once"),
    )


class Vote(db.Model):
    """Um voto = uma pessoa logada, numa categoria, escolhendo um indicado.
    Trocar o voto é só fazer update nesta linha (1 voto por pessoa por categoria)."""

    id = db.Column(db.Integer, primary_key=True)
    edition_category_id = db.Column(db.Integer, db.ForeignKey("edition_category.id"), nullable=False)
    voter_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=False)
    nominee_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("edition_category_id", "voter_id", name="uq_one_vote_per_category"),
    )


class StoryProgress(db.Model):
    """Onde cada pessoa parou no 'story' de revelação da premiação,
    pra retomar de onde parou se sair e voltar."""

    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey("person.id"), nullable=False)
    edition_id = db.Column(db.Integer, db.ForeignKey("edition.id"), nullable=False)
    current_step = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("person_id", "edition_id", name="uq_progress_per_edition"),
    )
