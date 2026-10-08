"""Create the Vietnamese course report PDF with ReportLab."""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets"
OUTPUT_DIR = ROOT / "output" / "pdf"
OUTPUT = OUTPUT_DIR / "Bao-cao-De-tai-36-Quan-ly-chung-cu.pdf"

INK = colors.HexColor("#18251F")
GREEN = colors.HexColor("#185D47")
PALE = colors.HexColor("#F5F8F5")
GRAY = colors.HexColor("#69776E")
LINE = colors.HexColor("#D9E1DB")
WHITE = colors.white


def register_fonts():
    candidates = [
        (Path("C:/Windows/Fonts/times.ttf"), Path("C:/Windows/Fonts/timesbd.ttf")),
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
    ]
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("Report", str(regular)))
            pdfmetrics.registerFont(TTFont("Report-Bold", str(bold)))
            return
    raise FileNotFoundError("A Unicode TrueType font is required for Vietnamese text.")


def make_styles():
    base = getSampleStyleSheet()
    styles = {
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName="Report", fontSize=10.1,
            leading=13.2, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6,
        ),
        "body_left": ParagraphStyle(
            "BodyLeft", parent=base["BodyText"], fontName="Report", fontSize=10,
            leading=13, textColor=INK, alignment=TA_LEFT, spaceAfter=4,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontName="Report-Bold", fontSize=14,
            leading=18, textColor=colors.black, spaceBefore=2, spaceAfter=10,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontName="Report-Bold", fontSize=11.5,
            leading=14, textColor=colors.black, spaceBefore=5, spaceAfter=6,
            keepWithNext=True,
        ),
        "caption": ParagraphStyle(
            "Caption", parent=base["BodyText"], fontName="Report", fontSize=8.5,
            leading=11, textColor=GRAY, alignment=TA_CENTER, spaceBefore=4, spaceAfter=8,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["BodyText"], fontName="Report", fontSize=8.4,
            leading=10.6, textColor=INK, alignment=TA_LEFT,
        ),
        "small_white": ParagraphStyle(
            "SmallWhite", parent=base["BodyText"], fontName="Report-Bold", fontSize=8.5,
            leading=10.7, textColor=WHITE, alignment=TA_LEFT,
        ),
        "cover": ParagraphStyle(
            "Cover", parent=base["Title"], fontName="Report-Bold", fontSize=20,
            leading=25, textColor=colors.black, alignment=TA_CENTER, spaceAfter=9,
        ),
        "cover_small": ParagraphStyle(
            "CoverSmall", parent=base["BodyText"], fontName="Report", fontSize=11,
            leading=15, textColor=GRAY, alignment=TA_CENTER,
        ),
        "cover_header": ParagraphStyle(
            "CoverHeader", parent=base["BodyText"], fontName="Report-Bold", fontSize=12,
            leading=16, textColor=colors.black, alignment=TA_CENTER,
        ),
        "code": ParagraphStyle(
            "CodeLabel", parent=base["BodyText"], fontName="Report-Bold", fontSize=8.2,
            leading=10, textColor=GRAY, spaceBefore=3, spaceAfter=2,
        ),
        "placeholder": ParagraphStyle(
            "Placeholder", parent=base["BodyText"], fontName="Report", fontSize=8.7,
            leading=12, textColor=GRAY, alignment=TA_CENTER,
        ),
    }
    return styles


def para(text, style, raw=False):
    return Paragraph(text if raw else escape(text), style)


def bullet(text, styles):
    return Paragraph("• " + escape(text), styles["body_left"])


def table(headers, rows, widths, styles, font_size=8.3):
    header_cells = [para(str(value), styles["small_white"]) for value in headers]
    body_cells = []
    for row in rows:
        body_cells.append([
            Paragraph(escape(str(value)), ParagraphStyle(
                f"Cell{font_size}", parent=styles["small"], fontSize=font_size,
                leading=font_size + 2.2,
            ))
            for value in row
        ])
    data = [header_cells] + body_cells
    result = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for row_no in range(1, len(data)):
        if row_no % 2 == 0:
            commands.append(("BACKGROUND", (0, row_no), (-1, row_no), PALE))
    result.setStyle(TableStyle(commands))
    return result


def code_block(text, label, styles):
    return [
        para(label.upper(), styles["code"]),
        Preformatted(text, ParagraphStyle(
            "Code", fontName="Courier", fontSize=8, leading=10,
            textColor=INK, backColor=PALE, borderColor=LINE,
            borderWidth=0.5, borderPadding=6, spaceAfter=7,
        )),
    ]


def image_slot(text, width=6.25 * inch, height=0.68 * inch, styles=None):
    cell = para(f"[DÁN ẢNH THẬT SAU KHI DEMO: {escape(text)}]", styles["placeholder"], raw=True)
    box = Table([[cell]], colWidths=[width], rowHeights=[height])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return box


def on_page(canvas, doc):
    page = canvas.getPageNumber()
    if page == 1:
        return
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(2.6 * cm, 1.55 * cm, width - 2.4 * cm, 1.55 * cm)
    canvas.setFont("Report", 8)
    canvas.setFillColor(GRAY)
    canvas.drawString(2.6 * cm, 1.1 * cm, "ĐỀ TÀI 36  ·  HỆ THỐNG QUẢN LÝ CHUNG CƯ")
    canvas.drawRightString(width - 2.4 * cm, 1.1 * cm, f"Trang {page}")
    canvas.restoreState()


def build():
    register_fonts()
    styles = make_styles()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    page_width, page_height = A4
    left, right, top, bottom = 2.6 * cm, 2.4 * cm, 2.3 * cm, 2.05 * cm
    doc = BaseDocTemplate(
        str(OUTPUT), pagesize=A4, title="Báo cáo đề tài 36 - Hệ thống quản lý chung cư",
        author="Sinh viên - vui lòng điền thông tin",
        leftMargin=left, rightMargin=right, topMargin=top, bottomMargin=bottom,
    )
    frame = Frame(left, bottom, page_width - left - right, page_height - top - bottom,
                  id="normal", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="report", frames=[frame], onPage=on_page)])

    story = []

    # Page 1: formal cover.
    story += [Spacer(1, 0.7 * inch)]
    story.append(para("[TÊN TRƯỜNG]", styles["cover_header"]))
    story.append(para("[KHOA / BỘ MÔN]", styles["cover_header"]))
    story += [Spacer(1, 0.7 * inch)]
    story.append(para("BÁO CÁO ĐỀ TÀI THỰC HÀNH", styles["cover"]))
    story.append(para("TRIỂN KHAI VÀ QUẢN TRỊ HỆ THỐNG PHẦN MỀM", styles["cover_header"]))
    story += [Spacer(1, 0.32 * inch)]
    story.append(para("<font color='#185D47'>ĐỀ TÀI 36</font>", styles["cover_header"], raw=True))
    story += [Spacer(1, 0.12 * inch)]
    story.append(para("HỆ THỐNG QUẢN LÝ CHUNG CƯ / CĂN HỘ", styles["cover"]))
    story.append(para("Flask · PostgreSQL · Nginx · Prometheus · Grafana · Loki",
                      styles["cover_small"]))
    story += [Spacer(1, 0.6 * inch)]
    story.append(table(["Thông tin", "Nội dung"], [
        ("Sinh viên", "[HỌ VÀ TÊN]"),
        ("Mã số sinh viên", "[MSSV]"),
        ("Lớp / khóa", "[LỚP / KHÓA]"),
        ("Giảng viên hướng dẫn", "[HỌ TÊN GIẢNG VIÊN]"),
    ], [1.8 * inch, 4.0 * inch], styles, font_size=10))
    story += [Spacer(1, 0.8 * inch)]
    story.append(para("THÁNG 10 NĂM 2026", styles["cover_header"]))

    # Page 2: summary.
    story += [PageBreak(), para("TÓM TẮT", styles["h1"])]
    story.append(para("Báo cáo trình bày thiết kế và cấu hình một hệ thống quản lý chung cư cho đề tài thực hành số 36. Ứng dụng cung cấp các nghiệp vụ quản lý cư dân, theo dõi phí dịch vụ, phát hành thông báo và tiếp nhận phản ánh. PostgreSQL là cơ sở dữ liệu; pgAdmin hỗ trợ quản trị; Nginx tiếp nhận HTTP và chuyển tiếp yêu cầu đến các dịch vụ bên trong.", styles["body"]))
    story.append(para("Hệ thống quan sát gồm Prometheus thu thập metrics, Grafana hiển thị dashboard, Loki lưu log và Promtail đọc log ứng dụng cùng access log Nginx. Các thành phần được khai báo bằng Docker Compose, phân thành các mạng Docker riêng và chỉ công bố cổng Nginx ra máy host.", styles["body"]))
    story.append(para("Stack đã được chạy cục bộ ngày 08/10/2026. Website, pgAdmin, Grafana và Prometheus truy cập qua Nginx trả HTTP 200; cả 5/5 Prometheus target ở trạng thái UP; dashboard có 8 panel. Ba truy vấn LogQL trả lần lượt 14, 29 và 2 dòng. Các ô ảnh vẫn chờ screenshot giao diện thật trước khi nộp.", styles["body"]))
    story.append(para("Mục tiêu thực hành", styles["h2"]))
    for item in [
        "Tổ chức mã nguồn, cấu hình dịch vụ và hướng dẫn chạy trong cùng repository.",
        "Triển khai ứng dụng có cơ sở dữ liệu PostgreSQL và công cụ pgAdmin.",
        "Thiết lập reverse proxy Nginx với security headers cơ bản.",
        "Thu thập metrics container, web server và database; tra cứu log bằng LogQL.",
        "Áp dụng quyền tối thiểu, mật khẩu mạnh, mạng cô lập và container non-root.",
    ]:
        story.append(bullet(item, styles))

    # Page 3: scope.
    story += [PageBreak(), para("1. PHẠM VI VÀ YÊU CẦU", styles["h1"])]
    story.append(para("Đề tài được giới hạn ở một tòa nhà mẫu tên An Bình. Dữ liệu mẫu trong ứng dụng là dữ liệu giả phục vụ trình diễn; không nhập thông tin cư dân thật khi đưa repository lên GitHub.", styles["body"]))
    story.append(table(["Hạng mục đề", "Thiết kế trong dự án", "Minh chứng cần ghi nhận"], [
        ("Mã nguồn / GitHub", "Repository gồm Flask app, cấu hình Compose, monitoring, logging, README và báo cáo.", "URL repository, tài khoản theo MSSV và ba commit rõ nội dung."),
        ("Ứng dụng + database", "Flask/Gunicorn quản lý cư dân, phí, thông báo, phản ánh; PostgreSQL + pgAdmin.", "Trang chức năng và bảng dữ liệu trong pgAdmin."),
        ("Reverse proxy", "Nginx làm điểm vào duy nhất, định tuyến theo path và thêm security headers.", "Truy cập website và response headers."),
        ("Giám sát", "Prometheus scrape web, Nginx exporter, postgres-exporter, cAdvisor; Grafana provision dashboard.", "Targets UP và dashboard có dữ liệu."),
        ("Log tập trung", "Promtail đọc log JSON từ volume; Loki nhận log; Grafana Explore chạy LogQL.", "Ba query LogQL trả về log."),
        ("Hardening", "Non-root, network isolation, DB role hạn chế, secret file, CSRF, headers, read-only.", "Compose, header response và phân tích quyền."),
    ], [1.25 * inch, 3.1 * inch, 1.65 * inch], styles, font_size=7.8))
    story += [Spacer(1, 7)]
    story.append(para("<b>Phạm vi triển khai.</b> Hệ thống dùng HTTP nội bộ với security headers vì đề cho phép lựa chọn này thay cho HTTPS tự ký. Khi triển khai trên mạng thật cần cấu hình TLS, thay mật khẩu demo và rà soát lại CSP theo các ứng dụng được proxy.", styles["body"], raw=True))

    # Page 4: architecture.
    story += [PageBreak(), para("2. KIẾN TRÚC VÀ CÁCH HOẠT ĐỘNG", styles["h1"])]
    story.append(para("Trình duyệt chỉ kết nối cổng HTTP của Nginx. Nginx chuyển yêu cầu ứng dụng đến Flask/Gunicorn; các path /pgadmin/, /grafana/ và /prometheus/ lần lượt dẫn tới công cụ quản trị hoặc quan sát. PostgreSQL không publish port trực tiếp ra host.", styles["body"]))
    arch = Image(str(ASSETS / "architecture.png"), width=6.35 * inch, height=3.27 * inch)
    story += [arch, para("Hình 1. Sơ đồ dịch vụ và các luồng metrics, log của hệ thống.", styles["caption"])]
    story.append(para("Bốn mạng Docker định nghĩa ranh giới kết nối. apartment-ingress chỉ gắn với Nginx để publish cổng host; apartment-edge là mạng nội bộ nơi Nginx giao tiếp với web, pgAdmin, Grafana và Prometheus; apartment-data chứa database cùng các client được cấp quyền; apartment-observability nối Prometheus, Grafana, Loki và exporter. Prometheus cần tham gia nhiều mạng để scrape mục tiêu ở các vùng khác nhau.", styles["body"]))
    story.append(para("Dữ liệu bền vững nằm trong named volumes: PostgreSQL, pgAdmin, Grafana, Prometheus, Loki và log. Lệnh docker compose down dừng container nhưng giữ dữ liệu; lệnh xóa volume mới làm mất trạng thái demo.", styles["body"]))

    # Page 5: model.
    story += [PageBreak(), para("3. MÔ HÌNH DỮ LIỆU VÀ NGHIỆP VỤ", styles["h1"])]
    story.append(para("Cơ sở dữ liệu apartment có bốn nhóm bảng. residents lưu căn hộ và liên hệ; fees lưu từng khoản phải thu; announcements lưu nội dung gửi cư dân; complaints lưu phản ánh, nhóm vấn đề và trạng thái xử lý. Bảng fees tham chiếu residents bằng khóa ngoại resident_id.", styles["body"]))
    erd = Image(str(ASSETS / "data-model.png"), width=6.35 * inch, height=2.95 * inch)
    story += [erd, para("Hình 2. Mô hình quan hệ dữ liệu ở mức khái niệm.", styles["caption"])]
    story.append(table(["Nghiệp vụ", "Đọc dữ liệu", "Ghi dữ liệu"], [
        ("Cư dân", "Danh sách theo mã căn hộ.", "Thêm hồ sơ mới; mã căn hộ duy nhất."),
        ("Phí dịch vụ", "Khoản thu, hạn nộp, tổng chưa thu.", "Đánh dấu đã thanh toán và ghi paid_at."),
        ("Thông báo", "Sắp xếp mới nhất trước.", "Tạo thông báo từ giao diện quản lý."),
        ("Phản ánh", "Ban quản lý xem toàn bộ hàng đợi.", "Cư dân gửi biểu mẫu; quản lý cập nhật trạng thái."),
    ], [1.3 * inch, 2.3 * inch, 2.4 * inch], styles, font_size=8.2))
    story.append(para("Các lệnh SQL dùng placeholder tham số thay vì nối chuỗi đầu vào. Biểu mẫu được bảo vệ bằng CSRF token. Dữ liệu mẫu được chèn idempotent ở mức căn hộ và tiêu đề, tránh nhân bản mỗi lần web container khởi động.", styles["body"]))

    # Page 6: web and database.
    story += [PageBreak(), para("4. ỨNG DỤNG VÀ CƠ SỞ DỮ LIỆU", styles["h1"])]
    story.append(para("Ứng dụng web", styles["h2"]))
    story.append(para("Ứng dụng viết bằng Flask, chạy sau Gunicorn với một worker và bốn thread. Người quản lý đăng nhập bằng mật khẩu được sinh khi tạo .env. Dashboard tổng hợp số cư dân, phí chưa thu, tổng tiền và phản ánh chưa giải quyết. Các trang chức năng cho phép thêm cư dân, ghi nhận thanh toán, đăng thông báo và cập nhật tiến độ phản ánh.", styles["body"]))
    story.append(para("PostgreSQL và pgAdmin", styles["h2"]))
    story.append(para("Container PostgreSQL khởi tạo database apartment và tài khoản bootstrap apartment_admin. Script init tạo role apartment_app với NOSUPERUSER, NOCREATEDB, NOCREATEROLE; role này được cấp CONNECT, quyền sử dụng/tạo bảng trong schema public và pg_monitor để exporter thu thập metrics. Ứng dụng và pgAdmin kết nối bằng apartment_app.", styles["body"]))
    story.append(table(["Cấu hình", "Giá trị", "Lý do"], [
        ("Database", "apartment", "Tên thống nhất."),
        ("Application role", "apartment_app", "Không dùng bootstrap superuser."),
        ("Network", "apartment-data", "Internal, không publish 5432."),
        ("Persistence", "postgres-data", "Giữ dữ liệu qua vòng đời container."),
        ("DB tool", "pgAdmin qua /pgadmin/", "Giao diện quản trị sau Nginx."),
    ], [1.35 * inch, 1.8 * inch, 2.85 * inch], styles, font_size=8.4))
    story.append(para("Kết quả runtime: container web, PostgreSQL và pgAdmin đều healthy; website /login trả HTTP 200 qua Nginx. Buổi demo vẫn cần thao tác tạo cư dân, ghi nhận khoản phí, đăng thông báo, gửi phản ánh và mở các bảng tương ứng trong pgAdmin; chèn ảnh thật vào khung minh chứng.", styles["body"]))

    # Page 7: proxy.
    story += [PageBreak(), para("5. NGINX REVERSE PROXY", styles["h1"])]
    story.append(para("Nginx dùng image unprivileged và lắng nghe cổng container 8080. Cổng host mặc định chỉ bind vào 127.0.0.1:8080; người dùng truy cập website qua một điểm vào. Các service phía sau chỉ expose cổng trên mạng Docker.", styles["body"]))
    story.append(table(["Path", "Upstream", "Mục đích"], [
        ("/", "web:8000", "Ứng dụng Flask."),
        ("/pgadmin/", "pgadmin:80", "Quản lý PostgreSQL."),
        ("/grafana/", "grafana:3000", "Dashboard metrics và log."),
        ("/prometheus/", "prometheus:9090", "Kiểm tra targets và PromQL."),
        ("/healthz", "Nginx local", "Healthcheck reverse proxy."),
        ("/nginx_status", "Nginx stub_status", "Chỉ exporter trong edge network."),
    ], [1.35 * inch, 1.7 * inch, 2.95 * inch], styles, font_size=8.3))
    story.append(para("Security headers và giới hạn truy cập", styles["h2"]))
    for item in [
        "X-Content-Type-Options: nosniff và X-Frame-Options: DENY.",
        "Referrer-Policy, Permissions-Policy và Content-Security-Policy được thêm ở Nginx.",
        "Giới hạn request đăng nhập và gửi phản ánh để giảm spam trong lab.",
        "Nginx chuyển tiếp Host, địa chỉ client và scheme để Flask nhận đúng thông tin proxy.",
    ]:
        story.append(bullet(item, styles))
    story.append(para("Phương án của bài tập là security headers qua HTTP, không phải HTTPS. Không đặt HSTS khi chưa phục vụ TLS. CSP có inline/eval để tương thích Grafana và pgAdmin sau subpath; khi dùng thật cần giới hạn theo kết quả kiểm tra trình duyệt.", styles["body"]))
    story.append(image_slot("website qua Nginx và response headers", styles=styles))

    # Page 8: monitoring.
    story += [PageBreak(), para("6. PROMETHEUS VÀ GRAFANA", styles["h1"])]
    story.append(para("Prometheus scrape mỗi 15 giây. Ứng dụng xuất số request theo method/endpoint/status và histogram latency. Nginx exporter đọc stub_status; postgres-exporter dùng role apartment_app; cAdvisor lấy số liệu CPU và bộ nhớ container từ filesystem host chỉ-đọc.", styles["body"]))
    story.append(table(["Job", "Target", "Metrics minh họa"], [
        ("apartment-web", "web:8000/metrics", "apartment_http_requests_total, latency histogram"),
        ("nginx", "nginx-exporter:9113", "nginx_connections_active"),
        ("postgres", "postgres-exporter:9187", "pg_up và chỉ số PostgreSQL"),
        ("containers", "cadvisor:8080", "CPU, memory của container"),
        ("prometheus", "localhost:9090", "up và trạng thái scrape"),
    ], [1.5 * inch, 2.3 * inch, 2.2 * inch], styles, font_size=8.1))
    story.append(para("Grafana tự nạp datasource Prometheus và Loki cùng dashboard Apartment Management Overview. Dashboard có 8 panel cho request, latency p95, PostgreSQL exporter, kết nối Nginx, CPU/bộ nhớ container và log. Kết quả runtime: datasource Prometheus/Loki đều OK, 5/5 target UP và API dashboard xác nhận 8 panel.", styles["body"]))
    story += code_block('up\nrate(apartment_http_requests_total[5m])\npg_up\nnginx_connections_active\nsum by (name) (rate(container_cpu_usage_seconds_total{id!="/"}[5m]))', "PromQL", styles)
    story.append(image_slot("Grafana dashboard có dữ liệu", styles=styles))
    story.append(para("Khi chụp minh chứng, mở Prometheus Targets và ghi trạng thái từng job. Chỉ đánh dấu job UP sau khi có ảnh hoặc kết quả thực tế; sơ đồ cấu hình trong báo cáo không phải ảnh runtime.", styles["body"]))

    # Page 9: logs.
    story += [PageBreak(), para("7. LOKI, PROMTAIL VÀ LOGQL", styles["h1"])]
    story.append(para("Ứng dụng ghi log JSON ra volume app-logs; Nginx ghi access log JSON ra nginx-logs. Promtail mount hai volume chỉ-đọc, trích trường level/event/status/method và gửi log tới Loki qua mạng observability. Grafana truy vấn Loki bằng datasource đã provision.", styles["body"]))
    story.append(table(["LogQL", "Mục đích"], [
        ('{service="apartment-web"} | json | level="ERROR"', "Tìm lỗi ứng dụng."),
        ('{service="apartment-web"} | json | event="http_request"', "Xem request Flask."),
        ('{service="nginx"} | json | status >= 400', "Tìm phản hồi HTTP lỗi."),
    ], [3.85 * inch, 2.15 * inch], styles, font_size=8.3))
    story.append(para("Label được giới hạn ở service, level, event, status và method. URL không được dùng làm label vì số lượng giá trị có thể tăng liên tục. Path vẫn có trong dòng JSON để lọc khi cần.", styles["body"]))
    story.append(para("Kết quả runtime qua Grafana API: cả ba truy vấn trả trạng thái 200; truy vấn access log, request Flask và HTTP lỗi lần lượt trả 14, 29 và 2 dòng trong khoảng 30 phút tại thời điểm ghi nhận.", styles["body"]))
    story.append(para("Promtail được giữ để khớp yêu cầu môn học. Tài liệu Grafana ghi Promtail đã hết vòng đời (EOL) từ ngày 02/03/2026 và không còn được duy trì; hệ thống này phù hợp cho lab theo đề, còn triển khai lâu dài cần chuyển pipeline sang Grafana Alloy. Nguồn: <link href='https://grafana.com/docs/loki/latest/send-data/promtail/' color='#185D47'>Grafana Promtail agent documentation</link>.", styles["body"], raw=True))
    story.append(image_slot("Grafana Explore trả về ba query LogQL", styles=styles))

    # Page 10: hardening.
    story += [PageBreak(), para("8. HARDENING HỆ THỐNG", styles["h1"])]
    story.append(para("Các kiểm soát dưới đây được đặt trong Dockerfile, Compose, script database và Nginx. Mục tiêu là giảm quyền của thành phần ứng dụng và giữ dịch vụ dữ liệu không mở trực tiếp ra host.", styles["body"]))
    story.append(table(["Kiểm soát", "Triển khai", "Lưu ý"], [
        ("Non-root", "Flask UID 10001; Nginx UID 101; PostgreSQL chạy tiến trình postgres riêng.", "cAdvisor cần đọc host metrics."),
        ("Network isolation", "Ingress chỉ gắn Nginx; edge, data, observability là internal; DB không publish port.", "Nginx là cửa vào host."),
        ("Least privilege", "apartment_app không superuser; exporter dùng quyền đọc metrics.", "pg_monitor dùng cho exporter."),
        ("Secrets", "Mật khẩu ngẫu nhiên trong .env; .gitignore loại khỏi Git.", "Không chụp hoặc commit secret."),
        ("Container", "read_only, tmpfs, cap_drop, no-new-privileges khi tương thích.", "Entry point DB/pgAdmin cần tạo volume."),
        ("Web security", "CSRF, SQL parameters, cookie HttpOnly/SameSite, security headers.", "HTTP demo; dùng TLS ngoài lab."),
        ("Log access", "Promtail đọc volume chỉ-đọc; không mount Docker socket.", "cAdvisor đọc host path chỉ-đọc."),
    ], [1.2 * inch, 3.0 * inch, 1.8 * inch], styles, font_size=7.6))
    story.append(para("Mật khẩu được tạo riêng cho từng máy bằng script. Không dùng tài khoản bootstrap trong ứng dụng; không commit .env. Trước khi public repository, thay ảnh demo có dữ liệu cá nhân bằng dữ liệu giả.", styles["body"]))
    story.append(image_slot("docker compose ps và cổng Nginx được publish", styles=styles))

    # Page 11: operation.
    story += [PageBreak(), para("9. TRIỂN KHAI VÀ DEMO", styles["h1"])]
    story.append(para("Trên Windows, mở PowerShell tại repository, tạo .env một lần rồi build stack. Stack đã chạy cục bộ; các lệnh dưới đây tái tạo demo. Chụp ảnh giao diện thật và hoàn tất các thao tác nghiệp vụ trước khi nộp.", styles["body"]))
    story += code_block("./scripts/new-secrets.ps1\ndocker compose up -d --build\ndocker compose ps\ndocker compose logs -f web nginx postgres", "PowerShell", styles)
    story.append(para("Thứ tự trình bày", styles["h2"]))
    for item in [
        "Đăng nhập; mở dashboard và các trang cư dân, phí, thông báo, phản ánh.",
        "Thêm cư dân, đăng thông báo và gửi phản ánh mẫu.",
        "Mở pgAdmin, kết nối postgres:5432 bằng apartment_app và xem các bảng.",
        "Mở Prometheus Targets và dashboard Grafana; giải thích từng exporter.",
        "Trong Grafana Explore, chạy ba LogQL và phân tích trường, nhãn.",
        "Mở Compose, chỉ ra published port, bốn mạng và thiết lập quyền.",
    ]:
        story.append(bullet(item, styles))
    story.append(para("Ảnh minh chứng cần chèn", styles["h2"]))
    story.append(image_slot("trang tổng quan ứng dụng", height=0.48 * inch, styles=styles))
    story.append(image_slot("pgAdmin và database apartment", height=0.48 * inch, styles=styles))
    story.append(image_slot("Prometheus Targets và Grafana", height=0.48 * inch, styles=styles))
    story.append(para("Các vùng trên là chỗ chèn ảnh thật, không phải kết quả runtime. Che email cá nhân và không hiển thị mật khẩu.", styles["body"]))

    # Page 12: evaluation and appendix.
    story += [PageBreak(), para("10. ĐÁNH GIÁ VÀ KẾT LUẬN", styles["h1"])]
    story.append(para("Bảng này liên kết từng tiêu chí chấm điểm với vị trí minh chứng. Trạng thái phản ánh lần chạy cục bộ ngày 08/10/2026; các ô chờ ảnh cần được thay bằng screenshot thật trước khi nộp.", styles["body"]))
    story.append(table(["Tiêu chí", "Tệp / giao diện", "Trạng thái demo"], [
        ("Quản lý mã nguồn (1.5)", "GitHub, README, git log.", "[CHỜ REPO]"),
        ("Ứng dụng + DB (1.5)", "Website, pgAdmin, dữ liệu.", "[HEALTHY; CHỜ ẢNH/CRUD]"),
        ("Nginx proxy", "URL website, response headers.", "[HTTP 200; CHỜ ẢNH]"),
        ("Prometheus + Grafana", "Targets và dashboard.", "[5/5 UP; 8 PANEL]"),
        ("Loki + LogQL", "Grafana Explore, ba truy vấn.", "[3 QUERY TRẢ LOG]"),
        ("Hardening", "Compose, role DB, headers, mạng.", "[ĐÃ CẤU HÌNH]"),
        ("Tổng thể", "Stack, báo cáo, phần trình bày.", "[CHỜ REPO + ẢNH]"),
    ], [1.7 * inch, 2.8 * inch, 1.5 * inch], styles, font_size=8.0))
    story.append(para("Kết luận", styles["h2"]))
    story.append(para("Thiết kế ghép ứng dụng nghiệp vụ với database và stack quan sát trong cùng Docker Compose. Khi bảo vệ, cần giải thích reverse proxy, role apartment_app, bốn mạng Docker, Prometheus scrape, đường đi của log từ volume qua Promtail vào Loki và ý nghĩa của từng LogQL. Bản nộp còn cần repository GitHub, thông tin sinh viên và screenshot minh chứng giao diện thật.", styles["body"]))
    story.append(para("Hạn chế", styles["h2"]))
    story.append(para("Tài khoản quản lý có một người dùng demo; chưa có TLS, phân quyền nhiều vai trò, backup tự động hoặc triển khai production. Promtail đã EOL nhưng được dùng để đáp ứng yêu cầu của đề.", styles["body"]))
    story.append(para("Mốc commit", styles["h2"]))
    story.append(table(["Commit", "Nội dung"], [
        ("1", "Ứng dụng + PostgreSQL/pgAdmin + Nginx reverse proxy."),
        ("2", "Prometheus, exporters, Grafana datasource và dashboard."),
        ("3", "Loki, Promtail, LogQL, hardening và tài liệu."),
    ], [0.8 * inch, 5.2 * inch], styles, font_size=8.3))
    story.append(para("Tài khoản GitHub đã xác thực: manhbo1000-sketch. Repository apartment-management chưa được tạo; author commit và bìa báo cáo vẫn dùng placeholder cho đến khi có MSSV, họ tên, lớp, trường và giảng viên hướng dẫn.", styles["body"]))
    story.append(para("Tài liệu tham khảo", styles["h2"]))
    story.append(para("Docker Compose: <link href='https://docs.docker.com/compose/' color='#185D47'>docs.docker.com/compose</link><br/>Prometheus: <link href='https://prometheus.io/docs/' color='#185D47'>prometheus.io/docs</link><br/>Grafana Docker: <link href='https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/' color='#185D47'>Grafana installation documentation</link><br/>Promtail lifecycle: <link href='https://grafana.com/docs/loki/latest/send-data/promtail/' color='#185D47'>Grafana Promtail agent documentation</link>", styles["body"], raw=True))
    story.append(para("Ngày lập báo cáo: 08/10/2026. Cập nhật ngày nộp, thông tin cá nhân, URL GitHub và ảnh demo trước khi nộp.", styles["body"]))

    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build()
