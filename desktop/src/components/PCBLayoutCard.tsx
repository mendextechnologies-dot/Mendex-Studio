import React, { useEffect, useRef, useState } from 'react';
import { rpcCall } from '../api/client';

type Component = { reference: string; value: string; x_m: number; y_m: number; locked: boolean; outline_anchor?: boolean; pads: unknown[] };
type Analysis = {
  source: string; context_sha256: string; populated: boolean; components: Component[];
  nets: { name: string; pads: { reference: string; pad: string }[] }[];
  copper_counts: Record<string, number>; warnings: string[];
  placement_constraints: PlacementReport;
};
type PlacementReport = {
  status: string; complete: boolean; fixed_references: string[]; notice: string;
  checks: Record<string, { status: string; complete: boolean; issues: Record<string, unknown>[]; unavailable: Record<string, unknown>[] }>;
};
type Preview = { can_create: boolean; placement_constraints: PlacementReport; analysis: Analysis };
type Candidate = {
  candidate_id: string; status: string; integrity: boolean; stale: boolean;
  created_at?: string; board_path?: string; analysis?: Analysis;
  placement_constraints?: PlacementReport; effective_constraint_status?: string;
};
type Move = { reference: string; x_m: number; y_m: number };

function PlacementChecks({ report }: { report?: PlacementReport }) {
  if (!report) return <p>Placement geometry: NOT_EVALUATED (no stored assessment).</p>;
  const names: Record<string, string> = {
    board_outline: 'Closed board outline', board_containment: 'Courtyards inside board',
    courtyard_overlap: 'Courtyard overlap by side', footprint_keepouts: 'Footprint keepouts', fixed_components: 'Fixed positions',
  };
  return <div aria-label="Placement constraint results" style={{ margin: '12px 0', overflowWrap: 'anywhere' }}>
    <p><strong>Placement drawings: {report.status}</strong>{!report.complete && ' · incomplete geometry coverage'}</p>
    <p>Fixed references: {report.fixed_references.join(', ') || 'None supplied or locked'}</p>
    {Object.entries(report.checks).map(([name, check]) => <div key={name} style={{ padding: '4px 0' }}>
      <strong>{names[name] || name}: {check.status}</strong>
      {!!(check.issues.length || check.unavailable.length) && <ul>
        {check.issues.map((issue, i) => <li key={`issue-${i}`}>{String(issue.code)} — {Object.entries(issue).filter(([k]) => k !== 'code').map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : String(v)}`).join('; ')}</li>)}
        {check.unavailable.map((entry, i) => <li key={`unavailable-${i}`}>{entry.reference ? `${String(entry.reference)}: ` : ''}{String(entry.reason)}</li>)}
      </ul>}
    </div>)}
    <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>{report.notice}</p>
  </div>;
}

export function PCBLayoutCard({ revisionId }: { revisionId: string }) {
  const [files, setFiles] = useState<{ path: string }[]>([]);
  const [editable, setEditable] = useState(false);
  const [path, setPath] = useState('');
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [moves, setMoves] = useState<Move[]>([]);
  const [reference, setReference] = useState('');
  const [x, setX] = useState('');
  const [y, setY] = useState('');
  const [reason, setReason] = useState('');
  const [fixed, setFixed] = useState<string[]>([]);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => { alive.current = false; };
  }, []);

  async function refresh() {
    const [inventory, history] = await Promise.all([
      rpcCall<{ editable: boolean; files: { path: string }[] }>('pcb_layout_files', { revision_id: revisionId }),
      rpcCall<Candidate[]>('pcb_layout_candidates', { revision_id: revisionId }),
    ]);
    if (!alive.current) return;
    setFiles(inventory.files); setEditable(inventory.editable); setCandidates(history);
    setPath(previous => inventory.files.some(f => f.path === previous) ? previous : inventory.files[0]?.path || '');
  }
  async function run(action: () => Promise<void>) {
    setBusy(true); setMessage('');
    try { await action(); }
    catch (error) { if (alive.current) { setMessage(String(error)); setPreview(null); } }
    finally { if (alive.current) setBusy(false); }
  }
  useEffect(() => { void run(refresh); }, [revisionId]);

  async function analyze() {
    const result = await rpcCall<Analysis>('pcb_layout_analyze', { revision_id: revisionId, relative_path: path });
    if (!alive.current) return;
    setAnalysis(result); setMoves([]); setReference(''); setFixed([]); setPreview(null);
    setMessage('Board analyzed. Choose explicit component moves or create an unchanged snapshot.');
  }
  function addMove() {
    if (!reference || !x.trim() || !y.trim() || !Number.isFinite(Number(x)) || !Number.isFinite(Number(y))) {
      setMessage('Select an unlocked component and enter finite X and Y positions in millimetres.'); return;
    }
    const move = { reference, x_m: Number(x) / 1000, y_m: Number(y) / 1000 };
    setMoves(previous => [...previous.filter(m => m.reference !== reference), move]); setPreview(null);
  }
  function request() {
    return { revision_id: revisionId, relative_path: analysis!.source,
      expected_context_sha256: analysis!.context_sha256, moves, rationale: reason, fixed_references: fixed };
  }
  async function previewPlan() {
    const result = await rpcCall<Preview>('pcb_layout_preview', request());
    if (alive.current) setPreview(result);
  }
  async function create() {
    if (!analysis) return;
    const result = await rpcCall<Candidate>('pcb_layout_create', request());
    await refresh();
    if (alive.current) setMessage(`Candidate created: ${result.candidate_id}. Source design preserved. No DRC performed.`);
  }
  const canMove = !!analysis && !Object.values(analysis.copper_counts).some(Boolean);
  const fieldStyle = { padding: '7px', border: '1px solid var(--border)', borderRadius: '5px', maxWidth: '100%' };
  return <section className="card" style={{ padding: 20, marginBottom: 18 }} aria-label="PCB layout experiments">
    <h3>PCB layout experiments</h3>
    <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
      Analyze a native board and create isolated draft candidates. Engineering evaluation: NOT_EVALUATED.
    </p>
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', margin: '12px 0' }}>
      <select aria-label="Layout board" style={fieldStyle} value={path} disabled={busy} onChange={e => {
        setPath(e.target.value); setAnalysis(null); setMoves([]); setMessage(''); setPreview(null); setFixed([]);
      }}>
        {!files.length && <option value="">No PCB board in this revision</option>}
        {files.map(f => <option key={f.path} value={f.path}>{f.path}</option>)}
      </select>
      <button className="btn btn-secondary" disabled={busy || !path} onClick={() => void run(analyze)}>Analyze board</button>
      <button className="btn btn-secondary" disabled={busy} onClick={() => void run(async () => {
        setAnalysis(null); setMoves([]); setPreview(null); setFixed([]); await refresh();
      })}>Refresh</button>
    </div>
    {!files.length && !busy && <p>Import a populated KiCad board into the revision’s pcb folder to begin.</p>}
    {analysis && <>
      <p>{analysis.components.length} components · {analysis.nets.length} connected net names · {analysis.components.filter(c => c.locked).length} locked components</p>
      <details><summary>Components and connectivity</summary>
        <div style={{ overflow: 'auto', maxHeight: 280 }}>
          <table style={{ width: '100%', fontSize: 12 }}><thead><tr><th>Reference</th><th>Value</th><th>X (mm)</th><th>Y (mm)</th><th>CAD constraint</th><th>Pads</th><th>Keep fixed</th></tr></thead>
            <tbody>{analysis.components.map(c => <tr key={c.reference}>
              <td>{c.reference}</td><td>{c.value}</td><td>{(c.x_m * 1000).toFixed(3)}</td><td>{(c.y_m * 1000).toFixed(3)}</td><td>{c.locked ? 'Locked' : c.outline_anchor ? 'Defines outline' : 'None'}</td><td>{c.pads.length}</td>
              <td><input type="checkbox" aria-label={`Keep ${c.reference} fixed`} checked={c.locked || !!c.outline_anchor || fixed.includes(c.reference)} disabled={busy || !editable || c.locked || c.outline_anchor} onChange={e => {
                setFixed(previous => e.target.checked ? [...previous, c.reference] : previous.filter(r => r !== c.reference));
                if (e.target.checked) { setMoves(previous => previous.filter(m => m.reference !== c.reference)); if (reference === c.reference) setReference(''); }
                setPreview(null);
              }} /></td>
            </tr>)}</tbody></table>
          {analysis.nets.map(n => <p key={n.name}><strong>{n.name}</strong>: {n.pads.map(p => `${p.reference}.${p.pad}`).join(', ')}</p>)}
        </div>
      </details>
      <details open><summary>{preview ? 'Proposed placement checks' : 'Current board placement checks'}</summary>
        <PlacementChecks report={preview?.placement_constraints || analysis.placement_constraints} />
      </details>
      {editable && canMove && <fieldset disabled={busy} style={{ marginTop: 12, padding: 12, border: '1px solid var(--border)' }}>
        <legend>Explicit placement moves</legend>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <select aria-label="Component to move" value={reference} style={fieldStyle} onChange={e => {
            setReference(e.target.value);
            const c = analysis.components.find(c => c.reference === e.target.value);
            setX(c ? String(c.x_m * 1000) : ''); setY(c ? String(c.y_m * 1000) : '');
          }}><option value="">Select movable component</option>{analysis.components.filter(c => !c.locked && !c.outline_anchor && !fixed.includes(c.reference)).map(c => <option key={c.reference}>{c.reference}</option>)}</select>
          <label>X (mm) <input aria-label="Target X in mm" type="number" step="any" style={{ ...fieldStyle, width: 110 }} value={x} onChange={e => setX(e.target.value)} /></label>
          <label>Y (mm) <input aria-label="Target Y in mm" type="number" step="any" style={{ ...fieldStyle, width: 110 }} value={y} onChange={e => setY(e.target.value)} /></label>
          <button className="btn btn-secondary" onClick={addMove}>Add / replace move</button>
        </div>
        {moves.map(m => <p key={m.reference}>{m.reference} → {(m.x_m * 1000).toFixed(3)}, {(m.y_m * 1000).toFixed(3)} mm <button onClick={() => { setMoves(previous => previous.filter(p => p.reference !== m.reference)); setPreview(null); }}>Remove</button></p>)}
      </fieldset>}
      {!canMove && <p>Existing tracks, vias or zones detected. This milestone supports an unchanged snapshot for this board.</p>}
      {editable ? <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
        <input aria-label="Layout experiment rationale" style={{ ...fieldStyle, flex: 1 }} maxLength={4000} value={reason} disabled={busy} placeholder="Reason for this layout experiment" onChange={e => setReason(e.target.value)} />
        <button className="btn btn-secondary" disabled={busy || !analysis.populated || !reason.trim()} onClick={() => void run(previewPlan)}>Check placement plan</button>
        <button className="btn btn-primary" disabled={busy || !analysis.populated || !reason.trim() || (!!moves.length && !preview?.can_create)} onClick={() => void run(create)}>{moves.length ? 'Create moved candidate' : 'Create snapshot candidate'}</button>
      </div> : <p>This revision is read-only. Create a draft revision for layout experiments.</p>}
      {!!moves.length && !preview?.can_create && <p>Check the placement plan. Moved candidates require complete, clear drawn-geometry checks.</p>}
      <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Checks cover supported straight-edged placement drawings. Electrical clearance, 3D collision, DRC and safety remain NOT_EVALUATED.</p>
    </>}
    {message && <p role="status" style={{ overflowWrap: 'anywhere' }}>{message}</p>}
    <details style={{ marginTop: 12 }}><summary>Candidate history ({candidates.length})</summary>
      {candidates.map(c => <div key={c.candidate_id} style={{ borderTop: '1px solid var(--border)', padding: '10px 0', overflowWrap: 'anywhere' }}>
        <strong>{c.status}</strong> · {c.integrity ? (c.stale ? 'Source context changed' : 'Hashes intact') : 'Evidence missing or changed'}
        <div>{c.candidate_id}</div><div>{c.board_path}</div>
        <p>Current placement result: {c.effective_constraint_status || 'NOT_EVALUATED'}</p>
        {c.placement_constraints && <details><summary>Stored geometry assessment{c.stale ? ' (historical, source changed)' : ''}</summary><PlacementChecks report={c.placement_constraints} /></details>}
        {c.analysis && <details><summary>Candidate component positions</summary>{c.analysis.components.map(p => <p key={p.reference}>{p.reference}: {(p.x_m * 1000).toFixed(3)}, {(p.y_m * 1000).toFixed(3)} mm</p>)}</details>}
      </div>)}
    </details>
  </section>;
}
