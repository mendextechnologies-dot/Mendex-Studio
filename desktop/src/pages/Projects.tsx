import React, { useState } from 'react';
import { ProjectRecord } from '../api/types';
import { FolderGit2, Search, ArrowRight, ShieldCheck } from 'lucide-react';

interface ProjectsProps {
  projects: ProjectRecord[];
  onSelectProject: (projectId: string) => void;
}

export const Projects: React.FC<ProjectsProps> = ({ projects, onSelectProject }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
      {/* Top Action Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc' }}>
            Engineering Projects Catalog
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
            Authoritative engineering baselines registered in the central SQLite repository.
          </p>
        </div>

        {/* Search */}
        <div style={{ position: 'relative', width: '280px' }}>
          <Search
            size={14}
            color="var(--text-dim)"
            style={{ position: 'absolute', left: '10px', top: '9px' }}
          />
          <input
            type="text"
            placeholder="Search by code or project name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              backgroundColor: '#121522',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              padding: '6px 12px 6px 32px',
              fontSize: '12px',
              color: '#f8fafc',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Projects Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '16px' }}>
        {filtered.map((proj) => (
          <div
            key={proj.product_id}
            className="card"
            style={{
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              cursor: 'pointer',
              minHeight: '180px',
            }}
            onClick={() => onSelectProject(proj.product_id)}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '12px', fontWeight: 800, color: '#60a5fa' }}>
                  {proj.code}
                </span>
                <span className={`badge ${proj.revision_status === 'PASSED' ? 'badge-green' : 'badge-blue'}`}>
                  {proj.revision_status}
                </span>
              </div>
              <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', marginTop: '6px' }}>
                {proj.name}
              </h3>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px', lineHeight: '1.4' }}>
                {proj.description || 'No description supplied.'}
              </p>
            </div>

            <div style={{ marginTop: '16px', borderTop: '1px solid var(--border)', paddingTop: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-dim)' }}>
                <span>Active Rev: <b>{proj.revision_label}</b></span>
                <span>Category: <b>{proj.category}</b></span>
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '4px', fontFamily: 'monospace' }}>
                Spec Hash: {proj.input_hash ? proj.input_hash.substring(0, 16) + '...' : 'N/A'}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
