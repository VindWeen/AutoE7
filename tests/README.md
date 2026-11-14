# Kiểm thử / Tests

Thư mục này chứa các file kiểm thử `test_*.py` và ảnh mẫu trong `fixtures/`.
Ứng dụng không nạp thư mục này khi chạy qua `run.bat` hoặc bản portable.

Chạy toàn bộ kiểm thử từ thư mục gốc của project trên Windows:

```powershell
py -m unittest discover -s tests -t . -v
```

Chạy riêng một nhóm, ví dụ kiểm tra cập nhật:

```powershell
py -m unittest tests.test_updates -v
```

Cài thư viện trong `requirements.txt` trước khi chạy. Các bài kiểm tra giao diện
cần Tkinter và phiên desktop Windows; các thao tác game/mạng trong kiểm thử được
mô phỏng. Giữ nguyên `fixtures/` để các bài nhận diện ảnh có dữ liệu đầu vào.

English: Run the commands above from the project root after installing the
dependencies. Tests live here alongside screenshot fixtures and are separate
from normal app startup. UI tests require Tkinter and a Windows desktop session.
