export interface AddressResult {
  so_nha: string; ngo_ngach_hem: string; thon_xom: string; duong: string;
  xa_phuong: string; ma_xa: string; tinh: string; ma_tinh: string;
  dia_chi_chuan: string; canh_bao: string[];
  xa_moi_ung_vien: Record<string, string>[];
  dau_vet: Record<string, unknown>[];
  phan_chua_phan_loai: string; thong_ke: Record<string, unknown>;
}
export interface ApiError { code: string; message: string }
export interface NormalizeResponse {
  input: string; result: AddressResult; elapsed_ms: number;
  status: 'processed' | 'needs_review';
}
export interface BatchInput { id: string; address: string }
export interface BatchItem {
  id: string; input: string; status: 'processed' | 'needs_review' | 'error';
  result?: AddressResult; elapsed_ms?: number; error?: ApiError;
}
export interface BatchResponse { items: BatchItem[]; elapsed_ms: number }
export interface HealthResponse {
  status: 'ok' | 'loading' | 'error'; engine: string; target_date: string;
  limits: { max_chars: number; max_batch: number }; message?: string;
}
