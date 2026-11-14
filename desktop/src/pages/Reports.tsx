import React, { useState } from 'react';
import { api } from '../api/client';
import { usePolling } from '../usePolling';
import { FileText, Download, ExternalLink, Eye, X, AlertCircle, CheckCircle2 } from 'lucide-react';

export const Reports: React.FC = () => {
  const { data, error } = usePolling(api.reports);
  const reports = data || [];

  const [actionError, setActionError] = useState('');
  const [actionMessage, setActionMessage] = useState('');

  // In-App Dossier Modal State
  const [activeReportDossier, setActiveReportDossier] = useState<{
    report_id: string;
    revision_id: string;
    generated_at: string | null;
    html_content: string;
    has_pdf: boolean;
    pdf_size_bytes: number;
  } | null>(null);
  const [isLoadingDossier, setIsLoadingDossier] = useState(false);

  const handlePreviewDossier = async (reportId: string) => {
    setIsLoadingDossier(true);
    setActionError('');
    try {
      const rep = await api.getReport(reportId);
      setActiveReportDossier(rep);
    } catch (e: any) {
      setActionError(e.message || String(e));
    } finally {
      setIsLoadingDossier(false);
    }
  };

  const handleOpenPdf = async (reportId: string) => {
    try {
      setActionError('');
      // Open in browser tab immediately
      window.open(`/api/report-file?id=${reportId}&type=pdf`, '_blank');
      // Also request background native open on desktop if configured
      api.openReport(reportId, 'pdf').catch(() => {});
      setActionMessage('Vector PDF opened in new browser tab.');
      setTimeout(() => setActionMessage(''), 5000);
    } catch (e: any) {
      setActionError(e.message || String(e));
      setTimeout(() => setActionError(''), 6000);
    }
  };

  const handleOpenHtml = async (reportId: string) => {
    try {
      setActionError('');
      // Open in browser tab immediately
      window.open(`/api/report-file?id=${reportId}&type=html`, '_blank');
      // Also request background native open on desktop if configured
      api.openReport(reportId, 'html').catch(() => {});
      setActionMessage('Interactive HTML dossier opened in new browser tab.');
      setTimeout(() => setActionMessage(''), 5000);
    } catch (e: any) {
      setActionError(e.message || String(e));
      setTimeout(() => setActionError(''), 6000);
    }
  };

  const handleExportPackage = async (reportId: string) => {
    try {
      setActionError('');
      setActionMessage('Generating and packing authoritative export package...');
      // 1. Ensure report package is compiled and recorded with cryptographic SHA-256
      await api.exportReport(reportId);
      // 2. Trigger browser download
      const a = document.createElement('a');
      a.href = `/api/report-file?id=${reportId}&type=export`;
      a.download = `report-package-${reportId.slice(0, 8)}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setActionMessage('Report package ZIP downloaded successfully.');
      setTimeout(() => setActionMessage(''), 5000);
    } catch (e: any) {
      setActionError(e.message || String(e));
      setTimeout(() => setActionError(''), 6000);
    }
  };

  const handleAction = async (call: () => Promise<unknown>, successMsg: string) => {
    try {
      setActionError('');
      await call();
      setActionMessage(successMsg);
      setTimeout(() => setActionMessage(''), 5000);
    } catch (e: any) {
      setActionError(e.message || String(e));
      setTimeout(() => setActionError(''), 6000);
    }
  };

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
      {error && <p role="alert" style={{ color: '#b91c1c', fontSize: '12px' }}>{error}. Displayed records may be stale.</p>}
      
      {actionError && (
        <div
          role="alert"
          style={{
            padding: '10px 14px',
            backgroundColor: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            borderRadius: '6px',
            color: '#b91c1c',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <AlertCircle size={15} />
          <span>{actionError}</span>
        </div>
      )}

      {actionMessage && (
        <div
          role="status"
          style={{
            padding: '10px 14px',
            backgroundColor: 'rgba(16, 185, 129, 0.12)',
            border: '1px solid rgba(16, 185, 129, 0.35)',
            borderRadius: '6px',
            color: '#047857',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <CheckCircle2 size={15} />
          <span>{actionMessage}</span>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#172033', margin: 0 }}>
            Authoritative Engineering Dossiers & Reports
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '4px' }}>
            Complete Product Engineering Dossiers (CPED) with recorded SHA-256 integrity status, vector schematics, 2D/3D PCB models, and SPICE/FEMM verification.
          </p>
        </div>
        <div style={{ fontSize: '12px', color: '#64748b', fontWeight: 600 }}>
          Total Compiled Dossiers: <strong style={{ color: '#1d4ed8' }}>{reports.length}</strong>
        </div>
      </div>

      <div className="card" style={{ overflow: 'hidden' }}>
        <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-dim)', background: '#f8fafc' }}>
              <th style={{ padding: '12px 14px' }}>Project</th>
              <th style={{ padding: '12px 14px' }}>Revision</th>
              <th style={{ padding: '12px 14px' }}>Dossier Type</th>
              <th style={{ padding: '12px 14px' }}>Compiled Date</th>
              <th style={{ padding: '12px 14px' }}>Integrity</th>
              <th style={{ padding: '12px 14px', textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {reports.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: '30px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No compiled engineering dossiers available. Open a project and click "Compile Complete Dossier (PDF)" to generate one.
                </td>
              </tr>
            ) : (
              reports.map((r: any, i: number) => {
                const isIntact = r.integrity === 'INTACT';
                const isAvailable = Boolean(r.available && r.integrity !== 'FAILED');
                return (
                  <tr key={r.report?.report_id || i} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '12px 14px', fontWeight: 700, color: '#1d4ed8' }}>
                      {r.project_name}
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <span className="badge badge-blue">{r.revision_label}</span>
                    </td>
                    <td style={{ padding: '12px 14px', color: '#172033', fontWeight: 500 }}>
                      Complete Product Dossier (CPED)
                    </td>
                    <td style={{ padding: '12px 14px', color: 'var(--text-dim)' }}>
                      {r.report?.generated_at ? new Date(r.report.generated_at).toLocaleString() : 'N/A'}
                    </td>
                    <td style={{ padding: '12px 14px' }}>
                      <span className={`badge ${isIntact ? 'badge-green' : 'badge-yellow'}`}>
                        {r.integrity || 'NOT_EVALUATED'}
                      </span>
                      {r.stale && <span className="badge badge-yellow" style={{ marginLeft: '4px' }}>Stale</span>}
                    </td>
                    <td style={{ padding: '12px 14px', textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '6px', alignItems: 'center' }}>
                        <button
                          className="btn btn-primary"
                          disabled={!isAvailable || isLoadingDossier}
                          onClick={() => handlePreviewDossier(r.report.report_id)}
                          style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
                          title="Preview full dossier inside Mendex Studio"
                        >
                          <Eye size={12} className={isLoadingDossier ? 'spin' : ''} />
                          <span>Preview</span>
                        </button>
                        <button
                          className="btn btn-secondary"
                          disabled={!isAvailable}
                          onClick={() => handleOpenPdf(r.report.report_id)}
                          style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
                          title="Open vector PDF"
                        >
                          <FileText size={12} />
                          <span>PDF</span>
                        </button>
                        <button
                          className="btn btn-secondary"
                          disabled={!isAvailable}
                          onClick={() => handleOpenHtml(r.report.report_id)}
                          style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
                          title="Open HTML report"
                        >
                          <ExternalLink size={12} />
                          <span>HTML</span>
                        </button>
                        <button
                          className="btn btn-secondary"
                          disabled={!isAvailable}
                          onClick={() => handleExportPackage(r.report.report_id)}
                          style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
                          title="Export standalone report package"
                        >
                          <Download size={12} />
                          <span>Export</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* IN-APP COMPLETE PRODUCT ENGINEERING DOSSIER (CPED) MODAL */}
      {activeReportDossier && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            backgroundColor: 'rgba(5, 7, 13, 0.85)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '20px',
          }}
        >
          <div
            className="card"
            style={{
              width: '100%',
              maxWidth: '1240px',
              height: '92vh',
              display: 'flex',
              flexDirection: 'column',
              backgroundColor: '#ffffff',
              border: '1px solid #cbd5e1',
              boxShadow: '0 25px 70px rgba(0,0,0,0.35)',
              borderRadius: '10px',
              overflow: 'hidden',
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                padding: '14px 20px',
                borderBottom: '1px solid #e2e8f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: '#f8fafc',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div
                  style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '6px',
                    background: 'rgba(37, 99, 235, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#2563eb',
                  }}
                >
                  <FileText size={20} />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                      Complete Product Engineering Dossier (CPED)
                    </h3>
                    {activeReportDossier.has_pdf && (
                      <span
                        style={{
                          fontSize: '11px',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: '#dcfce7',
                          color: '#15803d',
                          fontWeight: 700,
                          border: '1px solid #bbf7d0',
                        }}
                      >
                        Vector PDF Ready ({Math.round(activeReportDossier.pdf_size_bytes / 1024)} KB)
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                    Report ID: <code style={{ color: '#334155' }}>{activeReportDossier.report_id.slice(0, 8)}…</code> · Revision: <code style={{ color: '#334155' }}>{activeReportDossier.revision_id.slice(0, 8)}…</code> · Compiled: {activeReportDossier.generated_at ? new Date(activeReportDossier.generated_at).toLocaleString() : 'N/A'}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {activeReportDossier.has_pdf && (
                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ fontSize: '11px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '5px' }}
                    onClick={() => handleOpenPdf(activeReportDossier.report_id)}
                    title="Open in system vector PDF viewer"
                  >
                    <FileText size={12} />
                    <span>Open in PDF Viewer</span>
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: '11px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '5px' }}
                  onClick={() => handleOpenHtml(activeReportDossier.report_id)}
                  title="Open in browser window"
                >
                  <ExternalLink size={12} />
                  <span>Open in Browser</span>
                </button>
                <button
                  type="button"
                  onClick={() => setActiveReportDossier(null)}
                  style={{ background: 'transparent', border: 'none', color: '#64748b', cursor: 'pointer', padding: '6px' }}
                  title="Close preview"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Modal Body: Embedded Sandboxed Iframe */}
            <div style={{ flex: 1, position: 'relative', backgroundColor: '#f1f5f9' }}>
              <iframe
                srcDoc={activeReportDossier.html_content}
                title="Engineering Dossier Preview"
                sandbox="allow-same-origin allow-scripts"
                style={{
                  width: '100%',
                  height: '100%',
                  border: 'none',
                  backgroundColor: '#ffffff',
                }}
              />
            </div>

            {/* Modal Footer */}
            <div
              style={{
                padding: '10px 20px',
                borderTop: '1px solid #e2e8f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                backgroundColor: '#f8fafc',
                fontSize: '11px',
                color: '#64748b',
              }}
            >
              <div>
                Authoritative Dossier · KiCad 10 Schematic & 2D Layout · SPICE Oscilloscope · FEMM 4.2 FEA · IPC-9592B BOM · RS-274X Gerbers
              </div>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ fontSize: '11px', padding: '4px 14px' }}
                onClick={() => setActiveReportDossier(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
