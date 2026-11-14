# Quy tắc làm việc với AutoE7

## Chỉ sửa mã nguồn theo mặc định

- Áp dụng cho mọi phiên làm việc, kể cả phiên mới.
- Khi sửa lỗi hoặc thêm tính năng, mặc định chỉ chỉnh sửa mã nguồn và các tài liệu, tài nguyên hoặc kiểm thử cần thiết.
- Có thể chạy kiểm thử và kiểm tra mã nguồn để xác minh thay đổi.
- Người dùng kiểm tra trực tiếp bằng `run.bat`; thay đổi mã nguồn không cần build lại bản portable.
- Không tự build, đóng gói hoặc cập nhật EXE; không tự tạo hay cập nhật ZIP phát hành.
- Không tự sửa các bản phân phối trong `dist/` hoặc `release/` để đưa thay đổi vào bản chạy đã đóng gói.
- Khi được yêu cầu build, lưu log trong `build/<phiên-bản>/build.log` (ví dụ `build/latest-2026-11-14-r2/build.log`); không tạo build log rải ở thư mục gốc project.
- Chỉ build EXE hoặc xuất ZIP khi người dùng yêu cầu rõ ràng. Yêu cầu sửa lỗi hoặc thêm tính năng không bao hàm yêu cầu build hay đóng gói.
- Không tự tạo commit, amend commit, push, tạo repo GitHub hoặc đăng GitHub Release khi người dùng chưa yêu cầu rõ ràng thao tác tương ứng. Trao đổi ý tưởng hoặc yêu cầu sửa mã nguồn không phải là yêu cầu thực hiện các thao tác này.
- Sau khi sửa xong, báo ngắn gọn nội dung thay đổi và kết quả kiểm tra; không cần hỏi người dùng có muốn build, xuất ZIP, commit hay push hay không.

## Chuẩn bị đưa lên GitHub

- Trước lần commit/push đầu tiên, kiểm tra `.gitignore` và danh sách file thực tế sẽ đưa lên; không chỉ dựa vào `.gitignore` vì file đã được theo dõi vẫn có thể được commit.
- Chỉ đưa mã nguồn, tài nguyên cần cho ứng dụng, cấu hình mẫu, tài liệu và kiểm thử cần thiết lên repo.
- Không đưa bản build/portable/ZIP, thư viện cài cục bộ, cache, log, ảnh chẩn đoán, kết quả chạy thử, nghiên cứu cá nhân, bản sao lưu hoặc thông tin bí mật lên repo.
- Giữ tài nguyên trong `assets/`, `scenarios.json` và fixture cần thiết trong `tests/`; không loại toàn bộ ảnh hoặc JSON vì ứng dụng và kiểm thử sử dụng chúng.
- File phát hành chỉ đính kèm GitHub Releases khi người dùng yêu cầu phát hành; không lưu binary phát hành trong lịch sử mã nguồn.
