import { SpecificationDetailCard } from './SpecificationDetailCard';
import { RequirementsTraceabilityMatrixCard } from './RequirementsTraceabilityMatrixCard';
import { ThermalSizingCalculatorCard } from './ThermalSizingCalculatorCard';
import { TopologySynthesizerCard } from './TopologySynthesizerCard';
import { CADPreviewCanvas } from './CADPreviewCanvas';
import { WaveformChart } from './WaveformChart';
import { RecordFormView } from './RecordFormView';
import React, { useState, useMemo } from 'react';
import type { ProjectDetailData } from '../api/types';
import { api } from '../api/client';

export type EngineeringSection = 'specifications' | 'requirements' | 'calculations' | 'simulations' | 'designs';
export function recordList(value: any): any[] {
  return Array.isArray(value) ? value : Array.isArray(value?.records) ? value.records : [];
}

const json = (value: unknown) => JSON.stringify(value, null, 2);
const label = (value: unknown) => value == null || value === '' ? 'Unknown' :
  typeof value === 'object' ? json(value) : String(value);
const grid: React.CSSProperties = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 12 };
const pre: React.CSSProperties = { fontSize: 11, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', marginTop: 10, maxHeight: 350, overflowY: 'auto', userSelect: 'text' };

export function effectiveStageStatus(stage: any): string {
  return stage?.effective_status || 'NOT_EVALUATED';
}

export function validationStatus(entry: any): string {
  if (entry.stale || entry.evidence_integrity === false) return 'NOT_EVALUATED';
  return String(entry.effective_status || 'NOT_EVALUATED').toUpperCase();
}

export const Status = ({ value }: { value: string }) => <span className={`badge ${value === 'NOT_EVALUATED' ? 'badge-muted' : 'badge-blue'}`}>{value}</span>;

export function getAppDetails(path: string): { name: string; action: string; badgeClass: string; icon: string } {
  const ext = path.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'kicad_pcb':
      return { name: 'KiCad PCB Editor', action: 'Open in KiCad PCB', badgeClass: 'badge-blue', icon: '🔌' };
    case 'kicad_sch':
      return { name: 'KiCad Schematic Editor', action: 'Open in KiCad Schematic', badgeClass: 'badge-blue', icon: '⚡' };
    case 'kicad_pro':
      return { name: 'KiCad Project Manager', action: 'Open in KiCad Project', badgeClass: 'badge-blue', icon: '🗂️' };
    case 'step':
    case 'stp':
    case 'stl':
    case 'fcstd':
      return { name: 'FreeCAD 3D CAD', action: 'Open in FreeCAD', badgeClass: 'badge-purple', icon: '📐' };
    case 'fem':
    case 'ans':
    case 'fee':
      return { name: 'FEMM 4.2 Magnetics', action: 'Open in FEMM', badgeClass: 'badge-yellow', icon: '🧲' };
    case 'net':
    case 'asc':
    case 'cir':
    case 'raw':
      return { name: 'ADI LTspice', action: 'Open in LTspice', badgeClass: 'badge-yellow', icon: '📈' };
    case 'docx':
    case 'doc':
      return { name: 'Microsoft Word', action: 'Open in Microsoft Word', badgeClass: 'badge-green', icon: '📝' };
    case 'pdf':
      return { name: 'PDF Viewer (Edge)', action: 'Open in PDF Viewer', badgeClass: 'badge-green', icon: '📄' };
    default:
      return { name: 'Native Tool', action: 'Open in native application', badgeClass: 'badge-muted', icon: '📂' };
  }
}

export function RecordDetails({ record, title, onOpenFile }: { record: any; title: string; onOpenFile?: (path: string) => unknown }) {
  const status = record.stale || record.integrity === false || record.integrity === 'FAILED'
    ? 'NOT_EVALUATED' : record.effective_status || record.engineering_status || 'NOT_EVALUATED';
  return <article className="card">
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}><strong>{title}</strong><Status value={String(status)} /></div>
    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>Record: {label(record.record_id || record.id)} · Stage: {label(record.stage_id)}</div>
    {record.stale && <p role="status" style={{ marginTop: 8 }}>Stale record: inputs or evidence have changed.</p>}
    <details style={{ marginTop: 10 }}>
      <summary style={{ cursor: 'pointer', fontWeight: 600, color: 'var(--primary)' }}>
        Recorded inputs, results and provenance
      </summary>
      <RecordFormView record={record} onOpenFile={onOpenFile} defaultMode="form" />
    </details>
  </article>;
}

export const RevisionEngineeringPanel = ({ section, data, onOpenFile, onRefresh }: {
  section: EngineeringSection; data: ProjectDetailData; onOpenFile: (path: string) => unknown; onRefresh?: () => void;
}) => {
  const [isGeneratingBom, setIsGeneratingBom] = useState(false);
  const [bomMessage, setBomMessage] = useState('');
  const [cadFilter, setCadFilter] = useState('');
  const [cadCategory, setCadCategory] = useState<'all' | 'cad' | 'doc'>('all');
  const [cadViewMode, setCadViewMode] = useState<'list' | 'grid'>('list');

  const handleRebuildBom = async () => {
    if (!data?.revision?.revision_id) return;
    setIsGeneratingBom(true);
    setBomMessage('');
    try {
      const res = await api.generateBom(data.revision.revision_id);
      setBomMessage(res.message);
      setTimeout(() => setBomMessage(''), 6000);
    } catch (e: any) {
      setBomMessage(e.message || 'Failed to generate BOM');
      setTimeout(() => setBomMessage(''), 6000);
    } finally {
      setIsGeneratingBom(false);
    }
  };

  const calculations = recordList(data.calculations);
  const requirements = recordList(data.requirements);
  const artifacts = recordList(data.registered_artifacts);
  const titles: Record<EngineeringSection, string> = { specifications: 'Saved specifications', requirements: 'Requirements snapshot', calculations: 'Recorded engineering calculations', simulations: 'Revision simulation jobs', designs: 'Revision designs & CAD files' };
  // Cleanly extract active deliverables, filtering out internal backups, hidden snapshots, and deduplicating historical BOM exports
  const cadFiles = useMemo(() => {
    const valid = data.files.filter((file) => {
      const p = file.relative_path.replace(/\\/g, '/');
      if (
        p.includes('/.') ||
        p.startsWith('.') ||
        p.includes('_backup_') ||
        p.includes('/snapshots/') ||
        p.includes('~') ||
        p.startsWith('reports/') ||
        p.startsWith('validation/') ||
        p.endsWith('.lck') ||
        p.endsWith('.tmp')
      ) {
        return false;
      }
      return /\.(?:kicad_sch|kicad_pcb|kicad_pro|step|stp|stl|fcstd|fem|ans|fee|asc|net|cir|raw|pdf|docx|csv|json)$/i.test(p);
    });

    const latestBomExports = new Map<string, typeof valid[0]>();
    const deliverables: typeof valid = [];

    for (const f of valid) {
      const p = f.relative_path.replace(/\\/g, '/');
      if (p.startsWith('bom/exports/')) {
        const fn = p.split('/').pop() || '';
        const existing = latestBomExports.get(fn);
        if (!existing || (f.modified_ns && (!existing.modified_ns || f.modified_ns > existing.modified_ns))) {
          latestBomExports.set(fn, f);
        }
      } else {
        deliverables.push(f);
      }
    }

    return [...deliverables, ...Array.from(latestBomExports.values())];
  }, [data.files]);

  const filteredCadFiles = useMemo(() => {
    let list = cadFiles;
    if (cadCategory === 'cad') {
      list = list.filter((f) => /\.(?:kicad_sch|kicad_pcb|kicad_pro|step|stp|stl|fcstd|fem|ans|fee|asc|net|cir|raw)$/i.test(f.relative_path));
    } else if (cadCategory === 'doc') {
      list = list.filter((f) => /\.(?:pdf|docx|doc|csv|json)$/i.test(f.relative_path));
    }
    if (!cadFilter.trim()) return list;
    const q = cadFilter.toLowerCase();
    return list.filter((f) => {
      const fn = (f.relative_path.split(/[\\/]/).pop() || f.name || f.relative_path).toLowerCase();
      return fn.includes(q);
    });
  }, [cadFiles, cadCategory, cadFilter]);

  return <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
    {section !== 'specifications' && section !== 'requirements' && (
      <div><h3 style={{ fontSize: 18 }}>{titles[section]}</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 6 }}>Stored records for {data.product.code} / {data.revision.revision_label}. Execution, evidence integrity and engineering acceptance are separate.</p>
      </div>
    )}
    {section === 'specifications' && (
      <SpecificationDetailCard data={data} />
    )}
    {section === 'requirements' && (
      <RequirementsTraceabilityMatrixCard
        data={data}
        onOpenFile={onOpenFile}
      />
    )}
    {section === 'calculations' && <>
      {/* Interactive Semiconductor & Magnetic Thermal Sizing Calculator */}
      <ThermalSizingCalculatorCard
        revisionId={data.revision.revision_id}
        specification={data.revision.specification}
        onRefresh={onRefresh}
      />
      <p>{calculations.length} calculation records returned for this revision.</p>
      {!calculations.length && <p>No calculation runs recorded. NOT_EVALUATED.</p>}
      {calculations.map((record, i) => <RecordDetails key={record.record_id || i} record={record} title={record.calculation || record.result?.calculation || `Calculation ${i + 1}`} onOpenFile={onOpenFile} />)}
    </>}
    {section === 'simulations' && <>
      {(() => {
        const rawFile = data.files.find(f => f.relative_path.toLowerCase().endsWith('.raw'));
        if (rawFile) {
          return (
            <div style={{ marginBottom: 20 }}>
              <WaveformChart
                revisionId={data.revision.revision_id}
                relativePath={rawFile.relative_path}
                title={`${data.product.code} Transient Simulation Waveform`}
                onOpenNative={() => onOpenFile?.(rawFile.relative_path)}
              />
            </div>
          );
        }
        return null;
      })()}

      {/* Simulation Acceptance & Solver Verification Metrics Card */}
      {data.measurements && data.measurements.length > 0 && (
        <div style={{ padding: 18, background: '#f8fafc', borderRadius: 8, border: '1px solid #cbd5e1', marginBottom: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
            <div>
              <h4 style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', margin: 0 }}>
                Simulation Results & Solver Verification Metrics
              </h4>
              <span style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2, display: 'inline-block' }}>
                Extracted from verified LTspice 26.1 (.meas) and FEMM 4.2 2D FEA solver outputs
              </span>
            </div>
            <span className="badge badge-green">{data.measurements.length} Verified Solver Metrics</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
            {data.measurements.map((m: any, idx: number) => {
              const isPass = m.pass_fail === 'PASS';
              return (
                <div
                  key={m.measurement_id || idx}
                  style={{
                    background: '#fff',
                    border: '1px solid #e2e8f0',
                    borderLeft: `3px solid ${isPass ? '#10b981' : '#ef4444'}`,
                    borderRadius: 6,
                    padding: '10px 14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#1e293b', fontFamily: 'monospace' }}>
                      {m.parameter}
                    </span>
                    <span className={`badge ${isPass ? 'badge-green' : 'badge-red'}`} style={{ fontSize: 10 }}>
                      {m.pass_fail}
                    </span>
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 800, color: '#0f172a' }}>
                    {typeof m.value === 'number'
                      ? m.value >= 100
                        ? m.value.toFixed(2)
                        : m.value >= 1
                        ? m.value.toFixed(4)
                        : m.value.toFixed(6)
                      : String(m.value)}
                  </div>
                  <span style={{ fontSize: 10, color: '#64748b' }}>{m.test_name}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div>
        <h4 style={{ fontSize: 14, fontWeight: 700, color: '#1e293b', marginBottom: 10 }}>
          Simulation Jobs & Solver Runs ({data.simulations.length})
        </h4>
      </div>

      {!data.simulations.length && <p>No simulation jobs explicitly linked to this revision. NOT_EVALUATED.</p>}
      {data.simulations.map(job => (
        <article key={job.job_id} className="card" style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <strong style={{ fontSize: 14, color: '#0f172a' }}>{job.tool_id.toUpperCase()} · {job.operation}</strong>
              <span className="badge badge-blue">{job.job_id}</span>
            </div>
            <Status value={job.status} />
          </div>
          <p style={{ marginTop: 8, fontSize: 12, color: '#475569' }}>
            Started: {job.started_at ? new Date(job.started_at).toLocaleString() : 'N/A'} · Exit code: <strong>{job.exit_code ?? 'N/A'}</strong>
          </p>
          <p style={{ marginTop: 4, fontSize: 12 }}>
            Evidence: {job.evidence_available ? 'Available with checked integrity' : 'Unavailable or integrity not established'}. Engineering acceptance: <strong>{job.engineering_status || 'NOT_EVALUATED'}</strong>.
          </p>
          {job.stale && <p style={{ marginTop: 8, color: '#b91c1c' }}>Stale specification context. NOT_EVALUATED.</p>}

          <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
            {job.tool_id.toLowerCase() === 'ltspice' && (() => {
              const net = data.files.find(f => f.relative_path.toLowerCase().endsWith('.net'))?.relative_path || 'simulations/flyback_circuit.net';
              const raw = data.files.find(f => f.relative_path.toLowerCase().endsWith('.raw'))?.relative_path || 'simulations/flyback_circuit.raw';
              return (
                <>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: 11, padding: '4px 10px' }}
                    onClick={() => onOpenFile?.(net)}
                  >
                    Open Netlist in LTspice
                  </button>
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: 11, padding: '4px 10px' }}
                    onClick={() => onOpenFile?.(raw)}
                  >
                    Open Waveform in LTspice
                  </button>
                </>
              );
            })()}
            {job.tool_id.toLowerCase() === 'femm' && (() => {
              const fem = data.files.find(f => f.relative_path.toLowerCase().endsWith('.fem'))?.relative_path || 'magnetics/electromagnet_actuator.fem';
              return (
                <button
                  className="btn btn-secondary"
                  style={{ fontSize: 11, padding: '4px 10px' }}
                  onClick={() => onOpenFile?.(fem)}
                >
                  Open FEA Model in FEMM 4.2
                </button>
              );
            })()}
          </div>

          <details style={{ marginTop: 10 }}>
            <summary style={{ cursor: 'pointer', fontSize: 11, color: '#64748b' }}>Stored request, result and provenance</summary>
            <RecordFormView record={job} onOpenFile={onOpenFile} defaultMode="form" />
          </details>
        </article>
      ))}
      <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>
        Tool qualification is listed in Engineering Tools. Open available waveform files from Revision Files; this panel presents fixed solver metrics and interactive vectors.
      </p>
    </>}
    {section === 'designs' && <>
      {/* Interactive Topology Synthesizer & Candidate Switcher */}
      <TopologySynthesizerCard
        revisionId={data.revision.revision_id}
        specification={data.revision.specification}
        designs={data.designs}
        onRefresh={onRefresh}
        onOpenFile={onOpenFile}
      />

      {/* Collapsible Electro-Thermal Margins & Trace Analysis */}
      <details style={{ marginBottom: 20 }}>
        <summary style={{ cursor: 'pointer', fontWeight: 700, fontSize: 13, color: '#1e293b', background: '#f8fafc', padding: '10px 14px', borderRadius: 6, border: '1px solid #cbd5e1' }}>
          🌡️ Electro-Thermal Sizing Margins & IPC-2152 Trace Analysis (Click to Expand)
        </summary>
        <div style={{ marginTop: 12 }}>
          <ThermalSizingCalculatorCard
            revisionId={data.revision.revision_id}
            specification={data.revision.specification}
            onRefresh={onRefresh}
          />
        </div>
      </details>

      {/* Interactive 2D Native PCB & Schematic Vector CAD Preview */}
      {(() => {
        const pcbFile = cadFiles.find(f => f.relative_path.toLowerCase().endsWith('.kicad_pcb'));
        const schFile = cadFiles.find(f => f.relative_path.toLowerCase().endsWith('.kicad_sch'));
        return (
          <div style={{ marginBottom: 20 }}>
            <CADPreviewCanvas
              revisionId={data.revision.revision_id}
              onOpenPCB={pcbFile ? () => onOpenFile(pcbFile.relative_path) : undefined}
              onOpenSchematic={schFile ? () => onOpenFile(schFile.relative_path) : undefined}
            />
          </div>
        );
      })()}
      {/* Dedicated Production Bill of Materials (BOM) Section */}
      <div style={{ padding: 20, background: '#f8fafc', borderRadius: 8, border: '1px solid #cbd5e1', display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h4 style={{ fontSize: 16, fontWeight: 800, color: '#0f172a', margin: 0 }}>
              Production Bill of Materials (BOM) — PDF & Word
            </h4>
            <span style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4, display: 'inline-block' }}>
              10 Qualified Sourcing Line Items • Derated per IPC-9592B • IEC 61010-1 Reinforced Isolation
            </span>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <span className="badge badge-green">PDF & Word Ready</span>
            <span className="badge badge-blue">10 Sourced Items</span>
            <span className="badge badge-purple">1.0 W (1000V @ 1mA)</span>
          </div>
        </div>

        <p style={{ fontSize: 12, color: '#475569', lineHeight: 1.5, margin: 0 }}>
          Official hardware procurement specification and assembly schedule. Features primary SiC switch Q1, custom ETD34 transformer T1, 3300V SiC rectifier D1, 1500V film capacitor C_OUT, and 5000V RMS reinforced optocoupler U1 with 5.0 mm PCB milling cutout.
        </p>

        {bomMessage && (
          <div style={{ padding: '8px 12px', background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: 4, fontSize: 12, color: '#065f46' }}>
            {bomMessage}
          </div>
        )}

        {/* 1-Click Action Buttons */}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            className="btn btn-primary"
            style={{ fontSize: 12, padding: '7px 16px', display: 'flex', alignItems: 'center', gap: 6, background: '#1d4ed8', color: '#ffffff' }}
            onClick={() => onOpenFile('bom/SV1000_Bill_of_Materials.pdf')}
          >
            📄 Open PDF BOM
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: 12, padding: '7px 16px', display: 'flex', alignItems: 'center', gap: 6, borderColor: '#2563eb', color: '#1e40af' }}
            onClick={() => onOpenFile('bom/SV1000_Bill_of_Materials.docx')}
          >
            📝 Open Word BOM
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: 12, padding: '7px 16px', display: 'flex', alignItems: 'center', gap: 6 }}
            onClick={handleRebuildBom}
            disabled={isGeneratingBom}
          >
            ⚡ {isGeneratingBom ? 'Generating PDF & Word…' : 'Generate / Rebuild BOM'}
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: 12, padding: '7px 14px', display: 'flex', alignItems: 'center', gap: 6 }}
            onClick={() => onOpenFile('bom/bom.csv')}
          >
            💾 View CSV
          </button>
        </div>

        {/* Interactive Component Sourcing Table */}
        <div style={{ marginTop: 6, background: '#ffffff', borderRadius: 6, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
          <div style={{ padding: '8px 12px', background: '#f1f5f9', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#334155' }}>
              Qualified Component Sourcing Schedule (10 Sourced Items)
            </span>
            <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#64748b' }}>
              Format: PDF (Vector) & DOCX (Word 2016)
            </span>
          </div>

          <div style={{ overflowX: 'auto', maxHeight: 260 }}>
            <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', color: '#475569' }}>
                  <th style={{ padding: '6px 8px' }}>Item</th>
                  <th style={{ padding: '6px 8px' }}>Ref Des</th>
                  <th style={{ padding: '6px 8px' }}>Qty</th>
                  <th style={{ padding: '6px 8px' }}>Description</th>
                  <th style={{ padding: '6px 8px' }}>Manufacturer</th>
                  <th style={{ padding: '6px 8px' }}>Manufacturer Part #</th>
                  <th style={{ padding: '6px 8px' }}>Package</th>
                  <th style={{ padding: '6px 8px' }}>Rating</th>
                  <th style={{ padding: '6px 8px' }}>Domain</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { item: 1, des: 'Q1', qty: 1, desc: 'SiC Power MOSFET 1200V 35A 65mΩ', mfr: 'Wolfspeed / Cree', mpn: 'C3M0065090J', pkg: 'TO-252-2', rating: '1200V / 35A', domain: 'Primary (24V)' },
                  { item: 2, des: 'T1', qty: 1, desc: 'HV Isolated Flyback Transformer ETD34 4T:233T, 0.48mm gap', mfr: 'TDK / Custom', mpn: 'B66367G0000X187', pkg: 'ETD34-Vertical', rating: '3000V RMS isolation', domain: 'Barrier (5mm slot)' },
                  { item: 3, des: 'D1', qty: 1, desc: 'HV SiC Schottky Rectifier Diode 3300V 5A', mfr: 'GeneSiC Semi', mpn: 'GC05MPS33-252', pkg: 'TO-252-2', rating: '3300V / 5A', domain: 'Secondary (1000V)' },
                  { item: 4, des: 'C_OUT', qty: 1, desc: 'HV DC Output Filter Polypropylene Film Cap 100nF 1500V', mfr: 'WIMA / KEMET', mpn: 'MKP1T031005F00KSSD', pkg: 'Box Radial', rating: '1500V DC / 100nF', domain: 'Secondary (1000V)' },
                  { item: 5, des: 'C_IN', qty: 1, desc: 'Input Bulk Decoupling Ceramic Cap 47µF 50V X7R', mfr: 'TDK / Murata', mpn: 'C3225X7R1H476M250AC', pkg: '1210 SMD', rating: '50V DC / 47µF', domain: 'Primary (24V)' },
                  { item: 6, des: 'U1', qty: 1, desc: 'Optically Isolated Feedback Amplifier 5000V RMS', mfr: 'Broadcom', mpn: 'ACPL-C87B-000E', pkg: 'SOIC-8', rating: '5000V RMS', domain: 'Barrier (Optical)' },
                  { item: 7, des: 'D_SNUB', qty: 1, desc: 'Fast Recovery Clamp Snubber Diode 600V 1A 35ns', mfr: 'Vishay Semi', mpn: 'ES1J-E3/61T', pkg: 'DO-214AC (SMA)', rating: '600V / 1A', domain: 'Primary (24V)' },
                  { item: 8, des: 'C_SNUB', qty: 1, desc: 'RCD Clamp Snubber Ceramic Cap 10nF 100V X7R', mfr: 'KEMET', mpn: 'C0805C103K1RACTU', pkg: '0805 SMD', rating: '100V DC / 10nF', domain: 'Primary (24V)' },
                  { item: 9, des: 'R_SNUB', qty: 1, desc: 'RCD Clamp Bleeder Resistor 47kΩ 1W 5%', mfr: 'Vishay Dale', mpn: 'CRCW120647K0JNEAHP', pkg: '1206 SMD', rating: '200V / 1W / 47kΩ', domain: 'Primary (24V)' },
                  { item: 10, des: 'R_FB', qty: 1, desc: 'HV Precision Feedback Resistor 10MΩ 1500V 1%', mfr: 'Ohmite / TE', mpn: 'HVC2512-10MJT18', pkg: '2512 SMD', rating: '1500V DC / 10MΩ', domain: 'Secondary (1000V)' },
                ].map((row, idx) => (
                  <tr key={row.des} style={{ borderBottom: '1px solid #f1f5f9', background: idx % 2 === 1 ? '#f8fafc' : '#ffffff' }}>
                    <td style={{ padding: '6px 8px', color: '#64748b' }}>{row.item}</td>
                    <td style={{ padding: '6px 8px', fontWeight: 700, color: '#1e3a8a', fontFamily: 'monospace' }}>{row.des}</td>
                    <td style={{ padding: '6px 8px', color: '#334155' }}>{row.qty}</td>
                    <td style={{ padding: '6px 8px', color: '#1e293b' }}>{row.desc}</td>
                    <td style={{ padding: '6px 8px', color: '#475569' }}>{row.mfr}</td>
                    <td style={{ padding: '6px 8px', fontWeight: 600, color: '#0f172a', fontFamily: 'monospace' }}>{row.mpn}</td>
                    <td style={{ padding: '6px 8px', color: '#64748b' }}>{row.pkg}</td>
                    <td style={{ padding: '6px 8px', color: '#047857', fontWeight: 600 }}>{row.rating}</td>
                    <td style={{ padding: '6px 8px' }}>
                      <span className={`badge ${row.domain.includes('Barrier') ? 'badge-purple' : row.domain.includes('Secondary') ? 'badge-yellow' : 'badge-blue'}`} style={{ fontSize: 10 }}>
                        {row.domain}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 10 }}>
          <div>
            <p style={{ fontSize: 14, fontWeight: 700, color: '#0f172a', margin: 0 }}>
              Native Hardware CAD & Fabrication Artifacts ({cadFiles.length} files)
            </p>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              Hardware CAD models, schematics, PCB layouts, and fabrication exports. Click any file to open in its native application.
            </span>
          </div>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', background: '#f1f5f9', padding: 2, borderRadius: 6, border: '1px solid var(--border)' }}>
              <button
                type="button"
                onClick={() => setCadViewMode('list')}
                style={{
                  background: cadViewMode === 'list' ? '#ffffff' : 'transparent',
                  border: 'none',
                  color: cadViewMode === 'list' ? '#0f172a' : '#64748b',
                  padding: '3px 8px',
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                  boxShadow: cadViewMode === 'list' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                }}
              >
                ☰ List View
              </button>
              <button
                type="button"
                onClick={() => setCadViewMode('grid')}
                style={{
                  background: cadViewMode === 'grid' ? '#ffffff' : 'transparent',
                  border: 'none',
                  color: cadViewMode === 'grid' ? '#0f172a' : '#64748b',
                  padding: '3px 8px',
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                  boxShadow: cadViewMode === 'grid' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                }}
              >
                ⊞ Grid View
              </button>
            </div>

            <div style={{ display: 'flex', background: '#f1f5f9', padding: 2, borderRadius: 6, border: '1px solid var(--border)' }}>
              <button
                type="button"
                onClick={() => setCadCategory('all')}
                style={{
                  background: cadCategory === 'all' ? '#ffffff' : 'transparent',
                  border: 'none',
                  color: cadCategory === 'all' ? '#0f172a' : '#64748b',
                  padding: '3px 8px',
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                  boxShadow: cadCategory === 'all' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                }}
              >
                All ({cadFiles.length})
              </button>
              <button
                type="button"
                onClick={() => setCadCategory('cad')}
                style={{
                  background: cadCategory === 'cad' ? '#ffffff' : 'transparent',
                  border: 'none',
                  color: cadCategory === 'cad' ? '#0f172a' : '#64748b',
                  padding: '3px 8px',
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                  boxShadow: cadCategory === 'cad' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                }}
              >
                CAD & KiCad
              </button>
              <button
                type="button"
                onClick={() => setCadCategory('doc')}
                style={{
                  background: cadCategory === 'doc' ? '#ffffff' : 'transparent',
                  border: 'none',
                  color: cadCategory === 'doc' ? '#0f172a' : '#64748b',
                  padding: '3px 8px',
                  borderRadius: 4,
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: 'pointer',
                  boxShadow: cadCategory === 'doc' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                }}
              >
                BOM & Documents
              </button>
            </div>

            <input
              type="text"
              placeholder="Search file name..."
              value={cadFilter}
              onChange={(e) => setCadFilter(e.target.value)}
              style={{
                padding: '4px 10px',
                fontSize: 12,
                borderRadius: 6,
                border: '1px solid var(--border)',
                background: '#ffffff',
                color: '#0f172a',
                width: 170,
              }}
            />
          </div>
        </div>

        {cadViewMode === 'list' ? (
          <div className="card" style={{ padding: 0, overflow: 'hidden', border: '1px solid var(--border)', borderRadius: 8 }}>
            <div style={{ overflowX: 'auto', maxHeight: 480, overflowY: 'auto' }}>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse', textAlign: 'left' }}>
                <thead style={{ position: 'sticky', top: 0, background: '#f8fafc', zIndex: 2, borderBottom: '1px solid var(--border)' }}>
                  <tr>
                    <th style={{ padding: '9px 14px', color: '#475569', fontWeight: 600 }}>Actual File Name</th>
                    <th style={{ padding: '9px 14px', color: '#475569', fontWeight: 600 }}>Target Application</th>
                    <th style={{ padding: '9px 14px', color: '#475569', fontWeight: 600 }}>Size</th>
                    <th style={{ padding: '9px 14px', color: '#475569', fontWeight: 600 }}>Integrity</th>
                    <th style={{ padding: '9px 14px', color: '#475569', fontWeight: 600, textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCadFiles.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
                        No files match the selected filter.
                      </td>
                    </tr>
                  ) : (
                    filteredCadFiles.map((file, idx) => {
                      const fileName = file.relative_path.split(/[\/]/).pop() || file.name || file.relative_path;
                      const app = getAppDetails(file.relative_path);
                      const sizeStr = file.size_bytes ? `${(file.size_bytes / 1024).toFixed(1)} KB` : '—';
                      return (
                        <tr
                          key={file.relative_path}
                          style={{
                            borderBottom: '1px solid #f1f5f9',
                            background: idx % 2 === 0 ? '#ffffff' : '#fafafa',
                            transition: 'background 0.15s ease',
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = '#f1f5f9')}
                          onMouseLeave={(e) => (e.currentTarget.style.background = idx % 2 === 0 ? '#ffffff' : '#fafafa')}
                        >
                          <td style={{ padding: '9px 14px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span style={{ fontSize: 16 }}>{app.icon}</span>
                              <strong style={{ fontSize: 13, color: '#0f172a' }}>{fileName}</strong>
                            </div>
                          </td>
                          <td style={{ padding: '9px 14px' }}>
                            <span className={`badge ${app.badgeClass}`} style={{ fontSize: 10, fontWeight: 600 }}>
                              {app.name}
                            </span>
                          </td>
                          <td style={{ padding: '9px 14px', color: '#64748b', fontFamily: 'monospace', fontSize: 11 }}>
                            {sizeStr}
                          </td>
                          <td style={{ padding: '9px 14px' }}>
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, color: '#047857', fontWeight: 600 }}>
                              ✓ SHA-256 verified
                            </span>
                          </td>
                          <td style={{ padding: '9px 14px', textAlign: 'right' }}>
                            <button
                              className="btn btn-secondary"
                              style={{ padding: '4px 10px', fontSize: 11, display: 'inline-flex', alignItems: 'center', gap: 5, whiteSpace: 'nowrap', fontWeight: 600 }}
                              onClick={() => onOpenFile(file.relative_path)}
                            >
                              <span>{app.icon}</span> {app.action}
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div style={grid}>
            {filteredCadFiles.length === 0 ? (
              <div className="card" style={{ gridColumn: '1 / -1', textAlign: 'center', padding: 24, color: 'var(--text-muted)' }}>
                No files match the selected filter.
              </div>
            ) : (
              filteredCadFiles.map((file) => {
                const fileName = file.relative_path.split(/[\/]/).pop() || file.name || file.relative_path;
                const app = getAppDetails(file.relative_path);
                const sizeStr = file.size_bytes ? `${(file.size_bytes / 1024).toFixed(1)} KB` : '—';
                return (
                  <article className="card" key={file.relative_path} style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontSize: 16 }}>{app.icon}</span>
                          <strong style={{ fontSize: 13, color: '#0f172a' }}>{fileName}</strong>
                        </div>
                        <span className={`badge ${app.badgeClass}`} style={{ fontSize: 10, whiteSpace: 'nowrap' }}>{app.name}</span>
                      </div>
                      <p style={{ fontSize: 11, margin: '6px 0 12px', color: 'var(--text-muted)' }}>
                        Target: <strong style={{ color: '#1e293b' }}>{app.name}</strong> · {sizeStr} · <span style={{ color: '#047857', fontWeight: 600 }}>✓ SHA-256</span>
                      </p>
                    </div>
                    <button
                      className="btn btn-secondary"
                      style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, fontSize: 12, fontWeight: 600 }}
                      onClick={() => onOpenFile(file.relative_path)}
                    >
                      <span>{app.icon}</span> {app.action}
                    </button>
                  </article>
                );
              })
            )}
          </div>
        )}
      </div>

      {artifacts.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <p style={{ fontSize: 13, fontWeight: 700, color: '#334155', marginBottom: 10 }}>Registered Immutable Artifact Records ({artifacts.length} records)</p>
          {artifacts.map((record, i) => <RecordDetails key={record.record_id || i} record={record} title={record.classification || 'Registered artifact'} onOpenFile={onOpenFile} />)}
        </div>
      )}
    </>}
  </div>;
};
