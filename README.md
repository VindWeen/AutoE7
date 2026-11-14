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

## Tải và cài đặt

Chọn một bản tại [**Release mới nhất**](https://github.com/VindWeen/AutoE7/releases/latest). Cả hai đều dùng cho **Windows 10/11 x64**, không cần cài Python.

| Bản | Cách dùng | Cập nhật |
| --- | --- | --- |
| **Portable ZIP** | Giải nén toàn bộ, mở `AutoE7.exe` | Tải ZIP mới và giải nén vào thư mục mới |
| **Setup EXE** | Chạy bộ cài, mở từ Start Menu hoặc shortcut Desktop | Bấm **Cập nhật** trong app |

Dừng bản cũ trước khi nâng cấp. Bản cài mặc định ở `%LOCALAPPDATA%\Programs\AutoE7` và có thể gỡ trong Settings → Apps của Windows.

Bản cài tự tải Setup, kiểm tra SHA-256, lưu cấu hình, đóng app và cài vào đúng thư mục hiện tại rồi tự mở lại. Sau khi mở thành công, app dọn Setup trong cache của phiên bản hiện tại và các bản cũ. Mất mạng hoặc tải lỗi vẫn dùng bản đang cài.

### Chạy từ mã nguồn

Yêu cầu **Python 3.11+**, Tkinter và Python Launcher (`py`). Clone repo rồi mở **`run.bat`** để cài thư viện và chạy, hoặc dùng:

```powershell
py -m pip install -r requirements.txt
py app.py
```

## Sử dụng

1. Mở game, chuẩn bị đội hình và màn bắt đầu của hoạt động muốn chạy.
2. Chọn cửa sổ game, hoạt động và giới hạn trong AutoE7.
3. Thử **Chỉ nhận diện** trước, sau đó tắt tùy chọn này để cho phép click.
4. Bấm **Bắt đầu**. Dùng **Dừng** hoặc **F8** để kết thúc.

Khi bật kiểm tra tự động, mỗi lần mở tool sẽ kiểm tra cập nhật một lần trong nền và hiển thị kết quả cạnh tiêu đề **AutoE7**. Bấm thông báo bản mới để xem chi tiết: bản cài có nút **Cập nhật**, portable mở trang tải ZIP. Mất mạng vẫn dùng bình thường. Mở **Cài đặt** ở góc phải để đổi ngôn ngữ, bật/tắt kiểm tra tự động hoặc kiểm tra thủ công.

Cấu hình từng mode được tự lưu tại `%LOCALAPPDATA%\AutoE7\settings.json` và khôi phục khi chuyển mode hoặc mở lại tool. Tool nhớ mode gần nhất và chờ bạn bấm **Bắt đầu**. Cấu hình được giữ khi nâng cấp hoặc gỡ bản cài.

Episode hỗ trợ sảnh đang ẩn nút, sảnh có menu, Ready, chọn đội, trận đang chạy và các màn kết quả đã có mẫu. Khi bắt đầu lại, số vòng tính cho phiên mới; lượt đang dở được tính khi hoàn tất và trở về Ready. Màn chưa nhận diện được sẽ chờ, không click dò.

Secret Shop, Rookie Arena và Abyss cũng có thể bắt đầu từ sảnh hoặc tiếp tục ở màn đã có mẫu nhận diện. Abyss tự chọn Normal, kéo danh sách Battle sang phải và vào nhánh Abyss thường. Chuẩn bị sẵn đội hình và thiết lập chiến đấu cần dùng. Mỗi lần Bắt đầu dùng giới hạn/ngân sách mới; popup mua hoặc Refresh có sẵn sẽ được đóng rồi kiểm tra lại, không suy đoán chi tiêu trước đó.

## Lưu ý

- Các ảnh mẫu hiện dùng giao diện game tiếng Anh. Thay đổi giao diện hoặc hiệu ứng có thể ảnh hưởng nhận diện.
- Click nền và chụp cửa sổ bị che còn thử nghiệm; không thu nhỏ game trong khi chạy.
- Hunt chưa được hỗ trợ. Nên thử một vòng trước khi chạy dài.

[Hướng dẫn cài đặt](INSTALL-GUIDE.txt) · [Hướng dẫn portable](PORTABLE-GUIDE.txt) · [Kiểm thử](tests/README.md) · [Quy trình phát hành](RELEASING.md) · [Báo lỗi](https://github.com/VindWeen/AutoE7/issues)
