# Kiểm tra hai task agy lần 4 — 29/10/2026

Hai task đã bàn giao, nhưng chưa đạt nghiệm thu toàn bộ.

- Train/dev: 2.169 + 500 mẫu; 2.125 + 488 dùng được với tokenizer hiện
  tại; 56 ca lệch ranh giới đã đánh dấu đúng. Có 88 + 24 span ngõ/hẻm.
  Không tìm thấy lỗi offset/BIO, tên đích theo mã hoặc ba mã nguồn so
  với mẫu cha trong các kiểm tra đã chạy. 17 unit test và validator qua.
- Bảng provenance: 0 đối ứng đổi mã xã cũ, nhưng 54/56 đối ứng còn ghi
  kế thừa tên đường dù đối ứng mới là tên đường khác. Một dòng khác chỉ
  khác cách viết/tiền tố, không tính vào 54 lỗi tên.
- Test: 289 duyệt AI, 111 cần duyệt; 36 xã bị chia đều giữ xã đích trống.
  400 ID/input/URL giữ nguyên. 24 bài test và validator hiện hành qua.
- Fixture độc lập mới vẫn lọt: lấy `Tân Phú` của quận để gán phường
  Tân Phú cũ thuộc Quận 9, đích Tăng Nhơn Phú; và gán `Thôn 199999`
  từ input `KP 1`. Cả engine và validator vẫn chấp nhận.
- Căn cứ Hà Nội còn lẫn đợt 2024/2025; URL NQ1286 đã ghi trả 404.
  Audit Hải Phòng còn câu diễn giải chia phường theo NQ1232 chưa đúng.

[Báo cáo đầy đủ cùng script, fixture, snapshot, log và SHA-256](../../bao_cao/2026-10-29/kiem_tra_agy_lan_4/BAO_CAO.md).

Không sửa dữ liệu/lõi/mô hình hoặc gửi giao việc mới trong lượt kiểm tra.
