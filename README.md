# Hệ thống quản lý chung cư An Bình

Ứng dụng thực hành triển khai và quản trị hệ thống phần mềm. Hệ thống quản lý hồ sơ cư dân, phí dịch vụ, thông báo và phản ánh; PostgreSQL lưu dữ liệu, Nginx làm reverse proxy, Prometheus và Grafana giám sát metrics, Loki và Promtail tập trung log. Toàn bộ dịch vụ chạy bằng Docker Compose.

## Chức năng

- Đăng nhập quản lý bằng tài khoản khởi tạo từ tệp bí mật riêng.
- Xem tổng quan số cư dân, phí chờ thu, phản ánh chưa giải quyết và thông báo mới.
- Thêm cư dân, theo dõi phí và ghi nhận thanh toán.
- Đăng thông báo cho cư dân.
- Nhận phản ánh công khai và cập nhật trạng thái xử lý sau khi đăng nhập.
- pgAdmin để xem cấu trúc và dữ liệu PostgreSQL.
- Dashboard Grafana được provision tự động, gồm metrics ứng dụng, Nginx, PostgreSQL và container.
- Loki truy vấn log ứng dụng và access log Nginx bằng LogQL.

## Kiến trúc

~~~mermaid
flowchart LR
  User[Trình duyệt] -->|HTTP :8080| Nginx[Nginx reverse proxy]
  Nginx --> Web[Flask web :8000]
  Nginx --> PgAdmin[pgAdmin]
  Nginx --> Grafana[Grafana]
  Nginx --> Prom[Prometheus]
  Web -->|role apartment_app| DB[(PostgreSQL)]
  PgAdmin -->|role apartment_app| DB
  Prom --> Web
  Prom --> NginxExp[Nginx exporter]
  Prom --> PgExp[Postgres exporter]
  Prom --> Cadvisor[cAdvisor]
  Grafana --> Prom
  Grafana --> Loki[Loki]
  Promtail[Promtail] -->|application + Nginx logs| Loki
~~~

Docker dùng bốn mạng. apartment-ingress chỉ gắn với Nginx để publish cổng host; apartment-edge là mạng nội bộ nối proxy với web, pgAdmin, Grafana và Prometheus; apartment-data chứa database cùng các client được cấp quyền; apartment-observability nối Prometheus, Grafana, Loki và exporter. PostgreSQL, Grafana, Prometheus, Loki và pgAdmin không mở cổng riêng ra host.

## Chạy trên Windows

Yêu cầu Docker Desktop đang chạy và hỗ trợ Docker Compose.

1. Tạo các mật khẩu ngẫu nhiên cục bộ. PowerShell tại thư mục dự án:

   ~~~powershell
   ./scripts/new-secrets.ps1
   ~~~

   Script tạo .env nếu chưa tồn tại, in tài khoản demo để lưu lại và không ghi bí mật vào Git. Không chia sẻ tệp .env.

2. Build và khởi chạy:

   ~~~powershell
   docker compose up -d --build
   ~~~

3. Theo dõi trạng thái và log khởi động:

   ~~~powershell
   docker compose ps
   docker compose logs -f web nginx postgres
   ~~~

4. Mở các trang:

   | Thành phần | Địa chỉ |
   | --- | --- |
   | Website quản lý | http://localhost:8080 |
   | pgAdmin | http://localhost:8080/pgadmin/ |
   | Grafana | http://localhost:8080/grafana/ |
   | Prometheus | http://localhost:8080/prometheus/ |

   Đăng nhập ứng dụng bằng APP_ADMIN_USERNAME và APP_ADMIN_PASSWORD trong .env. Grafana dùng cùng cặp tên đăng nhập/mật khẩu. pgAdmin dùng PGADMIN_EMAIL và PGADMIN_PASSWORD.

5. Trong pgAdmin, đăng ký máy chủ nếu chưa có sẵn:

   - Host: postgres
   - Port: 5432
   - Maintenance database: apartment
   - Username: apartment_app
   - Password: giá trị APARTMENT_DB_PASSWORD trong .env

   Database chỉ nhận kết nối từ mạng Docker nội bộ. Không dùng apartment_admin cho ứng dụng; tài khoản này chỉ bootstrap PostgreSQL.

## Giám sát

Dashboard Apartment Management Overview được nạp tự động vào Grafana trong folder Apartment operations. Mở Dashboards → Apartment operations để xem:

- Tốc độ request và độ trễ p95 của ứng dụng.
- Trạng thái exporter PostgreSQL và kết nối Nginx.
- CPU và bộ nhớ container từ cAdvisor.
- Log lỗi ứng dụng và access log Nginx từ Loki.

Một số biểu thức PromQL để kiểm tra nhanh:

~~~promql
up
rate(apartment_http_requests_total[5m])
pg_up
nginx_connections_active
sum by (name) (rate(container_cpu_usage_seconds_total{id!="/"}[5m]))
~~~

## Truy vấn log bằng LogQL

Mở Grafana → Explore → chọn datasource Loki. Gửi vài request trên website để có log mới, sau đó chạy:

~~~logql
{service="apartment-web"} | json | level="ERROR"
~~~

Lọc các request do Flask ghi lại:

~~~logql
{service="apartment-web"} | json | event="http_request"
~~~

Lọc request lỗi từ Nginx:

~~~logql
{service="nginx"} | json | status >= 400
~~~

Promtail đọc hai volume log chỉ-đọc: log JSON của ứng dụng và access log JSON của Nginx. Label chỉ gồm service, mức độ, event, phương thức và mã trạng thái để tránh tạo label theo từng người dùng hoặc URL.

## Cấu hình bảo mật

- Flask và Nginx chạy bằng UID không phải root; container ứng dụng/Nginx và các collector có filesystem chỉ đọc hoặc capability bị loại bỏ khi tương thích.
- no-new-privileges được bật cho các dịch vụ ứng dụng và quan sát.
- PostgreSQL không publish cổng ra host; database thuộc mạng internal.
- Ứng dụng và exporter dùng role apartment_app không có quyền superuser, tạo database hoặc tạo role. Role có pg_monitor để exporter thu thập số liệu đọc.
- Mật khẩu được tạo ngẫu nhiên và lưu trong .env, được .gitignore loại khỏi Git. Không dùng giá trị trong .env.example để chạy.
- Nginx đặt giới hạn request đăng nhập và security headers gồm CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy.
- CSRF được bật cho biểu mẫu; cookie phiên có HttpOnly và SameSite=Lax; dữ liệu biểu mẫu được truy vấn bằng tham số SQL.
- cAdvisor chỉ mount các đường dẫn host ở chế độ read-only để đọc thống kê container. Container này cần quyền đọc metadata host để quan sát; không mount API Docker socket.
- Bài tập yêu cầu Promtail. Theo tài liệu Grafana, Promtail đã EOL ngày 02/03/2026; cấu hình này dành cho lab và nên chuyển sang Grafana Alloy cho hệ thống sử dụng lâu dài: https://grafana.com/docs/loki/latest/send-data/promtail/.

Nginx chạy HTTP với security headers theo lựa chọn của đề. Hãy bổ sung TLS khi triển khai trên mạng thật; CSP hiện cho phép inline/eval để giao diện công cụ Grafana/pgAdmin hoạt động qua cùng proxy.

## Dữ liệu và vòng đời

PostgreSQL tự tạo role ứng dụng khi khởi tạo volume lần đầu; ứng dụng tạo bảng và một số bản ghi mẫu khi khởi động. Tệp .env chỉ được đọc lúc container khởi tạo, nên đổi mật khẩu khi volume đã tồn tại không tự cập nhật mật khẩu role trong database.

- Dừng container nhưng giữ dữ liệu: docker compose down
- Khởi động lại: docker compose up -d
- Xóa toàn bộ dữ liệu demo: docker compose down -v (xóa database, Grafana, pgAdmin, Loki và log volumes)

## Bố cục repository

~~~text
app/                              Flask app, templates, CSS và Dockerfile
db/init/                          Tạo role PostgreSQL giới hạn quyền
nginx/                            Reverse proxy và cấu hình security headers
monitoring/prometheus/            Cấu hình scrape targets
monitoring/grafana/               Datasource provisioning và dashboard
monitoring/loki/                  Cấu hình lưu log
monitoring/promtail/              Pipeline đọc log ứng dụng/Nginx
scripts/new-secrets.ps1           Tạo bí mật ngẫu nhiên cho máy lab
docs/                             Báo cáo và checklist ảnh minh chứng
docker-compose.yml                Toàn bộ stack
~~~

## Chuẩn bị GitHub

Trước khi public repository:

1. Đổi MSSV/họ tên/lớp/trường trong báo cáo và đặt tên GitHub theo quy định môn học.
2. Không commit .env, mật khẩu, dữ liệu cư dân thật hoặc ảnh chụp chứa bí mật.
3. Tạo repository bằng tài khoản sinh viên, rồi thêm remote và push:

   ~~~powershell
   git remote add origin https://github.com/<MSSV>/<TEN_REPOSITORY>.git
   git push -u origin main
   ~~~

4. Kiểm tra các mốc commit:

   ~~~powershell
   git log --oneline
   ~~~

Tên/email author commit cần được đổi thành thông tin sinh viên trước khi push nếu đang để giá trị placeholder.

## Ảnh minh chứng cần chụp khi demo

Lưu ảnh vào docs/screenshots/ sau khi tự chạy stack:

1. Website tổng quan và các trang cư dân, phí, thông báo, phản ánh.
2. pgAdmin hiển thị các bảng trong database apartment.
3. Grafana dashboard với metrics đang có dữ liệu.
4. Prometheus trang Targets có các job ở trạng thái UP.
5. Grafana Explore hiển thị kết quả ít nhất ba query LogQL ở trên.
6. docker compose ps và cấu hình mạng/port minh họa hardening.

Không chụp .env hoặc thông tin xác thực. Thay các khung chờ trong báo cáo bằng ảnh thật sau khi demo.
