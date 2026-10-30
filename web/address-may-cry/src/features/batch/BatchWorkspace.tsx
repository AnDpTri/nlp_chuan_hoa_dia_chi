import React, { useState, useRef, useMemo, useEffect } from 'react';
import type { BatchInput, BatchItem } from '../../shared/contracts';
import { normalizeBatch } from '../../shared/api';
import { parseCSV, parsePastedLines, CSV_LIMITS } from './csvParser';
import { exportToCSV, exportToJSON, type BatchItemWithMeta } from './exportUtils';
import { SAMPLE_ADDRESSES, getSampleCsvContent } from './sampleData';
import styles from './batch.module.css';

export interface BatchWorkspaceProps {
  onInspect?: (item: BatchItem) => void;
}

const CHUNK_SIZE = 20;

// Bảng giải nghĩa cảnh báo bằng tiếng Việt tự nhiên
const WARNING_TRANSLATIONS: Record<string, { label: string; desc: string }> = {
  xa_bi_chia: {
    label: 'Xã bị chia tách 2025',
    desc: 'Đơn vị hành chính cũ bị chia tách thành nhiều xã/phường mới theo mốc 01/07/2025; cần rà soát vị trí cụ thể.',
  },
  nhieu_cach_hieu: {
    label: 'Nhiều cách hiểu',
    desc: 'Đầu vào có nhiều giả thuyết địa chỉ tương đồng về điểm số xếp hạng.',
  },
  mo_ho_moc_cu_moi: {
    label: 'Mơ hồ mốc cũ/mới',
    desc: 'Địa danh vừa khớp với tên cũ vừa trùng tên đơn vị hành chính mới.',
  },
  dau_vao_khong_dau: {
    label: 'Đầu vào không dấu',
    desc: 'Địa chỉ thiếu dấu tiếng Việt; hệ thống khôi phục theo xác suất từ điển.',
  },
  dau_vao_viet_tat: {
    label: 'Có từ viết tắt',
    desc: 'Chứa các từ viết tắt tiền tố (vd: d., p., q., tt., tp.).',
  },
  thieu_xa: {
    label: 'Khuyết cấp xã/phường',
    desc: 'Không tìm thấy thông tin xã/phường hợp lệ trong chuỗi đầu vào.',
  },
  thieu_tinh: {
    label: 'Khuyết cấp tỉnh/thành',
    desc: 'Không xác định được tỉnh/thành phố tương ứng.',
  },
  so_nha_can_duyet: {
    label: 'Số nhà phức hợp',
    desc: 'Số nhà chứa ký tự kiệt/hẻm, xẹt lồng ghép hoặc số lô cần đối soát.',
  },
  phan_chua_phan_loai: {
    label: 'Còn phần dư thừa',
    desc: 'Một số từ ngữ trong địa chỉ không khớp với danh mục hành chính hay tên đường.',
  },
};

export default function BatchWorkspace({ onInspect }: BatchWorkspaceProps) {
  // Chế độ nhập liệu: 'paste' (dán) | 'csv' (tệp CSV)
  const [inputMode, setInputMode] = useState<'paste' | 'csv'>('paste');

  // Trạng thái nhập liệu Dán
  const [pastedText, setPastedText] = useState<string>('');

  // Trạng thái nhập liệu CSV
  const [csvFileName, setCsvFileName] = useState<string>('');
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [csvRawRows, setCsvRawRows] = useState<Record<string, string>[]>([]);
  const [selectedAddressCol, setSelectedAddressCol] = useState<string>('');
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Danh sách dòng xử lý
  const [batchItems, setBatchItems] = useState<BatchItemWithMeta[]>([]);

  // Trạng thái thực thi
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processedCount, setProcessedCount] = useState<number>(0);
  const [totalElapsedMs, setTotalElapsedMs] = useState<number>(0);
  const [activeSessionId, setActiveSessionId] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Controller hủy request
  const abortControllerRef = useRef<AbortController | null>(null);

  // Bộ lọc & Tìm kiếm
  const [statusFilter, setStatusFilter] = useState<'all' | 'needs_review' | 'processed' | 'error'>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Phân trang
  const [pageSize, setPageSize] = useState<number>(25);
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Ngăn xem chi tiết (Drawer Inspector)
  const [inspectingItem, setInspectingItem] = useState<BatchItemWithMeta | null>(null);

  // Đồng bộ item đang xem chi tiết khi danh sách cập nhật
  useEffect(() => {
    if (inspectingItem) {
      const updated = batchItems.find(it => it.id === inspectingItem.id);
      if (updated) setInspectingItem(updated);
    }
  }, [batchItems, inspectingItem]);

  // Hủy tiến trình khi unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // --- CÁC HÀM XỬ LÝ NHẬP LIỆU ---

  // Xử lý nạp dữ liệu mẫu
  const handleLoadSample = (sample: string) => {
    setPastedText(prev => (prev ? `${prev.trim()}\n${sample}` : sample));
    setErrorMessage(null);
  };

  const handleLoadAllSamples = () => {
    const all = SAMPLE_ADDRESSES.map(s => s.address).join('\n');
    setPastedText(all);
    setErrorMessage(null);
  };

  // Tải về file CSV mẫu
  const handleDownloadSampleCsv = () => {
    const content = getSampleCsvContent();
    const blob = new Blob([content], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'mau_dia_chi_chuan.csv';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 100);
  };

  // Xử lý chọn tệp CSV
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) await processUploadedFile(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const processUploadedFile = async (file: File) => {
    setErrorMessage(null);
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setErrorMessage('Hiện tại hệ thống chỉ hỗ trợ tệp định dạng .csv (UTF-8). Vui lòng chuyển đổi tệp bảng tính sang CSV.');
      return;
    }
    if (file.size > CSV_LIMITS.MAX_FILE_BYTES) {
      setErrorMessage(`Dung lượng tệp ${(file.size / (1024 * 1024)).toFixed(1)}MB vượt quá giới hạn tối đa 5MB. Vui lòng chia nhỏ tệp.`);
      return;
    }

    try {
      const text = await file.text();
      const parsed = parseCSV(text);
      setCsvFileName(file.name);
      setCsvHeaders(parsed.headers);
      setCsvRawRows(parsed.rows);
      setSelectedAddressCol(parsed.detectedAddressColumn);
      // Tạo sẵn batchItems ban đầu
      const initialItems: BatchItemWithMeta[] = parsed.rows.map((row, idx) => ({
        id: `csv_row_${idx + 1}`,
        rowIndex: idx + 1,
        input: row[parsed.detectedAddressColumn] || '',
        status: 'processed' as const, // sẽ chuyển thành pending khi bắt đầu
        originalData: row,
      }));
      setBatchItems(initialItems);
      setProcessedCount(0);
      setTotalElapsedMs(0);
    } catch (err: any) {
      setErrorMessage(err.message || 'Lỗi khi đọc tệp CSV.');
    }
  };

  // Thay đổi cột địa chỉ được chọn trong CSV
  const handleAddressColChange = (newCol: string) => {
    setSelectedAddressCol(newCol);
    if (csvRawRows.length > 0) {
      const updated: BatchItemWithMeta[] = csvRawRows.map((row, idx) => ({
        id: `csv_row_${idx + 1}`,
        rowIndex: idx + 1,
        input: row[newCol] || '',
        status: 'processed' as const,
        originalData: row,
      }));
      setBatchItems(updated);
      setProcessedCount(0);
    }
  };

  // Chuẩn bị danh sách BatchItems từ Textarea
  const prepareItemsFromPaste = (): BatchItemWithMeta[] => {
    const lines = parsePastedLines(pastedText);
    return lines.map((line, idx) => ({
      id: `paste_row_${idx + 1}`,
      rowIndex: idx + 1,
      input: line,
      status: 'processed' as const,
      originalData: { dia_chi: line },
    }));
  };

  // --- TIẾN TRÌNH THỰC THI (CHUNK 20) ---

  const handleStartProcessing = async () => {
    setErrorMessage(null);

    let itemsToProcess: BatchItemWithMeta[] = [];
    if (inputMode === 'paste') {
      try {
        itemsToProcess = prepareItemsFromPaste();
        if (itemsToProcess.length === 0) {
          setErrorMessage('Vui lòng nhập hoặc dán ít nhất 1 dòng địa chỉ.');
          return;
        }
        setBatchItems(itemsToProcess);
      } catch (err: any) {
        setErrorMessage(err.message || 'Lỗi phân tích cú pháp danh sách dán.');
        return;
      }
    } else {
      if (batchItems.length === 0) {
        setErrorMessage('Chưa có dữ liệu từ tệp CSV. Vui lòng tải tệp lên trước.');
        return;
      }
      itemsToProcess = [...batchItems];
    }

    const sessionId = Date.now();
    setActiveSessionId(sessionId);
    setIsProcessing(true);
    setProcessedCount(0);
    setTotalElapsedMs(0);
    setCurrentPage(1);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    // Chia thành các chunk kích thước 20
    const total = itemsToProcess.length;
    let completed = 0;
    let cumulativeElapsed = 0;

    for (let i = 0; i < total; i += CHUNK_SIZE) {
      if (abortController.signal.aborted) break;

      const chunk = itemsToProcess.slice(i, i + CHUNK_SIZE);
      const apiInputs: BatchInput[] = chunk.map(it => ({ id: it.id, address: it.input }));

      try {
        const response = await normalizeBatch(apiInputs, abortController.signal);
        cumulativeElapsed += response.elapsed_ms || 0;

        // Cập nhật từng item theo kết quả trả về từ API
        const resultMap = new Map(response.items.map(it => [it.id, it]));

        itemsToProcess = itemsToProcess.map(it => {
          const resItem = resultMap.get(it.id);
          if (resItem) {
            return {
              ...it,
              status: resItem.status,
              result: resItem.result,
              elapsed_ms: resItem.elapsed_ms,
              error: resItem.error,
            };
          }
          return it;
        });

        completed += chunk.length;
        setBatchItems([...itemsToProcess]);
        setProcessedCount(completed);
        setTotalElapsedMs(cumulativeElapsed);
      } catch (err: any) {
        if (abortController.signal.aborted) {
          break;
        }
        // Gán trạng thái error cho chunk gặp sự cố
        itemsToProcess = itemsToProcess.map(it => {
          if (chunk.some(c => c.id === it.id)) {
            return {
              ...it,
              status: 'error' as const,
              error: { code: 'NETWORK_ERROR', message: err.message || 'Lỗi kết nối máy chủ' },
            };
          }
          return it;
        });
        completed += chunk.length;
        setBatchItems([...itemsToProcess]);
        setProcessedCount(completed);
      }
    }

    setIsProcessing(false);
    abortControllerRef.current = null;
  };

  // Hủy tiến trình
  const handleCancelProcessing = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsProcessing(false);
  };

  // Thử lại các dòng bị lỗi (Retry Failed Rows)
  const handleRetryFailed = async () => {
    const failedItems = batchItems.filter(it => it.status === 'error');
    if (failedItems.length === 0) return;

    setErrorMessage(null);
    setIsProcessing(true);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    let itemsCopy = [...batchItems];
    let cumulativeElapsed = totalElapsedMs;

    for (let i = 0; i < failedItems.length; i += CHUNK_SIZE) {
      if (abortController.signal.aborted) break;

      const chunk = failedItems.slice(i, i + CHUNK_SIZE);
      const apiInputs: BatchInput[] = chunk.map(it => ({ id: it.id, address: it.input }));

      try {
        const response = await normalizeBatch(apiInputs, abortController.signal);
        cumulativeElapsed += response.elapsed_ms || 0;
        const resultMap = new Map(response.items.map(it => [it.id, it]));

        itemsCopy = itemsCopy.map(it => {
          const resItem = resultMap.get(it.id);
          if (resItem) {
            return {
              ...it,
              status: resItem.status,
              result: resItem.result,
              elapsed_ms: resItem.elapsed_ms,
              error: resItem.error,
            };
          }
          return it;
        });

        setBatchItems([...itemsCopy]);
        setTotalElapsedMs(cumulativeElapsed);
      } catch (err: any) {
        if (abortController.signal.aborted) break;
      }
    }

    setIsProcessing(false);
    abortControllerRef.current = null;
  };

  // --- THỐNG KÊ STATE THỰC TẾ ---
  const counts = useMemo(() => {
    const total = batchItems.length;
    let processed = 0;
    let needs_review = 0;
    let error = 0;

    for (const it of batchItems) {
      if (it.status === 'processed') processed++;
      else if (it.status === 'needs_review') needs_review++;
      else if (it.status === 'error') error++;
    }

    return { total, processed, needs_review, error };
  }, [batchItems]);

  // Lọc và Tìm kiếm
  const filteredItems = useMemo(() => {
    return batchItems.filter(it => {
      // 1. Lọc theo trạng thái
      if (statusFilter !== 'all' && it.status !== statusFilter) {
        return false;
      }
      // 2. Tìm kiếm chuỗi
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const inInput = it.input.toLowerCase().includes(q);
        const inOutput = it.result?.dia_chi_chuan?.toLowerCase().includes(q) || false;
        const inCodes = (it.result?.ma_xa || '').includes(q) || (it.result?.ma_tinh || '').includes(q);
        const inWarnings = it.result?.canh_bao?.some(w => w.toLowerCase().includes(q)) || false;
        return inInput || inOutput || inCodes || inWarnings;
      }
      return true;
    });
  }, [batchItems, statusFilter, searchQuery]);

  // Phân trang dữ liệu
  const totalPages = Math.max(1, Math.ceil(filteredItems.length / pageSize));
  const paginatedItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredItems.slice(start, start + pageSize);
  }, [filteredItems, currentPage, pageSize]);

  // Xử lý xuất dữ liệu
  const handleExportCsv = (scope: 'all' | 'filtered') => {
    const itemsToExport = scope === 'filtered' ? filteredItems : batchItems;
    exportToCSV(itemsToExport, csvHeaders, `address_may_cry_${scope}_${Date.now()}.csv`);
  };

  const handleExportJson = (scope: 'all' | 'filtered') => {
    const itemsToExport = scope === 'filtered' ? filteredItems : batchItems;
    exportToJSON(itemsToExport, `address_may_cry_${scope}_${Date.now()}.json`);
  };

  return (
    <div className={styles.batchWorkspace}>
      {/* 1. Header & Lead Question */}
      <section className={styles.headerSection}>
        <div className={styles.titleRow}>
          <h1 className={styles.mainTitle}>Không gian xử lý hàng loạt (Batch Workspace)</h1>
          <span className={styles.targetTag}>Mốc hành chính: 01/07/2025</span>
        </div>
        <p className={styles.leadQuestion}>
          Dòng nào cần kiểm tra và xuất kết quả thế nào? Xử lý danh sách địa chỉ tự do, đối soát cảnh báo chia tách xã và xuất dữ liệu an toàn.
        </p>
      </section>

      {/* 2. Tabs chuyển đổi luồng nhập */}
      <nav className={styles.modeTabs} aria-label="Phương thức nhập địa chỉ">
        <button
          type="button"
          className={`${styles.tabBtn} ${inputMode === 'paste' ? styles.activeTab : ''}`}
          onClick={() => { setInputMode('paste'); setErrorMessage(null); }}
        >
          Dán danh sách nhiều dòng
        </button>
        <button
          type="button"
          className={`${styles.tabBtn} ${inputMode === 'csv' ? styles.activeTab : ''}`}
          onClick={() => { setInputMode('csv'); setErrorMessage(null); }}
        >
          Kéo / Chọn tệp CSV (UTF-8)
        </button>
      </nav>

      {/* 3. Thẻ nhập liệu */}
      <section className={styles.inputCard}>
        {inputMode === 'paste' ? (
          <div className={styles.textareaWrapper}>
            <textarea
              className={styles.addressTextarea}
              placeholder="Dán mỗi dòng một địa chỉ cần chuẩn hóa (tối đa 1.000 dòng, mỗi dòng tối đa 2.048 ký tự)...&#10;Ví dụ:&#10;268/10 NGUYỄN VĂN LINH, PHƯỜNG XUÂN KHÁNH, CẦN THƠ&#10;45 XÔ VIẾT NGHỆ TĨNH, P.AN CƯ, NINH KIỀU, CẦN THƠ"
              value={pastedText}
              onChange={e => setPastedText(e.target.value)}
              disabled={isProcessing}
              rows={6}
            />
            <div className={styles.textareaMeta}>
              <span>
                Số dòng hiện tại:{' '}
                <strong>{pastedText ? pastedText.split(/\r\n|\n|\r/).filter(l => l.trim()).length : 0}</strong> /{' '}
                {CSV_LIMITS.MAX_ROWS.toLocaleString('vi-VN')} dòng
              </span>
              <div className={styles.sampleChips}>
                <span>Mẫu thử nhanh:</span>
                <button type="button" className={styles.chipBtn} onClick={() => handleLoadSample(SAMPLE_ADDRESSES[0].address)}>
                  Cần Thơ (Sáp nhập)
                </button>
                <button type="button" className={styles.chipBtn} onClick={() => handleLoadSample(SAMPLE_ADDRESSES[1].address)}>
                  Xô Viết Nghệ Tĩnh
                </button>
                <button type="button" className={styles.chipBtn} onClick={() => handleLoadSample(SAMPLE_ADDRESSES[2].address)}>
                  Dịch Vọng (Chia tách)
                </button>
                <button type="button" className={styles.chipBtn} onClick={handleLoadAllSamples}>
                  Nạp tất cả 8 mẫu
                </button>
                {pastedText && (
                  <button type="button" className={styles.chipBtn} onClick={() => setPastedText('')}>
                    Xóa trắng
                  </button>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div
              className={`${styles.dropzone} ${isDragOver ? styles.dragOver : ''}`}
              onDragOver={e => { e.preventDefault(); setIsDragOver(true); }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={async e => {
                e.preventDefault();
                setIsDragOver(false);
                const file = e.dataTransfer.files?.[0];
                if (file) await processUploadedFile(file);
              }}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }}
            >
              <div className={styles.dropzoneIcon}>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <p className={styles.dropzoneTitle}>
                {csvFileName ? `Đã nạp: ${csvFileName}` : 'Kéo thả tệp CSV vào đây hoặc bấm để chọn'}
              </p>
              <p className={styles.dropzoneSub}>
                Hỗ trợ UTF-8 có/không BOM, dấu phẩy/chấm phẩy/tab, tối đa 5MB và 1.000 dòng.
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,text/csv"
                className={styles.hiddenFileInput}
                onChange={handleFileChange}
              />
            </div>

            {/* Cấu hình cột sau khi đọc CSV */}
            {csvHeaders.length > 0 && (
              <div className={styles.csvPreviewCard}>
                <div className={styles.csvMetaRow}>
                  <span>
                    Tổng cộng: <strong>{csvRawRows.length.toLocaleString('vi-VN')}</strong> dòng dữ liệu ·{' '}
                    <strong>{csvHeaders.length}</strong> cột
                  </span>
                  <div className={styles.columnSelectorGroup}>
                    <label htmlFor="address-col-select" style={{ fontWeight: 600 }}>Cột chứa địa chỉ:</label>
                    <select
                      id="address-col-select"
                      className={styles.columnSelect}
                      value={selectedAddressCol}
                      onChange={e => handleAddressColChange(e.target.value)}
                      disabled={isProcessing}
                    >
                      {csvHeaders.map(h => (
                        <option key={h} value={h}>{h}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button type="button" className={styles.chipBtn} onClick={handleDownloadSampleCsv}>
                Tải tệp CSV mẫu chuẩn (.csv)
              </button>
            </div>
          </div>
        )}

        {/* Thông báo lỗi nếu có */}
        {errorMessage && (
          <div style={{
            padding: '10px 14px',
            borderRadius: 'var(--b-radius-control)',
            backgroundColor: 'var(--b-pill-negative-bg)',
            color: 'var(--b-negative)',
            fontSize: 13,
            fontWeight: 500
          }}>
            {errorMessage}
          </div>
        )}

        {/* Nút hành động chính */}
        <div className={styles.actionRow}>
          <div className={styles.btnGroup}>
            {!isProcessing ? (
              <button
                type="button"
                className={styles.primaryBtn}
                onClick={handleStartProcessing}
                disabled={inputMode === 'paste' ? !pastedText.trim() : csvRawRows.length === 0}
              >
                Bắt đầu chuẩn hóa danh sách
              </button>
            ) : (
              <button
                type="button"
                className={styles.cancelBtn}
                onClick={handleCancelProcessing}
              >
                Hủy dừng tiến trình
              </button>
            )}

            {counts.error > 0 && !isProcessing && (
              <button
                type="button"
                className={styles.secondaryBtn}
                onClick={handleRetryFailed}
              >
                Thử lại {counts.error} dòng lỗi
              </button>
            )}
          </div>

          {/* Nhóm xuất tệp */}
          {batchItems.length > 0 && (
            <div className={styles.btnGroup}>
              <button
                type="button"
                className={styles.secondaryBtn}
                onClick={() => handleExportCsv(statusFilter === 'all' && !searchQuery ? 'all' : 'filtered')}
              >
                Xuất CSV (UTF-8 BOM)
              </button>
              <button
                type="button"
                className={styles.secondaryBtn}
                onClick={() => handleExportJson(statusFilter === 'all' && !searchQuery ? 'all' : 'filtered')}
              >
                Xuất JSON
              </button>
            </div>
          )}
        </div>
      </section>

      {/* 3b. Hướng dẫn nghiệp vụ trạng thái ban đầu (Khi chưa có danh sách xử lý) */}
      {batchItems.length === 0 && (
        <section style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 'var(--b-gap)',
          marginTop: 4
        }}>
          <div style={{
            backgroundColor: 'var(--b-surface)',
            border: '1px solid var(--b-border)',
            borderRadius: 'var(--b-radius-card)',
            padding: '18px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: 8
          }}>
            <span className={styles.guidanceTag}>
              Mốc chuẩn hóa 2025
            </span>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: 'var(--b-text)' }}>
              Tự động liên kết sáp nhập
            </h2>
            <p style={{ fontSize: 13, color: 'var(--b-muted)', lineHeight: 1.6, margin: 0 }}>
              Hệ thống xử lý linh hoạt địa chỉ chứa mốc cũ lẫn mới trong cùng câu mà không bắt chọn mốc nguồn. Các xã/phường sáp nhập mốc 01/07/2025 được quy về mã đơn vị hành chính mới nhất.
            </p>
          </div>

          <div style={{
            backgroundColor: 'var(--b-surface)',
            border: '1px solid var(--b-border)',
            borderRadius: 'var(--b-radius-card)',
            padding: '18px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: 8
          }}>
            <span className={styles.guidanceTag}>
              Tiến trình Chunk 20
            </span>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: 'var(--b-text)' }}>
              Minh bạch & Kiểm soát
            </h2>
            <p style={{ fontSize: 13, color: 'var(--b-muted)', lineHeight: 1.6, margin: 0 }}>
              Dữ liệu được gửi theo từng đợt 20 dòng để bảo đảm an toàn bộ nhớ và đo đạc độ trễ thực tế. Bạn có thể nhấn dừng bất cứ lúc nào mà không làm mất các dòng đã xử lý xong.
            </p>
          </div>

          <div style={{
            backgroundColor: 'var(--b-surface)',
            border: '1px solid var(--b-border)',
            borderRadius: 'var(--b-radius-card)',
            padding: '18px 20px',
            display: 'flex',
            flexDirection: 'column',
            gap: 8
          }}>
            <span className={styles.guidanceTag}>
              Xuất tệp an toàn
            </span>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, color: 'var(--b-text)' }}>
              Bảo vệ CSV Formula Injection
            </h2>
            <p style={{ fontSize: 13, color: 'var(--b-muted)', lineHeight: 1.6, margin: 0 }}>
              Tệp xuất CSV giữ nguyên toàn bộ cột gốc, thêm 6 trường kết quả và mã hành chính. Tự động vô hiệu hóa ký tự công thức (=, +, -, @) để chống tấn công bảng tính Excel.
            </p>
          </div>
        </section>
      )}

      {/* 4. Tiến độ thời gian thực (Chunk 20) */}
      {(isProcessing || processedCount > 0) && (
        <section className={styles.progressContainer}>
          <div className={styles.progressBarTrack}>
            <div
              className={styles.progressBarFill}
              style={{ width: `${counts.total > 0 ? (processedCount / counts.total) * 100 : 0}%` }}
            />
          </div>
          <div className={styles.progressStatsRow}>
            <span>
              Tiến độ: <strong>{processedCount}</strong> / {counts.total} dòng ({counts.total > 0 ? Math.round((processedCount / counts.total) * 100) : 0}%)
              {isProcessing && ' · Đang gửi từng gói 20 địa chỉ...'}
            </span>
            <span>
              Thời gian xử lý: <strong>{totalElapsedMs.toLocaleString('vi-VN')} ms</strong>
            </span>
          </div>
        </section>
      )}

      {/* 5. Dải đếm trạng thái thực chất (KPIs) */}
      {batchItems.length > 0 && (
        <section className={styles.kpiStrip}>
          <div className={styles.kpiCard}>
            <span className={styles.kpiLabel}>Tổng số dòng</span>
            <span className={styles.kpiValue}>{counts.total}</span>
          </div>
          <div className={`${styles.kpiCard} ${styles.kpiWarning}`}>
            <span className={styles.kpiLabel}>Cần kiểm tra (Review)</span>
            <span className={styles.kpiValue}>{counts.needs_review}</span>
          </div>
          <div className={`${styles.kpiCard} ${styles.kpiPositive}`}>
            <span className={styles.kpiLabel}>Đã xử lý (Processed)</span>
            <span className={styles.kpiValue}>{counts.processed}</span>
          </div>
          <div className={`${styles.kpiCard} ${styles.kpiNegative}`}>
            <span className={styles.kpiLabel}>Lỗi kết nối / định dạng</span>
            <span className={styles.kpiValue}>{counts.error}</span>
          </div>
        </section>
      )}

      {/* 6. Thanh công cụ Lọc & Tìm kiếm */}
      {batchItems.length > 0 && (
        <section className={styles.toolbarCard}>
          <div className={styles.filterTabs}>
            <button
              type="button"
              className={`${styles.filterBtn} ${statusFilter === 'all' ? styles.activeFilter : ''}`}
              onClick={() => { setStatusFilter('all'); setCurrentPage(1); }}
            >
              Tất cả <span className={styles.filterCountBadge}>{counts.total}</span>
            </button>
            <button
              type="button"
              className={`${styles.filterBtn} ${statusFilter === 'needs_review' ? styles.activeFilter : ''}`}
              onClick={() => { setStatusFilter('needs_review'); setCurrentPage(1); }}
            >
              Cần kiểm tra <span className={styles.filterCountBadge}>{counts.needs_review}</span>
            </button>
            <button
              type="button"
              className={`${styles.filterBtn} ${statusFilter === 'processed' ? styles.activeFilter : ''}`}
              onClick={() => { setStatusFilter('processed'); setCurrentPage(1); }}
            >
              Đã xử lý <span className={styles.filterCountBadge}>{counts.processed}</span>
            </button>
            {counts.error > 0 && (
              <button
                type="button"
                className={`${styles.filterBtn} ${statusFilter === 'error' ? styles.activeFilter : ''}`}
                onClick={() => { setStatusFilter('error'); setCurrentPage(1); }}
              >
                Lỗi <span className={styles.filterCountBadge}>{counts.error}</span>
              </button>
            )}
          </div>

          <div className={styles.searchBox}>
            <span className={styles.searchIcon}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </span>
            <input
              type="text"
              className={styles.searchInput}
              placeholder="Tìm theo địa chỉ, mã xã, cảnh báo..."
              value={searchQuery}
              onChange={e => { setSearchQuery(e.target.value); setCurrentPage(1); }}
            />
          </div>
        </section>
      )}

      {/* 7. Bảng kết quả (Desktop) & Thẻ kết quả (Mobile) */}
      {batchItems.length > 0 && (
        <section className={styles.tableContainer}>
          {/* Desktop Table View */}
          <div className={styles.tableScrollArea}>
            <table className={styles.dataTable}>
              <thead>
                <tr>
                  <th style={{ width: 48, textAlign: 'center' }}>STT</th>
                  <th>Địa chỉ đầu vào</th>
                  <th>Địa chỉ chuẩn hóa (01/07/2025)</th>
                  <th style={{ width: 140 }}>Trạng thái</th>
                  <th style={{ width: 160 }}>Cảnh báo / Ghi chú</th>
                  <th style={{ width: 70, textAlign: 'right' }}>Độ trễ</th>
                </tr>
              </thead>
              <tbody>
                {paginatedItems.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: 'center', padding: '32px 14px', color: 'var(--b-muted)' }}>
                      Không có dòng nào phù hợp với bộ lọc hoặc từ khóa tìm kiếm.
                    </td>
                  </tr>
                ) : (
                  paginatedItems.map(item => (
                    <tr
                      key={item.id}
                      className={`${styles.clickableRow} ${inspectingItem?.id === item.id ? styles.selectedRow : ''}`}
                      onClick={() => setInspectingItem(item)}
                    >
                      <td style={{ textAlign: 'center' }} className={styles.monoCell}>
                        {item.rowIndex}
                      </td>
                      <td style={{ maxWidth: 300, wordBreak: 'break-word' }}>
                        {item.input}
                      </td>
                      <td style={{ maxWidth: 340, wordBreak: 'break-word', fontWeight: 500 }}>
                        {item.result?.dia_chi_chuan || (
                          <span style={{ color: 'var(--b-muted)' }}>
                            {item.status === 'error' ? `[Lỗi: ${item.error?.message || 'Không thể xử lý'}]` : 'Chưa xử lý'}
                          </span>
                        )}
                      </td>
                      <td>
                        <span className={`${styles.statusBadge} ${
                          item.status === 'processed' ? styles.statusProcessed :
                          item.status === 'needs_review' ? styles.statusReview :
                          item.status === 'error' ? styles.statusError : styles.statusPending
                        }`}>
                          {item.status === 'processed' ? 'Đã xử lý' :
                           item.status === 'needs_review' ? 'Cần duyệt' :
                           item.status === 'error' ? 'Lỗi' : 'Chờ xử lý'}
                        </span>
                      </td>
                      <td>
                        {item.result?.canh_bao && item.result.canh_bao.length > 0 ? (
                          <div className={styles.warningTagList}>
                            {item.result.canh_bao.map(w => (
                              <span key={w} className={styles.warningTag} title={WARNING_TRANSLATIONS[w]?.desc || w}>
                                {WARNING_TRANSLATIONS[w]?.label || w}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span style={{ color: 'var(--b-muted)', fontSize: 12 }}>-</span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }} className={styles.monoCell}>
                        {item.elapsed_ms != null ? `${item.elapsed_ms}ms` : '-'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Mobile Cards View (< 768px) */}
          <div className={styles.mobileCardsContainer}>
            {paginatedItems.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px 12px', color: 'var(--b-muted)' }}>
                Không tìm thấy dòng phù hợp.
              </div>
            ) : (
              paginatedItems.map(item => (
                <div
                  key={item.id}
                  className={`${styles.mobileCard} ${inspectingItem?.id === item.id ? styles.selectedMobileCard : ''}`}
                  onClick={() => setInspectingItem(item)}
                >
                  <div className={styles.mobileCardHeader}>
                    <span className={styles.monoCell}>#{item.rowIndex}</span>
                    <span className={`${styles.statusBadge} ${
                      item.status === 'processed' ? styles.statusProcessed :
                      item.status === 'needs_review' ? styles.statusReview :
                      item.status === 'error' ? styles.statusError : styles.statusPending
                    }`}>
                      {item.status === 'processed' ? 'Đã xử lý' :
                       item.status === 'needs_review' ? 'Cần duyệt' :
                       item.status === 'error' ? 'Lỗi' : 'Chờ'}
                    </span>
                  </div>
                  <div className={styles.mobileCardInput}>{item.input}</div>
                  {item.result?.dia_chi_chuan && (
                    <div className={styles.mobileCardOutput}>{item.result.dia_chi_chuan}</div>
                  )}
                  {item.result?.canh_bao && item.result.canh_bao.length > 0 && (
                    <div className={styles.warningTagList}>
                      {item.result.canh_bao.map(w => (
                        <span key={w} className={styles.warningTag}>
                          {WARNING_TRANSLATIONS[w]?.label || w}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Thanh phân trang */}
          <div className={styles.paginationBar}>
            <div>
              Hiển thị <strong>{paginatedItems.length}</strong> / <strong>{filteredItems.length}</strong> dòng phù hợp
              {batchItems.length !== filteredItems.length && ` (trong tổng số ${batchItems.length} dòng)`}
            </div>
            <div className={styles.pageControls}>
              <button
                type="button"
                className={styles.pageBtn}
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              >
                Trước
              </button>
              <span>Trang {currentPage} / {totalPages}</span>
              <button
                type="button"
                className={styles.pageBtn}
                disabled={currentPage >= totalPages}
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              >
                Sau
              </button>
              <select
                className={styles.columnSelect}
                style={{ minHeight: 32, padding: '2px 8px', fontSize: 12 }}
                value={pageSize}
                onChange={e => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
              >
                <option value={25}>25 dòng/trang</option>
                <option value={50}>50 dòng/trang</option>
                <option value={100}>100 dòng/trang</option>
              </select>
            </div>
          </div>
        </section>
      )}

      {/* 8. Ngăn xem chi tiết chuyên sâu (Detail Drawer Inspector) */}
      {inspectingItem && (
        <div className={styles.drawerBackdrop} onClick={() => setInspectingItem(null)}>
          <aside
            className={styles.drawerPanel}
            onClick={e => e.stopPropagation()}
            role="dialog"
            aria-label="Chi tiết chuẩn hóa địa chỉ"
          >
            <div className={styles.drawerHeader}>
              <h3 className={styles.drawerTitle}>
                Dòng #{inspectingItem.rowIndex} · Chi tiết chuẩn hóa
              </h3>
              <button
                type="button"
                className={styles.closeDrawerBtn}
                onClick={() => setInspectingItem(null)}
                title="Đóng bảng chi tiết"
                aria-label="Đóng bảng chi tiết"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div className={styles.drawerBody}>
              {/* Nút kiểm tra ở chế độ đơn */}
              {onInspect && (
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    type="button"
                    className={styles.secondaryBtn}
                    onClick={() => {
                      onInspect(inspectingItem);
                      setInspectingItem(null);
                    }}
                  >
                    Kiểm tra ở chế độ đơn (Single Mode) →
                  </button>
                </div>
              )}

              {/* Trạng thái & Độ trễ */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className={`${styles.statusBadge} ${
                  inspectingItem.status === 'processed' ? styles.statusProcessed :
                  inspectingItem.status === 'needs_review' ? styles.statusReview :
                  inspectingItem.status === 'error' ? styles.statusError : styles.statusPending
                }`} style={{ fontSize: 12, padding: '4px 12px' }}>
                  {inspectingItem.status === 'processed' ? 'Đã xử lý chuẩn hóa' :
                   inspectingItem.status === 'needs_review' ? 'Cần rà soát (Có cảnh báo / mơ hồ)' :
                   inspectingItem.status === 'error' ? 'Lỗi xử lý' : 'Đang chờ'}
                </span>
                <span className={styles.monoCell}>
                  {inspectingItem.elapsed_ms != null ? `Độ trễ: ${inspectingItem.elapsed_ms}ms` : ''}
                </span>
              </div>

              {/* Đầu vào gốc */}
              <div className={styles.detailSection}>
                <span className={styles.sectionLabel}>Đầu vào thô (Raw Input)</span>
                <div className={styles.detailValueBox}>{inspectingItem.input}</div>
              </div>

              {/* Đầu ra chuẩn hóa */}
              <div className={styles.detailSection}>
                <span className={styles.sectionLabel}>Địa chỉ chuẩn hóa (Mốc 01/07/2025)</span>
                <div className={styles.detailValueBox} style={{ fontWeight: 600, color: 'var(--b-accent)' }}>
                  {inspectingItem.result?.dia_chi_chuan || (
                    <span style={{ color: 'var(--b-muted)' }}>Chưa có kết quả hoặc gặp lỗi</span>
                  )}
                </div>
              </div>

              {/* 6 trường cốt lõi */}
              {inspectingItem.result && (
                <div className={styles.detailSection}>
                  <span className={styles.sectionLabel}>6 Trường cốt lõi & Mã hành chính</span>
                  <div className={styles.fieldGrid}>
                    <div className={styles.fieldItem}>
                      <span className={styles.fieldItemLabel}>Số nhà</span>
                      <span className={styles.fieldItemValue}>{inspectingItem.result.so_nha || '-'}</span>
                    </div>
                    <div className={styles.fieldItem}>
                      <span className={styles.fieldItemLabel}>Ngõ / Ngách / Hẻm</span>
                      <span className={styles.fieldItemValue}>{inspectingItem.result.ngo_ngach_hem || '-'}</span>
                    </div>
                    <div className={styles.fieldItem}>
                      <span className={styles.fieldItemLabel}>Đường / Phố</span>
                      <span className={styles.fieldItemValue}>{inspectingItem.result.duong || '-'}</span>
                    </div>
                    <div className={styles.fieldItem}>
                      <span className={styles.fieldItemLabel}>Thôn / Xóm / Ấp</span>
                      <span className={styles.fieldItemValue}>{inspectingItem.result.thon_xom || '-'}</span>
                    </div>
                    <div className={styles.fieldItem}>
                      <span className={styles.fieldItemLabel}>Xã / Phường (Mã)</span>
                      <span className={styles.fieldItemValue}>
                        {inspectingItem.result.xa_phuong || '-'} {inspectingItem.result.ma_xa && `(${inspectingItem.result.ma_xa})`}
                      </span>
                    </div>
                    <div className={styles.fieldItem}>
                      <span className={styles.fieldItemLabel}>Tỉnh / Thành phố (Mã)</span>
                      <span className={styles.fieldItemValue}>
                        {inspectingItem.result.tinh || '-'} {inspectingItem.result.ma_tinh && `(${inspectingItem.result.ma_tinh})`}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Cảnh báo và lý do rà soát */}
              {inspectingItem.result?.canh_bao && inspectingItem.result.canh_bao.length > 0 && (
                <div className={styles.detailSection}>
                  <span className={styles.sectionLabel}>Lý do cần kiểm tra ({inspectingItem.result.canh_bao.length})</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {inspectingItem.result.canh_bao.map(w => {
                      const info = WARNING_TRANSLATIONS[w];
                      return (
                        <div key={w} style={{
                          padding: '10px 12px',
                          borderRadius: 'var(--b-radius-control)',
                          backgroundColor: 'var(--b-pill-warning-bg)',
                          border: '1px solid var(--b-warning)',
                          color: 'var(--b-pill-warning-ink)'
                        }}>
                          <div style={{ fontWeight: 600, fontSize: 13 }}>{info?.label || w}</div>
                          {info?.desc && <div style={{ fontSize: 12, marginTop: 2, opacity: 0.9 }}>{info.desc}</div>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Ứng viên xã mới nếu có */}
              {inspectingItem.result?.xa_moi_ung_vien && inspectingItem.result.xa_moi_ung_vien.length > 0 && (
                <div className={styles.detailSection}>
                  <span className={styles.sectionLabel}>Ứng viên xã mới khả dĩ (Sáp nhập/chia tách)</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {inspectingItem.result.xa_moi_ung_vien.map((cand, cIdx) => (
                      <div key={cIdx} style={{
                        padding: '8px 12px',
                        borderRadius: 'var(--b-radius-control)',
                        backgroundColor: 'var(--b-surface)',
                        border: '1px solid var(--b-border)',
                        fontSize: 13
                      }}>
                        Mã: <strong>{cand.ma || cand.ma_xa}</strong> · Tên: <strong>{cand.ten || cand.xa_phuong}</strong>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Thành phần chưa phân loại */}
              {inspectingItem.result?.phan_chua_phan_loai && (
                <div className={styles.detailSection}>
                  <span className={styles.sectionLabel}>Phần chưa phân loại (Bảo toàn)</span>
                  <div className={styles.detailValueBox} style={{ color: 'var(--b-muted)' }}>
                    {inspectingItem.result.phan_chua_phan_loai}
                  </div>
                </div>
              )}

              {/* Debug JSON Disclosure */}
              <details style={{
                border: '1px solid var(--b-border)',
                borderRadius: 'var(--b-radius-control)',
                padding: '10px 12px',
                fontSize: 12,
                color: 'var(--b-muted)',
                backgroundColor: 'var(--b-surface)'
              }}>
                <summary style={{ cursor: 'pointer', fontWeight: 600 }}>Xem dữ liệu phản hồi kỹ thuật (JSON)</summary>
                <pre style={{
                  marginTop: 10,
                  padding: 10,
                  backgroundColor: 'var(--b-raised)',
                  borderRadius: 4,
                  overflowX: 'auto',
                  fontSize: 11,
                  fontFamily: 'var(--b-font-mono)'
                }}>
                  {JSON.stringify(inspectingItem, null, 2)}
                </pre>
              </details>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
