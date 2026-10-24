# ĐỒ ÁN ĐA NGÀNH — HƯỚNG TTNT

**ĐẠI HỌC QUỐC GIA THÀNH PHỐ HỒ CHÍ MINH**  
**TRƯỜNG ĐẠI HỌC BÁCH KHOA**  
**KHOA KHOA HỌC VÀ KỸ THUẬT MÁY TÍNH**

**Đề tài:** Nhà thông minh  
**Nhóm:** 1  **Lớp:** L01  **Học kỳ:** 261

> Cấu trúc theo *Báo cáo Đồ án Đa ngành - Hướng TTNT.pdf*.  
> Nội dung đã điền lấy từ *User_requirements.pdf*.  
> Mục chưa có trong User Requirements được ghi *Chưa làm*.

---

## Mục lục

1. Giới thiệu
   - 1.1 Mục đích dự án
   - 1.2 Phạm vi dự án
   - 1.3 Từ viết tắt
2. Phân tích yêu cầu hệ thống
   - 2.1 Các đối tượng tương tác (Actors)
   - 2.2 Yêu cầu chức năng
   - 2.3 Yêu cầu phi chức năng
3. Thiết bị phần cứng
   - 3.1 Bộ vi điều khiển trung tâm
   - 3.2 Nhóm cảm biến thu thập dữ liệu
   - 3.3 Nhóm thiết bị chấp hành và hiển thị
   - 3.4 Sơ đồ kết nối phần cứng
4. Chi tiết Usecase
   - 4.1 Usecase 1: Đăng nhập
   - 4.2 Usecase 2: Đăng ký khuôn mặt
   - 4.3 Usecase 3: Xem thông số môi trường
   - 4.4 Usecase 4: Cảnh báo vượt ngưỡng
   - 4.5 Usecase 5: Điều khiển thiết bị thủ công
   - 4.6 Usecase 6: Xem nhật ký
   - 4.7 Usecase 7: Mở cửa bằng nhận diện khuôn mặt
   - 4.8 Usecase 8: Đối chiếu với mẫu khuôn mặt đã đăng ký
5. Mô hình hoá hệ thống
   - 5.1 Activity Diagram
   - 5.2 Sequence Diagram
6. Kiến trúc kỹ thuật hệ thống
   - 6.1 Tổng quan kiến trúc 4 tầng
   - 6.2 Luồng dữ liệu chính
   - 6.3 Kiến trúc Firmware
   - 6.4 Kiến trúc Backend
   - 6.5 Cơ sở dữ liệu
   - 6.6 Kiến trúc Frontend
7. Tích hợp AI
   - 7.1 Tổng quan giải pháp
   - 7.2 Kiến trúc mô hình
   - 7.3 Pipeline suy luận
   - 7.4 Cơ chế tự động
   - 7.5 Cơ chế ghi đè thủ công
8. Kết luận
   - 8.1 Kết quả đạt được
   - 8.2 Điểm nổi bật so với đề bài gốc
   - 8.3 Hạn chế và hướng phát triển

---

## 1 Giới thiệu

### 1.1 Mục đích dự án

Nhóm đề xuất xây dựng mô hình một phòng nhà thông minh. Người dùng có thể theo dõi nhiệt độ, độ ẩm và mức ánh sáng; nhận cảnh báo khi các thông số vượt ngưỡng; đồng thời bật hoặc tắt đèn, quạt và điều khiển cửa từ giao diện. Cửa có thể được mở bằng nhận diện khuôn mặt. Đèn và quạt còn có thể được điều khiển bằng một tập lệnh giọng nói tiếng Việt cố định.

Khi chức năng nhận diện khuôn mặt hoặc giọng nói gặp lỗi, người dùng vẫn có thể điều khiển thủ công trên giao diện.

Các mô hình AI không chạy trên Yolo:Bit. Board chỉ có nhiệm vụ thu thập dữ liệu cảm biến và điều khiển thiết bị. Quá trình suy luận khuôn mặt và giọng nói được thực hiện trên laptop đóng vai trò Gateway, sử dụng webcam và micro có sẵn của laptop.

### 1.2 Phạm vi dự án

> *Chưa làm trong User Requirements (báo cáo mẫu mô tả 4 thành phần: Web Dashboard, Backend, Adafruit IO, thiết bị phần cứng). Nhóm mới nêu: Yolo:Bit + Gateway (laptop) + Adafruit IO + dashboard; web riêng làm sau.*

### 1.3 Từ viết tắt

> *Chưa làm — bảng giải nghĩa từ viết tắt (IoT, AI, MQTT, …).*

---

## 2 Phân tích yêu cầu hệ thống

### 2.1 Các đối tượng tương tác (Actors)

- **Chủ nhà:** xem thông tin môi trường; điều khiển đèn, quạt và cửa; dùng nhận diện khuôn mặt để mở cửa; dùng giọng nói để bật hoặc tắt đèn và quạt.
- **Hệ thống:** đọc dữ liệu cảm biến, so sánh với ngưỡng, ghi nhật ký, chạy mô hình nhận diện khuôn mặt và nhận lệnh giọng nói tại Gateway.

### 2.2 Yêu cầu chức năng

#### Module 1 – Thu thập và hiển thị dữ liệu môi trường

- Đọc nhiệt độ và độ ẩm từ cảm biến DHT20; đọc mức ánh sáng từ cảm biến ánh sáng.
- Gửi dữ liệu lên Adafruit IO và hiển thị trên dashboard; có thể bổ sung hiển thị trên LCD.
- Biểu diễn ánh sáng theo thang từ 0 đến 100, trong đó 0 là tối và 100 là sáng; không quy đổi sang đơn vị lux.
- Đầu vào: DHT20 và cảm biến ánh sáng.

#### Module 2 – Kiểm tra ngưỡng và cảnh báo

- So sánh dữ liệu từ Module 1 với các ngưỡng có thể điều chỉnh.
- Khi thông số vượt ngưỡng, LED RGB đổi màu và dashboard hiển thị cảnh báo.
- Đầu vào: dữ liệu từ Module 1 và giá trị ngưỡng.
- Đầu ra: trạng thái LED RGB và cảnh báo trên dashboard.

#### Module 3 – Điều khiển thiết bị

- Bật hoặc tắt đèn LED RGB, quạt mini và điều khiển cửa bằng servo từ dashboard hoặc giao diện web.
- Cả ba thiết bị đầu ra đều có sẵn trong kit.
- Chức năng điều khiển thủ công không phụ thuộc vào các tính năng AI.
- Đầu ra: LED RGB, quạt mini và servo.

#### Module 4 – Nhật ký hoạt động

Hệ thống ghi lại:

- lịch sử dữ liệu cảm biến;
- các lần bật hoặc tắt đèn và quạt, cùng các lần đóng hoặc mở cửa;
- các lần hệ thống phát cảnh báo;
- các lần nhận diện khuôn mặt và kết quả đúng hoặc sai.

#### Module 5 – Giao diện

- Sử dụng dashboard Adafruit IO để giám sát và điều khiển hệ thống.
- Có thể bổ sung giao diện web dùng trên máy tính và điện thoại ở giai đoạn sau.
- Không phát triển ứng dụng native.

#### Các tính năng trí tuệ nhân tạo

- **Nhận diện khuôn mặt (AI chính):** sử dụng webcam laptop. Khi nhận diện đúng thành viên đã đăng ký, servo mở cửa; khi không nhận diện được, cửa vẫn đóng. Mô hình có quá trình huấn luyện và được đánh giá trên tập kiểm thử nội bộ.
- **Nhận dạng giọng nói (mở rộng):** sử dụng micro laptop để nhận một tập lệnh tiếng Việt cố định, gồm bật/tắt đèn và bật/tắt quạt.

### 2.3 Yêu cầu phi chức năng

- Dữ liệu cảm biến được cập nhật trên dashboard trong thời gian dưới 5 giây.
- Thiết bị phản hồi trong thời gian dưới 3 giây kể từ khi người dùng nhấn lệnh điều khiển.
- Hệ thống hoạt động ổn định trong khoảng 30 phút trình diễn và không mất kết nối với Adafruit IO.
- Giao diện có thể xem được trên cả điện thoại và máy tính.
- Độ chính xác của mô hình nhận diện khuôn mặt được đo và báo cáo bằng số liệu thực tế trên tập kiểm thử nội bộ, trong điều kiện ánh sáng của phòng demo và khoảng cách từ 0,5–1 m. Nhóm không cam kết trước một mức chính xác cố định.

---

## 3 Thiết bị phần cứng

Yolo:Bit được kết nối với laptop qua cổng USB. Laptop cần có kết nối Internet để giao tiếp với Adafruit IO.

### 3.1 Bộ vi điều khiển trung tâm

- **Yolo:Bit** (không dùng Yolo Uno).
- AI không chạy trên board; board chỉ thu thập cảm biến và điều khiển thiết bị.

> *Chưa làm: thông số chip, môi trường lập trình, so sánh với Yolo Uno như báo cáo mẫu.*

### 3.2 Nhóm cảm biến thu thập dữ liệu

| Vai trò | Thiết bị | Trong kit? |
| --- | --- | --- |
| Input | DHT20 (nhiệt độ, độ ẩm) | Có |
| Input | Cảm biến ánh sáng | Có |
| Input AI | Webcam laptop | Không – dùng máy Gateway |
| Input AI | Micro laptop | Không – dùng máy Gateway |

> *Chưa làm: mô tả nguyên lý từng cảm biến, bus I2C/analog như báo cáo mẫu.*

### 3.3 Nhóm thiết bị chấp hành và hiển thị

| Vai trò | Thiết bị | Trong kit? |
| --- | --- | --- |
| Output | Đèn 4 LED RGB | Có |
| Output | Quạt mini | Có |
| Output | Servo (mô phỏng cửa) | Có |
| Phụ | LCD 16x2 | Có, sử dụng nếu kịp |
| Không dùng | Bơm, cảm biến độ ẩm đất, cảm biến siêu âm, remote | Có, nhóm chủ động loại bỏ |

> *Chưa làm: cách điều khiển PWM, NeoPixel, góc servo.*

### 3.4 Sơ đồ kết nối phần cứng

> *Chưa làm — hình nối dây và bảng GPIO.*

---

## 4 Chi tiết Usecase

Một sơ đồ use case cho toàn hệ thống. Actor trái là **Chủ nhà**, actor phải là **Hệ thống**.

`<<include>>` chỉ có một mũi tên: **UC07 Mở cửa bằng nhận diện khuôn mặt** trỏ tới **UC08 Đối chiếu với mẫu khuôn mặt đã đăng ký**. UC02 Đăng ký khuôn mặt không include UC08.

Điều khiển bằng giọng nói tạm thời không nằm trên sơ đồ và chưa viết description.

---

### 4.1 Usecase 1: Đăng nhập

| | |
| --- | --- |
| Usecase ID | UC01 |
| Usecase Name | Đăng nhập |
| Actor | Chủ nhà |
| Description | Chủ nhà đăng nhập web của nhóm bằng tên đăng nhập và mật khẩu để dùng các chức năng trên web. |
| Precondition | Chủ nhà đã có tài khoản. |
| Post condition | Chủ nhà vào được trang chính của web. |
| Trigger | Chủ nhà mở trang đăng nhập. |
| Normal Flow | 1. Chủ nhà mở trang đăng nhập. 2. Chủ nhà nhập tên đăng nhập và mật khẩu. 3. Hệ thống kiểm tra tài khoản đúng. 4. Hệ thống mở trang chính. |
| Alternative Flow | Sai tên đăng nhập hoặc sai mật khẩu: hệ thống báo đăng nhập không thành công và giữ ở trang đăng nhập. |
| Exception Flow | Web không truy cập được: chủ nhà không đăng nhập được. |

---

### 4.2 Usecase 2: Đăng ký khuôn mặt

| | |
| --- | --- |
| Usecase ID | UC02 |
| Usecase Name | Đăng ký khuôn mặt |
| Actor | Chủ nhà |
| Description | Chủ nhà lưu mẫu khuôn mặt của mình để sau này dùng khi mở cửa. Bước này tạo mẫu mới, không so với mẫu đã có. |
| Precondition | Chủ nhà đã đăng nhập (UC01). Webcam laptop hoạt động. |
| Post condition | Mẫu khuôn mặt được lưu và gắn với tài khoản chủ nhà. |
| Trigger | Chủ nhà chọn chức năng đăng ký khuôn mặt. |
| Normal Flow | 1. Chủ nhà chọn đăng ký khuôn mặt. 2. Chủ nhà đứng trước webcam laptop. 3. Hệ thống lấy khuôn mặt. 4. Hệ thống lưu mẫu và gắn với tài khoản. |
| Alternative Flow | Đăng ký lại: mẫu mới thay mẫu đã lưu trước đó. |
| Exception Flow | Không thấy khuôn mặt hoặc webcam lỗi: hệ thống không lưu mẫu và báo đăng ký không thành công. |

---

### 4.3 Usecase 3: Xem thông số môi trường

| | |
| --- | --- |
| Usecase ID | UC03 |
| Usecase Name | Xem thông số môi trường |
| Actor | Chủ nhà |
| Description | Chủ nhà xem nhiệt độ, độ ẩm và mức ánh sáng hiện tại trên dashboard. Có thể xem thêm trên LCD nếu đã nối. |
| Precondition | Yolo:Bit đang nối cảm biến và laptop. Dashboard Adafruit mở được. |
| Post condition | Dashboard hiển thị nhiệt độ (°C), độ ẩm (%) và ánh sáng (thang 0–100). |
| Trigger | Chủ nhà mở dashboard. |
| Normal Flow | 1. Chủ nhà mở dashboard. 2. Hệ thống đọc DHT20 và cảm biến ánh sáng. 3. Hệ thống đưa số liệu lên Adafruit IO. 4. Dashboard hiển thị ba thông số. |
| Alternative Flow | Nếu đã nối LCD: LCD hiển thị cùng nhiệt độ, độ ẩm và ánh sáng. |
| Exception Flow | Mất kết nối Adafruit: dashboard không cập nhật số mới; chủ nhà thấy dữ liệu cũ hoặc trạng thái mất kết nối. |

---

### 4.4 Usecase 4: Cảnh báo vượt ngưỡng

| | |
| --- | --- |
| Usecase ID | UC04 |
| Usecase Name | Cảnh báo vượt ngưỡng |
| Actor | Hệ thống (khởi phát), Chủ nhà (nhận cảnh báo) |
| Description | Khi nhiệt độ, độ ẩm hoặc ánh sáng vượt ngưỡng đã cấu hình, đèn LED RGB đổi màu và dashboard hiện cảnh báo. |
| Precondition | Đang có dữ liệu môi trường (UC03). Ngưỡng đã có giá trị (mặc định hoặc chủ nhà đã chỉnh). |
| Post condition | LED ở màu cảnh báo và dashboard hiện cảnh báo. Khi thông số về trong ngưỡng, LED và dashboard trở lại bình thường. |
| Trigger | Một thông số vừa đọc vượt ngưỡng. |
| Normal Flow | 1. Hệ thống so sánh dữ liệu mới với ngưỡng. 2. Phát hiện vượt ngưỡng. 3. LED RGB đổi màu cảnh báo. 4. Dashboard hiển thị cảnh báo. 5. Khi thông số trở lại trong ngưỡng, LED và dashboard về trạng thái bình thường. |
| Alternative Flow | Chủ nhà sửa ngưỡng trên giao diện. Lần so sánh tiếp theo dùng ngưỡng mới. |
| Exception Flow | Không đọc được cảm biến: hệ thống không phát cảnh báo. Dashboard giữ trạng thái lần đọc hợp lệ gần nhất. |

---

### 4.5 Usecase 5: Điều khiển thiết bị thủ công

| | |
| --- | --- |
| Usecase ID | UC05 |
| Usecase Name | Điều khiển thiết bị thủ công |
| Actor | Chủ nhà |
| Description | Chủ nhà bật hoặc tắt đèn LED RGB, quạt mini, và đóng hoặc mở cửa (servo) từ dashboard hoặc web. Lệnh này không phụ thuộc nhận diện khuôn mặt. |
| Precondition | Đèn, quạt và servo đã nối với Yolo:Bit. Dashboard hoạt động. |
| Post condition | Thiết bị được chọn đổi đúng trạng thái. Dashboard hiển thị trạng thái mới. |
| Trigger | Chủ nhà bấm nút đèn, quạt hoặc cửa trên giao diện. |
| Normal Flow | 1. Chủ nhà mở dashboard. 2. Chủ nhà bấm bật/tắt đèn, bật/tắt quạt, hoặc mở/đóng cửa. 3. Hệ thống gửi lệnh tới Yolo:Bit. 4. LED, quạt hoặc servo thực hiện lệnh. 5. Dashboard cập nhật trạng thái thiết bị. |
| Alternative Flow | Chủ nhà điều khiển từng thiết bị độc lập. Lệnh cửa không bắt buộc phải qua nhận diện khuôn mặt. |
| Exception Flow | Thiết bị không phản hồi: dashboard báo lệnh không thành công và giữ trạng thái cũ. |

---

### 4.6 Usecase 6: Xem nhật ký

| | |
| --- | --- |
| Usecase ID | UC06 |
| Usecase Name | Xem nhật ký |
| Actor | Chủ nhà |
| Description | Chủ nhà xem lại lịch sử cảm biến, lần bật/tắt đèn và quạt, lần đóng/mở cửa, lần cảnh báo, và lần nhận diện khuôn mặt (đúng hoặc sai). |
| Precondition | Chủ nhà đang xem dashboard. Hệ thống đã ghi ít nhất các sự kiện phát sinh trong lúc chạy. |
| Post condition | Dashboard hiển thị các bản ghi tương ứng. |
| Trigger | Chủ nhà mở phần nhật ký trên dashboard. |
| Normal Flow | 1. Chủ nhà mở phần lịch sử. 2. Hệ thống lấy các bản ghi đã lưu. 3. Dashboard hiển thị lịch sử cảm biến, lịch sử điều khiển thiết bị, danh sách cảnh báo và kết quả nhận diện khuôn mặt. |
| Alternative Flow | Chưa phát sinh sự kiện loại nào: mục đó để trống, các mục khác vẫn xem được. |
| Exception Flow | Mất kết nối: không tải được lịch sử mới; báo lỗi tải dữ liệu. |

---

### 4.7 Usecase 7: Mở cửa bằng nhận diện khuôn mặt

| | |
| --- | --- |
| Usecase ID | UC07 |
| Usecase Name | Mở cửa bằng nhận diện khuôn mặt |
| Actor | Chủ nhà |
| Description | Chủ nhà đứng trước webcam laptop. Hệ thống đối chiếu khuôn mặt với mẫu đã đăng ký. Khớp thì servo mở cửa, không khớp thì cửa giữ đóng. |
| Precondition | Webcam laptop hoạt động. Đã lưu mẫu khuôn mặt (UC02). Servo cửa đã nối. Chương trình nhận diện trên laptop đang chạy. |
| Post condition | Cửa mở khi khớp, cửa đóng khi không khớp. Kết quả được ghi vào nhật ký (UC06). |
| Trigger | Chủ nhà hướng mặt vào webcam. |
| Include | UC08 Đối chiếu với mẫu khuôn mặt đã đăng ký. |
| Normal Flow | 1. Chủ nhà đứng trước webcam laptop. 2. Hệ thống thực hiện UC08. 3. UC08 trả về khớp. 4. Hệ thống ra lệnh mở cửa. 5. Servo mở cửa. 6. Hệ thống ghi kết quả nhận diện đúng. |
| Alternative Flow | UC08 trả về không khớp: servo không mở, cửa giữ đóng, hệ thống ghi kết quả sai. Chủ nhà vẫn mở cửa bằng nút trên dashboard (UC05). |
| Exception Flow | Webcam lỗi hoặc không đối chiếu được: cửa không mở. Điều khiển tay trên dashboard vẫn dùng được (UC05). |

---

### 4.8 Usecase 8: Đối chiếu với mẫu khuôn mặt đã đăng ký

| | |
| --- | --- |
| Usecase ID | UC08 |
| Usecase Name | Đối chiếu với mẫu khuôn mặt đã đăng ký |
| Actor | Không nối trực tiếp. UC07 include use case này. |
| Description | So khuôn mặt đang thấy trên webcam với mẫu đã lưu ở UC02. Kết quả chỉ là khớp hoặc không khớp. Use case này không tự mở cửa. |
| Precondition | UC02 đã lưu mẫu. UC07 đang gọi use case này. |
| Post condition | Có kết quả khớp hoặc không khớp để UC07 quyết định servo. |
| Trigger | UC07 cần đối chiếu khuôn mặt. |
| Normal Flow | 1. Hệ thống lấy khuôn mặt trước webcam. 2. Hệ thống so với mẫu đã lưu. 3. Khớp mẫu: trả về khớp. |
| Alternative Flow | Không khớp mẫu: trả về không khớp. UC07 giữ cửa đóng. |
| Exception Flow | Không thấy khuôn mặt hoặc chương trình nhận diện lỗi: trả về không đối chiếu được. UC07 không mở cửa. |

---


## 5 Mô hình hoá hệ thống

### 5.1 Activity Diagram

> *Chưa làm — sau này vẽ activity riêng cho UC01–UC07. UC08 nằm trong luồng UC07.*

#### 5.1.1 UC01: Đăng nhập

> *Chưa làm.*

#### 5.1.2 UC02: Đăng ký khuôn mặt

> *Chưa làm.*

#### 5.1.3 UC03: Xem thông số môi trường

> *Chưa làm.*

#### 5.1.4 UC04: Cảnh báo vượt ngưỡng

> *Chưa làm.*

#### 5.1.5 UC05: Điều khiển thiết bị thủ công

> *Chưa làm.*

#### 5.1.6 UC06: Xem nhật ký

> *Chưa làm.*

#### 5.1.7 UC07: Mở cửa bằng nhận diện khuôn mặt

> *Chưa làm.*

### 5.2 Sequence Diagram

> *Chưa làm — sau này vẽ sequence riêng cho UC01–UC07. UC08 nằm trong luồng UC07.*

#### 5.2.1 UC01: Đăng nhập

> *Chưa làm.*

#### 5.2.2 UC02: Đăng ký khuôn mặt

> *Chưa làm.*

#### 5.2.3 UC03: Xem thông số môi trường

> *Chưa làm.*

#### 5.2.4 UC04: Cảnh báo vượt ngưỡng

> *Chưa làm.*

#### 5.2.5 UC05: Điều khiển thiết bị thủ công

> *Chưa làm.*

#### 5.2.6 UC06: Xem nhật ký

> *Chưa làm.*

#### 5.2.7 UC07: Mở cửa bằng nhận diện khuôn mặt

> *Chưa làm.*

---

## 6 Kiến trúc kỹ thuật hệ thống

### 6.1 Tổng quan kiến trúc 4 tầng

> *Chưa làm. Báo cáo mẫu: Web – Backend – Adafruit IO – Edge (Yolo Uno). Nhóm mình (UR): Yolo:Bit – Gateway laptop – Adafruit IO – dashboard/web sau.*

### 6.2 Luồng dữ liệu chính

> *Chưa làm.*

### 6.3 Kiến trúc Firmware

> *Chưa làm. Mẫu dùng FreeRTOS trên Yolo Uno; nhóm dùng Yolo:Bit.*

### 6.4 Kiến trúc Backend

> *Chưa làm. Mẫu dùng Flask Blueprints.*

### 6.5 Cơ sở dữ liệu

> *Chưa làm. Mẫu dùng PostgreSQL. Module 4 (nhật ký) mới chỉ là yêu cầu.*

### 6.6 Kiến trúc Frontend

> *Chưa làm. Mẫu dùng React SPA. UR: dashboard Adafruit, web riêng giai đoạn sau.*

---

## 7 Tích hợp AI

> *Báo cáo mẫu là Edge AI / TinyML trên ESP32. User Requirements khác: AI chạy trên Gateway (laptop), không chạy trên Yolo:Bit.*

### 7.1 Tổng quan giải pháp

- AI chính: nhận diện khuôn mặt trên webcam laptop; đúng thành viên thì servo mở cửa.
- AI mở rộng: giọng nói trên micro laptop, tập lệnh cố định (bật/tắt đèn, bật/tắt quạt).

> *Chưa làm: mô tả pipeline, thư viện, cách train.*

### 7.2 Kiến trúc mô hình

> *Chưa làm.*

### 7.3 Pipeline suy luận

> *Chưa làm. Suy luận tại laptop (Gateway), không phải trên ESP32 như mẫu.*

### 7.4 Cơ chế tự động

> *Chưa làm. Mẫu có Auto Cooling Ramp — UR không có.*

### 7.5 Cơ chế ghi đè thủ công

Điều khiển thủ công không phụ thuộc AI. Khi Face hoặc giọng nói lỗi, người dùng vẫn bấm trên giao diện được.

> *Chưa làm: chi tiết timer / lockdown như báo cáo mẫu.*

---

## 8 Kết luận

### 8.1 Kết quả đạt được

> *Chưa làm.*

### 8.2 Điểm nổi bật so với đề bài gốc

> *Chưa làm.*

### 8.3 Hạn chế và hướng phát triển

> *Chưa làm.*
