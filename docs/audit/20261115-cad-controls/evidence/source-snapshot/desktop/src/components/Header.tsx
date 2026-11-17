import React from 'react';
import { RefreshCw, CheckCircle2, Cpu } from 'lucide-react';

interface HeaderProps {
  title: string;
  subtitle?: string;
  isSyncing: boolean;
  lastSyncTime?: string;
  onRefresh: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  subtitle,
  isSyncing,
  lastSyncTime,
  onRefresh,
}) => {
  return (
    <header
      style={{
        height: '56px',
        borderBottom: '1px solid var(--border)',
        backgroundColor: 'var(--bg-app)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        flexShrink: 0,
      }}
    >
      <div>
        <h1 style={{ fontSize: '15px', fontWeight: 700, color: '#172033', display: 'flex', alignItems: 'center', gap: '8px' }}>
          {title}
        </h1>
        {subtitle && (
          <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
            {subtitle}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Solvers Status */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '4px',
            backgroundColor: '#ecfdf5',
            border: '1px solid #a7f3d0',
            color: '#047857',
            fontSize: '11px',
            fontWeight: 600,
          }}
        >
          <Cpu size={13} />
          <span>Tool qualification: see Engineering Tools</span>
        </div>

        {/* Sync Status Badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '4px',
            backgroundColor: '#eff6ff',
            border: '1px solid #bfdbfe',
            color: '#1d4ed8',
            fontSize: '11px',
            fontWeight: 600,
          }}
        >
          <CheckCircle2 size={13} />
          <span>Refresh polling (4s)</span>
        </div>

        {/* Manual Refresh Button */}
        <button
          onClick={onRefresh}
          className="btn btn-secondary"
          style={{ padding: '4px 10px', height: '28px' }}
          title="Refresh current state"
        >
          <RefreshCw size={13} className={isSyncing ? 'spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>
    </header>
  );
};
