from functools import wraps
import re

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from psycopg2 import Error as DatabaseError
from werkzeug.security import generate_password_hash

from .database import one, query

main = Blueprint("main", __name__)


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def resident_portal():
    resident = one(
        "SELECT id, apartment_no, full_name, phone, email FROM residents WHERE id = %s",
        (current_user.resident_id,),
    )
    if not resident:
        abort(403)
    fees = query(
        """SELECT title, amount, due_date, status, paid_at
           FROM fees WHERE resident_id = %s ORDER BY due_date DESC""",
        (current_user.resident_id,),
    )
    notices = query("SELECT * FROM announcements ORDER BY published_at DESC LIMIT 5")
    complaints = query(
        """SELECT * FROM complaints WHERE resident_id = %s
           ORDER BY created_at DESC LIMIT 5""",
        (current_user.resident_id,),
    )
    return render_template(
        "resident_dashboard.html", resident=resident, fees=fees,
        notices=notices, complaints=complaints,
    )


@main.get("/")
@login_required
def dashboard():
    if not current_user.is_admin:
        return resident_portal()
    stats = one(
        """
        SELECT
          (SELECT count(*) FROM residents) AS residents,
          (SELECT count(*) FROM fees WHERE status = 'Chưa thu') AS unpaid_fees,
          (SELECT coalesce(sum(amount), 0) FROM fees WHERE status = 'Chưa thu') AS unpaid_amount,
          (SELECT count(*) FROM complaints WHERE status <> 'Đã giải quyết') AS open_complaints
        """
    )
    notices = query("SELECT * FROM announcements ORDER BY published_at DESC LIMIT 3")
    complaints = query("SELECT * FROM complaints ORDER BY created_at DESC LIMIT 4")
    return render_template(
        "dashboard.html", stats=stats, notices=notices, complaints=complaints
    )


@main.route("/residents", methods=["GET", "POST"])
@admin_required
def residents():
    if request.method == "POST":
        values = tuple(
            request.form.get(key, "").strip()
            for key in ("apartment_no", "full_name", "phone", "email")
        )
        if not all(values[:3]):
            flash("Mã căn hộ, họ tên và số điện thoại là bắt buộc.", "error")
        else:
            try:
                query(
                    """INSERT INTO residents (apartment_no, full_name, phone, email)
                       VALUES (%s, %s, %s, %s)""",
                    values,
                )
                flash("Đã thêm cư dân.", "success")
                return redirect(url_for("main.residents"))
            except DatabaseError as error:
                if getattr(error, "pgcode", None) == "23505":
                    flash("Mã căn hộ đã tồn tại.", "error")
                else:
                    raise
    items = query(
        """SELECT r.*, a.username AS account_username, a.active AS account_active
           FROM residents r
           LEFT JOIN resident_accounts a ON a.resident_id = r.id
           ORDER BY r.apartment_no"""
    )
    return render_template("residents.html", residents=items)


@main.post("/residents/<int:resident_id>/account")
@admin_required
def create_resident_account(resident_id):
    resident = one("SELECT id FROM residents WHERE id = %s", (resident_id,))
    if not resident:
        abort(404)
    username = request.form.get("username", "").strip().lower()
    initial_password = request.form.get("initial_password", "")
    if not re.fullmatch(r"[a-z0-9_.-]{3,64}", username):
        flash("Tên đăng nhập cần 3–64 ký tự: chữ thường, số, dấu chấm, gạch ngang hoặc gạch dưới.", "error")
        return redirect(url_for("main.residents"))
    if username == current_app.config["ADMIN_USERNAME"].lower():
        flash("Tên đăng nhập này dành cho tài khoản quản lý.", "error")
        return redirect(url_for("main.residents"))
    if len(initial_password) < 12:
        flash("Mật khẩu khởi tạo phải có ít nhất 12 ký tự.", "error")
        return redirect(url_for("main.residents"))
    existing = one("SELECT id FROM resident_accounts WHERE resident_id = %s", (resident_id,))
    if existing:
        flash("Căn hộ này đã có tài khoản cư dân.", "error")
        return redirect(url_for("main.residents"))
    try:
        query(
            """INSERT INTO resident_accounts
               (resident_id, username, password_hash, must_change_password)
               VALUES (%s, %s, %s, TRUE)""",
            (resident_id, username, generate_password_hash(initial_password)),
        )
    except DatabaseError as error:
        if getattr(error, "pgcode", None) == "23505":
            flash("Tên đăng nhập đã được sử dụng.", "error")
        else:
            raise
    else:
        flash("Đã cấp tài khoản. Cư dân phải đổi mật khẩu ở lần đăng nhập đầu tiên.", "success")
    return redirect(url_for("main.residents"))


@main.route("/fees", methods=["GET", "POST"])
@admin_required
def fees():
    if request.method == "POST":
        fee_id = request.form.get("fee_id", type=int)
        if fee_id:
            query(
                """UPDATE fees SET status = 'Đã thu', paid_at = now()
                   WHERE id = %s AND status = 'Chưa thu'""",
                (fee_id,),
            )
            flash("Đã ghi nhận thanh toán.", "success")
        return redirect(url_for("main.fees"))
    items = query(
        """SELECT f.*, r.apartment_no, r.full_name
           FROM fees f JOIN residents r ON r.id = f.resident_id
           ORDER BY f.due_date, r.apartment_no"""
    )
    totals = one(
        """SELECT count(*) FILTER (WHERE status = 'Đã thu') AS paid,
                  count(*) FILTER (WHERE status = 'Chưa thu') AS pending,
                  coalesce(sum(amount) FILTER (WHERE status = 'Chưa thu'), 0) AS amount
           FROM fees"""
    )
    return render_template("fees.html", fees=items, totals=totals)


@main.route("/announcements", methods=["GET", "POST"])
@admin_required
def announcements():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if len(title) < 4 or len(body) < 10:
            flash("Tiêu đề cần tối thiểu 4 ký tự, nội dung tối thiểu 10 ký tự.", "error")
        else:
            query("INSERT INTO announcements (title, body) VALUES (%s, %s)", (title, body))
            flash("Đã đăng thông báo.", "success")
            return redirect(url_for("main.announcements"))
    items = query("SELECT * FROM announcements ORDER BY published_at DESC")
    return render_template("announcements.html", announcements=items)


@main.route("/complaints", methods=["GET", "POST"])
def complaints():
    resident = None
    if current_user.is_authenticated and not current_user.is_admin:
        resident = one(
            "SELECT id, apartment_no, full_name FROM residents WHERE id = %s",
            (current_user.resident_id,),
        )
        if not resident:
            abort(403)
    if request.method == "POST":
        if resident:
            values = (
                resident["id"], resident["full_name"], resident["apartment_no"],
                request.form.get("category", "").strip(),
                request.form.get("content", "").strip(),
            )
        else:
            values = (
                None,
                request.form.get("resident_name", "").strip(),
                request.form.get("apartment_no", "").strip(),
                request.form.get("category", "").strip(),
                request.form.get("content", "").strip(),
            )
        if not all(values[1:]) or len(values[4]) < 10:
            flash("Vui lòng điền đủ thông tin và mô tả ít nhất 10 ký tự.", "error")
        else:
            query(
                """INSERT INTO complaints
                   (resident_id, resident_name, apartment_no, category, content)
                   VALUES (%s, %s, %s, %s, %s)""",
                values,
            )
            flash("Đã gửi phản ánh. Ban quản lý sẽ tiếp nhận và xử lý.", "success")
            return redirect(url_for("main.complaints"))
    items = []
    if current_user.is_authenticated:
        if current_user.is_admin:
            items = query("SELECT * FROM complaints ORDER BY created_at DESC")
        else:
            items = query(
                """SELECT * FROM complaints WHERE resident_id = %s
                   ORDER BY created_at DESC""",
                (current_user.resident_id,),
            )
    return render_template("complaints.html", complaints=items, resident=resident)


@main.post("/complaints/<int:complaint_id>/status")
@admin_required
def complaint_status(complaint_id):
    status = request.form.get("status")
    if status not in ("Mới tiếp nhận", "Đang xử lý", "Đã giải quyết"):
        flash("Trạng thái không hợp lệ.", "error")
    else:
        query("UPDATE complaints SET status = %s WHERE id = %s", (status, complaint_id))
        flash("Đã cập nhật phản ánh.", "success")
    return redirect(url_for("main.complaints"))
