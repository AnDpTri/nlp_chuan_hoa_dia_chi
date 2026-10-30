import type { NhanThanhPhan } from '../shared/contracts';

/** Tên thân thiện của từng loại thành phần (không hiện tên biến cho người dùng). */
export const KIND_LABEL: Record<NhanThanhPhan, string> = {
  so_nha: 'Số nhà',
  ngo_ngach_hem: 'Ngõ / ngách / hẻm',
  thon_xom: 'Thôn / xóm / ấp',
  duong: 'Đường / phố',
  xa: 'Xã / phường',
  huyen: 'Quận / huyện (cũ)',
  tinh: 'Tỉnh / thành phố',
  bo_qua: 'Bỏ qua',
};

export const KIND_SHORT: Record<NhanThanhPhan, string> = {
  so_nha: 'Số nhà',
  ngo_ngach_hem: 'Ngõ / hẻm',
  thon_xom: 'Thôn / xóm',
  duong: 'Đường',
  xa: 'Xã / phường',
  huyen: 'Quận / huyện',
  tinh: 'Tỉnh / TP',
  bo_qua: 'Bỏ qua',
};

export const KIND_ORDER: NhanThanhPhan[] = [
  'so_nha', 'ngo_ngach_hem', 'thon_xom', 'duong', 'xa', 'huyen', 'tinh', 'bo_qua',
];

export function kindOf(k: string): NhanThanhPhan {
  return (k in KIND_LABEL ? k : 'bo_qua') as NhanThanhPhan;
}

/** Lấy tên/mã từ một ứng viên xã mới; khóa trả về có thể khác nhau nên đọc linh hoạt. */
export function readCandidate(c: Record<string, string>) {
  const name = c.ten || c.xa_phuong || c.ten_xa || c.xa || '';
  const code = c.ma_xa || c.ma || '';
  const province = c.tinh || c.ten_tinh || '';
  const provinceCode = c.ma_tinh || '';
  if (!name && !code) {
    return { name: Object.values(c).filter(Boolean).join(' · '), code: '', province: '', provinceCode: '' };
  }
  return { name, code, province, provinceCode };
}
