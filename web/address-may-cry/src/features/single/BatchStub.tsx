import React from 'react';
import type { BatchItem } from '../../shared/contracts';

interface BatchWorkspaceProps {
  onInspect?: (item: BatchItem) => void;
}

export const BatchWorkspace: React.FC<BatchWorkspaceProps> = ({ onInspect }) => {
  return (
    <div style={{
      maxWidth: 900,
      margin: '40px auto',
      padding: '32px 24px',
      backgroundColor: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-card)',
      textAlign: 'center'
    }}>
      <div style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 48,
        height: 48,
        borderRadius: '50%',
        backgroundColor: 'var(--accent-light)',
        color: 'var(--accent)',
        marginBottom: 16
      }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
        </svg>
      </div>
      <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: 'var(--text)' }}>
        Không gian Xử lý Hàng loạt (Batch Workspace)
      </h2>
      <p style={{ fontSize: 14, color: 'var(--muted)', maxWidth: 540, margin: '0 auto 20px', lineHeight: 1.6 }}>
        Mô-đun hàng loạt thuộc sở hữu của Phiên B (<code>src/features/batch/BatchWorkspace.tsx</code>).
        Toàn bộ hệ thống giao diện chung, CSS variables và cổng tích hợp <code>onInspect</code> đã sẵn sàng để tự động nạp ngay khi tệp được khởi tạo.
      </p>
      <div style={{
        display: 'inline-block',
        textAlign: 'left',
        fontSize: 13,
        padding: '12px 16px',
        backgroundColor: 'var(--raised)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-control)',
        color: 'var(--muted)'
      }}>
        <div>• <strong>Giới hạn tải:</strong> 1.000 dòng / phiên làm việc</div>
        <div>• <strong>Chia nhỏ:</strong> 20 dòng / đợt (chunk) qua <code>/api/v1/batch</code></div>
        <div>• <strong>Visual Variables:</strong> <code>--ground, --surface, --accent, --border...</code></div>
      </div>
    </div>
  );
};

export default BatchWorkspace;
