# Thiết kế hiện tại: Voice Password bằng MFCC + DTW

Trình duyệt ghi WAV/PCM và cho nghe lại. Backend dùng FFmpeg đổi audio về mono 16 kHz, kiểm tra thời lượng 1–8 giây, độ lớn, clipping và khoảng lặng. Mỗi bản ghi được chia frame và trích 13 hệ số MFCC. Audio gốc được xóa sau xử lý.

Đăng ký: người dùng đọc **cùng một câu** 3 lần. Backend lưu ba ma trận MFCC và ba vector người nói trong `backend/data/templates/`, tính ngưỡng DTW và ngưỡng người nói rồi kích hoạt sau mẫu thứ ba.

Mở két: mẫu mới được so DTW với cả 3 ma trận. Điểm DTW là trung bình của **hai khoảng cách nhỏ nhất**. Nếu đạt ngưỡng, backend tính thêm độ giống người nói với ba vector đăng ký. Chỉ khi cả hai đạt mới ghi log Access Granted và mở két. Audio sai hoặc lỗi xử lý giữ két khóa. Mỗi hồ sơ có 5 lần thử sai liên tiếp trước khi tạm khóa 60 giây.

```text
Đăng ký: 3 lần đọc cùng câu → MFCC + vector người nói × 3 → hai ngưỡng riêng
Xác thực: đọc lại câu → MFCC → DTW với 3 mẫu → trung bình 2 điểm thấp nhất
                              → vector người nói → độ giống cosine với 3 mẫu
                                                ↓
                                cả hai đạt ngưỡng: mở két
```

Hồ sơ đoạn văn hoặc MFCC đơn thuần từ bản cũ vẫn ở database nhưng không tham gia xác thực hiện tại. Tạo hồ sơ mới bằng ba lần đọc cùng câu để có đủ cả hai loại đặc trưng.

Hạn chế: lớp người nói làm giảm nguy cơ giọng khác đọc đúng câu nhưng không bảo đảm chặn giọng AI được nhái sát hoặc bản ghi phát lại. Ngưỡng từ ba mẫu chỉ phục vụ demo ban đầu; cần validation có người thật, giọng AI và âm thanh phát lại để báo cáo FAR/FRR.
