from flask import redirect, request, session, url_for
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
import bcrypt

from models import (
    Consult,
    ConsultAssignment,
    Matter,
    Proposal,
    User,
    UserRole,
    db,
)


ADMIN_SESSION_KEY = "admin_user_id"


def _is_admin_logged_in():
    user_id = session.get(ADMIN_SESSION_KEY)
    if not user_id:
        return False

    user = User.query.get(user_id)
    return bool(user and user.role == UserRole.ADMIN)


class SecureAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not _is_admin_logged_in():
            return redirect(url_for('admin_login_form', next=request.url))
        return super().index()


class SecureModelView(ModelView):
    can_export = True
    page_size = 50

    def is_accessible(self):
        return _is_admin_logged_in()

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin_login_form', next=request.url))


class UserAdminView(SecureModelView):
    column_list = ("id", "email", "role")
    column_searchable_list = ("email",)
    column_filters = ("role",)
    form_excluded_columns = ("consults", "assignments")

    def on_model_change(self, form, model, is_created):
        password_value = getattr(model, "password", "")

        # Only hash when user typed a new plain-text password in admin UI.
        if password_value and not str(password_value).startswith("$2"):
            model.password = bcrypt.hashpw(
                str(password_value).encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")


class MatterAdminView(SecureModelView):
    column_list = ("id", "name")
    column_searchable_list = ("name",)
    form_excluded_columns = ("consults",)


class ConsultAdminView(SecureModelView):
    column_list = (
        "id",
        "client_id",
        "matter_id",
        "title",
        "urgent",
        "is_public",
        "status",
        "created_at",
    )
    column_searchable_list = ("title", "description")
    column_filters = ("urgent", "is_public", "status", "matter_id", "client_id")


class ConsultAssignmentAdminView(SecureModelView):
    column_list = ("id", "consult_id", "lawyer_id", "status", "assigned_at")
    column_filters = ("status", "lawyer_id", "consult_id")


class ProposalAdminView(SecureModelView):
    column_list = ("id", "consult_id", "lawyer_id", "status", "created_at")
    column_filters = ("status", "lawyer_id", "consult_id")


def init_admin(app):
    @app.get('/admin/login')
    def admin_login_form():
        if _is_admin_logged_in():
            return redirect(url_for('admin.index'))

        next_url = request.args.get('next', url_for('admin.index'))
        return f"""
        <html>
          <head><title>Juris Admin Login</title></head>
          <body style=\"font-family: sans-serif; max-width: 420px; margin: 48px auto;\">
            <h2>Juris Admin</h2>
            <p>Ingresa con un usuario ADMIN.</p>
            <form method=\"post\" action=\"{url_for('admin_login')}\">
              <input type=\"hidden\" name=\"next\" value=\"{next_url}\" />
              <label>Email</label><br />
              <input name=\"email\" type=\"email\" required style=\"width:100%;padding:8px;margin:6px 0 12px;\"/><br />
              <label>Contraseña</label><br />
              <input name=\"password\" type=\"password\" required style=\"width:100%;padding:8px;margin:6px 0 12px;\"/><br />
              <button type=\"submit\" style=\"padding:10px 14px;\">Entrar</button>
            </form>
          </body>
        </html>
        """

    @app.post('/admin/login')
    def admin_login():
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        next_url = request.form.get('next') or url_for('admin.index')

        user = User.query.filter_by(email=email).first()
        if not user or user.role != UserRole.ADMIN:
            return redirect(url_for('admin_login_form'))

        if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            return redirect(url_for('admin_login_form'))

        session[ADMIN_SESSION_KEY] = user.id
        return redirect(next_url)

    @app.get('/admin/logout')
    def admin_logout():
        session.pop(ADMIN_SESSION_KEY, None)
        return redirect(url_for('admin_login_form'))

    admin = Admin(
        app,
        name='Juris Admin',
        index_view=SecureAdminIndexView(url='/admin'),
    )

    admin.add_view(UserAdminView(User, db.session, name='Users', endpoint='admin_users'))
    admin.add_view(MatterAdminView(Matter, db.session, name='Matters', endpoint='admin_matters'))
    admin.add_view(ConsultAdminView(Consult, db.session, name='Consults', endpoint='admin_consults'))
    admin.add_view(
        ConsultAssignmentAdminView(
            ConsultAssignment,
            db.session,
            name='Assignments',
            endpoint='admin_assignments',
        )
    )
    admin.add_view(ProposalAdminView(Proposal, db.session, name='Proposals', endpoint='admin_proposals'))
