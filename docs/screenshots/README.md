# Ảnh minh chứng

Sau khi chạy demo, lưu ảnh thật vào thư mục này. Nên chụp:

1. Trang tổng quan, danh sách/cấp tài khoản cư dân, và cổng cư dân chỉ hiện dữ liệu của căn hộ đăng nhập.
2. pgAdmin mở database apartment.
3. Grafana dashboard có dữ liệu.
4. Prometheus Targets với các exporter UP và trang Alerts khi một target DOWN/Firing rồi hồi phục.
5. Grafana Explore trả về ít nhất ba truy vấn LogQL.
6. Docker Compose services và các cổng đã publish.
7. Lệnh tạo backup và kết quả khôi phục thử trong `apartment_restore_test` (không chụp nội dung bản dump hoặc bí mật).

Che mật khẩu, email cá nhân, địa chỉ IP công khai và dữ liệu thật trước khi nộp. Tệp .env không được chụp hoặc commit.
