# AutoE7

Mã nguồn: [VindWeen/AutoE7](https://github.com/VindWeen/AutoE7).

## Bản gửi cho người khác

Khi repo công khai đã có bản phát hành, vào mục **Releases**, chọn bản mới nhất và tải ZIP portable trong **Assets** (không phải `Source code`). Giải nén toàn bộ vào thư mục mới rồi mở `AutoE7.exe`; không cần chạy `run.bat` hay cài Python. Giữ nguyên `_internal`, `assets`, `scenarios.json` và `release_config.json` đi kèm. Xem `PORTABLE-GUIDE.txt` để sử dụng.

Bản portable sẽ được đăng tại [GitHub Releases](https://github.com/VindWeen/AutoE7/releases) khi có bản phát hành. Hiện repo cung cấp mã nguồn; chưa có release portable mới. Quy trình chuẩn bị và phát hành nằm trong [RELEASING.md](RELEASING.md).

## Cài đặt và cập nhật / Settings and updates

- Nút **Settings / Cài đặt** ở góc trên bên phải cho phép chuyển **Tiếng Việt / English** ngay trong phiên hiện tại. Lựa chọn và tùy chọn kiểm tra cập nhật được lưu theo tài khoản Windows tại `%LOCALAPPDATA%/AutoE7/settings.json`, dùng tiếp khi đổi thư mục portable.
- Khi bật kiểm tra lúc mở, tool đọc bản release công khai ổn định mới nhất từ GitHub trong luồng nền. Khi có bản mới, thông báo hiển thị phiên bản và ghi chú phát hành; **Mở trang tải** mở trang GitHub Releases trong trình duyệt. Nếu tool đang chạy tác vụ, chỉ hiện nút thông báo để tránh làm gián đoạn.
- Có thể kiểm tra thủ công trong Settings. Mất mạng, GitHub giới hạn truy cập hoặc chưa có release không ngăn tool chạy. Tool không tự tải, cài đặt hay ghi đè bản đang dùng.
- Tính năng này bắt đầu từ bản mã nguồn `2026.11.14-r1`. Các EXE cũ chưa có chức năng kiểm tra cập nhật: người dùng cần tải thủ công một bản mới có chức năng này trước.
- `release_config.json` đã trỏ đến repo công khai `VindWeen/AutoE7`. Nếu chuyển repo, nhà phát hành cập nhật giá trị `repository` dạng `owner/repository`. Để trống thì không gửi yêu cầu tự động; không nhúng token GitHub vào tool.

English: Open **Settings** to select Vietnamese or English and enable startup update checks. The check runs in the background. An update notice opens the official GitHub release page only when you choose **Open download page**. Download the portable ZIP under **Assets**, extract it to a new folder, stop the old instance and launch the new `AutoE7.exe`. Existing older executables without this feature require one manual download first.

Ứng dụng Windows nhận diện ảnh và click theo kịch bản. Có **Đi Map**, dùng 13 ảnh mẫu nhỏ được cắt từ ảnh đã cung cấp. Đi Hunt mới có mục chờ cấu hình, chưa chạy được vì chưa có ảnh/luồng Hunt.

## Chạy

1. Cài Python 3.11 trở lên với Python Launcher (`py`) và Tkinter.
2. Mở `run.bat` để cài thư viện và mở ứng dụng; hoặc chạy `py -m pip install -r requirements.txt` rồi `py app.py`.
3. Đặt game ở màn hình chọn map có nút Ready. Chọn đúng cửa sổ trong tool.
4. Nếu cửa sổ giả lập có thanh công cụ/viền, đặt vùng game bằng bốn tỷ lệ trái, trên, phải, dưới. Ví dụ `0,0.04,0.97,1`. Vùng phải chỉ chứa nội dung game, tỷ lệ gần 16:9 như ảnh mẫu.
5. Để **Chỉ nhận diện** bật, bấm Bắt đầu, đưa game ra trước và thao tác thủ công để xem log nhận diện. Chế độ này chỉ kiểm tra trạng thái đầu Ready vì không tự chuyển bước.
6. Bấm Dừng, tắt Chỉ nhận diện, đặt số vòng và Bắt đầu. Ở chế độ click thường, game phải ở foreground. F8 dừng toàn bộ tác vụ. Muốn dùng ứng dụng khác, xem các chế độ chạy nền bên dưới.

## Luồng Đi Map

### Không chiếm chuột (thử nghiệm)

Confirm MVP, Confirm bỏ truyện, Cancel Friend và các popup thưởng cũng thử lại tối đa 3 lần sau mỗi 3 giây khi nút cũ vẫn được nhận diện. Confirm MVP phải thấy màn tiếp theo mới được xác nhận thành công; vẫn quét MVP trong trạng thái chờ thưởng để phục hồi click bị bỏ qua. Popup Friend/thưởng được ưu tiên trước MVP, tránh bấm Confirm phía sau popup.

Ready, Select Team, Start và Start Quest cũng thử lại tối đa 3 lần sau mỗi khoảng chờ 3 giây nếu nút cũ vẫn khớp ảnh và chưa thấy bước tiếp theo. Áp dụng cho cả click nền và click thường. Ready/Select Team phải thấy màn tiếp theo mới xác nhận chuyển bước. Start/Start Quest có thể vào thẳng chiến đấu không có nút, nên chấp nhận khi không còn nút Start trong hai ảnh hợp lệ liên tiếp; ảnh loading/đen không được tính. Không cộng lại số vòng khi thử lại Ready.

Màn Clear chỉ được xác nhận qua bước khi nhận diện được màn kế tiếp (MVP/Friend), thay vì suy ra thành công khi chữ Clear mất khớp trong một khung hình hiệu ứng. Nếu vẫn thấy Clear, thử lại mũi tên sau 3 giây, tối đa 3 lần. Tool tiếp tục quét Clear ngay cả trong trạng thái chờ kết quả để khôi phục trường hợp click đầu bị bỏ qua. Đã kiểm thử mô phỏng mất nhận diện do hiệu ứng, thử lại và chuyển sang MVP; chưa thử bản sửa trực tiếp trong game.

Riêng Skip: nếu nút vẫn được nhận diện và chưa thấy Confirm, thử lại sau 3 giây, tối đa 3 lần ngoài lần gửi đầu. Mỗi lần thử lại dùng ảnh hiện tại và tọa độ trong cửa sổ, không dùng chuột desktop. Confirm được ưu tiên để tránh tiếp tục bấm Skip phía sau hộp thoại. Sau lần thử cuối, vẫn dừng nếu nút không biến mất trong 12 giây. Đã kiểm thử mô phỏng khoảng chờ, giới hạn thử lại và ưu tiên Confirm; chưa xác nhận trực tiếp trong game.

Skip/Skip Intro so khớp nét chữ để giảm ảnh hưởng của nền cốt truyện, với vùng tìm rộng hơn. Hộp Confirm bỏ truyện được ưu tiên ngay cả khi chữ Skip vẫn hiện phía sau hộp thoại. Dòng trạng thái hiển thị mẫu gần khớp nhất và điểm số khi đang chờ, giúp phân biệt chưa khớp ảnh với ứng dụng ngừng phản hồi. Đã kiểm tra trên năm cảnh Skip (gồm Rose và Coldhearted Knight), bốn màn đối chứng và ảnh trống/nhiễu; chưa xác nhận trên mọi cảnh trong game.

Popup Friend được xử lý cả trước và sau Confirm MVP. Khi bấm Cancel, tool giữ nguyên trạng thái đang chạy để tiếp tục nhận diện MVP hoặc màn thưởng/Ready, tùy thời điểm popup xuất hiện. Quy tắc dùng `next: "$same"` để biểu thị giữ nguyên trạng thái.

Click nền gửi vị trí chuột nội bộ (`WM_MOUSEMOVE`) trước nhấn nút và thả sau khoảng 100 ms để game có thời gian xử lý. Không di chuyển con trỏ desktop. Log ghi rõ HWND và tọa độ client được gửi. Sau click, tool chờ nút cũ biến mất; nếu nút vẫn còn sau 12 giây thì dừng báo game có thể không nhận click nền, thay vì tiếp tục như thể click đã thành công. Việc nút biến mất chỉ là tín hiệu chuyển cảnh, không khẳng định thao tác đã được game xác nhận. Đã kiểm tra thứ tự thông điệp và tọa độ bằng ba kiểm thử mô phỏng, chưa xác nhận bản sửa trong Epic Seven thực tế.

Bật tùy chọn **Không chiếm chuột** trước khi Bắt đầu và bỏ chọn **Chỉ nhận diện** nếu muốn click. Tool gửi `WM_LBUTTONDOWN/UP` trực tiếp tới cửa sổ, không di chuyển con trỏ và không yêu cầu game ở foreground. Với chế độ chụp thường, game vẫn phải hiển thị và không bị che. Chế độ này chưa được kiểm thử trong Epic Seven; game có thể bỏ qua thông điệp click dù Windows báo gửi thành công. Nếu log báo click nhưng game không phản hồi, dừng rồi tắt tùy chọn để dùng click thường.

### Nhận diện khi game bị che (thử nghiệm)

Bật **Chụp trực tiếp cửa sổ khi bị che** để lấy nội dung client qua Windows Graphics Capture thay vì chụp desktop (Windows 10/11). Khi chạy click phải bật cả **Không chiếm chuột**. Có thể thử trước với **Chỉ nhận diện**, ở màn Ready, rồi che game bằng trình duyệt: nếu vẫn nhận diện Ready thì đã lấy được ảnh, nhưng cần thử thêm chuyển cảnh để xác nhận ảnh tiếp tục cập nhật. Không thu nhỏ game. Đã kiểm tra lấy được ảnh từ cửa sổ Epic Seven thực tế; chưa kiểm thử toàn bộ luồng khi che game và click nền. Ảnh có thể đen, thiếu nội dung hoặc ngừng cập nhật tùy cách game render. Tool tạm chờ khi ảnh đen/trống do chuyển cảnh/loading, xóa ảnh cũ ngay và không click cho tới khi có ảnh hợp lệ trở lại. Nếu đen/trống liên tục quá 45 giây thì dừng. Với ảnh bình thường, tool dừng nếu không có ảnh mới quá 5 giây; không tự chuyển sang ảnh desktop. Việc chụp chạy trong luồng riêng để giao diện và F8 vẫn phản hồi. Khi dừng nhận ảnh, tool tạm ngừng nhận diện sau 3 giây để tránh dùng ảnh cũ. Game có thể không nhận click nền dù lấy được ảnh.

Ready → Select Team (nếu có) → Start hoặc Start Quest → chờ trận đấu. Tool cũng nhận diện Start/Start Quest ngay sau Ready khi game bỏ qua màn Select Team. Skip và Confirm bỏ truyện có thể xuất hiện nhiều lần trong trận. Clear → mũi tên phải → Cancel popup Friend (nếu có) → Confirm MVP → đóng Story Clear/Received Reward nếu có → đợi Ready để tính hoàn thành một vòng. Dừng trước khi click Ready nếu đã đủ số vòng.

Tool dùng đội hình và auto battle đã được chọn sẵn trong game. Không tự bật auto battle, chọn map kế tiếp, mua năng lượng hay xử lý thua trận. Số vòng lớn hơn 1 sẽ click Ready tại map game đang chọn sau vòng trước. Chỉ bắt đầu chạy từ màn hình Ready, không giữa trận.

## Điều chỉnh / thêm kịch bản

`scenarios.json` chứa danh sách quy tắc theo thứ tự ưu tiên. Mỗi quy tắc có tên `id` duy nhất, ảnh mẫu đã cắt trong `assets`, vùng tìm kiếm tham chiếu `rect`, điểm click `click`, trạng thái cho phép `phases`, trạng thái kế tiếp `next` và ngưỡng `threshold` tùy chọn. Tọa độ quy về 1280×720. Khung hình game được chuẩn hóa về kích thước này trước khi so khớp OpenCV. Ảnh mẫu giữ nguyên kích thước phần cắt trong hệ tọa độ 1280×720; không phóng ảnh mẫu thành toàn màn hình. Với Clear và popup thưởng, ảnh mẫu là chữ nhận diện trạng thái, còn điểm click là mũi tên tương ứng để tránh nhầm các mũi tên giống nhau. Cần thử với giao diện/ngôn ngữ game thực tế; đổi tỷ lệ khung hình, hiệu ứng hoặc giao diện có thể khiến ảnh không khớp.

Chỉ click sau hai lần nhận diện liên tiếp, chờ 1.5 giây giữa các lần click. Dừng nếu 10 phút không có thao tác phù hợp. Ảnh chụp màn hình được xử lý trong bộ nhớ; không đọc bộ nhớ game hay can thiệp tiến trình.

## Trạng thái kiểm thử

Đã kiểm tra cú pháp/import bằng Python 3.12 và lấy ảnh cửa sổ Epic Seven qua Windows Graphics Capture. PrintWindow không lấy được ảnh trong lần thử, nên dùng Windows Graphics Capture. Chưa kiểm thử tự click toàn bộ một vòng hoặc xác nhận ảnh vẫn cập nhật khi cửa sổ bị che. Cần thử chế độ nhận diện trước, sau đó thử một vòng. Có thể chạy `py check_capture.py` khi game đang mở để kiểm tra chụp ảnh (không click).





Skip dùng duy nhất mẫu chữ nhỏ skip_text.png, thử năm tỷ lệ và cho phép nét lệch 1 pixel. Điểm F1 kiểm tra cả độ phủ nét mẫu lẫn tỷ lệ nét phù hợp để hạn chế nhận nhầm nền dày nét. Ngưỡng riêng của cách tính này là 0.93 (không so trực tiếp với điểm correlation ở bản cũ). Kiểm thử test_skip_detection.py dùng các vùng góc màn hình từ năm cảnh Skip và bốn màn đối chứng (Confirm, đội hình, Clear, MVP), cùng ảnh trống/nhiễu. Không thay ngưỡng các nút khác.



## Abyss (Tháp)

Chọn **Abyss (Tháp)**, nhập **Số tầng**, hoặc tích **chạy tới khi dừng**; F8 để dừng. Chuẩn bị sẵn đội và bật auto battle trong game. Tool bấm Start ở màn Ready, theo dõi trận, bấm Next Floor rồi chỉ đếm tầng khi nhận diện lại Ready. Đủ tầng thì dừng tại Ready trước khi bấm Start tiếp. Trong trận, tool dùng Guardian lại mỗi khi nhận diện biểu tượng khả dụng ổn định sau lần dùng trước, không giới hạn một lần mỗi trận. Nhận diện Guardian hiện phụ thuộc ảnh mẫu trong `assets/abyss_available.png`, `assets/abyss_available_alternate.png` và `assets/abyss_spent.png`. Hai ảnh Guardian bổ sung đều là trạng thái khả dụng; chưa có ảnh trạng thái mờ của Guardian này.

Start/Next Floor cần hai khung nhận diện liên tiếp. Sau click, chỉ xác nhận khi thấy màn kế tiếp; nếu vẫn thấy đúng nút cũ thì thử lại mỗi 4 giây, tối đa 5 lần. Sau 45 giây chưa xác nhận sẽ dừng; không click mò khi loading. Giám hộ sáng: bấm avatar thứ 5 từ phải, chờ ít nhất 0,8 giây rồi bấm phía địch. Nếu chưa thành công, thử lại sau 3 giây khi avatar vẫn sáng. Chỉ ghi nhận dùng thành công khi thấy avatar xám 3 khung liên tiếp và đã chờ ít nhất 2 giây; mỗi trận ghi nhận một lần.

Mẫu giám hộ dùng hình trong ảnh người dùng cung cấp, chưa hỗ trợ mọi loại giám hộ. Đã kiểm tra nhận diện với 7 ảnh và kiểm thử logic thử lại/đếm tầng; chưa kiểm thử tự chạy toàn bộ tầng trong game thật. Thua trận, hết năng lượng hoặc màn lạ sẽ chờ rồi dừng theo timeout; không tự mua tài nguyên. Timeout không tiến triển chung là 10 phút.

## Reroll Secret Shop

Mở Secret Shop tiếng Anh, chọn **Reroll Secret Shop** trong tool. Tick Friendship Points (18,000 Gold), Covenant Bookmarks (184,000 Gold), Mystic Medals (280,000 Gold) tùy nhu cầu; mặc định chọn Covenant và Mystic. Ngân sách Skystone phải là số nguyên dương chia hết cho 3; để trống để chạy tới khi dừng/F8. Ngân sách chỉ tính lần refresh của lượt chạy này, không tính Gold mua hàng.

Tool cuộn lên đầu và quét shop đang mở trước khi refresh. Nó mua lần lượt mọi loại đã chọn xuất hiện trên cùng shop, xác minh tên item trong popup Buy và chỉ tính mua thành công khi nhận lại dòng đó ở trạng thái 0/1. Sau đó cuộn tới đáy, xác nhận thanh cuộn đã ở đáy và quét tiếp dòng 5–6. Dòng chồng lặp đã mua sẽ bị bỏ qua nhờ 0/1. Không refresh nếu chưa xác nhận quét xong đáy. Sau lần refresh cuối của ngân sách, tool vẫn quét và mua xong shop mới rồi mới dừng.

Click Buy/Refresh chỉ thử lại khi nút hoặc đúng popup nguồn vẫn được nhận diện, mỗi 3 giây tối đa 3 lần. Cuộn có xác nhận đầu/đáy, tối đa 5 lần. Sau khi gửi Confirm Refresh, tool tính 3 Skystone khi popup đóng và shop hiện lại ổn định qua hai lần quan sát; không yêu cầu danh sách hàng thay đổi. Nếu chưa ở đầu danh sách, tool cuộn lên rồi quét hàng. Chưa nhận diện lại shop thì không tính và không tự refresh thêm. Mỗi bước timeout 25 giây. Hết tiền, popup lạ hoặc sai item sẽ không tự xác nhận; tool dừng khi không thể tiến triển.

Chế độ Chỉ nhận diện không click hoặc cuộn; có thể tự cuộn game để xem kết quả. Chạy nền gửi WM_MOUSEWHEEL và click qua cửa sổ, vẫn tùy game có chấp nhận input hay không; không thu nhỏ game. Đã kiểm tra ảnh người dùng cung cấp và logic bằng test; chưa chạy mua hàng/tiêu Skystone trong game thật. Popup Covenant/Mystic dùng mẫu tên thu phóng từ dòng shop vì chưa có ảnh popup riêng; nếu không khớp tool sẽ dừng, không bấm Buy.

## Giao diện desktop

Giao diện tối với điểm nhấn vàng, chia cấu hình và nhật ký thành hai vùng. Thiết lập thay đổi theo Map/Abyss/Secret Shop; phần Vùng game nâng cao được thu gọn. Thanh Bắt đầu/Dừng luôn hiện, cấu hình có thể cuộn ở cửa sổ nhỏ. Các ô cấu hình được khóa trong lúc chạy và mở lại khi dừng; F8 vẫn dừng khẩn cấp. Danh sách cửa sổ ưu tiên Epic Seven và giữ lựa chọn hiện tại khi Làm mới.

Khắc phục nhận diện đầu/cuối Secret Shop khi thanh cuộn bị mờ/ẩn: ngoài mẫu thanh cuộn, tool dùng vị trí bốn nút số lượng để xác định bố cục. Với cách nhận diện bổ sung này, tool gửi cuộn trước khi xác nhận vị trí; trước khi quét đáy còn đối chiếu ảnh các dòng giữa để xác minh đã dịch chuyển đủ xuống phần cuối. Đã kiểm tra cuộn nền trên cửa sổ Epic Seven thực tế, không mua hoặc refresh trong lần kiểm tra.

## Rookie Arena

Mở sẵn danh sách Opponents của Rookie Arena tiếng Anh trước khi chạy. Chọn hoạt động **Rookie Arena**. Bot giữ nguyên đội hình đang chọn, bấm Challenge → Start, bật auto khi nhận diện auto chưa bật, rồi Confirm sau thắng/thua.

- **Cố định vị trí ưu tiên**: bắt đầu mỗi danh sách mới ở vị trí 1/2/3 đã chọn. Thua thì chọn ngẫu nhiên đối thủ chưa thua trong danh sách đó.
- **Tuần tự 1 → 2 → 3**: thua thì chuyển xuống đối thủ tiếp theo. Thắng hoặc danh sách refresh thì bắt đầu lại từ 1.
- Bỏ qua các ô đỏ có sẵn. Thua cả 3 thì dừng. Sau mỗi trận thắng, xóa lịch sử thua.
- Nhập **Số trận**, hoặc tích **Chạy tới khi dừng** để bỏ giới hạn số trận. Cả thắng và thua đều tính một trận; bot Confirm về danh sách trước khi dừng theo giới hạn.
- Mặc định hết lượt thì dừng. Tích **Tự mua lượt khi hết** để ưu tiên gói 100 tim/5 lượt, sau đó gói 30 SkyStone/5 lượt. Ngân sách SkyStone tính riêng mỗi lần bấm Bắt đầu; 0 chỉ cho phép mua bằng tim. Ngân sách không cần chia hết cho 30; phần dư dưới 30 không dùng.
- Chỉ bấm Buy khi nhận diện được loại tiền đang chọn và đủ tài nguyên. Không xác minh được số dư, mua thất bại hoặc chưa xác nhận tăng 5 lượt thì dừng; không gửi Buy lần nữa khi chưa biết kết quả.

Nhấn Dừng hoặc F8 để ngừng. Lần đầu dùng **Chỉ nhận diện**, sau đó thử giới hạn 1 trận. Nhận diện dựa trên ảnh mẫu đã cung cấp; chưa xác nhận tự chạy hoặc mua tài nguyên trong game thật. Không có ảnh thiếu tim thực tế nên cần kiểm tra trường hợp này khi gặp; bot không tự xác nhận popup lạ.

Rookie Arena r2: nhận diện danh sách bằng lời nhắc chọn đối thủ, không phụ thuộc tiêu đề Opponents vì tiêu đề đổi thành số trận thắng liên tiếp. Đã kiểm tra ảnh chuỗi thắng mới: đọc đúng 9 lượt, xác nhận trở về danh sách sau thắng và bắt đầu lại được. Số trận = 1 vẫn dừng sau một trận; tăng số trận hoặc tích Chạy tới khi dừng để tiếp tục.

Rookie Arena r3: bộ đọc số dùng so sánh glyph có nội suy để chịu được sai khác nhỏ khi đổi kích thước cửa sổ; bổ sung mẫu số 9 từ ảnh lỗi thực tế. Tiêu đề có mã phiên bản 2026.11.09-r3. Nhật ký ghi màn, số lượt, lựa chọn và trạng thái auto; trạng thái phân biệt chưa thấy màn và chưa đọc được số lượt. Nếu nhận diện bị kẹt sau 8 giây, lưu ảnh client đã chuẩn hóa tại diagnostics/rookie-arena-last.png (chỉ lưu cục bộ, ghi đè ảnh chẩn đoán trước). Chưa thể xác nhận đường chụp của máy người dùng chỉ từ ảnh chụp desktop; cần ảnh diagnostics nếu vẫn gặp lỗi.

Rookie Arena r4: sau Confirm Victory, tự xử lý màn thăng hạng bằng Confirm ở giữa dưới, rồi đóng Promotion Rewards bằng mũi tên Tap to close. Chỉ đếm một trận khi quay lại danh sách đối thủ; giới hạn số trận vẫn đóng hết các popup trước khi dừng. Các nút chỉ thử lại khi đúng màn nguồn còn được nhận diện, tối đa ba lần gửi trong 45 giây. Nhận diện thăng hạng không phụ thuộc tên rank. Đồng thời loại dấu cộng mua lượt nằm phía trên chữ số khỏi vùng OCR, kiểm tra danh sách sau lên rank đọc đúng 8 lượt.

Rookie Arena r5: sửa tách chữ số của bộ đếm lượt bằng cách giữ các nét rời nằm trong cùng vùng ngang của một chữ số, thay vì bỏ từng mảnh nhỏ. Đọc ở nhiều ngưỡng sáng và chỉ nhận kết quả khi các kết quả chắc chắn không mâu thuẫn. Mẫu chữ số bộ đếm tách riêng khỏi OCR tiền mua lượt. Ảnh lỗi 5/5 sau ba trận được giữ làm kiểm thử hồi quy. Chẩn đoán tự cập nhật cho mỗi lần kẹt nhận diện kéo dài 3 giây, kể cả sau nhiều trận; ảnh PNG kèm JSON trạng thái trong diagnostics/rookie-arena-last.*. Nhật ký bỏ các dòng màn=None thoáng qua khi đang hoạt ảnh kỹ năng.

Rookie Arena r6: sửa tình trạng không bật auto do nhận nhầm hiệu ứng màu xanh là avatar auto. Nhận diện auto dựa trên bố cục các avatar và dấu tick thay vì tỷ lệ màu xanh chung. Trạng thái auto phải được nhận ổn định qua hai lần quan sát; nhận thấy auto bật không đồng nghĩa đã gửi click. Nếu trước đó nhận nhầm bật nhưng sau đó thấy rõ ba skill thủ công, bot vẫn gửi một click bật auto. Mỗi trận chỉ gửi click auto tối đa một lần; nếu chưa xác nhận bật trong 30 giây thì dừng báo auto thay vì tự bấm lại làm tắt auto. Trạng thái desktop hiển thị cả auto quan sát được và đã gửi click hay chưa. Bắt đầu từ danh sách đối thủ; trận đang dở cần hoàn thành trước khi chạy lại bản mới.

Đi Map r7: sửa bỏ sót CLEAR khi nền map thay đổi bằng so nét chữ có dung sai vị trí. Kiểm tra hồi quy bằng ảnh lỗi thực tế và các màn khác; giữ xác nhận màn kế tiếp và giới hạn thử lại click. Chưa xác nhận chạy trực tiếp trong game.

Đi Map r8: nhận diện RANK UP bằng chữ thay vì số level, bấm mũi tên xuống rồi chờ màn tiếp theo. Giữ nguyên phase và số vòng khi đóng popup; thử lại có giới hạn khi popup còn hiện. Bổ sung ảnh hồi quy lên rank và CLEAR nền lâu đài.

2026.11.10-r1 — Rookie Arena: tự đóng Hero Friendship Level Increase bằng mũi tên Tap to close trước khi xử lý Victory. Nhận diện popup được ưu tiên hơn các nút kết quả phía sau và không phụ thuộc hero hoặc mức Friendship. Đóng popup giữ nguyên trận đang chạy và thao tác Confirm đang chờ; chỉ đếm trận sau khi thực sự trở về danh sách. Click đóng chỉ thử lại khi popup còn hiện, mỗi 4 giây tối đa 5 lần gửi, timeout 45 giây.

2026.11.10-r2 (chạy mã nguồn): Rookie Arena nhận diện ba skill có viền bạc/xanh như Landy bằng nét khung và cạnh trên phẳng, kèm nút A ở trạng thái tắt; vẫn phân biệt với bốn avatar auto, kể cả khi mũi tên A đang ở góc giống trạng thái tắt. Mỗi lần bấm Bắt đầu ở mọi hoạt động, tool khôi phục cửa sổ nếu đang thu nhỏ/phóng to và đưa vùng client game về đúng 1280×720 trước khi khởi tạo capture. Kích thước cửa sổ ngoài có thể lớn hơn vì có viền và thanh tiêu đề. Giữ vị trí/z-order của cửa sổ bình thường; nếu game từ chối kích thước thì báo lỗi và không bắt đầu click. Cấu hình vùng game nâng cao vẫn được áp dụng sau bước resize. Đóng tool đang mở rồi chạy lại run.bat để nạp bản sửa; không tạo EXE/ZIP cho lần cập nhật này.

2026.11.10-r3: sửa đọc lượt Rookie Arena khi nhóm tài nguyên trên thanh trên dịch sang trái. Tìm hậu tố /5 để định vị tử số, giữ bộ đọc nhiều ngưỡng và để số không rõ là unknown. Kiểm tra ảnh chẩn đoán 5/5 thực tế cùng các biến thể thu phóng/độ sáng; 46 kiểm thử Arena đạt. Chưa chạy click trong game thật.

2026.11.10-r4 (mã nguồn): Rookie Arena mở mua lượt theo vị trí bộ đếm được nhận diện, gồm cả các lần thử lại, thay vì bấm cố định x=550. Bổ sung mẫu chữ số Owned thực tế và nhận diện viền vàng nhạt của ô tiền đang chọn. Kiểm thử hồi quy từ ảnh 0/5 và popup có Friendship cooldown, xác nhận mua bằng Skystone một lần và chỉ tính 30 khi số lượt tăng. Không build EXE/ZIP cho lần sửa này.

2026.11.10-r5 (mã nguồn): không dùng thời gian từ đầu trận để kết luận lỗi auto khi HUD skill đang ẩn do đối thủ đi trước. Chỉ tính ngân sách chờ nhận diện manual tối đa 20 giây từ các lần quan sát HUD manual liên tục; vẫn cần hai quan sát manual để bấm, mỗi trận một click. Sau click giữ 30 giây xác nhận auto; giới hạn trận 30 phút và timeout mất nhận diện màn vẫn giữ. Kiểm thử tình huống đối thủ mở màn dài và skill chỉ hiện thoáng qua. Chưa build EXE/ZIP.

2026.11.10-r6 (mã nguồn): bổ sung mẫu chữ số Owned 3 và 5 từ popup lỗi 14351; trước đây điểm nhận diện 5 quá gần 6 nên tài nguyên bị trả về unknown. Giữ nguyên ngưỡng tin cậy và giới hạn ngân sách. Kiểm thử đọc đúng toàn bộ 14351 qua thu phóng/độ sáng, chọn mua Skystone khi Friendship cooldown, và không cho phép mua nếu số bị xóa. Chưa build EXE/ZIP.

2026.11.10-r7 (mã nguồn): cả chế độ tuần tự và cố định tự Refresh khi đã thua cả ba đối thủ. Nhận diện popup miễn phí hoặc trả Gold khi đọc được số lượt còn lại >0 (tối đa 30); không kiểm tra số Gold theo yêu cầu. Mỗi lần mở chỉ gửi Confirm một lần; chỉ xóa dấu thua khi danh sách mới khác danh sách cũ và không còn hàng đỏ, ổn định hai quan sát. Giữ số trận và ngân sách Skystone; hết lượt refresh ngày hoặc không xác minh được thì dừng có thông báo. Chưa build EXE/ZIP.

2026.11.10-r8 (mã nguồn): nhận diện ô skill thủ công bị tối với chữ Cannot use; vẫn yêu cầu đủ ba ô skill và icon auto tắt, không tự bấm dựa trên icon A đơn lẻ. Thêm bộ đếm thắng/thua theo phiên, chỉ chốt khi quay về danh sách sau kết quả (qua popup Friendship/thăng hạng không đếm trùng); giữ tổng trong trạng thái cả khi dừng. Chưa build EXE/ZIP.

2026.11.10-r9 (mã nguồn): xác nhận refresh bằng hai quan sát danh sách khác bản cũ, không yêu cầu hash mới giống hệt nhau giữa các ảnh khi chân dung có hiệu ứng. Nếu trước refresh thấy cả ba hàng đỏ, việc cả ba dấu thua biến mất cũng xác nhận thành công dù hash được giữ do đội hình tương tự. Vẫn không gửi lại Confirm và không chấp nhận danh sách cũ không có bằng chứng thay đổi. Thêm chẩn đoán bước refresh gồm hash, hàng thua trước/sau và số quan sát xác nhận. Chưa build EXE/ZIP.

2026.11.10-r10 (mã nguồn): sửa xác nhận auto khi hero đã chết: ô HUD đỏ có nhãn Skill thay cho ô xanh có tick. Vẫn yêu cầu đủ bốn ô HUD hợp lệ và ít nhất một ô xanh có tick, không dùng nút A xoay đơn lẻ, không gửi click auto lần hai. Ảnh chẩn đoán thực tế xác nhận auto_click_sent=true nhưng hero chết làm mất tick. Thêm kiểm thử 1–3 hero chết và ảnh màu đỏ trống đối chứng. Bổ sung tuổi click auto và cờ đã xác minh vào chẩn đoán. Chưa build EXE/ZIP.

2026.11.10-r11 (mã nguồn): nhận diện HUD manual tìm viền mỗi ô skill trong vùng lệch ngang nhỏ thay vì một vị trí cắt cứng. Khắc phục Rinak: ô thứ ba có viền mảnh/tối lệch vị trí, không phụ thuộc hình skill. Điều chỉnh ngưỡng sáng viền và giữ điều kiện cạnh/khung để phân biệt avatar auto. Kiểm thử ảnh thực tế Rinak qua thu phóng/độ sáng và thay nội dung skill. Chưa build EXE/ZIP.

2026.11.10-r12 (mã nguồn, thử nghiệm): bổ sung theo dõi nút A theo thời gian khi HUD không kết luận được. Lấy ít nhất sáu mẫu trải qua hai giây, chỉ xét vòng mũi tên trắng quanh chữ A để loại chuyển động nền; nút đứng yên và khớp mẫu tắt suốt chuỗi mới xác nhận manual, nhiều biến đổi vòng kèm các góc khác mẫu tắt mới xác nhận auto. Reset chuỗi khi rời trận, icon bị che hoặc gián đoạn lấy mẫu >1 giây. Giữ HUD làm bằng chứng bổ sung và giới hạn một click/trận. Log/chẩn đoán ghi auto_source=icon_sequence hoặc hud. Đã thử ảnh idle thật và chuỗi xoay mô phỏng; chưa kiểm chứng chuỗi nút A xoay trực tiếp trong game. Chưa build EXE/ZIP.

2026.11.13-r1: cập nhật nhãn phiên bản; Abyss dùng lại Guardian khi hồi trong cùng trận, bổ sung mẫu Guardian mới từ ảnh thực tế. Build EXE theo yêu cầu.
