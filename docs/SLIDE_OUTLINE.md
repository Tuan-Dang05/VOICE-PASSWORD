# Slide thuyết trình

1. Đề tài và mục tiêu mô phỏng két sắt bằng Voice Password.
2. Người dùng đăng ký một câu bằng ba lần đọc.
3. Sơ đồ browser → FastAPI → audio 16 kHz → MFCC → DTW → threshold → UI.
4. MFCC: ma trận đặc trưng theo frame.
5. DTW: so chuỗi MFCC dù tốc độ đọc khác nhẹ.
6. Hai điểm: DTW so câu mật khẩu và speaker similarity so người nói; cả hai phải đạt ngưỡng.
7. Demo thử câu sai, giọng khác đọc đúng câu, rồi giọng đăng ký đọc đúng câu để mở và tự khóa.
8. Kết quả test FAR/FRR/latency thật và giới hạn replay attack.
