import React from 'react';
import { IconLogo } from './Icons';
import type { HealthResponse } from '../shared/contracts';

interface HeaderProps {
  activeTab: 'single' | 'batch';
  onTabChange: (tab: 'single' | 'batch') => void;
  health: HealthResponse | null;
  healthLoading: boolean;
  onRefreshHealth: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  health,
  healthLoading,
  onRefreshHealth
}) => {
  return (
    <header style={{
      borderBottom: '1px solid var(--border)',
      backgroundColor: 'var(--ground)',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      backdropFilter: 'blur(8px)',
    }}>
      <div style={{
        maxWidth: 1200,
        margin: '0 auto',
        padding: '12px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12
      }}>
        {/* Brand identity */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <IconLogo size={32} />
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{
                fontSize: 18,
                fontWeight: 700,
                letterSpacing: '-0.02em',
                color: 'var(--text)'
              }}>
                Address May Cry
              </span>
              <span style={{
                fontSize: 11,
                fontWeight: 600,
                padding: '2px 8px',
                borderRadius: 4,
                backgroundColor: 'var(--surface)',
                color: 'var(--text)',
                border: '1px solid var(--border)',
                letterSpacing: '0.02em'
              }}>
                2025-07-01
              </span>
            </div>
            <div style={{
              fontSize: 12,
              color: 'var(--muted)',
              lineHeight: 1.2
            }}>
              Chuẩn hóa địa chỉ tiếng Việt đa thời kỳ
            </div>
          </div>
        </div>

        {/* Tab switcher */}
        <nav style={{
          display: 'flex',
          backgroundColor: 'var(--surface)',
          padding: 3,
          borderRadius: 'var(--radius-control)',
          border: '1px solid var(--border)',
          gap: 2
        }} role="tablist" aria-label="Chế độ làm việc">
          <button
            role="tab"
            aria-selected={activeTab === 'single'}
            onClick={() => onTabChange('single')}
            style={{
              padding: '6px 14px',
              fontSize: 13,
              fontWeight: activeTab === 'single' ? 600 : 500,
              color: activeTab === 'single' ? 'var(--text)' : 'var(--muted)',
              backgroundColor: activeTab === 'single' ? 'var(--raised)' : 'transparent',
              borderRadius: 'calc(var(--radius-control) - 2px)',
              boxShadow: activeTab === 'single' ? 'var(--shadow-sm)' : 'none',
              transition: 'all var(--duration-fast) var(--ease-standard)'
            }}
          >
            Đơn địa chỉ
          </button>
          <button
            role="tab"
            aria-selected={activeTab === 'batch'}
            onClick={() => onTabChange('batch')}
            style={{
              padding: '6px 14px',
              fontSize: 13,
              fontWeight: activeTab === 'batch' ? 600 : 500,
              color: activeTab === 'batch' ? 'var(--text)' : 'var(--muted)',
              backgroundColor: activeTab === 'batch' ? 'var(--raised)' : 'transparent',
              borderRadius: 'calc(var(--radius-control) - 2px)',
              boxShadow: activeTab === 'batch' ? 'var(--shadow-sm)' : 'none',
              transition: 'all var(--duration-fast) var(--ease-standard)'
            }}
          >
            Hàng loạt (Batch)
          </button>
        </nav>

        {/* Health & Engine status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={onRefreshHealth}
            title="Bấm để kiểm tra lại trạng thái API"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 10px',
              borderRadius: 999,
              fontSize: 12,
              fontWeight: 500,
              backgroundColor: health?.status === 'ok' ? 'var(--pill-positive-bg)' : 'var(--pill-neutral-bg)',
              color: health?.status === 'ok' ? 'var(--pill-positive-ink)' : 'var(--pill-neutral-ink)',
              border: '1px solid var(--border)'
            }}
          >
            <span style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              backgroundColor: health?.status === 'ok' ? 'var(--positive)' : (healthLoading ? 'var(--muted)' : 'var(--negative)'),
              display: 'inline-block'
            }} />
            <span>
              {healthLoading ? 'Đang kiểm tra...' : (health?.status === 'ok' ? `API Sẵn sàng (${health.engine || 'Engine'})` : 'Chưa kết nối API')}
            </span>
          </button>
        </div>
      </div>
    </header>
  );
};
