/** Bảng dịch mã cảnh báo của hệ thống sang câu tiếng Việt dễ hiểu. */
export interface WarningInfo {
  label: string;
  desc: string;
}

export const WARNING_INFO: Record<string, WarningInfo> = {
  xa_chia_suy_tu_duong: {
    label: 'Xã/phường mới suy ra từ tên đường',
    desc: 'Xã/phường cũ trong địa chỉ đã được chia về nhiều nơi. Hệ thống chọn xã/phường mới theo tên đường, dựa trên vị trí các số nhà đã biết trên đường đó (dữ liệu bản đồ cộng đồng, chưa phải xác nhận chính thức) — nên kiểm tra lại.',
  },
  thieu_xa: {
    label: 'Chưa nhận ra xã/phường',
    desc: 'Không tìm thấy tên xã/phường trong địa chỉ. Hãy bổ sung hoặc kiểm tra lại cách viết.',
  },
  thieu_tinh: {
    label: 'Chưa nhận ra tỉnh/thành phố',
    desc: 'Không tìm thấy tên tỉnh/thành phố trong địa chỉ. Hãy bổ sung hoặc kiểm tra lại cách viết.',
  },
  thieu_tinh_dau_vao: {
    label: 'Địa chỉ nhập không ghi tỉnh/thành phố',
    desc: 'Tỉnh/thành phố được suy ra từ phần còn lại của địa chỉ. Nên ghi rõ tỉnh/thành phố ngay trong địa chỉ gốc.',
  },
  xa_bi_chia: {
    label: 'Xã cũ được chia về nhiều nơi',
    desc: 'Đơn vị cũ sau 01/07/2025 được tách về nhiều xã/phường mới. Không đủ thông tin để chọn chắc một nơi, hãy xem danh sách ứng viên.',
  },
  nhieu_cach_hieu: {
    label: 'Địa chỉ có nhiều cách hiểu',
    desc: 'Có nhiều phương án gần ngang nhau. Kết quả hiện là phương án gần nhất, bạn nên kiểm tra lại.',
  },
  mo_ho_moc_cu_moi: {
    label: 'Tên trùng giữa đơn vị cũ và mới',
    desc: 'Tên này vừa là đơn vị hành chính cũ vừa là đơn vị mới, nên chưa chắc địa chỉ viết theo mốc nào.',
  },
  mau_thuan_hanh_chinh: {
    label: 'Các cấp hành chính không khớp nhau',
    desc: 'Xã/phường, quận/huyện và tỉnh/thành phố trong địa chỉ không thuộc cùng một nơi.',
  },
  don_vi_ghi_khong_khop: {
    label: 'Có đơn vị ghi không khớp',
    desc: 'Một đơn vị trong địa chỉ (thường là quận/huyện) không chứa xã/phường đã ghi. Kết quả lấy theo xã/phường và tỉnh, bỏ qua đơn vị không khớp — hãy kiểm tra lại.',
  },
  phan_chua_phan_loai: {
    label: 'Còn đoạn chữ chưa phân loại',
    desc: 'Có phần chữ trong địa chỉ chưa xếp được vào số nhà, ngõ, thôn, đường hay đơn vị hành chính nào.',
  },
  khop_gan_dung: {
    label: 'Tên chỉ khớp gần đúng',
    desc: 'Tên trong địa chỉ không giống hoàn toàn danh mục (có thể sai chính tả hoặc thiếu chữ). Hãy kiểm tra lại.',
  },
  dau_ten_khac_danh_muc: {
    label: 'Dấu tiếng Việt khác danh mục',
    desc: 'Tên viết khác dấu so với danh mục chính thức. Kết quả đã lấy theo danh mục.',
  },
  loai_hanh_chinh_khac_danh_muc: {
    label: 'Loại đơn vị khác danh mục',
    desc: 'Địa chỉ ghi loại đơn vị (xã, phường, thị trấn…) khác với danh mục. Kết quả đã lấy theo danh mục.',
  },
  loai_duong_suy_tu_crf: {
    label: 'Loại đường do hệ thống đoán',
    desc: 'Địa chỉ không ghi rõ “đường”, “phố”… nên hệ thống tự đoán từ cách viết. Chưa có dữ liệu để kiểm chứng.',
  },
  duong_suy_tu_vi_tri: {
    label: 'Tên đường đoán theo vị trí',
    desc: 'Tên đường được suy ra từ vị trí trong câu, không có từ khóa “đường” hay “phố” đi kèm.',
  },
  ten_duong_tham_chieu_train_chua_xac_minh: {
    label: 'Tên đường chưa được kiểm chứng',
    desc: 'Tên đường chỉ khớp với dữ liệu mẫu của hệ thống, chưa đối chiếu được với danh mục đường chính thức.',
  },
  ten_duong_viet_tat_chua_giai: {
    label: 'Tên đường viết tắt chưa giải nghĩa',
    desc: 'Tên đường đang viết tắt và hệ thống chưa mở rộng được thành tên đầy đủ.',
  },
  ten_chi_tiet_chua_xac_minh_dau: {
    label: 'Chưa xác minh dấu của tên chi tiết',
    desc: 'Tên đường/thôn gốc thiếu dấu, hệ thống không tự thêm dấu khi chưa có căn cứ.',
  },
  khong_co_doi_chieu: {
    label: 'Không có dữ liệu để đối chiếu',
    desc: 'Không có danh mục phù hợp để kiểm tra phần này, hệ thống chỉ chuẩn hóa cách viết.',
  },
  ung_vien_tra_cuu_bi_gioi_han: {
    label: 'Danh sách ứng viên bị giới hạn',
    desc: 'Có thể còn ứng viên khác chưa hiện ra vì số lượng tra cứu bị giới hạn.',
  },
  dau_vao_rong: {
    label: 'Chưa có địa chỉ để xử lý',
    desc: 'Ô nhập đang trống. Hãy nhập địa chỉ cần chuẩn hóa.',
  },
  ten_duong_chi_la_goi_y_chua_xac_minh: {
    label: 'Tên đường chỉ là gợi ý',
    desc: 'Tên đường là gợi ý của hệ thống và chưa được xác minh. Hãy kiểm tra trước khi dùng.',
  },
  so_nha_can_duyet: {
    label: 'Số nhà cần xem lại',
    desc: 'Số nhà có ký tự phân tách đặc biệt (/, -, ;) nên cần bạn rà soát.',
  },
  dau_vao_khong_dau: {
    label: 'Địa chỉ nhập không có dấu',
    desc: 'Địa chỉ thiếu dấu tiếng Việt, hệ thống khôi phục dấu theo danh mục.',
  },
  dau_vao_viet_tat: {
    label: 'Địa chỉ có từ viết tắt',
    desc: 'Địa chỉ chứa từ viết tắt (p., q., tp.…) đã được mở rộng.',
  },
};

export function describeWarning(code: string): WarningInfo {
  return (
    WARNING_INFO[code] ?? {
      label: `Cảnh báo khác (${code})`,
      desc: 'Hệ thống ghi nhận một cảnh báo chưa có lời giải thích. Hãy kiểm tra kết quả kỹ hơn.',
    }
  );
}
