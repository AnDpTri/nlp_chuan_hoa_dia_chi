import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { SingleWorkspace } from './features/single/SingleWorkspace';
import { getHealth } from './shared/api';
import type { HealthResponse, BatchItem } from './shared/contracts';

// BatchWorkspace imported from Session B's contract path
// @ts-ignore
import BatchWorkspace from './features/batch/BatchWorkspace';

export function App() {
  const [activeTab, setActiveTab] = useState<'single' | 'batch'>('single');
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);

  const fetchHealth = useCallback(async () => {
    setHealthLoading(true);
    try {
      const res = await getHealth();
      setHealth(res);
    } catch {
      setHealth(null);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  const handleInspectFromBatch = useCallback((item: BatchItem) => {
    setActiveTab('single');
  }, []);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        health={health}
        healthLoading={healthLoading}
        onRefreshHealth={fetchHealth}
      />

      <main style={{ flex: 1, paddingBottom: 48 }}>
        {activeTab === 'single' ? (
          <SingleWorkspace />
        ) : (
          <div style={{ padding: '0 16px' }}>
            {BatchWorkspace ? (
              <BatchWorkspace onInspect={handleInspectFromBatch} />
            ) : (
              <div style={{ padding: 24, textAlign: 'center' }}>Đang tải mô-đun hàng loạt...</div>
            )}
          </div>
        )}
      </main>

      <footer style={{
        borderTop: '1px solid var(--border)',
        padding: '16px 20px',
        textAlign: 'center',
        fontSize: 12,
        color: 'var(--muted)',
        backgroundColor: 'var(--ground)'
      }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
          <div>
            <strong>Address May Cry</strong> — Hệ thống Chuẩn hóa Địa chỉ Hành chính Việt Nam
          </div>
          <div>
            Mốc đích: <strong>01/07/2025</strong> · Quyết định cải cách hành chính số 1111/NQ-UBTVQH15
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
