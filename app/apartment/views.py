from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from psycopg2 import Error as DatabaseError

from .database import one, query

main = Blueprint("main", __name__)


@main.get("/")
@login_required
def dashboard():
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
@login_required
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
    items = query("SELECT * FROM residents ORDER BY apartment_no")
    return render_template("residents.html", residents=items)


@main.route("/fees", methods=["GET", "POST"])
@login_required
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
@login_required
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
    if request.method == "POST":
        fields = tuple(
            request.form.get(key, "").strip()
            for key in ("resident_name", "apartment_no", "category", "content")
        )
        if not all(fields) or len(fields[3]) < 10:
            flash("Vui lòng điền đủ thông tin và mô tả ít nhất 10 ký tự.", "error")
        else:
            query(
                """INSERT INTO complaints (resident_name, apartment_no, category, content)
                   VALUES (%s, %s, %s, %s)""",
                fields,
            )
            flash("Đã gửi phản ánh. Ban quản lý sẽ tiếp nhận và xử lý.", "success")
            return redirect(url_for("main.complaints"))
    items = []
    if current_user.is_authenticated:
        items = query("SELECT * FROM complaints ORDER BY created_at DESC")
    return render_template("complaints.html", complaints=items)


@main.post("/complaints/<int:complaint_id>/status")
@login_required
def complaint_status(complaint_id):
    status = request.form.get("status")
    if status not in ("Mới tiếp nhận", "Đang xử lý", "Đã giải quyết"):
        flash("Trạng thái không hợp lệ.", "error")
    else:
        query("UPDATE complaints SET status = %s WHERE id = %s", (status, complaint_id))
        flash("Đã cập nhật phản ánh.", "success")
    return redirect(url_for("main.complaints"))
