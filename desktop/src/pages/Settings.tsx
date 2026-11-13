import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { usePolling } from '../usePolling';
import { Settings as SettingsIcon, ShieldCheck, Terminal, HardDrive } from 'lucide-react';

export const Settings: React.FC = () => {
  const { data, error } = usePolling(api.settings);



  if (!data) {
    return <div style={{ padding: '24px', color: 'var(--text-muted)' }}>{error || 'Loading diagnostics?'}</div>;
  }

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
      {error && <p role="alert">{error}. Displayed records may be stale.</p>}
      <div>
        <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc' }}>
          Settings & Environment Diagnostics
        </h2>
        <p style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
          Authoritative backend environment parameters, runtime architecture, and offline data roots.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <Terminal size={16} color="#60a5fa" />
            <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc' }}>
              Execution & Core Environment
            </h3>
          </div>
          <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
            <tbody>
              <tr style={{ borderBottom: '1px solid #1f2436' }}>
                <td style={{ padding: '8px 0', color: 'var(--text-dim)' }}>Application:</td>
                <td style={{ padding: '8px 0', fontWeight: 600 }}>{data.application}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #1f2436' }}>
                <td style={{ padding: '8px 0', color: 'var(--text-dim)' }}>Desktop Protocol:</td>
                <td style={{ padding: '8px 0', fontWeight: 600, color: '#38bdf8' }}>v{data.protocol_version} (JSON-lines stdio)</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #1f2436' }}>
                <td style={{ padding: '8px 0', color: 'var(--text-dim)' }}>Python Engine:</td>
                <td style={{ padding: '8px 0', fontWeight: 600 }}>v{data.python_version}</td>
              </tr>
              <tr>
                <td style={{ padding: '8px 0', color: 'var(--text-dim)' }}>CLI Availability:</td>
                <td style={{ padding: '8px 0' }}><span className="badge badge-green">Operational</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <HardDrive size={16} color="#34d399" />
            <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc' }}>
              Authoritative Local Storage
            </h3>
          </div>
          <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
            <tbody>
              <tr style={{ borderBottom: '1px solid #1f2436' }}>
                <td style={{ padding: '8px 0', color: 'var(--text-dim)' }}>Data Root:</td>
                <td style={{ padding: '8px 0', fontFamily: 'monospace', color: '#93c5fd' }}>{data.data_root}</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #1f2436' }}>
                <td style={{ padding: '8px 0', color: 'var(--text-dim)' }}>Database Type:</td>
                <td style={{ padding: '8px 0', fontWeight: 600 }}>Local SQLite (studio.sqlite3)</td>
              </tr>
              <tr style={{ borderBottom: '1px solid #1f2436' }}>
                <td style={{ padding: '8px 0', color: 'var(--text-dim)' }}>Integrity Constraints:</td>
                <td style={{ padding: '8px 0' }}><span className="badge badge-green">PRAGMA foreign_keys = ON</span></td>
              </tr>
              <tr>
                <td style={{ padding: '8px 0', color: 'var(--text-dim)' }}>Cloud Independence:</td>
                <td style={{ padding: '8px 0' }}><span className="badge badge-green">100% Offline Capable</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
