from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import UserMixin, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from .database import one, query

auth = Blueprint("auth", __name__)


class AdminUser(UserMixin):
    def __init__(self, username):
        self.id = username
        self.display_name = "Ban quản lý"
        self.role = "admin"
        self.is_admin = True
        self.must_change_password = False


class ResidentUser(UserMixin):
    def __init__(self, account):
        self.id = account["username"]
        self.display_name = account["full_name"]
        self.role = "resident"
        self.is_admin = False
        self.resident_id = account["resident_id"]
        self.must_change_password = account["must_change_password"]
        self.password_hash = account["password_hash"]


def load_user(user_id):
    if user_id == current_app.config["ADMIN_USERNAME"]:
        return AdminUser(user_id)
    account = one(
        """SELECT a.username, a.resident_id, a.password_hash,
                  a.must_change_password, r.full_name
           FROM resident_accounts a
           JOIN residents r ON r.id = a.resident_id
           WHERE a.username = %s AND a.active = TRUE""",
        (user_id,),
    )
    return ResidentUser(account) if account else None


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        resident_username = username.lower()
        password = request.form.get("password", "")
        expected_username = current_app.config["ADMIN_USERNAME"]
        password_hash = current_app.config["ADMIN_PASSWORD_HASH"]
        user = None
        if username == expected_username and check_password_hash(password_hash, password):
            user = AdminUser(expected_username)
        else:
            account = one(
                """SELECT a.username, a.resident_id, a.password_hash,
                          a.must_change_password, r.full_name
                   FROM resident_accounts a
                   JOIN residents r ON r.id = a.resident_id
                   WHERE a.username = %s AND a.active = TRUE""",
                (resident_username,),
            )
            if account and check_password_hash(account["password_hash"], password):
                user = ResidentUser(account)
        if user:
            login_user(user, remember=False, fresh=True)
            current_app.logger.info(
                "login_succeeded",
                extra={"event": "login_succeeded", "username": user.id, "role": user.role},
            )
            if user.must_change_password:
                return redirect(url_for("auth.change_password"))
            return redirect(url_for("main.dashboard"))
        current_app.logger.warning(
            "login_failed",
            extra={"event": "login_failed", "username": username[:64]},
        )
        flash("Tên đăng nhập hoặc mật khẩu không đúng.", "error")
    return render_template("login.html")


@auth.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if current_user.is_admin:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirmation = request.form.get("confirmation", "")
        if not check_password_hash(current_user.password_hash, current_password):
            flash("Mật khẩu hiện tại không đúng.", "error")
        elif len(new_password) < 12:
            flash("Mật khẩu mới phải có ít nhất 12 ký tự.", "error")
        elif new_password != confirmation:
            flash("Hai lần nhập mật khẩu mới chưa khớp.", "error")
        else:
            query(
                """UPDATE resident_accounts
                   SET password_hash = %s, must_change_password = FALSE
                   WHERE username = %s""",
                (generate_password_hash(new_password), current_user.id),
            )
            flash("Đã đổi mật khẩu. Bạn có thể tiếp tục sử dụng cổng cư dân.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("change_password.html")


@auth.post("/logout")
def logout():
    logout_user()
    flash("Bạn đã đăng xuất.", "success")
    return redirect(url_for("auth.login"))
