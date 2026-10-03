# VoiceVault — khóa két bằng Voice Password dùng MFCC + DTW

Website mô phỏng két sắt. Bạn chọn **một câu ngắn**, đọc **cùng câu đó 3 lần** để đăng ký rồi đọc lại để mở két. MFCC + DTW kiểm tra câu mật khẩu. Để giảm trường hợp giọng khác hoặc giọng AI đọc đúng câu cũng mở được, hệ thống kiểm tra thêm **đặc trưng người nói** từ chính ba lần thu đó.

## Cài đặt sau khi clone (Windows)

Cần cài [Git](https://git-scm.com/downloads), Python 3.11, Node.js **22.12 trở lên** và [FFmpeg](https://ffmpeg.org/download.html). Kiểm tra trong PowerShell bằng `git --version`, `python --version`, `node --version`, `npm --version` và `ffmpeg -version`. Nếu `ffmpeg` không nhận lệnh, thêm thư mục chứa `ffmpeg.exe` vào `PATH` rồi mở terminal mới.

**1. Clone và tạo cấu hình cục bộ:**

```powershell
git clone https://github.com/Tuan-Dang05/VOICE-PASSWORD.git
cd VOICE-PASSWORD
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
notepad .env
```

Thay `VOICE_SECRET_KEY=change-this-before-sharing` trong `.env` bằng chuỗi ngẫu nhiên vừa tạo. Giữ file `.env` trên máy, không đưa lên GitHub. Các giá trị còn lại đã đặt cho localhost.

**2. Terminal thứ nhất — chạy backend:**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe ..\scripts\prepare_voice_models.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Lần đầu, lệnh `prepare_voice_models.py` tải mô hình nhận dạng người nói khoảng 27 MB vào `backend/data/models/`; lần sau không cần tải lại. Backend tự tạo database SQLite và các thư mục lưu mẫu. Khi thấy `Uvicorn running on http://127.0.0.1:8000`, kiểm tra [API health](http://localhost:8000/api/health) hoặc [OpenAPI](http://localhost:8000/docs).

**3. Terminal thứ hai — chạy frontend:**

```powershell
cd frontend
npm ci
npm run dev
```

Mở [http://localhost:5173](http://localhost:5173) bằng Chrome hoặc Edge. Đăng ký tài khoản, cho phép microphone và làm theo phần **Dùng thử** bên dưới. Để dừng ứng dụng, nhấn `Ctrl+C` trong cả hai terminal. Khi thay đổi code backend, `--reload` sẽ tự khởi động lại; sau khi thay dependency hoặc cấu hình thì khởi động lại thủ công.

## Dùng thử

1. Tại **Đăng ký giọng**, nhập tên và câu mật khẩu dễ đọc, ví dụ “Mở két an toàn”.
2. Đọc nguyên câu 3 lần riêng biệt, mỗi lần khoảng 1–3 giây. Sau từng lần, bấm **Dừng thu**, nghe lại và bấm **Lưu mẫu**. Lần thứ ba xong là sẵn sàng.
3. Tại **Két sắt**, chọn mật khẩu vừa tạo và đọc lại đúng câu. Nếu cả **điểm DTW ≤ ngưỡng DTW** và **độ giống người nói ≥ ngưỡng giọng**, két sẽ mở và tự khóa sau 8 giây.

Giữ cùng microphone và khoảng cách nói ổn định. Nếu bị từ chối, giao diện hiển thị riêng điểm DTW và độ giống giọng. Audio không hợp lệ hoặc lỗi xử lý không mở két. Câu nói thêm/bớt từ có thể bị từ chối vì đây là mật khẩu âm thanh cố định.

## Cách hoạt động và dữ liệu

Trình duyệt ghi WAV/PCM để nghe lại trước khi gửi. Backend dùng FFmpeg chuyển về mono 16 kHz, kiểm tra độ dài 1–8 giây, âm lượng, clipping và khoảng lặng. Từ mỗi lần thu, backend lưu:

- Một chuỗi MFCC theo frame để so câu mật khẩu bằng DTW.
- Một vector đặc trưng người nói do mô hình Sherpa-ONNX đã huấn luyện sẵn trích xuất.

Các đặc trưng nằm trong `backend/data/templates/*.npz`. Database `backend/data/voice_password.db` lưu tài khoản, câu mật khẩu, ngưỡng, đường dẫn mẫu và log. Audio gốc chỉ là file tạm, được xóa sau xử lý. Ba lần thu **tạo hồ sơ tham chiếu**, không train lại mô hình.

Ngưỡng DTW được đặt từ khoảng cách giữa ba lần thu; ngưỡng giọng được khởi tạo từ độ giống giữa ba vector. Đây là ngưỡng demo, **chưa được hiệu chỉnh theo FAR/FRR trên nhiều người**. Giọng AI được nhái sát giọng bạn hoặc bản ghi phát lại có thể vẫn vượt qua. [ASVspoof](https://www.asvspoof.org/index2021.html) nghiên cứu các kiểu tấn công này như những bài toán riêng, cần dữ liệu thử nghiệm và biện pháp chuyên biệt.

**Sau cập nhật này:** dừng backend cũ bằng `Ctrl+C`, chạy lại và tải trang bằng `Ctrl+F5`. Hồ sơ MFCC + DTW cũ **được giữ nguyên** trong database nhưng thiếu đặc trưng người nói do audio gốc đã xóa, nên được ghi là **Bản cũ** và không dùng để mở két. Bấm **Đăng ký đơn giản** để điền lại tên/câu và thu bộ ba mẫu mới. Không cần xóa mẫu cũ.

## Thử file giọng AI

Để tính điểm của file mà không thay đổi hồ sơ hay log (chạy từ thư mục gốc sau khi đã cài backend):

```powershell
backend\.venv\Scripts\python.exe scripts\diagnose_voice_sample.py giọng_test_AI.mp3 --profile-id 2
```

Script đọc được cả điểm DTW lẫn điểm người nói đối với **hồ sơ mới**. Với hồ sơ cũ, nó chỉ tính được DTW; file MP3 gốc từng thử có điểm 3,8618 so với ngưỡng 3,7467, nhưng bản phát qua loa rồi thu micro có thể cho điểm khác. File `giọng_test_AI.mp3` là dữ liệu thử cá nhân và **không nằm trong GitHub**; hãy thay bằng đường dẫn tới bản ghi của bạn. Thử giọng thật và giọng AI trên cùng thiết bị sau khi thu lại hồ sơ để đánh giá.

## Docker và kiểm thử

Nếu đã cài Docker Desktop, chạy từ thư mục gốc:

```powershell
Copy-Item .env.example .env
docker compose run --rm backend python scripts/prepare_voice_models.py --models-dir /app/data/models
docker compose up --build
```

Thay `VOICE_SECRET_KEY` trong `.env` trước khi chạy. Giao diện ở `http://localhost:5173`, API ở `http://localhost:8000`. Docker Compose chưa được chạy kiểm thử trên máy phát triển hiện tại vì máy đó không có Docker Desktop.

Lệnh chạy test:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm test
npm run build
```

Bộ dữ liệu test thật, tỷ lệ FAR/FRR và thời gian xử lý thực tế vẫn cần đo theo `docs/EVALUATION_PROTOCOL.md`. Không đưa bản ghi giọng của người tham gia lên Git nếu chưa được đồng ý.

## Cấu trúc repo và dữ liệu riêng tư

- `frontend/`: React, TypeScript, két 3D và thu WAV. `npm ci` dùng phiên bản trong `package-lock.json`.
- `backend/app/`: FastAPI, xử lý âm thanh, MFCC + DTW, kiểm tra người nói và SQLite; `backend/tests/` là test.
- `scripts/`, `docs/`, `datasets/manifest.example.csv`: công cụ chẩn đoán, hướng dẫn và mẫu mô tả dữ liệu đánh giá.
- `backend/data/`: database, đặc trưng giọng và mô hình tải về **chỉ nằm trên máy chạy**, không được commit. File audio thử cá nhân, `.env` và thư mục `Downloads/` cũng bị loại khỏi Git.
