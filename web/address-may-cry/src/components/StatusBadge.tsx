import React from 'react';
import { IconAlertTriangle, IconCheckCircle } from './Icons';
import './components.css';

type Status = 'processed' | 'needs_review' | 'error';

/** Trạng thái xử lý. "Đã xử lý" không có nghĩa là đã kiểm đúng; không hiện độ tin cậy giả. */
export function StatusBadge({ status }: { status: Status }) {
  if (status === 'needs_review') {
    return (
      <span className="badge badge-warning">
        <IconAlertTriangle size={15} aria-hidden="true" /> Cần xem lại
      </span>
    );
  }
  if (status === 'error') {
    return (
      <span className="badge badge-danger">
        <IconAlertTriangle size={15} aria-hidden="true" /> Lỗi xử lý
      </span>
    );
  }
  return (
    <span className="badge badge-neutral">
      <IconCheckCircle size={15} aria-hidden="true" /> Đã xử lý
    </span>
  );
}
