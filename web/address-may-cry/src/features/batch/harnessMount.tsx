import React from 'react';
import ReactDOM from 'react-dom/client';
import BatchWorkspace from './BatchWorkspace';

export function HarnessApp() {
  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--ground, #ffffff)',
      color: 'var(--text, #111211)',
      fontFamily: '"Geist", "Instrument Sans", sans-serif'
    }}>
      <header style={{
        padding: '12px 20px',
        borderBottom: '1px solid var(--border, #eaeaea)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: 'var(--ground, #ffffff)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontWeight: 700, fontSize: 18, color: 'var(--text, #111211)' }}>Address May Cry</span>
          <span style={{
            fontSize: 12,
            fontWeight: 700,
            padding: '2px 8px',
            borderRadius: 4,
            backgroundColor: '#d1ece7',
            color: '#073833',
            border: '1px solid #b2dfd8'
          }}>
            Batch Workspace · Phần B
          </span>
        </div>
      </header>
      <main style={{ paddingBottom: 48 }}>
        <BatchWorkspace onInspect={(item) => console.log('Inspect item:', item)} />
      </main>
    </div>
  );
}

const rootEl = document.getElementById('root');
if (rootEl) {
  ReactDOM.createRoot(rootEl).render(
    <React.StrictMode>
      <HarnessApp />
    </React.StrictMode>
  );
}
