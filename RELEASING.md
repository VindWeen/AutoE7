# Chuẩn bị GitHub và phát hành AutoE7

Các bước dưới đây là hướng dẫn, không phải lệnh tự động. Chỉ tạo repo, commit,
push, build, tạo ZIP hoặc đăng release khi người dùng yêu cầu thao tác đó.
Không có workflow tự build/phát hành khi sửa mã nguồn hoặc push.

## Lần đầu đưa mã nguồn lên

1. Xác nhận tài khoản/tổ chức, tên repo và quyền công khai. Kiểm tra đăng nhập GitHub.
2. Rà `.gitignore`, danh sách file định đưa lên, bí mật và thông tin tài khoản trong ảnh fixture.
   Không đưa `build/`, `dist/`, `release/`, cache, log, `diagnostics/`, thư viện cục bộ
   hoặc `research_epic7/` lên. Giữ các tài nguyên mà code và kiểm thử cần.
3. Tạo repo theo yêu cầu. Chỉ khởi tạo Git/commit/push khi đã được yêu cầu;
   xem lại danh sách staged thực tế trước commit. Không coi `.gitignore` là bảo đảm
   cho file đã được theo dõi từ trước.
4. Đặt `repository` trong `release_config.json` thành địa chỉ thật dạng `owner/name`.
   Repo phải công khai để kiểm tra cập nhật không cần token.

## Khi người dùng yêu cầu phát hành

1. Chọn phiên bản mới duy nhất dạng `YYYY.MM.DD-rN`, ví dụ `2026.11.14-r1`.
   Tăng revision khi phát hành nhiều lần trong ngày. Cập nhật `version` trong
   `release_config.json`; đây là nguồn phiên bản cho giao diện và bộ kiểm tra.
2. Chạy `py -m unittest discover -s tests -t . -v` từ thư mục gốc và kiểm tra trực tiếp qua `run.bat`, cả hai ngôn ngữ,
   các chế độ game có thay đổi và trạng thái mất mạng. Kiểm thử backend dùng mock,
   không yêu cầu repo hay release thật.
3. Sau khi có yêu cầu build, dùng cấu hình `AutoE7.spec` để tạo bản Windows portable.
   Cấu hình giữ `assets/`, `scenarios.json`, `release_config.json` và tài liệu cạnh EXE.
   Kiểm tra cấu trúc thực tế, không chỉ kiểm tra build thành công.
4. Kiểm tra bản portable trên Windows: mở EXE, chạy self-test, Settings Việt/Anh,
   mở trang release và hành vi ngoại tuyến. Không phát hành ZIP chưa kiểm thử.
5. Sau khi được yêu cầu đóng gói, nén toàn bộ thư mục portable thành
   `AutoE7-Windows-x64-YYYY.MM.DD-rN.zip`, bao gồm `_internal` và tài nguyên.
   Không commit ZIP/EXE vào repo mã nguồn.
6. Sau khi được yêu cầu commit/push, đưa mã nguồn và tag tương ứng lên GitHub.
   Tag phải đúng phiên bản, có thể thêm `v`, ví dụ `v2026.11.14-r1`.
7. Sau khi được yêu cầu đăng release, tạo GitHub Release theo tag đó, ghi các thay đổi,
   yêu cầu Windows và hướng dẫn nâng cấp; đính kèm ZIP portable vào **Assets**.
   Đánh dấu release ổn định là **Latest**. Draft/prerelease không được thông báo
   cho người dùng bản ổn định.
8. Kiểm tra liên kết tải công khai và kiểm tra cập nhật từ một bản cũ đã tích hợp
   tính năng này. GitHub tự tạo mục Releases và Assets khi có release.

## Kiểm tra trước khi báo hoàn tất

- Không nhúng token, đường dẫn cá nhân hoặc thông tin riêng trong cấu hình phát hành.
- Version trong tool và tag nhất quán; repo chính xác, công khai, release ổn định.
- Trang release có ZIP chạy được, không chỉ các archive Source code tự sinh.
- Bản cũ chưa tích hợp bộ kiểm tra không thể tự có tính năng này: cần tải thủ công lần đầu.
- Không có chức năng tự cập nhật tại chỗ; người dùng tải và giải nén vào thư mục mới.

Tham khảo API chính thức: https://docs.github.com/en/rest/releases/releases#get-the-latest-release

## Phát hành portable và bộ cài

- Khi người dùng yêu cầu cả hai, build payload với `AutoE7.spec`, kiểm tra EXE rồi tạo ZIP portable và chạy `installer/build.ps1 -SourceDir <payload>` để tạo Setup.
- Bộ cài phải tên `AutoE7-Setup-YYYY.MM.DD-rN.exe`, cùng phiên bản với tag và `release_config.json`. Xem [installer/README.md](installer/README.md).
- Thử cài mới, nâng cấp, giữ setting, mutex khi app đang mở, tự mở lại và gỡ cài đặt. Không tự cài đè bản người dùng đang dùng để kiểm thử.
- Đính kèm cả ZIP, Setup và các checksum SHA-256 vào cùng release. Bộ cập nhật chỉ tải Setup có đúng URL, tên, kích thước và digest `sha256:` trong GitHub asset metadata.
- Xác minh từ bản cũ: portable mở trang tải; bản cài đặt nhận được metadata Setup. Chỉ đánh dấu Latest sau khi các asset tải lên đầy đủ.
