# -*- coding: utf-8 -*-
"""
Danh mục các tuyến/đề xuất đường phố thuộc diện PENDING (chờ thẩm tra/tranh chấp)
hoặc REJECTED (từ chối do không phải tên đường, ngõ ngách, tòa nhà, tên cổ đã bãi bỏ).
Phục vụ lưu trữ minh bạch tại data/duong/v1/danh_muc_pending_rejected.jsonl và .csv.
"""

PENDING_REJECTED_ENTRIES = [
    # (raw_input, candidate_canonical_name, candidate_road_type, ma_tinh, ten_tinh, quan_huyen, status, rejection_reason, legal_source, administrative_era)

    # 1. Các trường hợp REJECTED: Tên ngõ, ngách, hẻm bị nhầm là tên đường
    ("Ngõ 165 Cầu Giấy", "Ngõ 165 Cầu Giấy", "Ngõ", "01", "Hà Nội", "Cầu Giấy", "rejected", "KHONG_PHAI_TEN_DUONG_LA_SO_NGO", "Đối soát cấu trúc địa chỉ: đây là số hiệu ngõ phụ của đường Cầu Giấy", "hien_hanh"),
    ("Ngõ 298 Ngọc Hồi", "Ngõ 298 Ngọc Hồi", "Ngõ", "01", "Hà Nội", "Thanh Trì", "rejected", "KHONG_PHAI_TEN_DUONG_LA_SO_NGO", "Đối soát cấu trúc địa chỉ: đây là số hiệu ngõ của đường Ngọc Hồi", "hien_hanh"),
    ("Hẻm 458 Cách Mạng Tháng Tám", "Hẻm 458 Cách Mạng Tháng Tám", "Hẻm", "79", "Hồ Chí Minh", "Quận 3", "rejected", "KHONG_PHAI_TEN_DUONG_LA_SO_NGO", "Đối soát cấu trúc địa chỉ: đây là số hẻm phụ của đường Cách Mạng Tháng Tám", "hien_hanh"),
    ("Ngách 1/2 Đỗ Nhuận", "Ngách 1/2 Đỗ Nhuận", "Ngách", "01", "Hà Nội", "Bắc Từ Liêm", "rejected", "KHONG_PHAI_TEN_DUONG_LA_SO_NGO", "Không phải tên đường chính quy; là ngách phụ gắn số nhà", "hien_hanh"),
    ("Kiệt 130 Trần Phú", "Kiệt 130 Trần Phú", "Kiệt", "48", "Đà Nẵng", "Hải Châu", "rejected", "KHONG_PHAI_TEN_DUONG_LA_SO_NGO", "Là kiệt hẻm dân sinh gắn số nhà đường Trần Phú, không có quyết định đặt tên đường", "hien_hanh"),

    # 2. Các trường hợp REJECTED: Tên tòa nhà, chung cư, dự án bất động sản
    ("Chung cư C2 Xuân Đỉnh", "", "", "01", "Hà Nội", "Bắc Từ Liêm", "rejected", "KHONG_PHAI_TEN_DUONG_LA_TOA_NHA", "Là tên công trình xây dựng/tòa chung cư, không phải tuyến đường giao thông công cộng", "hien_hanh"),
    ("Tòa nhà Keangnam Landmark 72", "", "", "01", "Hà Nội", "Nam Từ Liêm", "rejected", "KHONG_PHAI_TEN_DUONG_LA_TOA_NHA", "Tên tòa nhà thương mại tại đường Phạm Hùng, không phải tên đường", "hien_hanh"),
    ("Khu đô thị Trung Hòa - Nhân Chính", "", "", "01", "Hà Nội", "Cầu Giấy", "rejected", "KHONG_PHAI_TEN_DUONG_LA_KHU_DO_THI", "Tên phân khu đô thị tập trung nhiều tuyến đường, không phải tên một tuyến đường", "hien_hanh"),
    ("Vinhomes Central Park", "", "", "79", "Hồ Chí Minh", "Bình Thạnh", "rejected", "KHONG_PHAI_TEN_DUONG_LA_KHU_DO_THI", "Khu phức hợp đô thị ven sông, không phải tuyến đường độc lập trong danh mục", "hien_hanh"),
    ("Chợ Bến Thành", "", "", "79", "Hồ Chí Minh", "Quận 1", "rejected", "KHONG_PHAI_TEN_DUONG_LA_DIA_DANH", "Địa danh/công trình công cộng, không phải tên đường", "hien_hanh"),

    # 3. Các trường hợp REJECTED: Tên đường thời thuộc địa đã bãi bỏ hoàn toàn, không còn căn cứ lưu hành
    ("Boulevard Gallieni", "Trần Hưng Đạo", "Đại lộ", "79", "Hồ Chí Minh", "Quận 1, Quận 5", "rejected", "TEN_PHAP_CO_DA_THAY_THE_HOAN_TOAN", "Tên thời Pháp thuộc của đường Trần Hưng Đạo đã bãi bỏ từ năm 1955, không dùng trong chuẩn hóa hiện đại", "hien_hanh"),
    ("Rue Paul Blanchy", "Hai Bà Trưng", "Đường", "79", "Hồ Chí Minh", "Quận 1, Quận 3", "rejected", "TEN_PHAP_CO_DA_THAY_THE_HOAN_TOAN", "Tên cũ thời thuộc địa của đường Hai Bà Trưng, không còn hiệu lực văn bản", "hien_hanh"),
    ("Rue Borgnis Desbordes", "Tràng Thi", "Phố", "01", "Hà Nội", "Hoàn Kiếm", "rejected", "TEN_PHAP_CO_DA_THAY_THE_HOAN_TOAN", "Tên cổ thời Pháp của phố Tràng Thi, chỉ dùng tra cứu tài liệu lưu trữ cổ", "hien_hanh"),

    # 4. Các trường hợp REJECTED: Sai chính tả nghiêm trọng hoặc không có thực
    ("Đường Hoàng Diễu", "Hoàng Diệu", "Đường", "48", "Đà Nẵng", "Hải Châu", "rejected", "SAI_CHINH_TA_NGHIEM_TRONG", "Lỗi gõ sai chính tả của Hoàng Diệu (dấu ngã thay vì dấu nặng), không đưa vào danh mục chính thức", "hien_hanh"),
    ("Đường Trần Hưng Đạo 9999", "", "Đường", "01", "Hà Nội", "", "rejected", "KHONG_CO_THUC", "Tên giả lập/không tồn tại trên thực tế và không có hồ sơ pháp lý", "hien_hanh"),

    # 5. Các trường hợp PENDING: Dự thảo đặt tên đường đang lấy ý kiến HĐND
    ("Đường Trịnh Văn Bô kéo dài", "Trịnh Văn Bô kéo dài", "Đường", "01", "Hà Nội", "Nam Từ Liêm, Hoài Đức", "pending", "DU_THAO_CHUA_BAN_HANH", "Đang trong dự thảo đề án đặt tên đường của Sở VHTT Hà Nội trình HĐND TP, chưa ban hành quyết định chính thức", "hien_hanh"),
    ("Đường Vành đai 3.5 Mê Linh", "Vành đai 3.5", "Đường", "01", "Hà Nội", "Mê Linh", "pending", "DU_THAO_CHUA_BAN_HANH", "Dự án đường đang thi công, chưa có quyết định đặt tên chính thức bằng văn bản quy phạm pháp luật", "hien_hanh"),
    ("Đại lộ Đỗ Mười", "Đỗ Mười", "Đại lộ", "31", "Hải Phòng", "Thủy Nguyên", "pending", "DU_THAO_CHUA_BAN_HANH", "Tuyến đường trục trung tâm hành chính mới Bắc Sông Cấm đang hoàn thiện hồ sơ đặt tên", "hien_hanh"),
    ("Đường Vành đai 4 Vùng Thủ đô", "Vành đai 4", "Đường cao tốc", "01", "Hà Nội", "Hoài Đức, Đan Phượng", "pending", "DU_AN_DANG_XAY_DUNG", "Đang trong quá trình thi công xây dựng, chưa bàn giao khai thác và đặt tên số hiệu chính thức", "hien_hanh"),

    # 6. Các trường hợp PENDING: Tên tự phát của cộng đồng hoặc tranh chấp ranh giới
    ("Đường Giáp Ranh Vĩnh Lộc", "Đường Giáp Ranh Vĩnh Lộc", "Đường", "79", "Hồ Chí Minh", "Bình Chánh, Bình Tân", "pending", "TRANH_CHAP_CHUA_GIAI_QUYET", "Tuyến đường giáp ranh giữa 2 quận huyện có tên gọi tự phát khác nhau giữa người dân hai bên đường", "hien_hanh"),
    ("Đường Suối Mơ", "Suối Mơ", "Đường", "68", "Lâm Đồng", "Đà Lạt", "pending", "TEN_TU_PHAT_CHUA_CONG_NHAN", "Biển tên dân gian do các hộ kinh doanh du lịch tự gắn, chưa có trong ngân hàng tên đường của tỉnh", "hien_hanh"),
    ("Đường Cây Da Bác Hồ", "Cây Da Bác Hồ", "Đường", "79", "Hồ Chí Minh", "Củ Chi", "pending", "TEN_TU_PHAT_CHUA_CONG_NHAN", "Tên đường nội đồng di tích tại Tân Phú Trung do địa phương gọi tạm, chưa ra quyết định đặt tên đường", "hien_hanh"),
    ("Đường Liên Khu 5-6", "Liên Khu 5-6", "Đường", "79", "Hồ Chí Minh", "Bình Tân", "pending", "CAN_DOI_CHIEU_QUYET_DINH", "Tên tạm thời của tuyến giao thông nội bộ khu dân cư Bình Hưng Hòa B", "hien_hanh")
]
