# AutoE7

[Tiếng Việt](README.md) | [English](README.en.md)

Công cụ tự động hóa Epic Seven trên Windows bằng nhận diện hình ảnh, với giao diện Tiếng Việt và English.

## Tính năng

- **Episode** — vào từ sảnh hoặc nhận diện màn đang chạy để tiếp tục; lặp lại map đang chọn, xử lý Skip và kết quả.
- **Abyss** — vào từ sảnh qua Battle, chọn Abyss thường; chuyển tầng và sử dụng Guardian.
- **Rookie Arena** — vào từ sảnh qua Arena; chọn đối thủ, theo dõi thắng/thua và quản lý lượt đánh.
- **Secret Shop** — mở từ sảnh, làm mới và mua vật phẩm đã chọn theo ngân sách Skystone.
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

Mỗi lần mở, tool kiểm tra cập nhật một lần ở chế độ nền và hiển thị kết quả cạnh tiêu đề **AutoE7**. Có bản mới thì bấm thông báo để xem và mở trang tải; mất mạng vẫn dùng bình thường. Mở **Cài đặt** ở góc phải để đổi ngôn ngữ, bật/tắt kiểm tra tự động hoặc kiểm tra thủ công.

Cấu hình từng mode được tự lưu tại `%LOCALAPPDATA%\AutoE7\settings.json` và khôi phục khi chuyển mode hoặc mở lại tool. Tool nhớ mode gần nhất và chờ bạn bấm **Bắt đầu**.

Episode hỗ trợ sảnh đang ẩn nút, sảnh có menu, Ready, chọn đội, trận đang chạy và các màn kết quả đã có mẫu. Khi bắt đầu lại, số vòng tính cho phiên mới; lượt đang dở được tính khi hoàn tất và trở về Ready. Màn chưa nhận diện được sẽ chờ, không click dò.

Secret Shop, Rookie Arena và Abyss cũng có thể bắt đầu từ sảnh hoặc tiếp tục ở màn đã có mẫu nhận diện. Abyss tự chọn Normal, kéo danh sách Battle sang phải và vào nhánh Abyss thường. Chuẩn bị sẵn đội hình và thiết lập chiến đấu cần dùng. Mỗi lần Bắt đầu dùng giới hạn/ngân sách mới; popup mua hoặc Refresh có sẵn sẽ được đóng rồi kiểm tra lại, không suy đoán chi tiêu trước đó.

## Lưu ý

- Các ảnh mẫu hiện dùng giao diện game tiếng Anh. Thay đổi giao diện hoặc hiệu ứng có thể ảnh hưởng nhận diện.
- Click nền và chụp cửa sổ bị che còn thử nghiệm; không thu nhỏ game trong khi chạy.
- Hunt chưa được hỗ trợ. Nên thử một vòng trước khi chạy dài.

[Hướng dẫn portable](PORTABLE-GUIDE.txt) · [Kiểm thử](tests/README.md) · [Quy trình phát hành](RELEASING.md) · [Báo lỗi](https://github.com/VindWeen/AutoE7/issues)
