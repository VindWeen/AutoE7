# AutoE7

[Tiếng Việt](README.md) | [English](README.en.md)

Công cụ tự động hóa Epic Seven trên Windows bằng nhận diện hình ảnh, với giao diện Tiếng Việt và English.

## Tính năng

- **Episode** — lặp lại map đang chọn, xử lý Skip và các màn kết quả.
- **Abyss** — chạy theo số tầng, chuyển tầng và sử dụng Guardian.
- **Rookie Arena** — chọn đối thủ, theo dõi thắng/thua và quản lý lượt đánh.
- **Secret Shop** — làm mới, mua vật phẩm đã chọn theo ngân sách Skystone.
- Chế độ chỉ nhận diện, click không chiếm chuột và chụp cửa sổ khi bị che.
- Kiểm tra phiên bản mới từ GitHub Releases; **F8** để dừng tác vụ.

## Bắt đầu

### Chạy từ mã nguồn

Yêu cầu **Windows 10/11**, **Python 3.11+**, Tkinter và Python Launcher (`py`).

Tải hoặc clone repo, sau đó mở **`run.bat`**. Script sẽ cài các thư viện cần thiết và khởi động ứng dụng.

Hoặc chạy trong terminal tại thư mục project:

```powershell
py -m pip install -r requirements.txt
py app.py
```

### Bản portable

Tải ZIP tại [GitHub Releases](https://github.com/VindWeen/AutoE7/releases), giải nén toàn bộ rồi mở **`AutoE7.exe`**. Bản portable không cần cài Python.

## Sử dụng

1. Mở game, chuẩn bị đội hình và màn bắt đầu của hoạt động muốn chạy.
2. Chọn cửa sổ game, hoạt động và giới hạn trong AutoE7.
3. Thử **Chỉ nhận diện** trước, sau đó tắt tùy chọn này để cho phép click.
4. Bấm **Bắt đầu**. Dùng **Dừng** hoặc **F8** để kết thúc.

Mở **Cài đặt** ở góc phải để đổi ngôn ngữ hoặc kiểm tra cập nhật. Khi có bản mới, tool mở trang tải theo lựa chọn của bạn.

Cấu hình từng mode được tự lưu tại `%LOCALAPPDATA%\AutoE7\settings.json` và khôi phục khi chuyển mode hoặc mở lại tool. Tool nhớ mode gần nhất và chờ bạn bấm **Bắt đầu**.

## Lưu ý

- Các ảnh mẫu hiện dùng giao diện game tiếng Anh. Thay đổi giao diện hoặc hiệu ứng có thể ảnh hưởng nhận diện.
- Click nền và chụp cửa sổ bị che còn thử nghiệm; không thu nhỏ game trong khi chạy.
- Hunt chưa được hỗ trợ. Nên thử một vòng trước khi chạy dài.

[Hướng dẫn portable](PORTABLE-GUIDE.txt) · [Kiểm thử](tests/README.md) · [Quy trình phát hành](RELEASING.md) · [Báo lỗi](https://github.com/VindWeen/AutoE7/issues)
