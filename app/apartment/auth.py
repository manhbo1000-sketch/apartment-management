from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import UserMixin, current_user, login_user, logout_user
from werkzeug.security import check_password_hash

auth = Blueprint("auth", __name__)


class AdminUser(UserMixin):
    def __init__(self, username):
        self.id = username


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        expected_username = current_app.config["ADMIN_USERNAME"]
        password_hash = current_app.config["ADMIN_PASSWORD_HASH"]
        if username == expected_username and check_password_hash(password_hash, password):
            login_user(AdminUser(expected_username), remember=False, fresh=True)
            current_app.logger.info(
                "admin_login_succeeded",
                extra={"event": "login_succeeded", "username": expected_username},
            )
            return redirect(url_for("main.dashboard"))
        current_app.logger.warning(
            "admin_login_failed",
            extra={"event": "login_failed", "username": username[:64]},
        )
        flash("Tên đăng nhập hoặc mật khẩu không đúng.", "error")
    return render_template("login.html")


@auth.post("/logout")
def logout():
    logout_user()
    flash("Bạn đã đăng xuất.", "success")
    return redirect(url_for("auth.login"))
