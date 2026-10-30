import React from 'react';
import { IconLogo } from './Icons';
import type { HealthResponse } from '../shared/contracts';
import './header.css';

export type TabId = 'single' | 'batch';

interface HeaderProps {
  activeTab: TabId;
  hrefs: Record<TabId, string>;
  health: HealthResponse | null;
  healthLoading: boolean;
  onRefreshHealth: () => void;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, hrefs, health, healthLoading, onRefreshHealth }) => {
  const ok = health?.status === 'ok';
  const loadingEngine = health?.status === 'loading';
  const statusText = healthLoading
    ? 'Đang kiểm tra máy chủ…'
    : ok
      ? 'Máy chủ sẵn sàng'
      : loadingEngine
        ? 'Máy chủ đang khởi động…'
        : 'Chưa kết nối máy chủ';
  const dotClass = healthLoading || loadingEngine ? 'is-wait' : ok ? 'is-ok' : 'is-bad';

  return (
    <header className="site-header">
      <div className="site-header-inner">
        <a className="brand" href={hrefs.single} aria-label="Address May Cry, về trang một địa chỉ">
          <IconLogo size={34} aria-hidden="true" />
          <span className="brand-text">
            <span className="brand-name" translate="no">Address May Cry</span>
            <span className="brand-sub">Chuẩn hóa địa chỉ · mốc 01/07/2025</span>
          </span>
        </a>

        <nav className="main-nav" aria-label="Chế độ làm việc">
          <a href={hrefs.single} aria-current={activeTab === 'single' ? 'page' : undefined}>Một địa chỉ</a>
          <a href={hrefs.batch} aria-current={activeTab === 'batch' ? 'page' : undefined}>Hàng loạt</a>
        </nav>

        <button
          type="button"
          className="health"
          onClick={onRefreshHealth}
          aria-label={`${statusText}. Bấm để kiểm tra lại`}
        >
          <span className={`health-dot ${dotClass}`} aria-hidden="true" />
          <span className="health-text" aria-live="polite">{statusText}</span>
        </button>
      </div>
    </header>
  );
};
