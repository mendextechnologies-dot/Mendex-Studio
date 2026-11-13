import React from 'react';
import {
  LayoutDashboard,
  FolderGit2,
  Activity,
  Cpu,
  Wrench,
  FileText,
  Settings,
  ShieldCheck,
} from 'lucide-react';

export type RouteId =
  | 'dashboard'
  | 'projects'
  | 'simulations'
  | 'components'
  | 'tools'
  | 'reports'
  | 'settings';

interface SidebarProps {
  currentRoute: RouteId;
  onNavigate: (route: RouteId) => void;
  handshake?: any;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentRoute, onNavigate, handshake }) => {
  const navItems: Array<{ id: RouteId; label: string; icon: any; count?: number }> = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'projects', label: 'Engineering Projects', icon: FolderGit2 },
    { id: 'simulations', label: 'Simulation Center', icon: Activity },
    { id: 'components', label: 'Component Library', icon: Cpu },
    { id: 'tools', label: 'Engineering Tools', icon: Wrench },
    { id: 'reports', label: 'Reports & Evidence', icon: FileText },
    { id: 'settings', label: 'Settings & Diagnostics', icon: Settings },
  ];

  return (
    <aside
      style={{
        width: '240px',
        backgroundColor: 'var(--bg-sidebar)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        flexShrink: 0,
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
        }}
      >
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '6px',
            backgroundColor: '#1e3a5f',
            color: '#60a5fa',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            fontSize: '14px',
            border: '1px solid #2563eb',
          }}
        >
          M
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: '14px', letterSpacing: '-0.3px', color: '#f8fafc' }}>
            MENDEX STUDIO
          </div>
          <div style={{ fontSize: '10px', fontWeight: 600, color: '#38bdf8', letterSpacing: '0.5px' }}>
            v3.1 COMMAND CENTER
          </div>
        </div>
      </div>

      {/* Nav List */}
      <nav style={{ padding: '12px 8px', flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div
          style={{
            padding: '4px 12px',
            fontSize: '10px',
            fontWeight: 700,
            color: 'var(--text-dim)',
            letterSpacing: '0.8px',
            textTransform: 'uppercase',
          }}
        >
          Engineering Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = currentRoute === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '9px 12px',
                borderRadius: '6px',
                border: 'none',
                background: active ? '#1e293b' : 'transparent',
                color: active ? '#38bdf8' : '#94a3b8',
                fontWeight: active ? 600 : 500,
                fontSize: '12px',
                cursor: 'pointer',
                textAlign: 'left',
                width: '100%',
                transition: 'all 0.15s ease',
              }}
            >
              <Icon size={16} color={active ? '#38bdf8' : '#64748b'} />
              <span style={{ flex: 1 }}>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* System Integrity Footer */}
      <div
        style={{
          padding: '14px 16px',
          borderTop: '1px solid var(--border)',
          backgroundColor: '#0c0e17',
          fontSize: '11px',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#34d399', fontWeight: 600 }}>
          <ShieldCheck size={14} />
          <span>Core Python 3.13 Ready</span>
        </div>
        <div style={{ color: 'var(--text-dim)', fontSize: '10px' }}>
          Data: Local SQLite (Immutable)
        </div>
      </div>
    </aside>
  );
};
