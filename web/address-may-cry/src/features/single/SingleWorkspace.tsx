import React, { useState, useRef, useEffect, useCallback } from 'react';
import type { NormalizeResponse, AddressResult } from '../../shared/contracts';
import { normalizeAddress } from '../../shared/api';
import {
  IconCopy,
  IconCheck,
  IconAlertTriangle,
  IconCheckCircle,
  IconRefresh,
  IconX,
  IconCornerDownLeft,
  IconDownload,
  IconClipboard,
  IconChevronDown,
  IconLayers,
  IconHistory
} from '../../components/Icons';

const MAX_CHARS = 2048;

// Curated realistic samples from train/knowledge (no NLP test set data)
const SAMPLE_ADDRESSES = [
  {
    label: 'Cần Thơ (Viết tắt & Tuyến đường)',
    value: '45 XÔ VIẾT NGHỆ TĨNH P.AN CƯ- NINH KIỀU- CẦN THƠ'
  },
  {
    label: 'Cần Thơ (Số nhà & Phường)',
    value: '313, NGUYỄN VĂN LINH, PHƯỜNG AN KHÁNH, QUẬN NINH KIỀU, THÀNH PHỐ CẦN THƠ'
  },
  {
    label: 'Cần Thơ (Ngõ ngách & Viết tắt CMT8)',
    value: '110A CMT8, Phường An Thới, Quận Bình Thủy, TP Cần Thơ'
  },
  {
    label: 'Hà Nội (Xã cũ chuyển đổi 2025)',
    value: 'Số 42, Phố Bồ Đề, Phường Bồ Đề, Quận Long Biên, Hà Nội'
  },
  {
    label: 'Nông thôn (Thôn xóm cấp xã)',
    value: 'Thôn 4, Xã Hoằng Lộc, Huyện Hoằng Hóa, Tỉnh Thanh Hóa'
  }
];

// Human-readable warning messages
const WARNING_TRANSLATIONS: Record<string, { label: string; desc: string }> = {
  xa_bi_chia: {
    label: 'Xã bị chia tách',
    desc: 'Đơn vị hành chính cấp xã cũ được phân chia thành nhiều xã/phường mới theo đề án cải cách 01/07/2025.'
  },
  nhieu_cach_hieu: {
    label: 'Nhiều cách hiểu',
    desc: 'Tồn tại nhiều phương án hành chính có độ tương đồng ngữ cảnh cao trong không gian tìm kiếm.'
  },
  mo_ho_moc_cu_moi: {
    label: 'Mơ hồ mốc cũ/mới',
    desc: 'Chuỗi đầu vào chứa tên gọi hành chính xuất hiện ở cả danh mục cũ và danh mục mới với quan hệ khác nhau.'
  },
  ten_duong_tham_chieu_train_chua_xac_minh: {
    label: 'Tên đường tham chiếu',
    desc: 'Tên đường được nhận diện theo tập dữ liệu huấn luyện, chưa được chứng thực độc lập từ từ điển chuẩn.'
  },
  ten_chi_tiet_chua_xac_minh_dau: {
    label: 'Chưa xác minh dấu',
    desc: 'Tên đường hoặc thôn xóm gốc không có dấu tiếng Việt đầy đủ, hệ thống không tự ý đoán dấu khi thiếu cơ sở.'
  },
  so_nha_can_duyet: {
    label: 'Số nhà phức hợp',
    desc: 'Số nhà chứa ký tự phân tách đặc biệt (/, -, ;) cần người dùng rà soát thực tế.'
  },
  thieu_xa: {
    label: 'Khuyết thông tin xã/phường',
    desc: 'Không nhận diện được đơn vị hành chính cấp xã/phường từ văn bản đầu vào.'
  },
  thieu_tinh: {
    label: 'Khuyết thông tin tỉnh/thành',
    desc: 'Không nhận diện được đơn vị hành chính cấp tỉnh/thành phố.'
  },
  mau_thuan_hanh_chinh: {
    label: 'Mâu thuẫn hành chính',
    desc: 'Tồn tại xung đột giữa các cấp hành chính được phát hiện trong chuỗi.'
  }
};

interface HistoryItem {
  timestamp: number;
  input: string;
  response: NormalizeResponse;
}

export const SingleWorkspace: React.FC = () => {
  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<NormalizeResponse | null>(null);
  const [elapsedTimer, setElapsedTimer] = useState<number>(0);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [showDiagnostics, setShowDiagnostics] = useState<boolean>(false);
  const [sessionHistory, setSessionHistory] = useState<HistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState<boolean>(false);

  const abortControllerRef = useRef<AbortController | null>(null);
  const timerIntervalRef = useRef<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Copy helper with feedback
  const handleCopy = useCallback(async (text: string, fieldId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(fieldId);
      setTimeout(() => setCopiedField(null), 2000);
    } catch {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopiedField(fieldId);
      setTimeout(() => setCopiedField(null), 2000);
    }
  }, []);

  // Paste helper
  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setInput(text.slice(0, MAX_CHARS));
        if (textareaRef.current) textareaRef.current.focus();
      }
    } catch {
      if (textareaRef.current) textareaRef.current.focus();
    }
  }, []);

  // Clear input
  const handleClear = useCallback(() => {
    setInput('');
    setError(null);
    if (textareaRef.current) textareaRef.current.focus();
  }, []);

  // Main Normalize action
  const handleNormalize = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed) {
      setError('Vui lòng nhập địa chỉ cần chuẩn hóa.');
      return;
    }
    if (trimmed.length > MAX_CHARS) {
      setError(`Địa chỉ vượt quá giới hạn cho phép (${MAX_CHARS} ký tự).`);
      return;
    }

    // Cancel existing flight
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    setError(null);
    setElapsedTimer(0);

    const startTime = performance.now();
    timerIntervalRef.current = window.setInterval(() => {
      setElapsedTimer(Math.round(performance.now() - startTime));
    }, 20);

    try {
      const res = await normalizeAddress(trimmed, controller.signal);
      setResponse(res);
      // Save to memory session history
      setSessionHistory((prev) => [
        { timestamp: Date.now(), input: trimmed, response: res },
        ...prev.slice(0, 9)
      ]);
    } catch (err: unknown) {
      if ((err as Error).name === 'AbortError') return;
      setError((err as Error).message || 'Không thể chuẩn hóa địa chỉ. Vui lòng thử lại.');
    } finally {
      setLoading(false);
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
    }
  }, [input]);

  // Keyboard shortcut Ctrl/Cmd + Enter
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleNormalize();
    }
  };

  // Download diagnostic JSON
  const handleDownloadJson = () => {
    if (!response) return;
    const blob = new Blob([JSON.stringify(response, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `dia_chi_chuan_hoa_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) abortControllerRef.current.abort();
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, []);

  const result = response?.result;

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 16px' }}>
      {/* Editorial Introduction */}
      <div style={{ marginBottom: 24, textAlign: 'left' }}>
        <h1 style={{
          fontSize: 'clamp(22px, 3.5vw, 32px)',
          fontWeight: 700,
          letterSpacing: '-0.025em',
          color: 'var(--text)',
          lineHeight: 1.25,
          marginBottom: 6
        }}>
          Tháo gỡ & Chuẩn hóa Địa chỉ
        </h1>
        <p style={{
          fontSize: 14,
          color: 'var(--muted)',
          maxWidth: 680,
          lineHeight: 1.5
        }}>
          Chuyển đổi chuỗi địa chỉ hỗn hợp (viết tắt, đảo thứ tự, lẫn mốc cũ và mới) về đúng 6 trường cấu trúc và mã hành chính chính thức áp dụng từ ngày <strong>01/07/2025</strong>.
        </p>
      </div>

      {/* Main Grid: Input Column & Output Column */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 480px), 1fr))',
        gap: 'var(--gap)',
        alignItems: 'stretch'
      }}>
        {/* LEFT COLUMN: Input Workspace */}
        <section style={{
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-card)',
          padding: 20,
          display: 'flex',
          flexDirection: 'column'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 10
          }}>
            <label
              htmlFor="address-input"
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: 'var(--text)',
                textTransform: 'uppercase',
                letterSpacing: '0.04em'
              }}
            >
              Chuỗi địa chỉ gốc
            </label>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <button
                type="button"
                onClick={handlePaste}
                title="Dán từ bộ nhớ tạm"
                style={{
                  fontSize: 13,
                  color: 'var(--muted)',
                  padding: '5px 10px',
                  borderRadius: 6,
                  border: '1px solid var(--border)',
                  backgroundColor: 'var(--raised)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4
                }}
              >
                <IconClipboard size={14} /> Dán
              </button>
              {input && (
                <button
                  type="button"
                  onClick={handleClear}
                  title="Xóa nội dung"
                  style={{
                    fontSize: 13,
                    color: 'var(--muted)',
                    padding: '5px 10px',
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                    backgroundColor: 'var(--raised)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4
                  }}
                >
                  <IconX size={14} /> Xóa
                </button>
              )}
            </div>
          </div>

          {/* Textarea */}
          <div style={{ position: 'relative' }}>
            <textarea
              id="address-input"
              ref={textareaRef}
              rows={4}
              value={input}
              onChange={(e) => setInput(e.target.value.slice(0, MAX_CHARS))}
              onKeyDown={handleKeyDown}
              placeholder="Ví dụ: 313 Nguyễn Văn Linh, P. An Khánh, Q. Ninh Kiều, TP Cần Thơ..."
              disabled={loading}
              style={{
                width: '100%',
                padding: '12px 14px',
                fontSize: 14,
                lineHeight: 1.6,
                borderRadius: 'var(--radius-control)',
                resize: 'vertical',
                minHeight: 110,
                backgroundColor: 'var(--raised)',
                border: '1px solid var(--border)',
                outline: 'none',
                color: 'var(--text)'
              }}
            />
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: 6,
              fontSize: 13,
              color: 'var(--muted)'
            }}>
              <span>Nhấn <code>Ctrl + Enter</code> để xử lý nhanh</span>
              <span style={{ fontVariantNumeric: 'tabular-nums' }}>
                {input.length} / {MAX_CHARS}
              </span>
            </div>
          </div>

          {/* Action Row */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginTop: 16,
            gap: 12
          }}>
            <button
              type="button"
              onClick={handleNormalize}
              disabled={loading || !input.trim()}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                padding: '10px 20px',
                backgroundColor: 'var(--accent)',
                color: 'var(--accent-text)',
                fontWeight: 600,
                fontSize: 14,
                borderRadius: 'var(--radius-control)',
                border: '1px solid var(--accent)',
                transition: 'background-color var(--duration-fast) var(--ease-standard)'
              }}
            >
              {loading ? (
                <>
                  <IconRefresh size={16} className="spin" />
                  <span>Đang xử lý ({elapsedTimer} ms)...</span>
                </>
              ) : (
                <>
                  <span>Chuẩn hóa địa chỉ</span>
                  <IconCornerDownLeft size={14} />
                </>
              )}
            </button>

            {/* Session history toggle button */}
            {sessionHistory.length > 0 && (
              <button
                type="button"
                onClick={() => setShowHistory((prev) => !prev)}
                style={{
                  fontSize: 13,
                  color: 'var(--muted)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-control)',
                  border: '1px solid var(--border)',
                  backgroundColor: 'var(--raised)'
                }}
              >
                <IconHistory size={14} />
                <span>Lịch sử phiên ({sessionHistory.length})</span>
              </button>
            )}
          </div>

          {/* Quick Realistic Samples */}
          <div style={{ marginTop: 20 }}>
            <div style={{
              fontSize: 13,
              fontWeight: 600,
              color: 'var(--muted)',
              marginBottom: 8,
              textTransform: 'uppercase',
              letterSpacing: '0.04em'
            }}>
              Mẫu thử nghiệm thực tế:
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {SAMPLE_ADDRESSES.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    setInput(sample.value);
                    if (textareaRef.current) textareaRef.current.focus();
                  }}
                  style={{
                    textAlign: 'left',
                    padding: '8px 12px',
                    borderRadius: 6,
                    backgroundColor: 'var(--raised)',
                    border: '1px solid var(--border)',
                    fontSize: 13.5,
                    color: 'var(--text)',
                    lineHeight: 1.45,
                    transition: 'border-color var(--duration-fast)'
                  }}
                >
                  <span style={{ fontWeight: 650, color: 'var(--text)', marginRight: 6 }}>
                    [{sample.label}]
                  </span>
                  {sample.value}
                </button>
              ))}
            </div>
          </div>

          {/* In-memory Session History Drawer */}
          {showHistory && sessionHistory.length > 0 && (
            <div style={{
              marginTop: 16,
              padding: 14,
              backgroundColor: 'var(--raised)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-control)'
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 8
              }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
                  Lịch sử các lượt chuẩn hóa vừa qua (Bộ nhớ tạm):
                </span>
                <button
                  type="button"
                  onClick={() => setSessionHistory([])}
                  style={{ fontSize: 11, color: 'var(--negative)' }}
                >
                  Xóa lịch sử
                </button>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {sessionHistory.map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setInput(item.input);
                      setResponse(item.response);
                    }}
                    style={{
                      textAlign: 'left',
                      padding: '6px 8px',
                      borderRadius: 4,
                      backgroundColor: 'var(--surface)',
                      border: '1px solid var(--border)',
                      fontSize: 12
                    }}
                  >
                    <div style={{ color: 'var(--muted)', fontSize: 11 }}>
                      {new Date(item.timestamp).toLocaleTimeString('vi-VN')} · {item.response.elapsed_ms} ms · {item.response.status}
                    </div>
                    <div style={{ color: 'var(--text)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.input}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* RIGHT COLUMN: Results Presentation */}
        <section style={{
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-card)',
          padding: 20,
          display: 'flex',
          flexDirection: 'column'
        }}>
          {/* Header row of output */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 16
          }}>
            <h2 style={{
              fontSize: 13,
              fontWeight: 600,
              color: 'var(--text)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              display: 'flex',
              alignItems: 'center',
              gap: 6
            }}>
              <IconLayers size={15} /> Kết quả chuẩn hóa
            </h2>

            {response && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {response.status === 'processed' ? (
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                    padding: '3px 8px',
                    borderRadius: 999,
                    fontSize: 13,
                    fontWeight: 600,
                    backgroundColor: 'var(--pill-neutral-bg)',
                    color: 'var(--pill-neutral-ink)'
                  }}>
                    <IconCheckCircle size={14} /> Đã xử lý ({response.elapsed_ms} ms)
                  </span>
                ) : (
                  <span style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                    padding: '3px 8px',
                    borderRadius: 999,
                    fontSize: 13,
                    fontWeight: 600,
                    backgroundColor: 'var(--pill-warning-bg)',
                    color: 'var(--pill-warning-ink)'
                  }}>
                    <IconAlertTriangle size={14} /> Cần xem lại ({response.elapsed_ms} ms)
                  </span>
                )}
              </div>
            )}
          </div>

          {/* State 1: Error state */}
          {error && (
            <div style={{
              padding: '14px 16px',
              backgroundColor: 'var(--pill-negative-bg)',
              color: 'var(--pill-negative-ink)',
              border: '1px solid rgba(180, 35, 24, 0.2)',
              borderRadius: 'var(--radius-control)',
              marginBottom: 16
            }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <IconAlertTriangle size={18} style={{ flexShrink: 0, marginTop: 2 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13.5 }}>Không thể hoàn tất yêu cầu</div>
                  <div style={{ fontSize: 13, marginTop: 2 }}>{error}</div>
                  <button
                    type="button"
                    onClick={handleNormalize}
                    style={{
                      marginTop: 8,
                      fontSize: 13,
                      fontWeight: 600,
                      padding: '4px 10px',
                      borderRadius: 4,
                      backgroundColor: 'var(--negative)',
                      color: '#ffffff'
                    }}
                  >
                    Thử lại
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* State 2: Architectural Overview State (Balances with left column height) */}
          {!response && !loading && !error && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
              padding: '4px 0'
            }}>
              <div style={{
                fontSize: 13.5,
                fontWeight: 600,
                color: 'var(--text)',
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}>
                <span>Sơ đồ Bóc tách 6 Cấp độ Hành chính:</span>
              </div>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: 8
              }}>
                {[
                  { step: '1', name: 'Số nhà', ex: 'Số 313, 268/10', desc: 'Bóc tách số nhà, số lô, bảo toàn tiền tố và hậu tố chữ' },
                  { step: '2', name: 'Ngõ / Hẻm', ex: 'Ngõ 42, Hẻm 110A', desc: 'Nhận diện ngõ, ngách, hẻm, kiệt với phân nhánh đa cấp' },
                  { step: '3', name: 'Thôn / Xóm', ex: 'Thôn 4, Bản Lướt', desc: 'Nhận diện thôn, buôn, xóm, ấp, bản và khu phố dân cư' },
                  { step: '4', name: 'Tuyến đường', ex: 'Đường Nguyễn Văn Linh', desc: 'Khôi phục tên đường đầy đủ từ các từ viết tắt và biến thể' },
                  { step: '5', name: 'Phường / Xã mới', ex: 'Mốc 01/07/2025', desc: 'Quy chuẩn theo NQ 1111/NQ-UBTVQH15, gắn mã xã chuẩn' },
                  { step: '6', name: 'Tỉnh / TP mới', ex: 'Mã tỉnh chính thức', desc: 'Xác định tỉnh/thành phố trực thuộc TW, gắn mã tỉnh' }
                ].map((item) => (
                  <div key={item.step} style={{
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-control)',
                    backgroundColor: 'var(--raised)',
                    border: '1px solid var(--border)',
                    fontSize: 13
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 2 }}>
                      <span style={{ fontWeight: 650, color: 'var(--text)' }}>
                        {item.step}. {item.name}
                      </span>
                      <span style={{ color: 'var(--muted)', fontSize: 11.5, fontFamily: 'var(--font-mono)' }}>
                        {item.ex}
                      </span>
                    </div>
                    <div style={{ color: 'var(--muted)', fontSize: 12, lineHeight: 1.4 }}>
                      {item.desc}
                    </div>
                  </div>
                ))}
              </div>
              <div style={{
                marginTop: 8,
                padding: '12px 14px',
                borderRadius: 'var(--radius-control)',
                backgroundColor: 'var(--raised)',
                border: '1px solid var(--border)',
                fontSize: 13,
                color: 'var(--muted)',
                lineHeight: 1.55
              }}>
                <strong style={{ color: 'var(--text)' }}>Quy chuẩn Nghị quyết 1111/NQ-UBTVQH15:</strong> Các xã/phường sáp nhập hoặc đổi tên được tự động quy đổi về mã chính thức áp dụng từ ngày <strong>01/07/2025</strong>. Đối với các đơn vị bị chia tách đa hướng, hệ thống bảo tồn cờ cảnh báo <code>xa_bi_chia</code> và danh sách ứng viên để người dùng thẩm định.
              </div>
            </div>
          )}

          {/* State 3: Loading Skeleton */}
          {loading && (
            <div style={{ padding: '20px 0' }}>
              <div style={{
                height: 48,
                backgroundColor: 'var(--raised)',
                borderRadius: 'var(--radius-control)',
                marginBottom: 16,
                border: '1px solid var(--border)',
                display: 'flex',
                alignItems: 'center',
                padding: '0 16px',
                color: 'var(--muted)',
                fontSize: 13
              }}>
                Đang chạy suy luận pipeline qua mô hình... ({elapsedTimer} ms)
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <div key={i} style={{
                    height: 56,
                    backgroundColor: 'var(--raised)',
                    borderRadius: 'var(--radius-control)',
                    border: '1px solid var(--border)'
                  }} />
                ))}
              </div>
            </div>
          )}

          {/* State 4: Normalized Results Display */}
          {result && !loading && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Canonical Standardized Address Banner */}
              <div style={{
                padding: '16px 18px',
                backgroundColor: 'var(--raised)',
                border: '1.5px solid var(--accent)',
                borderRadius: 'var(--radius-control)',
                position: 'relative'
              }}>
                <div style={{
                  fontSize: 12,
                  fontWeight: 650,
                  textTransform: 'uppercase',
                  color: 'var(--accent)',
                  letterSpacing: '0.04em',
                  marginBottom: 4
                }}>
                  Địa chỉ chuẩn hóa (Mốc 01/07/2025)
                </div>
                <div style={{
                  fontSize: 'clamp(15px, 2vw, 17px)',
                  fontWeight: 600,
                  color: 'var(--text)',
                  lineHeight: 1.4,
                  wordBreak: 'break-word',
                  paddingRight: 40
                }}>
                  {result.dia_chi_chuan || '(Không tạo được chuỗi chuẩn)'}
                </div>
                <button
                  type="button"
                  onClick={() => handleCopy(result.dia_chi_chuan, 'canonical')}
                  title="Sao chép địa chỉ chuẩn"
                  style={{
                    position: 'absolute',
                    right: 12,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    padding: '8px 10px',
                    borderRadius: 6,
                    backgroundColor: copiedField === 'canonical' ? 'var(--pill-positive-bg)' : 'var(--surface)',
                    color: copiedField === 'canonical' ? 'var(--pill-positive-ink)' : 'var(--text)',
                    border: '1px solid var(--border)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                    fontSize: 13,
                    fontWeight: 500
                  }}
                >
                  {copiedField === 'canonical' ? <IconCheck size={14} /> : <IconCopy size={14} />}
                  <span>{copiedField === 'canonical' ? 'Đã chép' : 'Chép'}</span>
                </button>
              </div>

              {/* Raw vs Normalized Diff */}
              <div style={{
                fontSize: 13.5,
                padding: '10px 14px',
                borderRadius: 'var(--radius-control)',
                backgroundColor: 'var(--raised)',
                border: '1px solid var(--border)'
              }}>
                <div style={{ color: 'var(--muted)', marginBottom: 2 }}>
                  <strong>Chuỗi đầu vào:</strong> {response.input}
                </div>
                <div style={{ color: 'var(--text)' }}>
                  <strong>Chuẩn hóa:</strong> {result.dia_chi_chuan}
                </div>
              </div>

              {/* Warnings / Needs Review Callouts */}
              {result.canh_bao && result.canh_bao.length > 0 && (
                <div style={{
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-control)',
                  backgroundColor: 'var(--pill-warning-bg)',
                  border: '1px solid rgba(146, 64, 14, 0.2)'
                }}>
                  <div style={{
                    fontSize: 13,
                    fontWeight: 700,
                    color: 'var(--pill-warning-ink)',
                    textTransform: 'uppercase',
                    marginBottom: 6,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4
                  }}>
                    <IconAlertTriangle size={15} /> Cần lưu ý khi sử dụng ({result.canh_bao.length}):
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {result.canh_bao.map((w, idx) => {
                      const t = WARNING_TRANSLATIONS[w];
                      return (
                        <div key={idx} style={{ fontSize: 13, color: 'var(--pill-warning-ink)', lineHeight: 1.45 }}>
                          • <strong>{t ? t.label : w}:</strong> {t ? t.desc : 'Cảnh báo từ hệ thống.'}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 6 Structured Administrative Fields Matrix */}
              <div>
                <div style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: 'var(--muted)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  marginBottom: 8
                }}>
                  Cấu trúc 6 thành phần hành chính:
                </div>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: 10
                }}>
                  {/* Field 1: Số nhà */}
                  <FieldCard
                    label="1. Số nhà"
                    value={result.so_nha}
                    onCopy={() => handleCopy(result.so_nha, 'so_nha')}
                    isCopied={copiedField === 'so_nha'}
                  />

                  {/* Field 2: Ngõ ngách hẻm */}
                  <FieldCard
                    label="2. Ngõ / Ngách / Hẻm"
                    value={result.ngo_ngach_hem}
                    onCopy={() => handleCopy(result.ngo_ngach_hem, 'ngo_ngach_hem')}
                    isCopied={copiedField === 'ngo_ngach_hem'}
                  />

                  {/* Field 3: Thôn xóm */}
                  <FieldCard
                    label="3. Thôn / Xóm / Bản"
                    value={result.thon_xom}
                    onCopy={() => handleCopy(result.thon_xom, 'thon_xom')}
                    isCopied={copiedField === 'thon_xom'}
                  />

                  {/* Field 4: Đường / Tuyến phố */}
                  <FieldCard
                    label="4. Tuyến đường / Phố"
                    value={result.duong}
                    onCopy={() => handleCopy(result.duong, 'duong')}
                    isCopied={copiedField === 'duong'}
                  />

                  {/* Field 5: Phường / Xã mới */}
                  <FieldCard
                    label="5. Phường / Xã mới"
                    value={result.xa_phuong}
                    code={result.ma_xa}
                    codeLabel="Mã xã"
                    onCopy={() => handleCopy(result.xa_phuong, 'xa_phuong')}
                    onCopyCode={result.ma_xa ? () => handleCopy(result.ma_xa, 'ma_xa') : undefined}
                    isCopied={copiedField === 'xa_phuong'}
                    isCodeCopied={copiedField === 'ma_xa'}
                  />

                  {/* Field 6: Tỉnh / Thành phố mới */}
                  <FieldCard
                    label="6. Tỉnh / TP mới"
                    value={result.tinh}
                    code={result.ma_tinh}
                    codeLabel="Mã tỉnh"
                    onCopy={() => handleCopy(result.tinh, 'tinh')}
                    onCopyCode={result.ma_tinh ? () => handleCopy(result.ma_tinh, 'ma_tinh') : undefined}
                    isCopied={copiedField === 'tinh'}
                    isCodeCopied={copiedField === 'ma_tinh'}
                  />
                </div>
              </div>

              {/* Unclassified Remnants Notice */}
              {result.phan_chua_phan_loai && (
                <div style={{
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-control)',
                  backgroundColor: 'var(--raised)',
                  border: '1px dashed var(--control)',
                  fontSize: 13
                }}>
                  <span style={{ fontWeight: 600, color: 'var(--warning)', marginRight: 6 }}>
                    Phần chưa phân loại:
                  </span>
                  <code style={{ backgroundColor: 'var(--surface)', padding: '2px 6px', borderRadius: 4 }}>
                    {result.phan_chua_phan_loai}
                  </code>
                </div>
              )}

              {/* Split Wards Alternatives Drawer */}
              {result.xa_moi_ung_vien && result.xa_moi_ung_vien.length > 0 && (
                <div style={{
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-control)',
                  backgroundColor: 'var(--raised)',
                  border: '1px solid var(--border)'
                }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', marginBottom: 8 }}>
                    Ứng viên xã mới phát sinh (Do xã cũ bị phân tách):
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8 }}>
                    {result.xa_moi_ung_vien.map((cand, cIdx) => (
                      <div key={cIdx} style={{
                        padding: '6px 10px',
                        borderRadius: 6,
                        backgroundColor: 'var(--surface)',
                        border: '1px solid var(--border)',
                        fontSize: 12
                      }}>
                        <div style={{ fontWeight: 600 }}>{cand.ten || cand.ma_xa}</div>
                        <div style={{ color: 'var(--muted)', fontSize: 11 }}>
                          Mã: <code>{cand.ma_xa}</code> · Tỉnh: <code>{cand.ma_tinh}</code>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Diagnostics & Technical Disclosure */}
              <div style={{
                borderRadius: 'var(--radius-control)',
                backgroundColor: 'var(--raised)',
                border: '1px solid var(--border)',
                overflow: 'hidden'
              }}>
                <button
                  type="button"
                  onClick={() => setShowDiagnostics((prev) => !prev)}
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: 13,
                    fontWeight: 600,
                    color: 'var(--text)',
                    backgroundColor: 'var(--surface)'
                  }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <IconDownload size={14} /> Dấu vết kỹ thuật & Debug JSON ({response.elapsed_ms} ms)
                  </span>
                  <IconChevronDown size={14} style={{ transform: showDiagnostics ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
                </button>

                {showDiagnostics && (
                  <div style={{ padding: 14 }}>
                    <div style={{
                      display: 'flex',
                      gap: 8,
                      marginBottom: 10,
                      flexWrap: 'wrap'
                    }}>
                      <button
                        type="button"
                        onClick={() => handleCopy(JSON.stringify(response, null, 2), 'raw-json')}
                        style={{
                          fontSize: 12,
                          padding: '4px 10px',
                          borderRadius: 4,
                          border: '1px solid var(--border)',
                          backgroundColor: 'var(--surface)',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4
                        }}
                      >
                        {copiedField === 'raw-json' ? <IconCheck size={13} /> : <IconCopy size={13} />}
                        <span>{copiedField === 'raw-json' ? 'Đã chép JSON' : 'Sao chép JSON'}</span>
                      </button>
                      <button
                        type="button"
                        onClick={handleDownloadJson}
                        style={{
                          fontSize: 12,
                          padding: '4px 10px',
                          borderRadius: 4,
                          border: '1px solid var(--border)',
                          backgroundColor: 'var(--surface)',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4
                        }}
                      >
                        <IconDownload size={13} />
                        <span>Tải về tệp .json</span>
                      </button>
                    </div>
                    <pre style={{
                      backgroundColor: 'var(--ground)',
                      padding: 12,
                      borderRadius: 6,
                      fontSize: 11.5,
                      lineHeight: 1.5,
                      color: 'var(--text)',
                      overflowX: 'auto',
                      maxHeight: 260,
                      border: '1px solid var(--border)'
                    }}>
                      {JSON.stringify(response, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

// Sub-component: FieldCard
interface FieldCardProps {
  label: string;
  value?: string;
  code?: string;
  codeLabel?: string;
  onCopy?: () => void;
  onCopyCode?: () => void;
  isCopied?: boolean;
  isCodeCopied?: boolean;
}

const FieldCard: React.FC<FieldCardProps> = ({
  label,
  value,
  code,
  codeLabel,
  onCopy,
  onCopyCode,
  isCopied,
  isCodeCopied
}) => {
  const displayVal = value ? value.trim() : '';

  return (
    <div style={{
      backgroundColor: 'var(--raised)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-control)',
      padding: '10px 12px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      minHeight: 74
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontSize: 12,
        fontWeight: 650,
        color: 'var(--muted)',
        marginBottom: 4
      }}>
        <span>{label}</span>
        {displayVal && onCopy && (
          <button
            type="button"
            onClick={onCopy}
            title={`Sao chép ${label}`}
            style={{
              padding: 2,
              color: isCopied ? 'var(--positive)' : 'var(--muted)',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            {isCopied ? <IconCheck size={13} /> : <IconCopy size={13} />}
          </button>
        )}
      </div>

      <div style={{
        fontSize: 14,
        fontWeight: 500,
        color: displayVal ? 'var(--text)' : 'var(--control)',
        wordBreak: 'break-word',
        fontStyle: displayVal ? 'normal' : 'italic'
      }}>
        {displayVal || '—'}
      </div>

      {code !== undefined && code !== '' && (
        <div style={{
          marginTop: 6,
          paddingTop: 4,
          borderTop: '1px dashed var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: 12
        }}>
          <span style={{ color: 'var(--muted)' }}>{codeLabel}:</span>
          <button
            type="button"
            onClick={onCopyCode}
            title={`Sao chép mã: ${code}`}
            style={{
              fontFamily: 'var(--font-mono)',
              fontWeight: 600,
              backgroundColor: isCodeCopied ? 'var(--pill-positive-bg)' : 'var(--surface)',
              color: isCodeCopied ? 'var(--pill-positive-ink)' : 'var(--accent)',
              padding: '2px 6px',
              borderRadius: 4,
              border: '1px solid var(--border)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 3
            }}
          >
            <span>{code}</span>
            {isCodeCopied ? <IconCheck size={11} /> : <IconCopy size={11} />}
          </button>
        </div>
      )}
    </div>
  );
};
