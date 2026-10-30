/**
 * Dữ liệu mẫu thực tế tiếng Việt cho Address May Cry (Phần B).
 * Dùng địa chỉ thực tế từ dữ liệu huấn luyện / chuẩn hành chính, không bịa kết quả.
 * Bao gồm các ca hỗn hợp:
 * - Trộn lẫn mốc cũ và mới
 * - Mất dấu và viết tắt tiền tố
 * - Số nhà kiệt hẻm phức tạp
 * - Cảnh báo xã bị chia tách
 */

export interface SampleAddress {
  label: string;
  address: string;
  note: string;
}

export const SAMPLE_ADDRESSES: SampleAddress[] = [
  {
    label: 'Cần Thơ (Sáp nhập 2025)',
    address: '268/10 NGUYỄN VĂN LINH, PHƯỜNG XUÂN KHÁNH, QUẬN NINH KIỀU, THÀNH PHỐ CẦN THƠ',
    note: 'Xuân Khánh sáp nhập vào Ninh Kiều mốc 2025',
  },
  {
    label: 'Cần Thơ (Từ danh nhân nhầm tỉnh)',
    address: '45 XÔ VIẾT NGHỆ TĨNH P.AN CƯ- NINH KIỀU- CẦN THƠ',
    note: 'Tên đường Xô Viết Nghệ Tĩnh có chữ TĨNH dễ bị nhầm thành cấp tỉnh',
  },
  {
    label: 'Hà Nội (Xã bị chia tách)',
    address: 'Số 16 ngõ 12 Trần Quý Kiên, phường Dịch Vọng, quận Cầu Giấy, Hà Nội',
    note: 'Dịch Vọng chia tách năm 2025 cần kiểm tra',
  },
  {
    label: 'TP.HCM (Xa lộ và tiền tố)',
    address: '120, Xa lộ Hà Nội, Phường Tăng Nhơn Phú, Thành phố Thủ Đức, Thành phố Hồ Chí Minh',
    note: 'Tiền tố Xa lộ giữ nguyên không gán nhầm Đường',
  },
  {
    label: 'Đà Nẵng (Không dấu & viết tắt)',
    address: 'so 369A d. hoang thi loan, phuong hoa minh, quan lien chieu, thanh pho da nang',
    note: 'Viết tắt d. và mất toàn bộ dấu tiếng Việt',
  },
  {
    label: 'Huế (Đường tỉnh lẻ OOV)',
    address: '296 Lý Thái Tổ, P. Hương Sơ, TP. Huế, Thừa Thiên Huế',
    note: 'Kiểm tra độ phủ tên đường địa phương',
  },
  {
    label: 'Đồng Tháp (Thôn xóm tổ ấp)',
    address: 'Tổ 1, ấp 4, xã Mỹ Long, huyện Cao Lãnh, Đồng Tháp',
    note: 'Thôn xóm nông thôn không có số nhà',
  },
  {
    label: 'Tây Ninh (Mã Plus code)',
    address: '843M+RH3 Hòa Thành District, Tây Ninh',
    note: 'Mã số vị trí kết hợp địa danh',
  },
];

/**
 * Tạo nội dung tệp CSV mẫu chuẩn để người dùng tải về thử nghiệm
 */
export function getSampleCsvContent(): string {
  const headers = ['stt', 'ma_khach_hang', 'dia_chi', 'ghi_chu_don_hang'];
  const rows = [
    ['1', 'KH_001', '"268/10 NGUYỄN VĂN LINH, PHƯỜNG XUÂN KHÁNH, QUẬN NINH KIỀU, CẦN THƠ"', 'Đơn giao giờ hành chính'],
    ['2', 'KH_002', '"45 XÔ VIẾT NGHỆ TĨNH, P.AN CƯ, NINH KIỀU, CẦN THƠ"', 'Gọi trước 15 phút'],
    ['3', 'KH_003', '"Số 16 ngõ 12 Trần Quý Kiên, phường Dịch Vọng, Cầu Giấy, Hà Nội"', 'Nhà riêng trong ngõ'],
    ['4', 'KH_004', '"120, Xa lộ Hà Nội, Phường Tăng Nhơn Phú, Thủ Đức, TP.HCM"', 'Tòa nhà mặt tiền'],
    ['5', 'KH_005', '"so 369A d. hoang thi loan, phuong hoa minh, quan lien chieu, da nang"', 'Địa chỉ không dấu'],
    ['6', 'KH_006', '"296 Lý Thái Tổ, P. Hương Sơ, TP. Huế, Thừa Thiên Huế"', 'Giao buổi sáng'],
    ['7', 'KH_007', '"Tổ 1, ấp 4, xã Mỹ Long, huyện Cao Lãnh, Đồng Tháp"', 'Khu vực nông thôn'],
    ['8', 'KH_008', '"843M+RH3 Hòa Thành, Tây Ninh"', 'Địa chỉ theo vị trí số'],
  ];

  const lines = [headers.join(',')];
  for (const r of rows) {
    lines.push(r.join(','));
  }
  return '\uFEFF' + lines.join('\r\n');
}
