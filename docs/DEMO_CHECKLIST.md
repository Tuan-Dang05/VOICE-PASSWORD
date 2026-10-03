# Checklist demo

1. Khởi động backend và frontend trên localhost; kiểm tra microphone Chrome hoặc Edge.
2. Tại **Đăng ký giọng**, chọn câu ngắn, đọc đúng câu đó 3 lần, nghe lại từng lần và lưu.
3. Tại **Két sắt**, đọc sai câu: Access Denied; xem điểm DTW và ngưỡng trong lịch sử.
4. Cho người khác hoặc giọng AI đọc đúng câu: Access Denied nếu điểm người nói dưới ngưỡng. Ghi lại điểm DTW và độ giống người nói của từng lần thử.
5. Đọc đúng câu bằng giọng đã đăng ký: Access Granted; xem cửa két 3D mở rồi tự khóa.
6. Giải thích MFCC + DTW kiểm tra câu, còn vector người nói là lớp kiểm tra bổ sung. Cả hai phải đạt ngưỡng.
7. Kết luận giới hạn giọng nhái và replay attack, điều kiện thu và kết quả kiểm thử thực tế.

Nút **Xem thử mở két** chỉ mô phỏng hoạt ảnh, không phải lần xác thực.
