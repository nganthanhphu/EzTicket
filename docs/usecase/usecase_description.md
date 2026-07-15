# Đặc tả usecase

## Đặt vé
| Thuộc tính | Chi tiết |
| :--- | :--- |
| **Usecase ID** | UC01 |
| **Tên usecase** | Đặt vé |
| **Mô tả** | Cho phép khách hàng đặt vé sự kiện trên hệ thống để nhận vé tham gia sự kiện |
| **Actor chính** | Khách hàng |
| **Actor phụ** | EmailService |
| **Tiền điều kiện** | Khách hàng đã đăng nhập vào hệ thống thành công |
| **Hậu điều kiện** | Sau khi đặt vé khách hàng phải tiến hành thanh toán và gửi vé điện tử qua email |
| **Luồng hoạt động** | 1. Khách hàng chọn sự kiện muốn mua vé<br>2. Khách hàng chọn loại vé muốn đặt<br>3. Khách hàng chọn số lượng vé<br>4. Khách hàng áp dụng voucher<br>5. Hệ thống kiểm tra voucher<br>6. Khách hàng bấm đặt vé<br>7. Hệ thống giữ vé và yêu cầu thanh toán<br>8. Khách hàng tiến hành chụp khuôn mặt<br>9. Hệ thống tạo vé và gửi qua email<br>10. Kết thúc |
| **Luồng thay thế** | A5.1 Nếu voucher không hợp lệ, quay lại bước 4 |
| **Luồng ngoại lệ** | E6.1 Nếu khách hàng hủy đặt vé, kết thúc usecase<br>E6.2 Nếu vé không đáp ứng đủ số lượng, kết thúc usecase<br>E7.1 Nếu thanh toán thất bại, kết thúc usecase |

---

## Xác thực vé
| Thuộc tính | Chi tiết |
| :--- | :--- |
| **Usecase ID** | UC02 |
| **Tên usecase** | Xác thực vé |
| **Mô tả** | Kiểm tra tính hợp lệ của vé và xác nhận khách được phép vào sự kiện. |
| **Actor chính** | Nhà tổ chức |
| **Actor phụ** | FaceRecognitionService |
| **Tiền điều kiện** | Nhân viên đã đăng nhâp bằng tài khoản nhà tổ chức sự kiện |
| **Hậu điều kiện** | Không có |
| **Luồng hoạt động** | 1. Nhân viên tổ chức sự kiện chọn chức năng soát vé.<br>2. Nhân viên quét mã vé khách hàng cung cấp<br>3. Hệ thống xử lý và thông báo kết quả xác thực mã vé.<br>4. Nhân viên quét khuôn mặt của khách hàng<br>5. Hệ thống xử lý xác thực khuôn mặt thông qua FaceRecognitionService và thông báo kết quả xác thực khuôn mặt.<br>6. Kết thúc |
| **Luồng thay thế** | A3.1 Nếu mã vé không hợp lệ, thông báo và quay lại bước 2<br>A5.1 Nếu khuôn mặt không hợp lệ, thông báo và quay lại bước 4 |
| **Luồng ngoại lệ** | Không có |

---

## Thống kê doanh thu
| Thuộc tính | Chi tiết |
| :--- | :--- |
| **Usecase ID** | UC03 |
| **Tên usecase** | Thống kê doanh thu |
| **Mô tả** | Usecase này cho phép quản trị viên và nhà tổ chức xem thống kê doanh thu vé sự kiện bán ra |
| **Actor chính** | Quản trị viên, Nhà tổ chức |
| **Actor phụ** | ChartJS |
| **Tiền điều kiện** | Người dùng đã đăng nhập với vai trò quản trị viên hoặc nhà tổ chức |
| **Hậu điều kiện** | Không có |
| **Luồng hoạt động** | 1. Người dùng chọn chức năng xem báo cáo doanh thu<br>2. Người dùng chọn loại báo cáo thống kê<br>3. Người dùng chọn thời điểm thống kê<br>4. Hệ thống lấy dữ liệu thống kê tương ứng<br>5. Hệ thống vẽ biểu đồ sử dụng Chart.js<br>6. Kết thúc |
| **Luồng thay thế** | Không có |
| **Luồng ngoại lệ** | Không có |

---

## Hủy vé
| Thuộc tính | Chi tiết |
| :--- | :--- |
| **Usecase ID** | UC04 |
| **Tên usecase** | Hủy vé |
| **Mô tả** | Usecase này cho phép khách hàng hủy vé trong thời gian cho phép nếu không còn nhu cầu không tham gia sư kiện |
| **Actor chính** | Khách hàng |
| **Actor phụ** | EmailService |
| **Tiền điều kiện** | Khách hàng đăng nhập thành công vào tài khoản |
| **Hậu điều kiện** | Khách hàng hủy vé thành công và hệ thống đã ghi nhận. |
| **Luồng hoạt động** | 1. Khách hàng chọn vé cần hủy trong giao diện lịch sử đặt vé<br>2. Khách hàng xác nhận hủy vé<br>3. Hệ thống kiểm tra điều kiện hủy vé<br>4. Hệ thống ghi nhận, cập nhật vé và sự kiện<br>5. Hệ thống gửi thông báo qua email.<br>6. Kết thúc |
| **Luồng thay thế** | Không có |
| **Luồng ngoại lệ** | E3.1 Nếu vé đã quá thời hạn cho phép hủy, thông báo và kết thúc usecase |
