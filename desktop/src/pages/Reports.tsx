import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { usePolling } from '../usePolling';
import { FileText, Download, ExternalLink } from 'lucide-react';

export const Reports: React.FC = () => {
  const { data, error } = usePolling(api.reports);
  const reports = data || [];



  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
      {error && <p role="alert">{error}. Displayed records may be stale.</p>}
      <div>
        <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#172033' }}>
          Authoritative Engineering Dossiers & Reports
        </h2>
        <p style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
          Draft reports with recorded integrity status. File integrity does not establish engineering approval.
        </p>
      </div>

      <div className="card">
        <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-dim)' }}>
              <th style={{ padding: '10px 12px' }}>Project</th>
              <th style={{ padding: '10px 12px' }}>Revision</th>
              <th style={{ padding: '10px 12px' }}>Report Type</th>
              <th style={{ padding: '10px 12px' }}>Generated Date</th>
              <th style={{ padding: '10px 12px' }}>Evidence integrity</th>
            </tr>
          </thead>
          <tbody>
            {reports.map((r, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #f3f6fb' }}>
                <td style={{ padding: '10px 12px', fontWeight: 700, color: '#1d4ed8' }}>{r.project_name}</td>
                <td style={{ padding: '10px 12px' }}><span className="badge badge-blue">{r.revision_label}</span></td>
                <td style={{ padding: '10px 12px', color: '#172033' }}>Executive Engineering Dossier</td>
                <td style={{ padding: '10px 12px', color: 'var(--text-dim)' }}>
                  {r.report?.generated_at ? new Date(r.report.generated_at).toLocaleString() : 'N/A'}
                </td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace', color: '#047857', fontSize: '11px' }}>
                  {r.integrity || 'NOT_EVALUATED'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
