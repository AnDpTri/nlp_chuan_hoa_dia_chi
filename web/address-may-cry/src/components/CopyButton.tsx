import React, { useCallback, useEffect, useRef, useState } from 'react';
import { IconCheck, IconCopy } from './Icons';
import './components.css';

export async function copyText(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }
}

interface CopyButtonProps {
  text: string;
  /** Mô tả thứ đang chép, ví dụ "dòng có đối chiếu". */
  what: string;
  idleLabel?: string;
  doneLabel?: string;
  className?: string;
}

export function CopyButton({ text, what, idleLabel = 'Chép', doneLabel = 'Đã chép', className = '' }: CopyButtonProps) {
  const [done, setDone] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current); }, []);

  const onClick = useCallback(async () => {
    await copyText(text);
    setDone(true);
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setDone(false), 1800);
  }, [text]);

  return (
    <button
      type="button"
      className={`copy-btn ${done ? 'is-done' : ''} ${className}`}
      onClick={onClick}
      aria-label={`Chép ${what}`}
    >
      {done ? <IconCheck size={15} aria-hidden="true" /> : <IconCopy size={15} aria-hidden="true" />}
      <span aria-hidden="true">{done ? doneLabel : idleLabel}</span>
      <span className="sr-only" role="status" aria-live="polite">{done ? `Đã chép ${what}` : ''}</span>
    </button>
  );
}
