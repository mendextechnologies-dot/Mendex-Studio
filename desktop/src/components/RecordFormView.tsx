import React, { useState } from 'react';
import {
  FileText,
  Copy,
  Check,
  Code,
  Sliders,
  ShieldCheck,
  ShieldAlert,
  Hash,
  ExternalLink,
  Layers,
  AlertTriangle,
  FileCode,
  Info,
  Tag,
  Clock,
  Database,
  Cpu,
} from 'lucide-react';

export interface RecordFormViewProps {
  record: any;
  title?: string;
  onOpenFile?: (path: string) => void;
  defaultMode?: 'form' | 'json';
}

function formatBytes(bytes?: number | null): string {
  if (bytes == null || isNaN(bytes)) return '-';
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]} (${bytes.toLocaleString()} bytes)`;
}

function humanizeKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
    .replace(/ V\b/g, ' (V)')
    .replace(/ A\b/g, ' (A)')
    .replace(/ W\b/g, ' (W)')
    .replace(/ Hz\b/g, ' (Hz)')
    .replace(/ Uh\b/g, ' (µH)')
    .replace(/ Mm\b/g, ' (mm)')
    .replace(/ M2\b/g, ' (m²)')
    .replace(/ Mm2\b/g, ' (mm²)')
    .replace(/ K\b/g, ' (K)')
    .replace(/ T\b/g, ' (T)')
    .replace(/ Sha256\b/g, ' SHA-256')
    .replace(/ Id\b/g, ' ID');
}

interface FormFieldProps {
  label: string;
  value: React.ReactNode;
  fieldKey?: string;
  mono?: boolean;
  copyable?: string;
  fullWidth?: boolean;
}

const FormField: React.FC<FormFieldProps> = ({ label, value, mono, copyable, fullWidth }) => {
  const [copied, setCopied] = useState(false);
  const onCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!copyable) return;
    navigator.clipboard.writeText(copyable);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 3,
        background: '#f8fafc',
        padding: '7px 10px',
        borderRadius: 6,
        border: '1px solid #e2e8f0',
        minWidth: 0,
        gridColumn: fullWidth ? '1 / -1' : undefined,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 6 }}>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.4px', color: '#64748b' }}>
          {label}
        </span>
        {copyable && (
          <button
            type="button"
            onClick={onCopy}
            title={`Copy ${label}`}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              padding: '1px 4px',
              fontSize: 10,
              color: copied ? '#10b981' : '#94a3b8',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 3,
            }}
          >
            {copied ? <Check size={11} /> : <Copy size={11} />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        )}
      </div>
      <div
        style={{
          fontSize: 12,
          fontWeight: 500,
          color: '#1e293b',
          wordBreak: 'break-word',
          fontFamily: mono ? 'var(--font-mono, monospace)' : 'inherit',
          lineHeight: '1.4',
        }}
      >
        {value != null && value !== '' ? value : <span style={{ color: '#94a3b8', fontStyle: 'italic' }}>null</span>}
      </div>
    </div>
  );
};

export const RecordFormView: React.FC<RecordFormViewProps> = ({
  record,
  title,
  onOpenFile,
  defaultMode = 'form',
}) => {
  const [viewMode, setViewMode] = useState<'form' | 'json'>(defaultMode);
  const [copiedAllJson, setCopiedAllJson] = useState(false);

  if (!record || typeof record !== 'object') {
    return <div style={{ padding: 12, color: '#64748b', fontSize: 12 }}>No record payload available.</div>;
  }

  const handleCopyJson = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(JSON.stringify(record, null, 2));
    setCopiedAllJson(true);
    setTimeout(() => setCopiedAllJson(false), 2000);
  };

  // Extract known categorical groups
  const {
    // Primary identification
    record_id,
    id,
    classification,
    kind,
    stage_id,
    attempt,
    sequence,
    schema_version,
    timestamp,

    // File / Artifact details
    relative_path,
    size_bytes,
    source,
    reason,
    snapshot_path,

    // Statuses
    engineering_status,
    review_status,
    effective_status,
    status,
    stale,
    snapshot_integrity,
    original_integrity,
    integrity,

    // Cryptographic hashes & IDs
    sha256,
    input_hash,
    assignment_id,
    project_id,
    revision_id,
    design_id,
    design_revision_id,

    // Payloads
    specification,
    parameters,
    inputs,
    result,
    results,
    assumptions,
    warnings,
    error,
    formula_reference,
    implementation,
    unit_conventions,

    // Everything else
    ...unhandled
  } = record;

  const actualRecordId = record_id || id;
  const actualEffectiveStatus = effective_status || engineering_status || status || 'NOT_EVALUATED';
  const effectiveReviewStatus = review_status || 'NOT_REVIEWED';

  // Extract sub-assumptions if present in specification
  const specAssumptions: string[] = Array.isArray(specification?.assumptions)
    ? specification.assumptions
    : Array.isArray(assumptions)
    ? assumptions
    : [];

  const effectiveWarnings: string[] = Array.isArray(warnings)
    ? warnings
    : warnings
    ? [String(warnings)]
    : [];

  return (
    <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* View Mode Toolbar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 8,
          background: '#f1f5f9',
          padding: '4px 8px',
          borderRadius: 6,
          border: '1px solid #e2e8f0',
        }}
      >
        <div style={{ display: 'inline-flex', alignItems: 'center', background: '#e2e8f0', borderRadius: 4, padding: 2 }}>
          <button
            type="button"
            onClick={() => setViewMode('form')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              padding: '4px 10px',
              fontSize: 11,
              fontWeight: 600,
              border: 'none',
              borderRadius: 3,
              cursor: 'pointer',
              background: viewMode === 'form' ? '#ffffff' : 'transparent',
              color: viewMode === 'form' ? '#1e293b' : '#64748b',
              boxShadow: viewMode === 'form' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <Sliders size={12} />
            <span>Form View</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode('json')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              padding: '4px 10px',
              fontSize: 11,
              fontWeight: 600,
              border: 'none',
              borderRadius: 3,
              cursor: 'pointer',
              background: viewMode === 'json' ? '#ffffff' : 'transparent',
              color: viewMode === 'json' ? '#1e293b' : '#64748b',
              boxShadow: viewMode === 'json' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <Code size={12} />
            <span>Raw JSON</span>
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {relative_path && onOpenFile && (
            <button
              type="button"
              onClick={() => onOpenFile(relative_path)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                padding: '3px 8px',
                fontSize: 11,
                fontWeight: 600,
                color: '#2563eb',
                background: '#eff6ff',
                border: '1px solid #bfdbfe',
                borderRadius: 4,
                cursor: 'pointer',
              }}
              title={`Open ${relative_path}`}
            >
              <ExternalLink size={11} />
              <span>Open Target</span>
            </button>
          )}

          <button
            type="button"
            onClick={handleCopyJson}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              padding: '3px 8px',
              fontSize: 11,
              fontWeight: 600,
              color: copiedAllJson ? '#10b981' : '#475569',
              background: '#ffffff',
              border: '1px solid #cbd5e1',
              borderRadius: 4,
              cursor: 'pointer',
            }}
            title="Copy full JSON record"
          >
            {copiedAllJson ? <Check size={11} /> : <Copy size={11} />}
            <span>{copiedAllJson ? 'Copied JSON' : 'Copy JSON'}</span>
          </button>
        </div>
      </div>

      {/* Raw JSON View Mode */}
      {viewMode === 'json' ? (
        <pre
          style={{
            fontSize: 11,
            whiteSpace: 'pre-wrap',
            overflowWrap: 'anywhere',
            background: '#0f172a',
            color: '#f8fafc',
            padding: 12,
            borderRadius: 6,
            maxHeight: 400,
            overflowY: 'auto',
            fontFamily: 'var(--font-mono, monospace)',
            userSelect: 'text',
          }}
        >
          {JSON.stringify(record, null, 2)}
        </pre>
      ) : (
        /* Form View Mode */
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Header Badges & Context */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: 8,
              padding: '8px 12px',
              background: '#f8fafc',
              borderRadius: 6,
              border: '1px solid #e2e8f0',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              {classification && (
                <span className="badge badge-blue" style={{ fontSize: 11 }}>
                  {String(classification).toUpperCase()}
                </span>
              )}
              {kind && (
                <span
                  style={{
                    fontSize: 11,
                    padding: '2px 8px',
                    borderRadius: 4,
                    background: '#e2e8f0',
                    color: '#334155',
                    fontWeight: 600,
                  }}
                >
                  {kind}
                </span>
              )}
              {stage_id && (
                <span style={{ fontSize: 11, color: '#64748b' }}>
                  Stage: <strong>{stage_id}</strong>
                </span>
              )}
              {attempt != null && (
                <span style={{ fontSize: 11, color: '#64748b' }}>
                  Attempt: <strong>#{attempt}</strong>
                </span>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span
                style={{
                  fontSize: 11,
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontWeight: 700,
                  background:
                    actualEffectiveStatus === 'PASS' || actualEffectiveStatus === 'RECORDED'
                      ? 'rgba(16, 185, 129, 0.15)'
                      : 'rgba(100, 116, 139, 0.15)',
                  color:
                    actualEffectiveStatus === 'PASS' || actualEffectiveStatus === 'RECORDED'
                      ? '#047857'
                      : '#475569',
                  border:
                    actualEffectiveStatus === 'PASS' || actualEffectiveStatus === 'RECORDED'
                      ? '1px solid rgba(16, 185, 129, 0.3)'
                      : '1px solid rgba(100, 116, 139, 0.3)',
                }}
              >
                {actualEffectiveStatus}
              </span>
              {review_status && (
                <span
                  style={{
                    fontSize: 11,
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontWeight: 700,
                    background:
                      effectiveReviewStatus === 'APPROVED'
                        ? 'rgba(16, 185, 129, 0.15)'
                        : 'rgba(245, 158, 11, 0.15)',
                    color: effectiveReviewStatus === 'APPROVED' ? '#047857' : '#92400e',
                    border:
                      effectiveReviewStatus === 'APPROVED'
                        ? '1px solid rgba(16, 185, 129, 0.3)'
                        : '1px solid rgba(245, 158, 11, 0.3)',
                  }}
                >
                  {effectiveReviewStatus}
                </span>
              )}
            </div>
          </div>

          {/* Section 1: Artifact & File Properties */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <h5 style={{ fontSize: 12, fontWeight: 700, color: '#334155', display: 'flex', alignItems: 'center', gap: 6 }}>
              <FileText size={14} style={{ color: '#2563eb' }} />
              <span>File & Operational Properties</span>
            </h5>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 8 }}>
              {relative_path && (
                <FormField
                  label="Relative File Path"
                  value={relative_path}
                  mono
                  copyable={relative_path}
                  fullWidth
                />
              )}
              {size_bytes != null && (
                <FormField
                  label="File Size"
                  value={formatBytes(size_bytes)}
                />
              )}
              {source && (
                <FormField
                  label="Source Agency / Engineer"
                  value={source}
                />
              )}
              {schema_version && (
                <FormField
                  label="Schema Version"
                  value={`v${schema_version}`}
                />
              )}
              {timestamp && (
                <FormField
                  label="Recorded Timestamp"
                  value={String(timestamp)}
                  mono
                />
              )}
              {reason && (
                <FormField
                  label="Engineering Reason / Intent"
                  value={reason}
                  fullWidth
                />
              )}
            </div>
          </div>

          {/* Section 2: Cryptographic Provenance & Evidence */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <h5 style={{ fontSize: 12, fontWeight: 700, color: '#334155', display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldCheck size={14} style={{ color: '#059669' }} />
              <span>Cryptographic Provenance & Snapshot Integrity</span>
            </h5>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 8 }}>
              {sha256 && (
                <FormField
                  label="SHA-256 Digest (Payload)"
                  value={sha256}
                  mono
                  copyable={sha256}
                  fullWidth
                />
              )}
              {input_hash && (
                <FormField
                  label="Input Hash"
                  value={input_hash}
                  mono
                  copyable={input_hash}
                  fullWidth
                />
              )}
              {snapshot_path && (
                <FormField
                  label="Immutable Snapshot Path"
                  value={snapshot_path}
                  mono
                  copyable={snapshot_path}
                  fullWidth
                />
              )}
              {actualRecordId && (
                <FormField
                  label="Record ID"
                  value={actualRecordId}
                  mono
                  copyable={actualRecordId}
                />
              )}
              {assignment_id && (
                <FormField
                  label="Assignment ID"
                  value={assignment_id}
                  mono
                  copyable={assignment_id}
                />
              )}
              {project_id && (
                <FormField
                  label="Project ID"
                  value={project_id}
                  mono
                  copyable={project_id}
                />
              )}
              {revision_id && (
                <FormField
                  label="Revision ID"
                  value={revision_id}
                  mono
                  copyable={revision_id}
                />
              )}
              <FormField
                label="Snapshot Integrity"
                value={
                  snapshot_integrity === false ? (
                    <span style={{ color: '#dc2626', fontWeight: 700 }}>FAILED</span>
                  ) : (
                    <span style={{ color: '#059669', fontWeight: 700 }}>VALID / UNALTERED</span>
                  )
                }
              />
              <FormField
                label="Original Integrity"
                value={
                  original_integrity === false ? (
                    <span style={{ color: '#dc2626', fontWeight: 700 }}>FAILED</span>
                  ) : (
                    <span style={{ color: '#059669', fontWeight: 700 }}>VALID / UNALTERED</span>
                  )
                }
              />
            </div>
          </div>

          {/* Section 3: Specification Parameters (if present) */}
          {specification && typeof specification === 'object' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <h5 style={{ fontSize: 12, fontWeight: 700, color: '#334155', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Sliders size={14} style={{ color: '#7c3aed' }} />
                <span>Specification Parameters</span>
              </h5>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 8 }}>
                {Object.entries(specification).map(([k, v]) => {
                  if (k === 'assumptions' || k === 'schema_version' || k === 'source') return null;
                  return (
                    <FormField
                      key={k}
                      label={humanizeKey(k)}
                      value={v == null ? null : String(v)}
                      mono={typeof v === 'number'}
                    />
                  );
                })}
              </div>
            </div>
          )}

          {/* Section 4: Engineering Assumptions & Constraints (if present) */}
          {specAssumptions.length > 0 && (
            <div
              style={{
                background: '#eff6ff',
                border: '1px solid #bfdbfe',
                borderRadius: 6,
                padding: '10px 14px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <Info size={14} style={{ color: '#2563eb' }} />
                <span style={{ fontSize: 11, fontWeight: 700, color: '#1e40af', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                  Engineering Assumptions & Baseline Constraints ({specAssumptions.length})
                </span>
              </div>
              <ul style={{ margin: '4px 0 0 16px', fontSize: 11, color: '#1e3a8a', lineHeight: '1.5' }}>
                {specAssumptions.map((item, idx) => (
                  <li key={idx} style={{ marginBottom: 4 }}>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Section 5: Calculation Inputs & Parameters (if present) */}
          {((parameters && typeof parameters === 'object') || (inputs && typeof inputs === 'object')) && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <h5 style={{ fontSize: 12, fontWeight: 700, color: '#334155', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Cpu size={14} style={{ color: '#0284c7' }} />
                <span>Input Parameters & Boundary Conditions</span>
              </h5>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 8 }}>
                {Object.entries(parameters || inputs || {}).map(([k, v]) => (
                  <FormField
                    key={k}
                    label={humanizeKey(k)}
                    value={v == null ? null : String(v)}
                    mono={typeof v === 'number'}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Section 6: Calculation Results & Outputs (if present) */}
          {((result && typeof result === 'object') || (results && typeof results === 'object')) && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <h5 style={{ fontSize: 12, fontWeight: 700, color: '#334155', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Layers size={14} style={{ color: '#059669' }} />
                <span>Calculated Results & Electrical Metrics</span>
              </h5>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 8 }}>
                {Object.entries(result || results || {}).map(([k, v]) => {
                  if (typeof v === 'object' && v !== null && !Array.isArray(v)) {
                    return null; // Skip sub-nested inputs already displayed
                  }
                  return (
                    <FormField
                      key={k}
                      label={humanizeKey(k)}
                      value={v == null ? null : String(v)}
                      mono={typeof v === 'number'}
                    />
                  );
                })}
              </div>
            </div>
          )}

          {/* Section 7: Warnings or Errors (if present) */}
          {effectiveWarnings.length > 0 && (
            <div
              style={{
                background: '#fffbeb',
                border: '1px solid #fde68a',
                borderRadius: 6,
                padding: '10px 14px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <AlertTriangle size={14} style={{ color: '#d97706' }} />
                <span style={{ fontSize: 11, fontWeight: 700, color: '#92400e', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
                  Calculation Warnings ({effectiveWarnings.length})
                </span>
              </div>
              <ul style={{ margin: '4px 0 0 16px', fontSize: 11, color: '#78350f', lineHeight: '1.5' }}>
                {effectiveWarnings.map((item, idx) => (
                  <li key={idx} style={{ marginBottom: 4 }}>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {error && (
            <div
              style={{
                background: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: 6,
                padding: '10px 14px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <AlertTriangle size={14} style={{ color: '#dc2626' }} />
                <span style={{ fontSize: 11, fontWeight: 700, color: '#991b1b', textTransform: 'uppercase' }}>
                  Execution Error
                </span>
              </div>
              <p style={{ margin: 0, fontSize: 11, color: '#7f1d1d' }}>{String(error)}</p>
            </div>
          )}

          {/* Section 8: Implementation Details (if present) */}
          {(implementation || formula_reference || unit_conventions) && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <h5 style={{ fontSize: 12, fontWeight: 700, color: '#334155', display: 'flex', alignItems: 'center', gap: 6 }}>
                <FileCode size={14} style={{ color: '#475569' }} />
                <span>Implementation Reference & Conventions</span>
              </h5>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 8 }}>
                {implementation && (
                  <FormField
                    label="Implementation Function"
                    value={implementation}
                    mono
                    copyable={implementation}
                    fullWidth
                  />
                )}
                {formula_reference && (
                  <FormField
                    label="Formula Reference"
                    value={formula_reference}
                    fullWidth
                  />
                )}
                {unit_conventions && (
                  <FormField
                    label="Unit Conventions"
                    value={unit_conventions}
                    fullWidth
                  />
                )}
              </div>
            </div>
          )}

          {/* Section 9: Additional Unmapped Metadata (guarantees zero data loss) */}
          {Object.keys(unhandled).length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <h5 style={{ fontSize: 12, fontWeight: 700, color: '#64748b', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Database size={14} />
                <span>Additional Record Metadata</span>
              </h5>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 8 }}>
                {Object.entries(unhandled).map(([k, v]) => (
                  <FormField
                    key={k}
                    label={humanizeKey(k)}
                    value={
                      typeof v === 'object' && v !== null
                        ? JSON.stringify(v)
                        : v == null
                        ? null
                        : String(v)
                    }
                    mono={typeof v === 'number' || typeof v === 'object'}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
