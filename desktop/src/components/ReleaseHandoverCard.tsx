import React, { useEffect, useState, useMemo } from 'react';
import {
  PackageCheck,
  Archive,
  RefreshCw,
  FolderOpen,
  Download,
  Copy,
  Check,
  FileCode,
  Layers,
  Cpu,
  FileSpreadsheet,
  ShieldCheck,
  AlertTriangle,
  Search,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  FileCheck2,
} from 'lucide-react';
import { api } from '../api/client';
import type { ReleasePackageData, ReleaseDeliverableItem } from '../api/types';

interface ReleaseHandoverCardProps {
  revisionId: string;
  projectCode: string;
  projectName: string;
  onOpenProjectFile?: (relativePath: string) => void;
}

export const ReleaseHandoverCard: React.FC<ReleaseHandoverCardProps> = ({
  revisionId,
  projectCode,
  projectName,
  onOpenProjectFile,
}) => {
  const [data, setData] = useState<ReleasePackageData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [building, setBuilding] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedSha, setCopiedSha] = useState<boolean>(false);
  const [copiedManifest, setCopiedManifest] = useState<boolean>(false);
  const [copiedItemSha, setCopiedItemSha] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [manifestExpanded, setManifestExpanded] = useState<boolean>(false);
  const [authorName, setAuthorName] = useState<string>('Lead Systems Engineer');

  const loadData = () => {
    setLoading(true);
    setError(null);
    api.getReleasePackage(revisionId)
      .then((res: ReleasePackageData) => {
        setData(res);
      })
      .catch((err: any) => {
        setError(err.message || String(err));
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [revisionId]);

  const handleBuild = () => {
    setBuilding(true);
    setError(null);
    api.buildReleasePackage(revisionId, authorName)
      .then((res: ReleasePackageData) => {
        setData(res);
      })
      .catch((err: any) => {
        setError(err.message || String(err));
      })
      .finally(() => setBuilding(false));
  };

  const handleReveal = () => {
    api.revealReleasePackage(revisionId).catch((err: any) => {
      console.error('Failed to reveal package folder:', err);
    });
  };

  const handleCopySha = (sha: string) => {
    navigator.clipboard.writeText(sha);
    setCopiedSha(true);
    setTimeout(() => setCopiedSha(false), 2000);
  };

  const handleCopyManifest = () => {
    if (!data) return;
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopiedManifest(true);
    setTimeout(() => setCopiedManifest(false), 2000);
  };

  const handleCopyItemSha = (sha: string) => {
    navigator.clipboard.writeText(sha);
    setCopiedItemSha(sha);
    setTimeout(() => setCopiedItemSha(null), 2000);
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const filteredContents = useMemo(() => {
    if (!data || !data.contents) return [];
    return data.contents.filter((item) => {
      const matchesCategory =
        activeCategory === 'all' || item.category === activeCategory;
      const matchesSearch =
        !searchQuery ||
        item.file.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.sha256.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [data, activeCategory, searchQuery]);

  const categoryMeta: Record<string, { label: string; icon: any; color: string; bg: string }> = {
    cad: { label: 'CAD & Netlists', icon: FileCode, color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.1)' },
    fabrication: { label: 'RS-274X Fabrication', icon: Layers, color: '#10b981', bg: 'rgba(16, 185, 129, 0.1)' },
    assembly: { label: 'SMT Assembly & CPL', icon: Cpu, color: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.1)' },
    bom: { label: 'Procurement BOM', icon: FileSpreadsheet, color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)' },
    testing_qa: { label: 'Quality & Test Plans', icon: ShieldCheck, color: '#06b6d4', bg: 'rgba(6, 182, 212, 0.1)' },
    other: { label: 'Deliverables', icon: Archive, color: '#64748b', bg: 'rgba(100, 116, 139, 0.1)' },
  };

  return (
    <div
      style={{
        background: '#ffffff',
        borderRadius: 8,
        border: '1px solid #cbd5e1',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
        padding: '24px',
        marginBottom: '24px',
      }}
    >
      {/* Header Strip */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 16,
          borderBottom: '1px solid #e2e8f0',
          paddingBottom: 16,
          marginBottom: 20,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 8,
              background: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              boxShadow: '0 2px 4px rgba(59, 130, 246, 0.25)',
            }}
          >
            <PackageCheck size={24} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: '#0f172a', margin: 0 }}>
                Formal Production Release Handover Package Builder
              </h3>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: 12,
                  background: data?.package_exists ? '#dcfce7' : '#fef3c7',
                  color: data?.package_exists ? '#15803d' : '#b45309',
                  border: `1px solid ${data?.package_exists ? '#bbf7d0' : '#fde68a'}`,
                }}
              >
                {data?.package_exists ? '✓ RELEASE BUNDLE READY' : '⏳ PENDING COMPILATION'}
              </span>
            </div>
            <p style={{ fontSize: 12, color: '#64748b', margin: '4px 0 0 0' }}>
              Multi-disciplinary manufacturing archive bundling KiCad schematics, Gerbers, drills, CPL placement, BOM schedules, laboratory test plan, and SHA-256 release manifest.
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={loadData}
            disabled={loading || building}
            style={{
              padding: '7px 12px',
              borderRadius: 6,
              background: '#f8fafc',
              border: '1px solid #cbd5e1',
              color: '#475569',
              fontSize: 12,
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              cursor: 'pointer',
            }}
            title="Refresh package manifest"
          >
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            Refresh
          </button>

          {data?.package_exists && (
            <button
              onClick={handleReveal}
              style={{
                padding: '7px 12px',
                borderRadius: 6,
                background: '#f1f5f9',
                border: '1px solid #cbd5e1',
                color: '#334155',
                fontSize: 12,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                cursor: 'pointer',
              }}
              title="Reveal release package folder in Windows Explorer"
            >
              <FolderOpen size={13} color="#2563eb" />
              Reveal in Explorer
            </button>
          )}

          <button
            onClick={handleBuild}
            disabled={loading || building}
            style={{
              padding: '7px 16px',
              borderRadius: 6,
              background: 'linear-gradient(135deg, #1e40af 0%, #2563eb 100%)',
              border: 'none',
              color: '#ffffff',
              fontSize: 12,
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              cursor: building ? 'not-allowed' : 'pointer',
              boxShadow: '0 2px 4px rgba(37, 99, 235, 0.25)',
              opacity: building ? 0.8 : 1,
            }}
          >
            <Archive size={14} className={building ? 'spin' : ''} />
            {building ? 'Synthesizing Archive...' : data?.package_exists ? 'Recompile Release Package' : 'Build Release Handover Package'}
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            padding: '12px 16px',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: 6,
            color: '#b91c1c',
            fontSize: 13,
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Executive Telemetry Strip */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: 12,
          marginBottom: 20,
        }}
      >
        <div
          style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: 6,
            padding: '12px 16px',
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
            Release Deliverables
          </div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', marginTop: 4 }}>
            {data?.package_exists ? data.contents.length : data?.available_candidates_count ?? 0}
            <span style={{ fontSize: 12, fontWeight: 500, color: '#64748b', marginLeft: 6 }}>
              {data?.package_exists ? 'files sealed' : 'files detected'}
            </span>
          </div>
          <div style={{ fontSize: 11, color: '#10b981', marginTop: 2 }}>
            5 engineering disciplines
          </div>
        </div>

        <div
          style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: 6,
            padding: '12px 16px',
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
            Package Archive Size
          </div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', marginTop: 4 }}>
            {data?.package_exists ? formatBytes(data.package_size_bytes) : '—'}
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
            DEFLATE compressed ZIP
          </div>
        </div>

        <div
          style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: 6,
            padding: '12px 16px',
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
            Attributable Signatory
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', marginTop: 4, textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
            {data?.generator || authorName}
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
            {data?.generated_at ? new Date(data.generated_at).toLocaleString() : 'Pending sign-off'}
          </div>
        </div>

        <div
          style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: 6,
            padding: '12px 16px',
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
            Manifest Governance
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', marginTop: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
            <ShieldCheck size={16} color="#16a34a" />
            SHA-256 Registered
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
            Immutable design package
          </div>
        </div>
      </div>

      {/* Package Filename & Fingerprint Ribbon */}
      {data?.package_exists && (
        <div
          style={{
            background: '#f0fdf4',
            border: '1px solid #bbf7d0',
            borderRadius: 6,
            padding: '12px 16px',
            marginBottom: 20,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <FileCheck2 size={20} color="#15803d" />
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#166534' }}>
                {data.package_filename}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 2 }}>
                <span style={{ fontSize: 11, color: '#15803d', fontFamily: 'monospace' }}>
                  SHA256: {data.package_sha256}
                </span>
                <button
                  onClick={() => data.package_sha256 && handleCopySha(data.package_sha256)}
                  style={{
                    background: 'none',
                    border: 'none',
                    padding: '2px 4px',
                    cursor: 'pointer',
                    color: '#15803d',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 3,
                    fontSize: 10,
                  }}
                  title="Copy SHA-256 fingerprint"
                >
                  {copiedSha ? <Check size={11} color="#16a34a" /> : <Copy size={11} />}
                  {copiedSha ? 'Copied' : 'Copy'}
                </button>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              onClick={handleCopyManifest}
              style={{
                padding: '6px 12px',
                borderRadius: 5,
                background: '#ffffff',
                border: '1px solid #bbf7d0',
                color: '#166534',
                fontSize: 11,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                cursor: 'pointer',
              }}
            >
              {copiedManifest ? <Check size={12} color="#16a34a" /> : <Copy size={12} />}
              {copiedManifest ? 'Manifest Copied!' : 'Copy Manifest JSON'}
            </button>
            <button
              onClick={() => setManifestExpanded(!manifestExpanded)}
              style={{
                padding: '6px 12px',
                borderRadius: 5,
                background: '#ffffff',
                border: '1px solid #bbf7d0',
                color: '#166534',
                fontSize: 11,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                cursor: 'pointer',
              }}
            >
              {manifestExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {manifestExpanded ? 'Hide Raw Manifest' : 'View Manifest'}
            </button>
          </div>
        </div>
      )}

      {/* Raw Manifest Viewer Drawer */}
      {manifestExpanded && data && (
        <div
          style={{
            background: '#0f172a',
            borderRadius: 6,
            padding: 16,
            marginBottom: 20,
            overflowX: 'auto',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8' }}>
              release_manifest.json (Cryptographic Deliverables Register)
            </span>
            <button
              onClick={handleCopyManifest}
              style={{
                background: 'rgba(255,255,255,0.1)',
                border: 'none',
                color: '#f8fafc',
                padding: '4px 8px',
                borderRadius: 4,
                fontSize: 11,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              {copiedManifest ? <Check size={11} color="#4ade80" /> : <Copy size={11} />}
              Copy
            </button>
          </div>
          <pre style={{ margin: 0, fontSize: 11, fontFamily: 'monospace', color: '#e2e8f0', lineHeight: 1.5, maxHeight: 260, overflowY: 'auto' }}>
            {JSON.stringify(
              {
                product_code: data.product_code,
                product_name: data.product_name,
                revision: data.revision_label,
                package: data.package_filename,
                archive_sha256: data.package_sha256,
                size_bytes: data.package_size_bytes,
                generated_at: data.generated_at,
                generator: data.generator,
                total_deliverables: data.contents.length,
                governance_notice: data.governance_notice,
                contents: data.contents,
              },
              null,
              2
            )}
          </pre>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
          marginBottom: 16,
        }}
      >
        {/* Category Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <button
            onClick={() => setActiveCategory('all')}
            style={{
              padding: '5px 10px',
              borderRadius: 6,
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              border: activeCategory === 'all' ? '1px solid #2563eb' : '1px solid #e2e8f0',
              background: activeCategory === 'all' ? '#eff6ff' : '#ffffff',
              color: activeCategory === 'all' ? '#1d4ed8' : '#64748b',
            }}
          >
            All Items ({data?.contents?.length || 0})
          </button>
          {Object.entries(categoryMeta).map(([catKey, meta]) => {
            const count = data?.categories?.[catKey]?.length || 0;
            if (count === 0 && catKey === 'other') return null;
            const Icon = meta.icon;
            const isActive = activeCategory === catKey;
            return (
              <button
                key={catKey}
                onClick={() => setActiveCategory(catKey)}
                style={{
                  padding: '5px 10px',
                  borderRadius: 6,
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                  border: isActive ? `1px solid ${meta.color}` : '1px solid #e2e8f0',
                  background: isActive ? meta.bg : '#ffffff',
                  color: isActive ? meta.color : '#64748b',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 5,
                }}
              >
                <Icon size={12} color={isActive ? meta.color : '#94a3b8'} />
                {meta.label} ({count})
              </button>
            );
          })}
        </div>

        {/* Search */}
        <div style={{ position: 'relative', width: 220 }}>
          <Search size={13} style={{ position: 'absolute', left: 9, top: 9, color: '#94a3b8' }} />
          <input
            type="text"
            placeholder="Search deliverables / sha..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '6px 10px 6px 28px',
              borderRadius: 6,
              border: '1px solid #cbd5e1',
              fontSize: 11,
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Deliverables Table */}
      <div style={{ border: '1px solid #e2e8f0', borderRadius: 6, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
          <thead>
            <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569', textAlign: 'left' }}>
              <th style={{ padding: '8px 12px', fontWeight: 600, width: 140 }}>Category</th>
              <th style={{ padding: '8px 12px', fontWeight: 600 }}>Deliverable File</th>
              <th style={{ padding: '8px 12px', fontWeight: 600, width: 90 }}>Size</th>
              <th style={{ padding: '8px 12px', fontWeight: 600 }}>SHA-256 Digest</th>
              <th style={{ padding: '8px 12px', fontWeight: 600, textAlign: 'right', width: 80 }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredContents.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ padding: '24px', textAlign: 'center', color: '#94a3b8' }}>
                  {data?.package_exists
                    ? 'No deliverables match the active category and filter criteria.'
                    : 'Release package pending compilation. Click "Build Release Handover Package" above to bundle deliverables.'}
                </td>
              </tr>
            ) : (
              filteredContents.map((item, idx) => {
                const meta = categoryMeta[item.category] || categoryMeta.other;
                const Icon = meta.icon;
                return (
                  <tr
                    key={item.file + idx}
                    style={{
                      borderBottom: '1px solid #f1f5f9',
                      background: idx % 2 === 0 ? '#ffffff' : '#fafafa',
                    }}
                  >
                    <td style={{ padding: '8px 12px' }}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          padding: '2px 7px',
                          borderRadius: 4,
                          background: meta.bg,
                          color: meta.color,
                          fontWeight: 600,
                          fontSize: 10,
                        }}
                      >
                        <Icon size={10} color={meta.color} />
                        {meta.label}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px', fontWeight: 600, color: '#1e293b', fontFamily: 'monospace' }}>
                      {item.file}
                    </td>
                    <td style={{ padding: '8px 12px', color: '#64748b' }}>
                      {formatBytes(item.size_bytes)}
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ fontFamily: 'monospace', color: '#475569', fontSize: 10 }}>
                          {item.sha256 ? `${item.sha256.slice(0, 16)}...` : '—'}
                        </span>
                        {item.sha256 && (
                          <button
                            onClick={() => handleCopyItemSha(item.sha256)}
                            style={{
                              background: 'none',
                              border: 'none',
                              cursor: 'pointer',
                              color: '#94a3b8',
                              padding: 2,
                            }}
                            title="Copy full SHA-256"
                          >
                            {copiedItemSha === item.sha256 ? (
                              <Check size={11} color="#16a34a" />
                            ) : (
                              <Copy size={11} />
                            )}
                          </button>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                      {onOpenProjectFile && (
                        <button
                          onClick={() => onOpenProjectFile(item.file)}
                          style={{
                            background: 'none',
                            border: '1px solid #cbd5e1',
                            borderRadius: 4,
                            padding: '3px 8px',
                            cursor: 'pointer',
                            color: '#334155',
                            fontSize: 10,
                            fontWeight: 600,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 3,
                          }}
                        >
                          <ExternalLink size={10} />
                          Open
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Governance & Engineering Notice */}
      <div
        style={{
          marginTop: 18,
          padding: '12px 16px',
          background: '#f8fafc',
          borderLeft: '3px solid #2563eb',
          borderRadius: 4,
          fontSize: 11,
          color: '#475569',
          lineHeight: 1.5,
        }}
      >
        <strong>Engineering Governance & Quality Qualification Notice:</strong>{' '}
        {data?.governance_notice ||
          'All manufacturing and test package files are cryptographically registered with SHA-256 checksums. Design-to-manufacturing release requires attributable human sign-off; physical testing verification must precede production fabrication per project rules.'}
      </div>
    </div>
  );
};
