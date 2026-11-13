import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { usePolling } from '../usePolling';
import { ToolRecord } from '../api/types';
import { Wrench, CheckCircle2, AlertCircle } from 'lucide-react';

export const EngineeringTools: React.FC = () => {
  const { data, error } = usePolling(api.tools);
  const tools = data || [];



  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
      {error && <p role="alert">{error}. Displayed records may be stale.</p>}
      <div>
        <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#172033' }}>
          Engineering Solver Integrations
        </h2>
        <p style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
          Local headless execution runners for electrical simulation, 2D FEA magnetics, and CAD qualification.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '16px' }}>
        {tools.map((t) => {
          const isReady = t.health.state === 'READY';
          const isDetected = t.health.state === 'DETECTED';
          const badgeClass = isReady ? 'badge-green' : isDetected ? 'badge-blue' : t.health.state === 'NOT_CONFIGURED' ? 'badge-yellow' : 'badge-red';
          const isData = t.descriptor.category.toLowerCase().includes('dataset') ||
                        t.descriptor.category.toLowerCase().includes('benchmark') ||
                        t.descriptor.category.toLowerCase().includes('resource');
          const pathDisplay = t.health.executable_path || t.health.installed_path || (isData ? 'Curated offline dataset resource' : 'Not detected on host');

          return (
            <div key={t.descriptor.tool_id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#172033' }}>
                    {t.descriptor.name}
                  </h3>
                  <div style={{ fontSize: '11px', color: '#1d4ed8', fontWeight: 600 }}>
                    {t.descriptor.category.toUpperCase()}
                  </div>
                </div>
                <span className={`badge ${badgeClass}`}>
                  {t.health.state}
                </span>
              </div>

              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px', lineHeight: '1.4' }}>
                {t.descriptor.description}
              </p>

              <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid var(--border)', fontSize: '11px' }}>
                <div style={{ color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={pathDisplay}>
                  Path: <span style={{ fontFamily: 'monospace', color: '#334155' }}>{pathDisplay}</span>
                </div>
                {t.health.version && (
                  <div style={{ color: 'var(--text-dim)', marginTop: '2px' }}>
                    Version: <b style={{ color: '#334155' }}>{t.health.version}</b>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
