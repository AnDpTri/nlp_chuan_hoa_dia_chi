# -*- coding: utf-8 -*-
"""
Explicit mapping for the verified grounded corrections.
Audited and updated with exact source ward codes (ma_xa_cu) matching input text.
Split-ward cases (such as Lac Dao, Van Lam, Hung Yen) are strictly kept provisional (can_duyet) with empty target ward.
"""

GROUNDED_29_PATCHES = {
    'VNTEST0013': { # 107 - 109 Đỗ Xuân Hợp, phường Phước Long B, Quận 9
        'ma_xa_cu': '26848', 'ma_huyen_cu': '769', 'ma_tinh_cu': '79',
        'ma_xa': '26848', 'ma_tinh': '79', 'xa_phuong': 'Phường Phước Long', 'tinh': 'Thành phố Hồ Chí Minh',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen', 'thieu_tinh'],
        'reason': "Đầu vào ghi rõ 'phường Phước Long B, Quận 9'; Quận 9 sáp nhập vào TP Thủ Đức, Phường Phước Long B (mã cũ 26848) thành Phường Phước Long (mã 26848, TP.HCM)."
    },
    'VNTEST0016': { # 288 Nguyễn Văn Linh, An Khánh, NK, CT
        'ma_xa_cu': '31149', 'ma_huyen_cu': '916', 'ma_tinh_cu': '92',
        'ma_xa': '31147', 'ma_tinh': '92', 'xa_phuong': 'Phường Tân An', 'tinh': 'Thành phố Cần Thơ',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen', 'khong_khop_tinh', 'thieu_tinh'],
        'reason': "Đầu vào viết tắt 'An Khánh, NK, CT' (Phường An Khánh, Ninh Kiều, Cần Thơ, mã cũ 31149); sáp nhập thành Phường Tân An (mã 31147, TP Cần Thơ)."
    },
    'VNTEST0017': { # A2-12A Gò Dưa ,P.Tam Bình ,Q. Thủ Đức
        'ma_xa_cu': '26803', 'ma_huyen_cu': '769', 'ma_tinh_cu': '79',
        'ma_xa': '26803', 'ma_tinh': '79', 'xa_phuong': 'Phường Tam Bình', 'tinh': 'Thành phố Hồ Chí Minh',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen', 'thieu_tinh'],
        'reason': "Đầu vào ghi rõ 'P.Tam Bình ,Q. Thủ Đức'; Phường Tam Bình (mã cũ 26803) giữ nguyên tên (mã 26803, TP.HCM)."
    },
    'VNTEST0038': { # 8 Cộng Hòa, Phường 4, Hồ Chí Minh, Việt Nam
        'ma_xa_cu': '26968', 'ma_huyen_cu': '766', 'ma_tinh_cu': '79',
        'ma_xa': '26968', 'ma_tinh': '79', 'xa_phuong': 'Phường Tân Sơn Nhất', 'tinh': 'Thành phố Hồ Chí Minh',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'trung_ten_xa'],
        'reason': "Tuyến đường Cộng Hòa chạy qua Phường 4, Quận Tân Bình (mã cũ 26968); sáp nhập thành Phường Tân Sơn Nhất (mã 26968, TP.HCM)."
    },
    'VNTEST0039': { # 709, Nguyễn Thị Định, Cát Lái, 2, Hồ Chí Minh
        'ma_xa_cu': '27109', 'ma_huyen_cu': '769', 'ma_tinh_cu': '79',
        'ma_xa': '27112', 'ma_tinh': '79', 'xa_phuong': 'Phường Cát Lái', 'tinh': 'Thành phố Hồ Chí Minh',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen'],
        'reason': "Đầu vào ghi rõ 'Cát Lái, 2, Hồ Chí Minh' (Phường Cát Lái, Quận 2 cũ nay thuộc TP Thủ Đức, mã cũ 27109); chuyển thành Phường Cát Lái (mã mới 27112)."
    },
    'VNTEST0046': { # ĐT.281, Thôn Trịnh Xá, Xã Lạc Đạo, Hưng Yên
        'ma_xa_cu': '11989', 'ma_huyen_cu': '325', 'ma_tinh_cu': '33',
        'ma_xa': '', 'ma_tinh': '33', 'xa_phuong': '', 'tinh': 'Tỉnh Hưng Yên',
        'is_split_ward': True,
        'reason': "Đầu vào có 'Xã Lạc Đạo, Hưng Yên'; Xã Lạc Đạo (mã cũ 11989) là xã bị chia theo bảng chuyển đổi thành Xã Lạc Đạo (11992) và Xã Đại Đồng (11995); không có số nhà chi tiết nên bảo lưu can_duyet và giữ ứng viên."
    },
    'VNTEST0053': { # Chợ Đậu, Khu dân cư mới thông Cát Lư, Thôn Cát Lư, Xã Lạc Đạo, Hưng Yên
        'ma_xa_cu': '11989', 'ma_huyen_cu': '325', 'ma_tinh_cu': '33',
        'ma_xa': '', 'ma_tinh': '33', 'xa_phuong': '', 'tinh': 'Tỉnh Hưng Yên',
        'is_split_ward': True,
        'reason': "Đầu vào có Thôn Cát Lư, Xã Lạc Đạo, Hưng Yên; Xã Lạc Đạo (mã cũ 11989) là xã bị chia thành Xã Lạc Đạo (11992) và Xã Đại Đồng (11995); bảo lưu can_duyet và giữ ứng viên."
    },
    'VNTEST0055': { # ĐT.385;ĐT.281, Nghĩa Lộ, Xã Lạc Đạo, Hưng Yên
        'ma_xa_cu': '11989', 'ma_huyen_cu': '325', 'ma_tinh_cu': '33',
        'ma_xa': '', 'ma_tinh': '33', 'xa_phuong': '', 'tinh': 'Tỉnh Hưng Yên',
        'is_split_ward': True,
        'reason': "Đầu vào có Nghĩa Lộ, Xã Lạc Đạo, Hưng Yên; Xã Lạc Đạo (mã cũ 11989) là xã bị chia thành Xã Lạc Đạo (11992) và Xã Đại Đồng (11995); bảo lưu can_duyet và giữ ứng viên."
    },
    'VNTEST0058': { # Thon Pac Ngoi, Xa Nam Mau, Ba Be district, Bac Kan
        'ma_xa_cu': '01909', 'ma_huyen_cu': '061', 'ma_tinh_cu': '06',
        'ma_xa': '01906', 'ma_tinh': '19', 'xa_phuong': 'Xã Ba Bể', 'tinh': 'Tỉnh Thái Nguyên',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen'],
        'reason': "Đầu vào không dấu 'Xa Nam Mau, Ba Be district, Bac Kan'; Xã Nam Mẫu (mã cũ 01909), Ba Bể sáp nhập thành Xã Ba Bể (mã 01906, Tỉnh Thái Nguyên)."
    },
    'VNTEST0081': { # Lạc Long Quân, P. Điện Dương, TX. Điện Bàn, T. Quảng Nam
        'ma_xa_cu': '20581', 'ma_huyen_cu': '507', 'ma_tinh_cu': '49',
        'ma_xa': '20579', 'ma_tinh': '48', 'xa_phuong': 'Phường Điện Bàn Đông', 'tinh': 'Thành phố Đà Nẵng',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen', 'khong_khop_tinh', 'thieu_tinh'],
        'reason': "Đầu vào có 'P. Điện Dương, TX. Điện Bàn, T. Quảng Nam'; Phường Điện Dương (mã cũ 20581) sáp nhập thành Phường Điện Bàn Đông (mã 20579, TP Đà Nẵng)."
    },
    'VNTEST0090': { # 229 Tôn Đức Thắng, p. Nghĩa Thành, Thị xã Gia Nghĩa, Đăk Nông, Việt Nam
        'ma_xa_cu': '24612', 'ma_huyen_cu': '660', 'ma_tinh_cu': '67',
        'ma_xa': '24611', 'ma_tinh': '68', 'xa_phuong': 'Phường Bắc Gia Nghĩa', 'tinh': 'Tỉnh Lâm Đồng',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen'],
        'reason': "Đầu vào có 'p. Nghĩa Thành, Thị xã Gia Nghĩa, Đăk Nông'; Phường Nghĩa Thành (mã cũ 24612) sáp nhập thành Phường Bắc Gia Nghĩa (mã 24611, Tỉnh Lâm Đồng)."
    },
    'VNTEST0092': { # 908 Phú Riềng Đỏ, Tân Xuân, Tx. Đồng Xoài, Bình Phước, Việt Nam
        'ma_xa_cu': '25204', 'ma_huyen_cu': '689', 'ma_tinh_cu': '70',
        'ma_xa': '25195', 'ma_tinh': '75', 'xa_phuong': 'Phường Bình Phước', 'tinh': 'Tỉnh Đồng Nai',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen'],
        'reason': "Đầu vào có 'Tân Xuân, Tx. Đồng Xoài, Bình Phước'; Phường Tân Xuân (mã cũ 25204) sáp nhập thành Phường Bình Phước (mã 25195, Tỉnh Đồng Nai)."
    },
    'VNTEST0118': { # 97 Hoàng Diệu 2, Phường Linh Trung, Quận Thủ Đức, TP HCM
        'ma_xa_cu': '26800', 'ma_huyen_cu': '769', 'ma_tinh_cu': '79',
        'ma_xa': '26800', 'ma_tinh': '79', 'xa_phuong': 'Phường Linh Xuân', 'tinh': 'Thành phố Hồ Chí Minh',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen'],
        'reason': "Đầu vào có 'Phường Linh Trung, Quận Thủ Đức, TP HCM'; Phường Linh Trung (mã cũ 26800) sáp nhập thành Phường Linh Xuân (mã 26800, TP.HCM)."
    },
    'VNTEST0143': { # Khối phố Cẩm Sa, P Điện Nam Bắc, TX Điện Bàn, T Quảng Nam
        'ma_xa_cu': '20578', 'ma_huyen_cu': '507', 'ma_tinh_cu': '49',
        'ma_xa': '20579', 'ma_tinh': '48', 'xa_phuong': 'Phường Điện Bàn Đông', 'tinh': 'Thành phố Đà Nẵng',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen', 'khong_khop_tinh', 'thieu_tinh'],
        'reason': "Đầu vào có 'P Điện Nam Bắc, TX Điện Bàn, T Quảng Nam'; Phường Điện Nam Bắc (mã cũ 20578) sáp nhập thành Phường Điện Bàn Đông (mã 20579, TP Đà Nẵng)."
    },
    'VNTEST0179': { # 373 Nguyễn Oanh, Phường 17, Hồ Chí Minh, Việt Nam
        'ma_xa_cu': '26875', 'ma_huyen_cu': '764', 'ma_tinh_cu': '79',
        'ma_xa': '26884', 'ma_tinh': '79', 'xa_phuong': 'Phường Gò Vấp', 'tinh': 'Thành phố Hồ Chí Minh',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'trung_ten_xa'],
        'reason': "Đường Nguyễn Oanh chạy qua Phường 17, Quận Gò Vấp (mã cũ 26875); sáp nhập thành Phường Gò Vấp (mã 26884, TP.HCM)."
    },
    'VNTEST0197': { # 272, Trần Hưng Đạo,, Cửa Bắc Ward, Nam Định City, Nam Dinh Province
        'ma_xa_cu': '13669', 'ma_huyen_cu': '356', 'ma_tinh_cu': '36',
        'ma_xa': '13669', 'ma_tinh': '37', 'xa_phuong': 'Phường Nam Định', 'tinh': 'Tỉnh Ninh Bình',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen', 'khong_khop_tinh', 'thieu_tinh'],
        'reason': "Đầu vào tiếng Anh 'Cửa Bắc Ward, Nam Định City'; Phường Cửa Bắc (mã cũ 13669) sáp nhập thành Phường Nam Định (mã 13669, Tỉnh Ninh Bình)."
    },
    'VNTEST0246': { # Ta Van Day, Ta Van, Sapa, Lao Cai
        'ma_xa_cu': '03040', 'ma_huyen_cu': '088', 'ma_tinh_cu': '10',
        'ma_xa': '03037', 'ma_tinh': '15', 'xa_phuong': 'Xã Tả Van', 'tinh': 'Tỉnh Lào Cai',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen'],
        'reason': "Đầu vào không dấu 'Ta Van, Sapa, Lao Cai'; Xã Tả Van, Sa Pa (mã cũ 03040) chuyển thành Xã Tả Van (mã mới 03037) trong danh mục mốc 01/07/2025."
    },
    'VNTEST0266': { # Thôn Xuân Phú, X. Tam Thái, H. Phú Ninh, T.Quảng Nam
        'ma_xa_cu': '20386', 'ma_huyen_cu': '518', 'ma_tinh_cu': '49',
        'ma_xa': '20364', 'ma_tinh': '48', 'xa_phuong': 'Xã Chiên Đàn', 'tinh': 'Thành phố Đà Nẵng',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen', 'khong_khop_tinh', 'thieu_tinh'],
        'reason': "Đầu vào có 'X. Tam Thái, H. Phú Ninh, T.Quảng Nam'; Xã Tam Thái (mã cũ 20386) sáp nhập thành Xã Chiên Đàn (mã 20364, TP Đà Nẵng)."
    },
    'VNTEST0277': { # ấp 2 xã tiến hưng - thị xã đồng xoài - bình phước
        'ma_xa_cu': '25213', 'ma_huyen_cu': '689', 'ma_tinh_cu': '70',
        'ma_xa': '25195', 'ma_tinh': '75', 'xa_phuong': 'Phường Bình Phước', 'tinh': 'Tỉnh Đồng Nai',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen'],
        'reason': "Đầu vào có 'xã tiến hưng - thị xã đồng xoài - bình phước'; Xã Tiến Hưng (mã cũ 25213) sáp nhập thành Phường Bình Phước (mã 25195, Tỉnh Đồng Nai)."
    },
    'VNTEST0280': { # Đường Mỹ Xuân-Tóc Tiên, ấp 5, xã Tóc Tiên, Thị xã Phú Mỹ, Bà Rịa - Vũng Tàu
        'ma_xa_cu': '26731', 'ma_huyen_cu': '754', 'ma_tinh_cu': '77',
        'ma_xa': '26728', 'ma_tinh': '79', 'xa_phuong': 'Xã Châu Pha', 'tinh': 'Thành phố Hồ Chí Minh',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen'],
        'reason': "Đầu vào có 'xã Tóc Tiên, Thị xã Phú Mỹ, Bà Rịa - Vũng Tàu'; Xã Tóc Tiên (mã cũ 26731) sáp nhập thành Xã Châu Pha (mã 26728, TP.HCM)."
    },
    'VNTEST0288': { # 56 Dong Ho, KP 1, Phuong Dong, Ho, Tx. Ha Tien, Kien Giang
        'ma_xa_cu': '30769', 'ma_huyen_cu': '900', 'ma_tinh_cu': '91',
        'ma_xa': '30769', 'ma_tinh': '91', 'xa_phuong': 'Phường Hà Tiên', 'tinh': 'Tỉnh An Giang',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen'],
        'reason': "Đầu vào có 'Phuong Dong, Ho, Tx. Ha Tien, Kien Giang'; Phường Đông Hồ (mã cũ 30769) sáp nhập thành Phường Hà Tiên (mã 30769, Tỉnh An Giang)."
    },
    'VNTEST0291': { # 208/5, Hùng Vương, 1, Bạc Liêu, Việt Nam
        'ma_xa_cu': '31825', 'ma_huyen_cu': '954', 'ma_tinh_cu': '95',
        'ma_xa': '31825', 'ma_tinh': '96', 'xa_phuong': 'Phường Bạc Liêu', 'tinh': 'Tỉnh Cà Mau',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'trung_ten_xa'],
        'reason': "Đầu vào có '1, Bạc Liêu' (Phường 1, thành phố Bạc Liêu, mã cũ 31825); Phường 1 sáp nhập thành Phường Bạc Liêu (mã 31825, Tỉnh Cà Mau)."
    },
    'VNTEST0308': { # La Pán Tẩn, Mù Cang Chải District, Yên Bái, Vietnam
        'ma_xa_cu': '04483', 'ma_huyen_cu': '137', 'ma_tinh_cu': '15',
        'ma_xa': '04492', 'ma_tinh': '15', 'xa_phuong': 'Xã Púng Luông', 'tinh': 'Tỉnh Lào Cai',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen'],
        'reason': "Đầu vào có 'La Pán Tẩn, Mù Cang Chải District, Yên Bái'; Xã La Pán Tẩn (mã cũ 04483) sáp nhập thành Xã Púng Luông (mã 04492, Tỉnh Lào Cai)."
    },
    'VNTEST0309': { # 123/8, Hẻm 123 đường số 3, Bình Hưng Hòa, Bình Tân, Hồ Chí Minh, Thành phố Hồ Chí Minh
        'so_nha': '123/8', 'ngo_ngach_hem': 'Hẻm 123', 'duong': 'Đường Số 3',
        'reason': "Đầu vào '123/8, Hẻm 123 đường số 3'; trích xuất đầy đủ số nhà '123/8' (không bóc tách cụt '8' sai ranh giới) và phần ngõ/hẻm 'Hẻm 123'."
    },
    'VNTEST0325': { # 1232 Hùng Vương, X. Duy Sơn, H. Duy Xuyên, T. Quảng Nam
        'ma_xa_cu': '20620', 'ma_huyen_cu': '508', 'ma_tinh_cu': '49',
        'ma_xa': '20623', 'ma_tinh': '48', 'xa_phuong': 'Xã Duy Xuyên', 'tinh': 'Thành phố Đà Nẵng',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen', 'khong_khop_tinh', 'thieu_tinh'],
        'reason': "Đầu vào có 'X. Duy Sơn, H. Duy Xuyên, T. Quảng Nam'; Xã Duy Sơn (mã cũ 20620) sáp nhập thành Xã Duy Xuyên (mã 20623, TP Đà Nẵng)."
    },
    'VNTEST0349': { # 16A, Trần Hưng Đạo, 2, Phường 2, Soc Trang
        'ma_xa_cu': '31510', 'ma_huyen_cu': '941', 'ma_tinh_cu': '94',
        'ma_xa': '31510', 'ma_tinh': '92', 'xa_phuong': 'Phường Phú Lợi', 'tinh': 'Thành phố Cần Thơ',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'trung_ten_xa'],
        'reason': "Đầu vào có 'Phường 2, Soc Trang'; Phường 2 (mã cũ 31510) sáp nhập thành Phường Phú Lợi (mã 31510, TP Cần Thơ)."
    },
    'VNTEST0361': { # Nam Dam hamlet, Quan Ba commune, Quan Ba, Ha Giang
        'ma_xa_cu': '00898', 'ma_huyen_cu': '029', 'ma_tinh_cu': '02',
        'ma_xa': '00874', 'ma_tinh': '08', 'xa_phuong': 'Xã Quản Bạ', 'tinh': 'Tỉnh Tuyên Quang',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen'],
        'reason': "Đầu vào có 'Quan Ba commune, Quan Ba, Ha Giang'; Xã Quản Bạ (mã cũ 00898) sáp nhập thành Xã Quản Bạ (mã 00874, Tỉnh Tuyên Quang)."
    },
    'VNTEST0382': { # 86 Nguyễn Vịnh, TDP Vĩnh Hoà, TT. Sịa, H. Quảng Điền, TP. Huế
        'ma_xa_cu': '19867', 'ma_huyen_cu': '477', 'ma_tinh_cu': '46',
        'ma_xa': '19867', 'ma_tinh': '46', 'xa_phuong': 'Xã Quảng Điền', 'tinh': 'Thành phố Huế',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen'],
        'reason': "Đầu vào có 'TT. Sịa, H. Quảng Điền, TP. Huế'; Thị trấn Sịa (mã cũ 19867) sáp nhập thành Xã Quảng Điền (mã 19867, Thành phố Huế)."
    },
    'VNTEST0384': { # ĐT611, X. Quế Châu, H. Quế Sơn, T. Quảng Nam
        'ma_xa_cu': '20680', 'ma_huyen_cu': '509', 'ma_tinh_cu': '49',
        'ma_xa': '20662', 'ma_tinh': '48', 'xa_phuong': 'Xã Quế Sơn Trung', 'tinh': 'Thành phố Đà Nẵng',
        'canh_bao_remove': ['chua_xac_dinh_xa', 'khong_khop_huyen', 'khong_khop_tinh', 'thieu_tinh'],
        'reason': "Đầu vào có 'X. Quế Châu, H. Quế Sơn, T. Quảng Nam'; Xã Quế Châu (mã cũ 20680) sáp nhập thành Xã Quế Sơn Trung (mã 20662, TP Đà Nẵng)."
    }
}
