# Protocol đánh giá MFCC + DTW

Với mỗi người tham gia đã đồng ý, chọn **một câu mật khẩu cố định** (ví dụ “Mở két an toàn”). Đăng ký bằng 3 lần đọc câu đó trong phòng yên tĩnh. Thu thêm mẫu validation/test ở buổi hoặc thời điểm khác; không tái sử dụng audio đăng ký làm test.

Tập test nên có năm nhóm: đúng người đọc đúng câu; đúng người đọc câu khác; người khác đọc đúng câu; giọng AI đọc đúng câu hoặc âm thanh phát lại; audio quá nhỏ hoặc lỗi. Thử thêm nói nhanh/chậm, đổi khoảng cách microphone và có tiếng ồn. Ghi ID người đọc, câu, thiết bị, điều kiện thu và nhãn kết quả trong `datasets/manifest.example.csv`.

Điểm DTW càng thấp càng giống câu; độ giống người nói càng cao càng khớp. Hai ngưỡng từ ba mẫu chỉ là giá trị khởi đầu. Script `scripts/calibrate_threshold.py` đọc CSV `label,score` (nhãn `genuine`/`impostor`) để chọn ngưỡng DTW dựa trên validation; ngưỡng người nói cũng phải kiểm tra trên giọng thật và giọng AI trước khi báo cáo kết quả. Dùng tập test độc lập, không chọn lại test sau khi xem điểm.

Báo cáo confusion matrix, accuracy, FAR, FRR, median/p95 thời gian xử lý và các trường hợp từ chối nhầm. Mục tiêu ≥90% accuracy và ≤2 giây là mục tiêu, không phải kết quả đã được chứng minh. Nêu rõ nguy cơ replay attack và việc MFCC + DTW không phải giải pháp sinh trắc học hoàn chỉnh.
