import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { ProjectDetailData } from '../api/types';
import { CoreAssemblyPreview } from './CoreAssemblyPreview';
import { PartsBOMEditor } from './PartsBOMEditor';

const list = (x: any): any[] => Array.isArray(x) ? x : x?.records || [];
const card: React.CSSProperties = { padding: 20, border: '1px solid var(--border)', borderRadius: 10, background: 'var(--bg-card, white)' };
const row: React.CSSProperties = { display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' };
const field: React.CSSProperties = { width: '100%', padding: 8, border: '1px solid #cbd5e1', borderRadius: 5, color: '#172033', background: '#fff' };
const cell: React.CSSProperties = { padding: 10, textAlign: 'left', borderBottom: '1px solid #e2e8f0', verticalAlign: 'top' };
const empty = () => ({ schema_version: '1.0', scope: 'Transformer core and support assembly', parts: [] as any[], issues: [] as any[], notes: '' });

export function CoreAssemblySelector({ data, onSelected }: { data: ProjectDetailData; onSelected: (revisionId: string) => void }) {
  const [label, setLabel] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  if (data.revision.lifecycle_status !== 'draft') return null;
  return <section style={card}>
    <strong>Project workflow</strong>
    <p style={{ margin: '8px 0', color: '#52627a' }}>For a core and support assembly, select the mechanical workflow. This creates a new draft revision with copied source files and preserves this revision in history.</p>
    <form style={row} onSubmit={async e => { e.preventDefault(); setBusy(true); setError(''); try {
      const result = await api.createCoreAssemblyRevision(data.revision.revision_id, label, data.input_hash);
      onSelected(result.revision.revision_id);
    } catch (err) { setError(String(err)); } finally { setBusy(false); } }}>
      <label>New revision label <input required pattern="[A-Za-z0-9][A-Za-z0-9_-]*" aria-label="Assembly revision label" value={label} onChange={e => setLabel(e.target.value)} style={field} placeholder="e.g. R002" /></label>
      <button className="btn btn-primary" disabled={busy}>Use core and support assembly workflow</button>
    </form>{error && <p role="alert">{error}</p>}
  </section>;
}

export function CoreAssemblyWorkbench({ data, onBack, onSelectRevision, onReload }: {
  data: ProjectDetailData; onBack: () => void; onSelectRevision?: (id: string) => void; onReload?: () => void;
}) {
  const tabs = ['Overview', 'Requirements', 'Mechanical design', 'Part Catalog & Specs', 'Turnkey Engineering & FAT', 'Fit decisions', 'Inspection', 'Lifecycle', 'Files'];
  const [tab, setTab] = useState('Overview');
  const [assembly, setAssembly] = useState<any>(null);
  const [design, setDesign] = useState(empty);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [review, setReview] = useState<any>(null);
  const [reviewer, setReviewer] = useState('');
  const [comments, setComments] = useState('');
  const [decision, setDecision] = useState<'APPROVED' | 'REJECTED' | 'CHANGES_REQUESTED'>('CHANGES_REQUESTED');
  const [stageId, setStageId] = useState('requirements');
  const rid = data.revision.revision_id;
  const editable = data.revision.lifecycle_status === 'draft';
  const stages = data.lifecycle?.stages || [];
  const activeStages = stages.filter(s => s.status === 'IN_PROGRESS' && !s.stale);
  const recordStage = activeStages.some(s => s.definition.id === stageId) ? stageId : activeStages[0]?.definition.id || '';
  const load = async () => {
    const result = await api.coreAssembly(rid);
    setAssembly(result); setDesign(result.design || empty()); setDirty(false);
  };
  useEffect(() => { let cancelled = false; api.coreAssembly(rid).then(result => {
    if (!cancelled) { setAssembly(result); setDesign(result.design || empty()); setDirty(false); }
  }).catch(e => { if (!cancelled) setError(String(e)); }); return () => { cancelled = true; }; }, [rid]);
  const run = async (operation: () => Promise<unknown>, success = 'Saved.') => {
    setBusy(true); setError(''); setMessage('');
    try { await operation(); setMessage(success); onReload?.(); } catch (e) { setError(String(e)); } finally { setBusy(false); }
  };
  const open = async (path: string) => {
    setBusy(true); setError(''); setMessage('');
    try {
      await api.openFile(rid, path);
      setMessage(`Launched ${path.split('/').pop()} in native application.`);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  const update = (patch: any) => { setDesign(d => ({ ...d, ...patch })); setDirty(true); };
  const parts = design.parts;
  const steps = data.files.filter(f => /\.(step|stp|fcstd)$/i.test(f.relative_path));
  const linkedSteps = steps.filter(f => parts.some(p => p.cad_relative_path === f.relative_path));
  const isPlasma = Boolean(data.product.code === 'PCE-100' || data.product.name.toLowerCase().includes('plasma'));
  const reqs = list(data.requirements).slice(-1)[0]?.requirements || [];
  const inspection = data.files.filter(f => /(^validation\/|inspection|certificate)/i.test(f.relative_path) && /\.(md|pdf|json|csv)$/i.test(f.relative_path));
  const getPartImg = (name: string) => assembly?.part_images?.[name] || `/api/workspace-file?path=reports/part-specifications/${name}.png`;
  const fileButtons = (files: typeof data.files) => <div style={{ display: 'grid', gap: 8 }}>{files.length ? files.map(f =>
    <div key={f.relative_path} style={{ ...row, justifyContent: 'space-between', padding: 10, background: '#f1f5f9', borderRadius: 5 }}>
      <span style={{ overflowWrap: 'anywhere' }}>{f.relative_path}</span>
      <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => open(f.relative_path)}>{/\.(step|stp|fcstd)$/i.test(f.relative_path) ? 'Open CAD part' : 'Open document'}</button>
    </div>) : <p>No files supplied.</p>}</div>;
  const save = async (e: React.FormEvent) => { e.preventDefault(); await run(async () => {
    await api.saveCoreAssembly({ revision_id: rid, stage_id: recordStage, expected_input_hash: data.input_hash,
      expected_design_sha256: assembly?.design_sha256 || null, design, source: 'Engineer input in assembly workspace',
      reason: 'Update sourced mechanical design and supplied issue dispositions', idempotency_key: crypto.randomUUID() });
    await load();
  }, 'Assembly design snapshot saved. Engineering checks remain NOT_EVALUATED.'); };
  return <main style={{ padding: 24, display: 'grid', gap: 18, overflowY: 'auto' }}>
    <header style={{ ...card, background: 'linear-gradient(120deg, #edf8f7, #f3f6ff)' }}>
      <div style={{ ...row, justifyContent: 'space-between' }}><button className="btn btn-secondary" onClick={onBack}>Back to projects</button>
        <label>Revision <select aria-label="Assembly revision" value={rid} onChange={e => onSelectRevision?.(e.target.value)} style={{ ...field, width: 'auto' }}>
          {data.revisions.map(r => <option key={r.revision_id} value={r.revision_id}>{r.revision_label} ({r.lifecycle_status})</option>)}
        </select></label></div>
      <p style={{ color: '#0f766e', fontWeight: 700, marginTop: 18 }}>CORE & SUPPORT ASSEMBLY</p>
      <h2 style={{ margin: '6px 0' }}>{data.product.code} · {data.product.name}</h2>
      <p>Mechanical parts, ferrite references, fit decisions and dimensional inspection.</p>
      <div style={{ ...row, marginTop: 12 }}><span className="badge badge-blue">{data.revision.revision_label} · {data.revision.lifecycle_status}</span>
        <span className="badge badge-muted">Engineering: NOT_EVALUATED</span><span>{dirty ? 'Unsaved changes' : 'Saved revision data'}</span></div>
    </header>
    {error && <p role="alert" style={{ color: '#b91c1c' }}>{error}</p>}{message && <p role="status">{message}</p>}
    <nav aria-label="Assembly sections" style={row}>{tabs.map(t => <button key={t} className={`btn ${tab === t ? 'btn-primary' : 'btn-secondary'}`} aria-pressed={tab === t} onClick={() => setTab(t)}>{t}</button>)}</nav>
    {!assembly ? <p>Loading assembly records…</p> : <>
      {!assembly.design_integrity && <p role="status">{assembly.design ? 'The saved design or its linked CAD has changed or failed an integrity check. Review the sources and record a new design snapshot.' : 'A current intact assembly design has not been recorded. Enter sourced parts and decisions below.'}</p>}
      {tab === 'Overview' && <>
        <CoreAssemblyPreview revisionId={rid} designHash={assembly.design_sha256} />

        {/* AI Autonomous Spec-to-Design Engineering Pipeline */}
        <section style={{
          ...card,
          background: 'linear-gradient(135deg, #091e3a, #0f2b48)',
          color: '#ffffff',
          border: '1.5px solid #0284c7',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 14 }}>
            <div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                <span style={{
                  background: '#0284c7',
                  color: '#fff',
                  fontSize: 10.5,
                  fontWeight: 800,
                  padding: '2px 8px',
                  borderRadius: 4,
                  textTransform: 'uppercase',
                  letterSpacing: '0.6px'
                }}>
                  AUTONOMOUS ENGINEERING ENGINE
                </span>
                <span style={{
                  background: '#047857',
                  color: '#a7f3d0',
                  fontSize: 10.5,
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: 4,
                }}>
                  SPEC-TO-PRODUCTION READY
                </span>
              </div>
              <h3 style={{ margin: 0, fontSize: 18, color: '#ffffff' }}>
                {isPlasma ? 'AI Spec-to-Design Autonomous Pipeline (IPR Plasma Chamber & Electrodes)' : 'AI Spec-to-Design Autonomous Pipeline (from Client Specification)'}
              </h3>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#93c5fd' }}>
                {isPlasma
                  ? 'Mendex Studio ingests raw tender specifications (final_specification_2026-11-04-17-30-59.pdf) and autonomously synthesizes 3D CAD solids, formal 2D manufacturing drawings, thermal & hydraulic cooling multiphysics, cleanroom SOP, and IPR FAT protocol without human drafting.'
                  : 'Mendex Studio ingests raw technical specifications (e.g. final_specs_307.pdf) and autonomously synthesizes 3D CAD solids, formal 2D manufacturing drawings, multiphysics simulations, and turnkey release dossiers without human drafting.'}
              </p>
            </div>

            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: 12, padding: '7px 14px', background: '#1e3a5f', color: '#67e8f9', borderColor: '#0284c7' }}
              disabled={busy}
              onClick={() => open(isPlasma ? 'requirements/source/final_specification_2026-11-04-17-30-59_ecb605978af1d5792e0b153fde1ebe59.pdf' : 'requirements/source/final_specs_307_2026-08-11-10-31-12_4ea8f4019383b7edff4ef049136ed4c1 (2).pdf')}
            >
              📄 Open Source Tender Spec (PDF)
            </button>
          </div>

          {/* 5-Stage Autonomous Pipeline Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 12,
            marginTop: 10,
          }}>
            {/* Stage 1 */}
            <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: 8, padding: 12, border: '1px solid rgba(255,255,255,0.1)' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase' }}>1. Spec Ingestion</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginTop: 4 }}>{isPlasma ? 'UHV Vacuum & Cooling' : 'Requirements Parsing'}</div>
              <div style={{ fontSize: 11, color: '#cbd5e1', marginTop: 4, lineHeight: 1.4 }}>
                {isPlasma
                  ? 'UHV vacuum boundary (< 1e-8 mbar·l/s), 3.0 bar cooling circuit, ETP Copper body, AISI 430 Flange, Grade AX05 BN.'
                  : '48 Toroidal ferrites, 3 limbs (equilateral 207mm pitch), 1 MHz 3F4, PTFE support structure, M8 SS bolts.'}
              </div>
            </div>

            {/* Stage 2 */}
            <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: 8, padding: 12, border: '1px solid rgba(255,255,255,0.1)' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase' }}>2. 3D Solid CAD</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginTop: 4 }}>Parametric Synthesis</div>
              <div style={{ fontSize: 11, color: '#cbd5e1', marginTop: 4, lineHeight: 1.4 }}>
                {isPlasma
                  ? 'FreeCAD OpenCASCADE B-Rep constructs chamber, stepped electrode, 1/4" cooling coils, waveguide & flange assembly (.step).'
                  : 'FreeCAD B-Rep engine constructs plates, limbs, spacers, toroids & 99-solid exploded assembly (.step).'}
              </div>
            </div>

            {/* Stage 3 */}
            <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: 8, padding: 12, border: '1px solid #10b981' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#34d399', textTransform: 'uppercase' }}>3. 2D Drafting (AI)</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginTop: 4 }}>TechDraw HLR Vector</div>
              <div style={{ fontSize: 11, color: '#cbd5e1', marginTop: 4, lineHeight: 1.4 }}>
                {isPlasma
                  ? 'ISO 5457 A3 drawing with Front view, Section B-B, internal M90x1.0 thread, Ra 1.6-3.0 µm finish, ISO 2768-m tolerances (PCE-01).'
                  : 'ISO 5457 A3 drawing with Front view, Section B-B, blind hole callouts, ISO 2768-m tolerances, and title block.'}
              </div>
            </div>

            {/* Stage 4 */}
            <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: 8, padding: 12, border: '1px solid rgba(255,255,255,0.1)' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase' }}>4. Multiphysics</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginTop: 4 }}>{isPlasma ? 'Thermal & Hydraulic 3.0 Bar' : '1 MHz FEA & Litz Sizing'}</div>
              <div style={{ fontSize: 11, color: '#cbd5e1', marginTop: 4, lineHeight: 1.4 }}>
                {isPlasma
                  ? 'Coupled cooling solver: 2.5 L/min flow, ΔT = 5.73 K rise, 0.28 bar pressure drop (< 3.0 bar limit), 100 kW heat removal.'
                  : 'FEMM 4.2 harmonic magnetic solver (B_pk = 0.042 T) + 0.5mm AWG 44 Litz sizing in Ø56mm bore (>80 kV isolation).'}
              </div>
            </div>

            {/* Stage 5 */}
            <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: 8, padding: 12, border: '1px solid rgba(255,255,255,0.1)' }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase' }}>5. Production Release</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f8fafc', marginTop: 4 }}>Turnkey Publication</div>
              <div style={{ fontSize: 11, color: '#cbd5e1', marginTop: 4, lineHeight: 1.4 }}>
                {isPlasma
                  ? '8-Page formal specification catalog PDF + ISO 7 Cleanroom Assembly SOP + IPR Witness FAT Acceptance Protocol.'
                  : '8-Sheet publication-ready specification catalog PDF with verified BOM, volume pricing, and fit review.'}
              </div>
            </div>
          </div>
        </section>

        <section style={card}><h3>Assembly scope</h3><p style={{ margin: '10px 0' }}>{design.scope}</p><p>{design.notes || 'No design notes supplied.'}</p></section>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 12 }}>
          {[[parts.length, 'Supply BOM lines'], [linkedSteps.length, 'Linked CAD parts'], [reqs.length, 'Sourced requirements'], [design.issues.filter(i => !i.disposition.trim()).length, 'Decisions awaiting input']].map(([n, text]) => <section key={String(text)} style={card}><strong style={{ fontSize: 28 }}>{n}</strong><p>{text}</p></section>)}
        </div>
        <section style={card}><h3>Current lifecycle</h3>{stages.map((s, i) => <p key={s.definition.id} style={{ padding: '6px 0' }}>{i + 1}. {s.definition.name} <span className="badge badge-muted">{s.effective_status || s.status}</span></p>)}</section>
        {editable && <details><summary>Create next draft revision</summary><CoreAssemblySelector data={data} onSelected={id => { onSelectRevision?.(id); onReload?.(); }} /></details>}
      </>}
      {tab === 'Requirements' && <section style={{ ...card, overflowX: 'auto' }}><h3>Core and assembly requirements</h3>
        {!reqs.length ? <p>No sourced requirements recorded.</p> : <table style={{ width: '100%' }}><thead><tr>{['Requirement', 'Target / limits', 'Source', 'Verification'].map(x => <th style={cell} key={x}>{x}</th>)}</tr></thead><tbody>{reqs.map((r: any) => <tr key={r.id}>
          <td style={cell}>{r.description}<p style={{ fontSize: 12, marginTop: 5 }}>{r.acceptance_criterion}</p></td><td style={cell}>{r.target_value ?? 'Not specified'} {r.unit}<p>{r.min_value != null ? `${r.min_value} – ${r.max_value} ${r.unit}` : ''}</p></td><td style={cell}>{r.source}</td><td style={cell}>{r.verification_status || 'NOT_EVALUATED'}</td>
        </tr>)}</tbody></table>}</section>}
      {(tab === 'Mechanical design' || tab === 'Fit decisions') && <form onSubmit={save} style={{ display: 'grid', gap: 16 }}>
        {tab === 'Mechanical design' && <>
          <CoreAssemblyPreview revisionId={rid} designHash={assembly.design_sha256} />
          <section style={card}><h3>Mechanical assembly definition</h3><label>Scope<textarea required disabled={!editable} value={design.scope} onChange={e => update({ scope: e.target.value })} style={field} /></label>
            <label>Design notes<textarea disabled={!editable} value={design.notes} onChange={e => update({ notes: e.target.value })} style={field} /></label></section>
          <PartsBOMEditor
            parts={parts}
            update={update}
            editable={editable}
            steps={steps}
            open={open}
            busy={busy}
          />
          <section style={card}>
            <h3>{isPlasma ? 'Master Assembly CAD & Certified STEP Components' : 'Master Combined Assembly & Sourced STEP Parts'}</h3>
            <p style={{ margin: '8px 0', color: '#52627a' }}>
              {isPlasma
                ? 'Launch the complete 10-solid UHV Chamber 3D assembly in FreeCAD, or inspect individual certified OFE copper and boron nitride STEP models.'
                : 'Access the complete reconstructed 99-solid 3D assembly or individual sourced part STEP models for native CAD inspection.'}
            </p>

            {/* Master Combined Assembly Card */}
            <div style={{
              background: 'linear-gradient(135deg, #f0fdfa, #f8fafc)',
              border: '1.5px solid #0f766e',
              borderRadius: 8,
              padding: 16,
              marginBottom: 16,
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: 12,
                marginBottom: 10,
              }}>
                <div>
                  <span className="badge badge-blue" style={{ marginBottom: 6, display: 'inline-block' }}>MASTER COMBINED 3D ASSEMBLY</span>
                  <h4 style={{ margin: '2px 0', fontSize: 15, color: '#0f172a' }}>
                    {isPlasma ? 'PCE-100 Complete UHV Plasma Chamber & Electrodes Assembly' : 'HFT-000 Complete Transformer Core Assembly'}
                  </h4>
                  <p style={{ margin: '4px 0 0', fontSize: 12, color: '#475569' }}>
                    {isPlasma
                      ? '10 Solid Bodies (Chamber · Electrodes · 1/4" Water Coil · BN Discs · Waveguide · Flange) · 440 × 440 × 346 mm'
                      : '99 Solid Bodies (48 Ferrites · 45 Spacers · 3 Limbs · 2 Supports · 1 Base Plate) · 530 × 357 × 370 mm'}
                  </p>
                </div>

                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 600 }}
                    disabled={busy}
                    onClick={() => open(isPlasma ? 'mechanical/core-assembly/a-pce100/PCE-100-complete-assembly.step' : 'mechanical/core-assembly/a-2ce3be18/HFT-000-exploded-assembly.step')}
                    title={isPlasma ? "Opens master 3D CAD STEP assembly in FreeCAD" : "Opens exploded 3D model with all 99 components separated in space"}
                  >
                    {isPlasma ? '📦 Open Master Assembly (.step)' : '💥 Open Exploded View (Separated Parts)'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 6 }}
                    disabled={busy}
                    onClick={() => open(isPlasma ? 'mechanical/core-assembly/a-pce100/PCE-100-complete-assembly.FCStd' : 'mechanical/core-assembly/a-2ce3be18/HFT-000-core-assembly.FCStd')}
                    title="Opens FreeCAD Project (.FCStd)"
                  >
                    🛠️ Open FreeCAD Project (.FCStd)
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 6 }}
                    disabled={busy}
                    onClick={() => open(isPlasma ? 'mechanical/PCE-01-chamber.step' : 'mechanical/core-assembly/a-2ce3be18/HFT-000-core-assembly.step')}
                    title={isPlasma ? "Open Chamber Body STEP in FreeCAD" : "Opens master combined assembled STEP file"}
                  >
                    {isPlasma ? '🔬 Open Chamber Body STEP' : '📦 Open Assembled STEP (.step)'}
                  </button>
                </div>
              </div>

              <div style={{
                fontSize: 11,
                color: '#0f766e',
                background: '#ccfbf1',
                padding: '6px 10px',
                borderRadius: 6,
                border: '1px solid #99f6e4',
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}>
                <span>💡</span>
                <span>
                  <strong>FreeCAD Launch Hint:</strong> Clicking will launch FreeCAD with the selected 3D CAD model. If FreeCAD is already running in your taskbar, Windows will bring it into focus.
                </span>
              </div>
            </div>

            <h4 style={{ margin: '14px 0 8px', fontSize: 13, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              {isPlasma ? 'Individual Component Part STEPs (7 Certified Parts)' : 'Individual Component Part STEPs (4 Sourced Parts)'}
            </h4>
            {fileButtons(linkedSteps)}
          </section>
        </>}
        {tab === 'Fit decisions' && <section style={card}><h3>Fit, materials and design decisions</h3><p style={{ margin: '8px 0' }}>Record your clarification and its owner. A supplied disposition remains separate from verified inspection evidence.</p>
          {design.issues.map((issue, i) => <article key={i} style={{ borderTop: '1px solid #cbd5e1', padding: '16px 0' }}><h4>{issue.id} · {issue.title}</h4><p style={{ margin: '8px 0' }}>{issue.description}</p><small>Source: {issue.source}</small>
            <details><summary>Edit decision definition and source</summary>{['id', 'title', 'description', 'source'].map(key => <label key={key} style={{ display: 'block', marginTop: 8 }}>{key}<input required disabled={!editable} style={field} value={issue[key]} onChange={e => update({ issues: design.issues.map((x, idx) => idx === i ? { ...x, [key]: e.target.value } : x) })} /></label>)}</details>
            <label style={{ display: 'block', marginTop: 10 }}>Your clarification<textarea aria-label={`${issue.id} clarification`} disabled={!editable} style={field} value={issue.disposition} onChange={e => update({ issues: design.issues.map((x, idx) => idx === i ? { ...x, disposition: e.target.value } : x) })} /></label>
            <label>Decision owner<input disabled={!editable} aria-label={`${issue.id} owner`} style={field} value={issue.owner} onChange={e => update({ issues: design.issues.map((x, idx) => idx === i ? { ...x, owner: e.target.value } : x) })} /></label>
          </article>)}
          {!design.issues.length && <p>No decisions recorded.</p>}
          <button type="button" className="btn btn-secondary" disabled={!editable} onClick={() => update({ issues: [...design.issues, { id: `DECISION${design.issues.length + 1}`, title: '', description: '', source: '', disposition: '', owner: '' }] })}>Add decision</button>
        </section>}
        <div style={{ ...card, ...row }}><label>Record under stage<select aria-label="Assembly record stage" style={field} value={recordStage} onChange={e => setStageId(e.target.value)}>{activeStages.map(s => <option key={s.definition.id} value={s.definition.id}>{s.definition.name}</option>)}</select></label>
          <button className="btn btn-primary" disabled={!editable || busy || !dirty || !recordStage}>Save assembly design</button>
          <span>Creates a new version and preserves earlier records.</span>
        </div>
      </form>}
      {tab === 'Part Catalog & Specs' && <section style={{ display: 'grid', gap: 16 }}>{isPlasma ? (
<>
        {/* Master Catalog Banner */}
        <div style={{
          background: 'linear-gradient(135deg, #0f172a, #1e293b)',
          color: '#ffffff',
          borderRadius: 8,
          padding: 20,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
        }}>
          <div>
            <span style={{
              background: '#0ea5e9',
              color: '#fff',
              fontSize: 11,
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: 4,
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              PUBLICATION DELIVERABLE · 8 SHEETS
            </span>
            <h3 style={{ margin: '6px 0 2px', fontSize: 18, color: '#ffffff' }}>
              PCE-100 Master Technical Specification Dossier &amp; Part Catalog
            </h3>
            <p style={{ margin: 0, fontSize: 12, color: '#cbd5e1' }}>
              Complete engineering specification sheets with 3D CAD renders, dimensional tolerances, material callouts, and component schedules.
            </p>
          </div>

          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-primary"
              style={{ fontSize: 13, padding: '8px 16px', display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 700 }}
              disabled={busy}
              onClick={() => open('reports/PCE-100-Plasma-Chamber-Specification-Catalog.pdf')}
            >
              📄 Open Specification Catalog (PDF)
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: 13, padding: '8px 16px', display: 'inline-flex', alignItems: 'center', gap: 6 }}
              disabled={busy}
              onClick={() => open('reports/PCE-100-Plasma-Chamber-Specification-Catalog.html')}
            >
              🌐 View HTML Catalog
            </button>
          </div>
        </div>

        {/* Thermal & Hydraulic Multiphysics Banner */}
        <div style={{
          background: 'linear-gradient(135deg, #1e1b4b, #312e81)',
          color: '#ffffff',
          borderRadius: 8,
          padding: 18,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
        }}>
          <div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
              <span style={{
                background: '#6366f1',
                color: '#fff',
                fontSize: 10,
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 4,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                THERMAL &amp; HYDRAULIC MULTIPHYSICS · 3.0 BAR COOLING
              </span>
              <span className="badge badge-green" style={{ background: '#22c55e', color: '#fff', fontSize: 10, fontWeight: 700 }}>
                PROOF PRESSURE RATED (3.0 BAR)
              </span>
            </div>
            <h3 style={{ margin: '0 0 2px', fontSize: 17, color: '#ffffff' }}>
              Chamber Wall Thermal Dissipation &amp; 1/4" Hydraulic Circuit Analysis
            </h3>
            <p style={{ margin: 0, fontSize: 12, color: '#c7d2fe' }}>
              Finite-difference solver analysis: 100 kW heat dissipation capacity, 2.5 L/min flow rate, ΔT = 5.73 K rise, coolant pressure drop 0.28 bar (well within 3.0 bar proof limit).
            </p>
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-primary"
              style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 700, background: '#4f46e5', borderColor: '#4338ca' }}
              disabled={busy}
              onClick={() => open('reports/PCE-100-Thermal-and-Hydraulic-Cooling-Analysis.json')}
            >
              📄 Open Hydraulic Analysis (JSON)
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6 }}
              disabled={busy}
              onClick={() => open('reports/PCE-100-Plasma-Chamber-Specification-Catalog.pdf')}
            >
              📈 View Thermal Curves in Catalog
            </button>
          </div>
        </div>

        {/* AI Autonomous 2D Manufacturing Drawing Banner */}
        <div style={{
          background: 'linear-gradient(135deg, #064e3b, #047857)',
          color: '#ffffff',
          borderRadius: 8,
          padding: 18,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
        }}>
          <div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
              <span style={{
                background: '#10b981',
                color: '#fff',
                fontSize: 10,
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 4,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                AUTONOMOUS 2D DRAFTING · FREECAD TECHDRAW
              </span>
              <span className="badge badge-green" style={{ background: '#34d399', color: '#064e3b', fontSize: 10, fontWeight: 700 }}>
                ISO 5457 A3 / ISO 7200
              </span>
            </div>
            <h3 style={{ margin: '0 0 2px', fontSize: 17, color: '#ffffff' }}>
              Autonomous 2D Manufacturing Drawing (HLR Vector TechDraw · PCE-01)
            </h3>
            <p style={{ margin: 0, fontSize: 12, color: '#a7f3d0' }}>
              Hidden Line Removal (HLR) orthographic projections, Section B-B, internal M90×1.0 thread callout, ISO 2768-m linear tolerances, and Ra 1.6-3.0 µm vacuum surface finish.
            </p>
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-primary"
              style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 700, background: '#059669', borderColor: '#047857' }}
              disabled={busy}
              onClick={() => open('reports/PCE-01-Autonomous-Manufacturing-Drawing.pdf')}
            >
              📐 Open AI 2D Drawing (PDF)
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6 }}
              disabled={busy}
              onClick={() => open('reports/PCE-01-Autonomous-Manufacturing-Drawing.svg')}
            >
              🌐 View Vector SVG
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6 }}
              disabled={busy}
              onClick={() => open('reports/PCE-01-Autonomous-Manufacturing-Drawing.png')}
            >
              🖼️ View Render (PNG)
            </button>
          </div>
        </div>

        {/* Part Cards Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
          gap: 16,
        }}>
          {/* Card: PCE-100 Exploded Assembly */}
          <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>PCE-100 Exploded Assembly</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Master 3D CAD Reconstruction · 7 Solid Subsystems</div>
              </div>
              <span className="badge badge-blue">7 SOLIDS</span>
            </div>
            <div style={{ padding: 12, textAlign: 'center', background: '#f8fafc' }}>
              <img
                src={getPartImg('PCE-100_exploded_specification')}
                alt="PCE-100 Exploded Assembly"
                style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'contain', cursor: 'pointer' }}
                onClick={() => open('reports/part-specifications/PCE-100_exploded_specification.png')}
                title="Click to open high-resolution image"
              />
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
                <div><strong>Envelope:</strong> 440.0 × 440.0 × 346.0 mm · <strong>Mass:</strong> ~28.5 kg</div>
                <div><strong>Contents:</strong> Chamber, Electrode, 1/4" Tube Coils, 2x BN Discs, Waveguide, Flange</div>
                <div style={{ color: '#0f766e' }}><strong>Vacuum Boundary:</strong> UHV Helium leak rate &lt; 1.0 × 10⁻⁸ mbar·l/s</div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/part-specifications/PCE-100_exploded_specification.png')}>
                  🖼️ Download Image
                </button>
                <button type="button" className="btn btn-primary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/core-assembly/a-pce100/PCE-100-complete-assembly.step')}>
                  📦 Open STEP CAD
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px', borderColor: '#0f766e', color: '#0f766e' }} onClick={() => open('reports/PCE-100-Plasma-Chamber-Specification-Catalog.pdf')}>
                  📄 Spec Catalog (PDF)
                </button>
              </div>
            </div>
          </div>

          {/* Card: PCE-01 Chamber Body */}
          <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>PCE-01: Plasma Chamber Body</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Main Chamber Cavity &amp; Neck · ETP Copper</div>
              </div>
              <span className="badge badge-muted">1 INSTALLED</span>
            </div>
            <div style={{ padding: 12, textAlign: 'center', background: '#f8fafc' }}>
              <img
                src={getPartImg('PCE-01_specification')}
                alt="PCE-01 Chamber Body"
                style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'contain', cursor: 'pointer' }}
                onClick={() => open('reports/part-specifications/PCE-01_specification.png')}
                title="Click to open high-resolution image"
              />
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
                <div><strong>Dimensions:</strong> OD 200.0 × ID 146.0 × H 193.0 mm · <strong>Mass:</strong> ~6.85 kg</div>
                <div><strong>Material:</strong> Electrolytic Tough Pitch Copper (UNS C11000 / IS 191)</div>
                <div><strong>Features:</strong> 6x Ø5.5 mm holes on PCD 166.3 mm, internal M90×1.0 mm neck thread</div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/part-specifications/PCE-01_specification.png')}>
                  🖼️ Download Image
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/PCE-01-chamber.step')}>
                  📦 Open STEP CAD
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px', background: '#ecfdf5', borderColor: '#059669', color: '#059669', fontWeight: 600 }} onClick={() => open('reports/PCE-01-Autonomous-Manufacturing-Drawing.pdf')}>
                  📐 AI 2D Drawing (PDF)
                </button>
              </div>
            </div>
          </div>

          {/* Card: PCE-02 Electrode */}
          <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>PCE-02: Plasma Electrode</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Stepped Orifice Discharge Disc · ETP Copper</div>
              </div>
              <span className="badge badge-muted">1 INSTALLED</span>
            </div>
            <div style={{ padding: 12, textAlign: 'center', background: '#f8fafc' }}>
              <img
                src={getPartImg('PCE-02_specification')}
                alt="PCE-02 Plasma Electrode"
                style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'contain', cursor: 'pointer' }}
                onClick={() => open('reports/part-specifications/PCE-02_specification.png')}
                title="Click to open high-resolution image"
              />
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
                <div><strong>Dimensions:</strong> OD 90.0 mm × T 6.0 mm · <strong>Mass:</strong> ~0.32 kg</div>
                <div><strong>Material:</strong> Pure ETP Copper (Min 100% IACS Electrical Conductivity)</div>
                <div><strong>Features:</strong> Center orifice Ø8.0 mm, 4x M3 on PCD 50.0 mm, vacuum vent flats</div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/part-specifications/PCE-02_specification.png')}>
                  🖼️ Download Image
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/PCE-02-electrode.step')}>
                  📦 Open STEP CAD
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/cad/IPR_Plasma_Chamber_Fabrication_Drawings_Package.pdf')}>
                  📄 2D Drawing (PDF)
                </button>
              </div>
            </div>
          </div>

          {/* Card: PCE-03 Cooling Coils */}
          <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>PCE-03: 1/4" Water Cooling Circuit</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Serpentine Jacket Tube · ETP Cu + SS-400 Ferrules</div>
              </div>
              <span className="badge badge-muted">4 LOOPS</span>
            </div>
            <div style={{ padding: 12, textAlign: 'center', background: '#f8fafc' }}>
              <img
                src={getPartImg('PCE-03_specification')}
                alt="PCE-03 Cooling Coils"
                style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'contain', cursor: 'pointer' }}
                onClick={() => open('reports/part-specifications/PCE-03_specification.png')}
                title="Click to open high-resolution image"
              />
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
                <div><strong>Dimensions:</strong> 1/4" OD (6.35 mm) × 4 Hairpin Loops · <strong>Pressure:</strong> 3.0 bar proof</div>
                <div><strong>Material:</strong> Seamless ETP Copper Tube + SS 304 Swagelok Connectors</div>
                <div><strong>Performance:</strong> 2.5 L/min flow rate, ΔT = 5.73 K at 100 kW thermal load</div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/part-specifications/PCE-03_specification.png')}>
                  🖼️ Download Image
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/PCE-03-cooling-coil.step')}>
                  📦 Open STEP CAD
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/PCE-100-Thermal-and-Hydraulic-Cooling-Analysis.json')}>
                  📄 Hydraulic JSON
                </button>
              </div>
            </div>
          </div>

          {/* Card: PCE-04 BN Disc 1 */}
          <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>PCE-04: Boron Nitride Disc 1</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>High-Dielectric Vacuum Insulator · Grade AX05</div>
              </div>
              <span className="badge badge-muted">1 INSTALLED</span>
            </div>
            <div style={{ padding: 12, textAlign: 'center', background: '#f8fafc' }}>
              <img
                src={getPartImg('PCE-04_specification')}
                alt="PCE-04 BN Disc 1"
                style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'contain', cursor: 'pointer' }}
                onClick={() => open('reports/part-specifications/PCE-04_specification.png')}
                title="Click to open high-resolution image"
              />
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
                <div><strong>Dimensions:</strong> OD 80.0 mm × T 5.0 mm · <strong>Mass:</strong> ~0.048 kg</div>
                <div><strong>Material:</strong> Hot-Pressed Hexagonal Boron Nitride (Grade AX05, 99.0% BN)</div>
                <div><strong>Features:</strong> Center orifice Ø8.0 mm, 4x C-Bore Ø3.5/6.5 mm on PCD 80 mm</div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/part-specifications/PCE-04_specification.png')}>
                  🖼️ Download Image
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/PCE-04-bn-disc1.step')}>
                  📦 Open STEP CAD
                </button>
              </div>
            </div>
          </div>

          {/* Card: PCE-05 Ridged Waveguide */}
          <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>PCE-05: Ridged Microwave Waveguide</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Dual-Ridged Microwave Launcher · ETP Copper</div>
              </div>
              <span className="badge badge-muted">1 INSTALLED</span>
            </div>
            <div style={{ padding: 12, textAlign: 'center', background: '#f8fafc' }}>
              <img
                src={getPartImg('PCE-05_specification')}
                alt="PCE-05 Waveguide"
                style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'contain', cursor: 'pointer' }}
                onClick={() => open('reports/part-specifications/PCE-05_specification.png')}
                title="Click to open high-resolution image"
              />
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
                <div><strong>Dimensions:</strong> 74.0 × 36.0 × 138.0 mm · <strong>Mass:</strong> ~1.85 kg</div>
                <div><strong>Material:</strong> Pure ETP Copper, Wire EDM machined ridged throat</div>
                <div><strong>Features:</strong> 10.83 × 12.09 mm internal ridge, O-ring seal land Ra ≤ 0.8 µm</div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/part-specifications/PCE-05_specification.png')}>
                  🖼️ Download Image
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/PCE-05-waveguide.step')}>
                  📦 Open STEP CAD
                </button>
              </div>
            </div>
          </div>

          {/* Card: PCE-06 BN Disc 2 */}
          <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>PCE-06: Boron Nitride Disc 2</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Dielectric Vacuum Barrier · Grade AX05</div>
              </div>
              <span className="badge badge-muted">1 INSTALLED</span>
            </div>
            <div style={{ padding: 12, textAlign: 'center', background: '#f8fafc' }}>
              <img
                src={getPartImg('PCE-06_specification')}
                alt="PCE-06 BN Disc 2"
                style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'contain', cursor: 'pointer' }}
                onClick={() => open('reports/part-specifications/PCE-06_specification.png')}
                title="Click to open high-resolution image"
              />
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
                <div><strong>Dimensions:</strong> OD 89.0 mm × T 3.40 mm · <strong>Mass:</strong> ~0.038 kg</div>
                <div><strong>Material:</strong> Hot-Pressed Hexagonal Boron Nitride (Grade AX05)</div>
                <div><strong>Features:</strong> Rectangular RF aperture 38.2 × 6.35 mm, dry machined</div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/part-specifications/PCE-06_specification.png')}>
                  🖼️ Download Image
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/PCE-06-bn-disc2.step')}>
                  📦 Open STEP CAD
                </button>
              </div>
            </div>
          </div>

          {/* Card: PCE-07 SS 430 Flange */}
          <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>PCE-07: UHV Interface Flange</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Main Vacuum Interface · AISI 430 Stainless Steel</div>
              </div>
              <span className="badge badge-muted">1 INSTALLED</span>
            </div>
            <div style={{ padding: 12, textAlign: 'center', background: '#f8fafc' }}>
              <img
                src={getPartImg('PCE-07_specification')}
                alt="PCE-07 SS 430 Flange"
                style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'contain', cursor: 'pointer' }}
                onClick={() => open('reports/part-specifications/PCE-07_specification.png')}
                title="Click to open high-resolution image"
              />
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
                <div><strong>Dimensions:</strong> OD 440.0 × ID 200.0 × T 14.0 mm · <strong>Mass:</strong> ~13.2 kg</div>
                <div><strong>Material:</strong> Annealed Ferritic Stainless Steel AISI 430 (Flatness &lt; 0.03 mm)</div>
                <div><strong>Features:</strong> 32x Ø9 mm on PCD 415 mm, AS568-261 Viton O-ring seal groove</div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/part-specifications/PCE-07_specification.png')}>
                  🖼️ Download Image
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/PCE-07-flange.step')}>
                  📦 Open STEP CAD
                </button>
              </div>
            </div>
          </div>
        </div>
</>
) : (
<>{/* Master Catalog Banner */}
        <div style={{
          background: 'linear-gradient(135deg, #0f172a, #1e293b)',
          color: '#ffffff',
          borderRadius: 8,
          padding: 20,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
        }}>
          <div>
            <span style={{
              background: '#0ea5e9',
              color: '#fff',
              fontSize: 11,
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: 4,
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              PUBLICATION DELIVERABLE · 8 SHEETS
            </span>
            <h3 style={{ margin: '6px 0 2px', fontSize: 18, color: '#ffffff' }}>
              HFT-000 Master Technical Specification Dossier &amp; Part Catalog
            </h3>
            <p style={{ margin: 0, fontSize: 12, color: '#cbd5e1' }}>
              Complete engineering specification sheets with 3D CAD renders, dimensional tolerances, material callouts, and component schedules.
            </p>
          </div>

          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-primary"
              style={{ fontSize: 13, padding: '8px 16px', display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 700 }}
              disabled={busy}
              onClick={() => open('reports/HFT-000-Core-Assembly-Specification-Catalog.pdf')}
            >
              📄 Open Complete Specification PDF (8 Pages)
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: 13, padding: '8px 16px', display: 'inline-flex', alignItems: 'center', gap: 6 }}
              disabled={busy}
              onClick={() => open('reports/HFT-000-Core-Assembly-Specification-Catalog.html')}
            >
              🌐 View HTML Dossier
            </button>
          </div>
        </div>

        {/* FEMM 4.2 Magnetic FEA & Litz Wire Banner */}
        <div style={{
          background: 'linear-gradient(135deg, #1e1b4b, #312e81)',
          color: '#ffffff',
          borderRadius: 8,
          padding: 18,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
        }}>
          <div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
              <span style={{
                background: '#6366f1',
                color: '#fff',
                fontSize: 10,
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 4,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                FEMM 4.2 FEA REPORT · 100 kHz
              </span>
              <span className="badge badge-green" style={{ background: '#22c55e', color: '#fff', fontSize: 10, fontWeight: 700 }}>
                NON-SATURATING (89.2% MARGIN)
              </span>
            </div>
            <h3 style={{ margin: '0 0 2px', fontSize: 17, color: '#ffffff' }}>
              FEMM 4.2 Harmonic Magnetic FEA &amp; Ø0.5 mm Litz Wire Analysis
            </h3>
            <p style={{ margin: 0, fontSize: 12, color: '#c7d2fe' }}>
              2D electromagnetic solver analysis: Flux density B_pk = 0.042 T, Dowell AC resistance factor Fr = 1.102 (vs 11.22 for solid wire), and 90.2% copper loss reduction.
            </p>
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-primary"
              style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 700, background: '#4f46e5', borderColor: '#4338ca' }}
              disabled={busy}
              onClick={() => open('reports/HFT-000-FEMM-Magnetic-FEA-Report.pdf')}
            >
              📄 Open FEMM FEA Report (PDF)
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6 }}
              disabled={busy}
              onClick={() => open('reports/HFT-000-FEMM-Flux-Density-2D.png')}
            >
              📈 View 2D Flux Plot
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6 }}
              disabled={busy}
              onClick={() => open('simulations/femm/hft_litz_model.fem')}
            >
              🧲 Open Model in FEMM 4.2
            </button>
          </div>
        </div>

        {/* AI Autonomous 2D Manufacturing Drawing Banner */}
        <div style={{
          background: 'linear-gradient(135deg, #064e3b, #047857)',
          color: '#ffffff',
          borderRadius: 8,
          padding: 18,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 16,
        }}>
          <div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
              <span style={{
                background: '#10b981',
                color: '#fff',
                fontSize: 10,
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 4,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                AUTONOMOUS 2D DRAFTING · FREECAD TECHDRAW
              </span>
              <span className="badge badge-green" style={{ background: '#34d399', color: '#064e3b', fontSize: 10, fontWeight: 700 }}>
                ISO 5457 A3 / ISO 7200
              </span>
            </div>
            <h3 style={{ margin: '0 0 2px', fontSize: 17, color: '#ffffff' }}>
              Autonomous 2D Manufacturing Drawing (HLR Vector TechDraw)
            </h3>
            <p style={{ margin: 0, fontSize: 12, color: '#a7f3d0' }}>
              Hidden Line Removal (HLR) orthographic projections, Section B-B, blind hole callouts, ISO 2768-m linear tolerances, and title block generated directly from 3D CAD solids.
            </p>
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-primary"
              style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 700, background: '#059669', borderColor: '#047857' }}
              disabled={busy}
              onClick={() => open('reports/HFT-02-Autonomous-Manufacturing-Drawing.pdf')}
            >
              📐 Open AI 2D Drawing (PDF)
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6 }}
              disabled={busy}
              onClick={() => open('reports/HFT-02-Autonomous-Manufacturing-Drawing.svg')}
            >
              🌐 View Vector SVG
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6 }}
              disabled={busy}
              onClick={() => open('reports/HFT-02-AI-Manufacturing-Drawing.png')}
            >
              🖼️ View Render (PNG)
            </button>
          </div>
        </div>

        {/* Part Cards Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
          gap: 16,
        }}>
          {/* Card: Exploded Master Assembly */}
          <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>HFT-000 Exploded Assembly</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Master 3D CAD Reconstruction · 99 Solid Bodies</div>
              </div>
              <span className="badge badge-blue">99 SOLIDS</span>
            </div>
            <div style={{ padding: 12, textAlign: 'center', background: '#f8fafc' }}>
              <img
                src={getPartImg('HFT-000_exploded_specification')}
                alt="Exploded Assembly"
                style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'contain', cursor: 'pointer' }}
                onClick={() => open('reports/part-specifications/HFT-000_exploded_specification.png')}
                title="Click to open high-resolution image"
              />
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
                <div><strong>Envelope:</strong> 530 × 357 × 370 mm</div>
                <div><strong>Contents:</strong> 48 Ferrites · 45 Spacers · 3 Limbs · 2 Supports · 1 Base Plate</div>
                <div><strong>Spatial Gaps:</strong> 4 mm between toroids; base -80 mm; supports ±95 mm</div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/part-specifications/HFT-000_exploded_specification.png')}>
                  🖼️ Download / Open Image
                </button>
                <button type="button" className="btn btn-primary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/core-assembly/a-2ce3be18/HFT-000-exploded-assembly.step')}>
                  💥 Open STEP in FreeCAD
                </button>
              </div>
            </div>
          </div>

          {/* Card: HFT-01 Base Plate */}
          <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>HFT-01: Base Mounting Plate</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Structural Substructure · AISI 304 SS</div>
              </div>
              <span className="badge badge-muted">1 INSTALLED</span>
            </div>
            <div style={{ padding: 12, textAlign: 'center', background: '#f8fafc' }}>
              <img
                src={getPartImg('HFT-01_specification')}
                alt="HFT-01 Base Plate"
                style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'contain', cursor: 'pointer' }}
                onClick={() => open('reports/part-specifications/HFT-01_specification.png')}
                title="Click to open high-resolution image"
              />
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
                <div><strong>Dimensions:</strong> 530.0 × 140.0 × 15.0 mm · <strong>Mass:</strong> ~8.25 kg</div>
                <div><strong>Material:</strong> Austenitic Stainless Steel AISI 304 / EN 1.4301</div>
                <div><strong>Features:</strong> 6× M8 tapped support holes, 4× cabinet deck slots</div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/part-specifications/HFT-01_specification.png')}>
                  🖼️ Download / Open Image
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/source-update-20261118/HFT-01.STEP')}>
                  📦 Open STEP CAD
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/source/HFT-01.pdf')}>
                  📄 2D Drawing (PDF)
                </button>
              </div>
            </div>
          </div>

          {/* Card: HFT-02 Upright Clamp Support */}
          <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>HFT-02: Upright Clamp Support</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Vertical Retention Endplate · Glass-Filled Polymer / Al</div>
              </div>
              <span className="badge badge-muted">2 INSTALLED</span>
            </div>
            <div style={{ padding: 12, textAlign: 'center', background: '#f8fafc' }}>
              <img
                src={getPartImg('HFT-02_specification')}
                alt="HFT-02 Upright Support"
                style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'contain', cursor: 'pointer' }}
                onClick={() => open('reports/part-specifications/HFT-02_specification.png')}
                title="Click to open high-resolution image"
              />
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
                <div><strong>Dimensions:</strong> 357.0 × 370.0 × 20.0 mm · <strong>Mass:</strong> ~3.40 kg each</div>
                <div><strong>Limb Triad:</strong> 3× Ø64.2 mm counterbore seats (207.0 mm pitch)</div>
                <div><strong>Mounting:</strong> 3× Ø9.0 mm clearance through-holes for M8 SS bolts</div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/part-specifications/HFT-02_specification.png')}>
                  🖼️ Download Image
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/source-update-20261118/HFT-02.STEP')}>
                  📦 Open STEP CAD
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/source/HFT-02.pdf')}>
                  📄 Sourced PDF
                </button>
                <button type="button" className="btn btn-primary" style={{ fontSize: 11, padding: '5px 10px', background: '#059669', borderColor: '#047857' }} onClick={() => open('reports/HFT-02-Autonomous-Manufacturing-Drawing.pdf')}>
                  📐 AI TechDraw (PDF)
                </button>
              </div>
            </div>
          </div>

          {/* Card: HFT-03 Core Limb Mandrel Rod */}
          <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>HFT-03: Core Limb Mandrel Rod</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Precision Mandrel · Glass-Filled PTFE / G10</div>
              </div>
              <span className="badge badge-muted">3 INSTALLED</span>
            </div>
            <div style={{ padding: 12, textAlign: 'center', background: '#f8fafc' }}>
              <img
                src={getPartImg('HFT-03_specification')}
                alt="HFT-03 Core Limb Rod"
                style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'contain', cursor: 'pointer' }}
                onClick={() => open('reports/part-specifications/HFT-03_specification.png')}
                title="Click to open high-resolution image"
              />
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
                <div><strong>Dimensions:</strong> Ø63.95 mm OD × 420.0 mm Length · <strong>Mass:</strong> ~1.95 kg</div>
                <div><strong>Material:</strong> High-dielectric composite (Breakdown &gt; 15 kV/mm)</div>
                <div style={{ color: '#b45309' }}><strong>Fit Conflict D09:</strong> Core bore 63.7 mm min vs Limb OD 63.95 mm</div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/part-specifications/HFT-03_specification.png')}>
                  🖼️ Download / Open Image
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/source-update-20261118/HFT-03.STEP')}>
                  📦 Open STEP CAD
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/source/HFT-03.pdf')}>
                  📄 2D Drawing (PDF)
                </button>
              </div>
            </div>
          </div>

          {/* Card: HFT-04 Inter-Core PTFE Spacer */}
          <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>HFT-04: High-Voltage PTFE Spacer</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Acoustic &amp; Creepage Barrier · Virgin PTFE</div>
              </div>
              <span className="badge badge-muted">45 INST + 10 SPARE</span>
            </div>
            <div style={{ padding: 12, textAlign: 'center', background: '#f8fafc' }}>
              <img
                src={getPartImg('HFT-04_specification')}
                alt="HFT-04 PTFE Spacer"
                style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'contain', cursor: 'pointer' }}
                onClick={() => open('reports/part-specifications/HFT-04_specification.png')}
                title="Click to open high-resolution image"
              />
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
                <div><strong>Dimensions:</strong> OD 107.0 mm × ID 65.0 mm × T 1.0 mm · <strong>Mass:</strong> ~12.5 g</div>
                <div><strong>Material:</strong> Pure Virgin PTFE (Dielectric constant 2.1)</div>
                <div><strong>Role:</strong> Acoustic dampening between toroids &amp; creepage barrier</div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/part-specifications/HFT-04_specification.png')}>
                  🖼️ Download / Open Image
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/source-update-20261118/HFT-04.STEP')}>
                  📦 Open STEP CAD
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/source/HFT-04.pdf')}>
                  📄 2D Drawing (PDF)
                </button>
              </div>
            </div>
          </div>

          {/* Card: Toroidal Ferrite Core */}
          <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>T107/65/25: Toroidal Ferrite Core</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Magnetic Toroid · Ferroxcube 3C90 / 3F4</div>
              </div>
              <span className="badge badge-muted">48 INST + 24 SPARE</span>
            </div>
            <div style={{ padding: 12, textAlign: 'center', background: '#f8fafc' }}>
              <img
                src={getPartImg('FERRITE-CORE_specification')}
                alt="Ferrite Core"
                style={{ maxWidth: '100%', maxHeight: 220, borderRadius: 6, objectFit: 'contain', cursor: 'pointer' }}
                onClick={() => open('reports/part-specifications/FERRITE-CORE_specification.png')}
                title="Click to open high-resolution image"
              />
            </div>
            <div style={{ padding: 14, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
                <div><strong>Dimensions:</strong> OD 107 ±2.0 × ID 65 ±1.3 × H 25 ±0.75 mm · <strong>Mass:</strong> ~530 g</div>
                <div><strong>Magnetic:</strong> Effective volume V_e = 132,600 mm³ · Area A_e = 512 mm²</div>
                <div style={{ color: '#b45309' }}><strong>Warning:</strong> Bore tolerance min is 63.7 mm (D09 clearance)</div>
              </div>
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('reports/part-specifications/FERRITE-CORE_specification.png')}>
                  🖼️ Download / Open Image
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px' }} onClick={() => open('mechanical/source-update-20261118/data Sheet.pdf')}>
                  📄 Sourced Datasheet (PDF)
                </button>
              </div>
            </div>
          </div>
        </div></>
)}</section>}
      {tab === 'Turnkey Engineering & FAT' && <section style={{ display: 'grid', gap: 16 }}>{isPlasma ? (
<>
        {/* Master Header Banner */}
        <div style={{
          background: 'linear-gradient(135deg, #091e3a, #0f2b48)',
          color: '#ffffff',
          borderRadius: 8,
          padding: 20,
          border: '1.5px solid #0284c7',
        }}>
          <span style={{
            background: '#0284c7',
            color: '#fff',
            fontSize: 10.5,
            fontWeight: 800,
            padding: '2px 8px',
            borderRadius: 4,
            textTransform: 'uppercase',
            letterSpacing: '0.6px'
          }}>
            CDR TO FAT INDUSTRIALIZATION
          </span>
          <h3 style={{ margin: '6px 0 2px', fontSize: 18, color: '#ffffff' }}>
            Turnkey Engineering, Cleanroom Vacuum SOP &amp; IPR FAT Acceptance Center
          </h3>
          <p style={{ margin: 0, fontSize: 12, color: '#93c5fd' }}>
            Complete closure of the IPR tender product development cycle: MSLD Helium leak testing (&lt; 1e-8 mbar·l/s), 3.0 bar hydrostatic pressure hold, ultrasonic cleanroom vacuum assembly SOP with silver flash anti-galling plating, and 6-stage customer witness acceptance protocol.
          </p>
        </div>

        {/* 4 Engineering Modules Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: 16 }}>

          {/* Module 1: UHV Vacuum Boundary & MSLD Leak Testing */}
          <div style={{ background: '#fff', border: '1.5px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '14px 18px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>1. UHV Vacuum Boundary &amp; MSLD Leak Testing</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Mass Spectrometer Leak Detector (&lt; 1.0 × 10⁻⁸ mbar·l/s)</div>
              </div>
              <span className="badge badge-green" style={{ background: '#10b981', color: '#fff', fontSize: 10, fontWeight: 700 }}>
                SPEC COMPLIANT
              </span>
            </div>
            <div style={{ padding: 16, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
              <div>
                <div><strong>Helium Leak Limit:</strong> Q_leak &lt; <strong>1.0 × 10⁻⁸ mbar·l/s</strong> overall and for each brazed/welded joint.</div>
                <div style={{ marginTop: 4 }}><strong>Instrument Sensitivity:</strong> Calibrated MSLD sensitivity &le; 5 × 10⁻¹¹ mbar·l/s; background stabilized &lt; 1 × 10⁻⁹ mbar·l/s.</div>
                <div style={{ marginTop: 4 }}><strong>Joint Geometry:</strong> Continuous full-penetration vacuum boundary; zero virtual trapped volumes on blind threads.</div>
                <div style={{ marginTop: 4 }}><strong>Test Modes:</strong> Combined vacuum chamber envelope hood testing + precision sniffer probe sniffing at 1.0 bar differential.</div>
              </div>
              <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-primary" style={{ fontSize: 11, padding: '6px 12px', background: '#0f766e', borderColor: '#115e59' }} onClick={() => open('reports/PCE-100-Factory-Acceptance-Test-Protocol.pdf')}>
                  📄 Open FAT Acceptance Protocol (PDF)
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '6px 12px' }} onClick={() => open('reports/PCE-100-Factory-Acceptance-Test-Protocol.html')}>
                  🌐 View Protocol (HTML)
                </button>
              </div>
            </div>
          </div>

          {/* Module 2: Thermal & Hydraulic Cooling Circuit Multi-physics */}
          <div style={{ background: '#fff', border: '1.5px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '14px 18px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>2. Thermal &amp; Hydraulic Multi-physics Engine</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>3.0 Bar Water Cooling Circuit &amp; Heat Dissipation</div>
              </div>
              <span className="badge badge-green" style={{ background: '#0284c7', color: '#fff', fontSize: 10, fontWeight: 700 }}>
                3.0 BAR RATED
              </span>
            </div>
            <div style={{ padding: 16, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
              <div>
                <div><strong>Operating Pressure:</strong> <strong>3.0 bar</strong> nominal operating (proof test 4.5 bar hold for 30 minutes with zero drop).</div>
                <div style={{ marginTop: 4 }}><strong>Circuit Construction:</strong> 1/4" seamless ETP copper tubing in 4 serpentine hairpin loops wrapped around OD100 neck.</div>
                <div style={{ marginTop: 4 }}><strong>Flow Rate:</strong> <strong>2.5 L/min</strong> cooling water flow rate yielding ΔT = 5.73 K at 100 kW thermal dissipation.</div>
                <div style={{ marginTop: 4 }}><strong>Pressure Drop:</strong> Laminar hydraulic friction drop &Delta;P = <strong>0.28 bar</strong> (well within supply capability).</div>
                <div style={{ marginTop: 4 }}><strong>Fittings:</strong> Swagelok SS-400 double-ferrule compression unions on inlet/outlet stubs.</div>
              </div>
              <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-primary" style={{ fontSize: 11, padding: '6px 12px', background: '#0284c7', borderColor: '#0369a1' }} onClick={() => open('reports/PCE-100-Thermal-and-Hydraulic-Cooling-Analysis.json')}>
                  📄 Open Hydraulic Analysis (JSON)
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '6px 12px' }} onClick={() => open('reports/PCE-100-Plasma-Chamber-Specification-Catalog.pdf')}>
                  📈 Open Spec Catalog (PDF)
                </button>
              </div>
            </div>
          </div>

          {/* Module 3: Cleanroom Vacuum Assembly & Anti-Galling SOP */}
          <div style={{ background: '#fff', border: '1.5px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '14px 18px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>3. Cleanroom Vacuum Assembly &amp; Anti-Galling SOP</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Standard Operating Procedure SOP-PCE-100</div>
              </div>
              <span className="badge badge-muted">ISO CLASS 7</span>
            </div>
            <div style={{ padding: 16, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
              <div>
                <div><strong>Cleanroom Protocol:</strong> ISO Class 7 cleanroom assembly; powder-free nitrile gloves; lint-free polyester wipes.</div>
                <div style={{ marginTop: 4 }}><strong>4-Stage Ultrasonic Cleaning:</strong> Alconox alkaline wash (55°C, 20 min) &rarr; DI water rinse &rarr; Acetone degrease &rarr; Electronic-grade IPA rinse.</div>
                <div style={{ marginTop: 4 }}><strong>Anti-Galling Thread Treatment:</strong> Mandatory <strong>5 µm pure silver flash plating</strong> on M90×1.0 mm and electrode threads to prevent vacuum galling.</div>
                <div style={{ marginTop: 4 }}><strong>Vacuum Bakeout:</strong> Vacuum oven bakeout at 150°C for 24 hours under &lt; 1 × 10⁻⁵ mbar before packaging.</div>
              </div>
              <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-primary" style={{ fontSize: 11, padding: '6px 12px' }} onClick={() => open('reports/PCE-100-Manufacturing-Assembly-SOP.pdf')}>
                  📄 Open Assembly SOP (PDF)
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '6px 12px' }} onClick={() => open('reports/PCE-100-Manufacturing-Assembly-SOP.html')}>
                  🌐 View SOP (HTML)
                </button>
              </div>
            </div>
          </div>

          {/* Module 4: FAT & Customer Acceptance Protocol */}
          <div style={{ background: '#fff', border: '1.5px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '14px 18px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>4. Factory Acceptance Test (FAT) Protocol</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>IPR Customer Witness Inspection Document</div>
              </div>
              <span className="badge badge-green" style={{ background: '#0f766e', color: '#fff', fontSize: 10, fontWeight: 700 }}>
                IPR TENDER COMPLIANT
              </span>
            </div>
            <div style={{ padding: 16, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
              <div>
                <div><strong>6-Stage Witness Protocol:</strong> 1. Dimensional CMM inspection; 2. Visual &amp; Dye Penetrant weld test; 3. 3.0 Bar pressure hold; 4. MSLD Helium leak test; 5. RF Waveguide VSWR sweep; 6. Nitrogen purge packaging.</div>
                <div style={{ marginTop: 4 }}><strong>Vacuum Acceptance Threshold:</strong> MSLD leak rate &lt; 1.0 × 10⁻⁸ mbar·l/s at 100% Helium concentration.</div>
                <div style={{ marginTop: 4 }}><strong>Pressure Acceptance Threshold:</strong> Zero pressure drop and zero visible leakage at 3.0 bar hold for 30 minutes.</div>
                <div style={{ marginTop: 4 }}><strong>Dual Sign-off Blocks:</strong> Attributable Manufacturer QA Lead + IPR Scientific Officer acceptance signatures.</div>
              </div>
              <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-primary" style={{ fontSize: 11, padding: '6px 12px', background: '#0f766e', borderColor: '#115e59' }} onClick={() => open('reports/PCE-100-Factory-Acceptance-Test-Protocol.pdf')}>
                  📄 Open FAT Protocol (PDF)
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '6px 12px' }} onClick={() => open('reports/PCE-100-Factory-Acceptance-Test-Protocol.html')}>
                  🌐 View FAT Protocol (HTML)
                </button>
              </div>
            </div>
          </div>

        </div>
</>
) : (
<>{/* Master Header Banner */}
        <div style={{
          background: 'linear-gradient(135deg, #091e3a, #0f2b48)',
          color: '#ffffff',
          borderRadius: 8,
          padding: 20,
          border: '1.5px solid #0284c7',
        }}>
          <span style={{
            background: '#0284c7',
            color: '#fff',
            fontSize: 10.5,
            fontWeight: 800,
            padding: '2px 8px',
            borderRadius: 4,
            textTransform: 'uppercase',
            letterSpacing: '0.6px'
          }}>
            CDR TO FAT INDUSTRIALIZATION
          </span>
          <h3 style={{ margin: '6px 0 2px', fontSize: 18, color: '#ffffff' }}>
            Turnkey Engineering, Manufacturing SOP &amp; FAT Acceptance Center
          </h3>
          <p style={{ margin: 0, fontSize: 12, color: '#93c5fd' }}>
            Complete closure of the industrial product development cycle: CTE mismatch analysis (D09 resolution), 1 MHz coupled SPICE subcircuits, cleanroom manufacturing SOP with torque standards, and IPR customer witness acceptance protocols.
          </p>
        </div>

        {/* 4 Engineering Modules Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: 16 }}>

          {/* Module 1: CTE Mismatch & Thermal Fit Engine */}
          <div style={{ background: '#fff', border: '1.5px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '14px 18px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>1. Thermal Expansion &amp; Fit Engine (D09)</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>PTFE vs Ferrite CTE Analysis &amp; Belleville Clamping</div>
              </div>
              <span className="badge badge-green" style={{ background: '#10b981', color: '#fff', fontSize: 10, fontWeight: 700 }}>
                HAZARD MITIGATED
              </span>
            </div>
            <div style={{ padding: 16, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
              <div>
                <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: '8px 12px', borderRadius: 6, marginBottom: 10, color: '#991b1b' }}>
                  <strong>As-Drawn Danger (Ø64.0 mm Mandrel):</strong> At 85°C (&Delta;T = 60 K), PTFE expansion causes <strong>-0.73 mm interference</strong> under minimum core bore (63.7 mm), causing tensile hoop stress fracture of ceramic ferrites.
                </div>
                <div><strong>Engineered Solution:</strong> Skim mandrel OD to <strong>Ø62.70 mm</strong> (+0/-0.1 mm), guaranteeing <strong>&ge; 0.25 mm radial gap</strong> at maximum temperature.</div>
                <div style={{ marginTop: 6 }}><strong>Axial Stack Tolerance:</strong> &plusmn;13.5 mm worst-case (&plusmn;3.1 mm RSS). Solved via 4x DIN 2093 Belleville disc springs (2-series/2-parallel) providing <strong>280 N pre-load</strong> (14.2x safety margin).</div>
                <div style={{ marginTop: 6 }}><strong>Cooling Airflow:</strong> Total losses 173 W (145 W core + 28 W winding). Requires <strong>45 CFM forced-air fan</strong> (1.5 m/s) to cap steady-state temperature rise at <strong>27.7°C (52.7°C hotspot)</strong>.</div>
              </div>
              <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '6px 12px' }} onClick={() => open('reports/HFT-000-Thermal-and-Tolerance-Stack-Analysis.json')}>
                  📄 View Thermal Fit JSON
                </button>
              </div>
            </div>
          </div>

          {/* Module 2: Coupled SPICE Subcircuit Exporter */}
          <div style={{ background: '#fff', border: '1.5px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '14px 18px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>2. 1 MHz Coupled SPICE Subcircuit</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>LTspice / ngspice 3-Limb Model (.subckt &amp; .cir)</div>
              </div>
              <span className="badge badge-blue">1 MHz MODEL</span>
            </div>
            <div style={{ padding: 16, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
              <div>
                <div><strong>Inductance:</strong> L_mag = <strong>8.32 mH per limb</strong> (16 turns, AL = 32.5 µH/turn²).</div>
                <div style={{ marginTop: 4 }}><strong>Spatial Coupling:</strong> Equilateral triad layout provides symmetric mutual coupling <strong>k12 = k23 = k31 = 0.085</strong> across 207 mm center pitch.</div>
                <div style={{ marginTop: 4 }}><strong>High-Frequency Conduction:</strong> Dowell AC proximity factor Fr = 1.102 for Type 2 Litz (1000x AWG 44 strands), yielding <strong>R_ac = 0.098 &Omega;</strong> at 1 MHz.</div>
                <div style={{ marginTop: 4 }}><strong>Core Loss Damping:</strong> Parallel equivalent damping <strong>R_p = 4.44 M&Omega;</strong> (modeling 145 W core loss at Q = 85).</div>
                <div style={{ marginTop: 4 }}><strong>Parasitics:</strong> C_turn = 8.5 pF, C_gnd = 24.0 pF (Self-resonant frequency SRF &gt; 18 MHz).</div>
              </div>
              <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-primary" style={{ fontSize: 11, padding: '6px 12px', background: '#4f46e5', borderColor: '#4338ca' }} onClick={() => open('simulations/spice/HFT_000_1MHZ.subckt')}>
                  ⚡ Open SPICE Subcircuit (.subckt)
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '6px 12px' }} onClick={() => open('simulations/spice/HFT_000_testbench.cir')}>
                  🔬 Open Testbench Netlist (.cir)
                </button>
              </div>
            </div>
          </div>

          {/* Module 3: Manufacturing SOP & Torque Standard */}
          <div style={{ background: '#fff', border: '1.5px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '14px 18px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>3. Manufacturing Assembly SOP &amp; Torque</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>Standard Operating Procedure SOP-HFT-000</div>
              </div>
              <span className="badge badge-muted">ISO CLASS 8</span>
            </div>
            <div style={{ padding: 16, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
              <div>
                <div><strong>Cleanroom Protocol:</strong> ISO Class 8 cleanroom or dust-free laminar flow bench with anti-static smocks.</div>
                <div style={{ marginTop: 4 }}><strong>Critical DFM Reinforcement:</strong> Mandatory pre-installation of <strong>M8 &times; 1.25 &times; 16 mm 304 SS Helicoil Inserts</strong> in all PTFE support holes to prevent cold-flow creep under load.</div>
                <div style={{ marginTop: 4 }}><strong>Stacking Sequence:</strong> Staged vertical fixture assembly alternating 1 toroid + 1 spacer (16 ferrites + 15 spacers per limb).</div>
                <div style={{ marginTop: 4 }}><strong>Calibrated Torquing:</strong> 4-pass cross-diagonal sequence (Pass 1: 2.0 N&middot;m, Pass 2: 6.5 N&middot;m, Pass 3: <strong>12.5 N&middot;m &plusmn; 0.5 N&middot;m</strong> with Loctite 243).</div>
              </div>
              <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-primary" style={{ fontSize: 11, padding: '6px 12px' }} onClick={() => open('reports/HFT-000-Manufacturing-Assembly-SOP.pdf')}>
                  📄 Open Assembly SOP (PDF)
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '6px 12px' }} onClick={() => open('reports/HFT-000-Manufacturing-Assembly-SOP.html')}>
                  🌐 View SOP (HTML)
                </button>
              </div>
            </div>
          </div>

          {/* Module 4: FAT & Customer Acceptance Protocol */}
          <div style={{ background: '#fff', border: '1.5px solid #cbd5e1', borderRadius: 8, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '14px 18px', background: '#f8fafc', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ fontSize: 14, color: '#0f172a' }}>4. Factory Acceptance Test (FAT) Protocol</strong>
                <div style={{ fontSize: 11, color: '#64748b' }}>IPR Customer Witness Inspection Document</div>
              </div>
              <span className="badge badge-green" style={{ background: '#0f766e', color: '#fff', fontSize: 10, fontWeight: 700 }}>
                TENDER 307 COMPLIANT
              </span>
            </div>
            <div style={{ padding: 16, flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', fontSize: 12, color: '#334155', lineHeight: 1.5 }}>
              <div>
                <div><strong>Tender Clause 1 &amp; 8:</strong> Dimensional inspection sheet with &plusmn;2 mm limb tolerance and &plusmn;5 mm support tolerances.</div>
                <div style={{ marginTop: 4 }}><strong>Tender Clause 3 &amp; 5:</strong> Ferroxcube 3F4 batch CoC verification (&mu;_i = 912, B_sat = 0.385 T).</div>
                <div style={{ marginTop: 4 }}><strong>Tender Clause 7:</strong> 24 spare ferrite cores verified and packed in foam-lined crate.</div>
                <div style={{ marginTop: 4 }}><strong>Electrical &amp; Hi-Pot Tests:</strong> 5.0 kV_RMS AC (50 Hz / 60s) dielectric withstand (0.18 mA leakage), Megger &gt; 2.5 G&Omega; @ 1 kV DC.</div>
                <div style={{ marginTop: 4 }}><strong>Dual Sign-off:</strong> Attributable QA Engineer + IPR Scientific Officer acceptance blocks.</div>
              </div>
              <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-primary" style={{ fontSize: 11, padding: '6px 12px', background: '#0f766e', borderColor: '#115e59' }} onClick={() => open('reports/HFT-000-Factory-Acceptance-Test-Protocol.pdf')}>
                  📄 Open FAT Protocol (PDF)
                </button>
                <button type="button" className="btn btn-secondary" style={{ fontSize: 11, padding: '6px 12px' }} onClick={() => open('reports/HFT-000-Factory-Acceptance-Test-Protocol.html')}>
                  🌐 View FAT Protocol (HTML)
                </button>
              </div>
            </div>
          </div>

        </div></>
)}</section>}
      {tab === 'Inspection' && <section style={card}>
        <div style={{
          background: 'linear-gradient(135deg, #0f766e, #115e59)',
          color: '#ffffff',
          borderRadius: 8,
          padding: 16,
          marginBottom: 16,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
        }}>
          <div>
            <span style={{ background: '#34d399', color: '#064e3b', fontSize: 10, fontWeight: 800, padding: '2px 8px', borderRadius: 4, textTransform: 'uppercase' }}>
              CUSTOMER ACCEPTANCE PROTOCOL
            </span>
            <h4 style={{ margin: '4px 0 2px', fontSize: 16, color: '#ffffff' }}>
              {isPlasma ? 'IPR Factory Acceptance Test (FAT) Document (PCE-100)' : 'IPR Factory Acceptance Test (FAT) Document'}
            </h4>
            <p style={{ margin: 0, fontSize: 12, color: '#ccfbf1' }}>
              {isPlasma
                ? 'Compliant with tender specification: physical CMM inspection, material CoCs (ETP Cu, SS 430, Boron Nitride AX05), MSLD Helium leak test (< 1e-8 mbar·l/s), and 3.0 bar pressure hold.'
                : 'Compliant with final_specs_307 Section 2: physical inspection (±2mm / ±5mm), material CoC, 5 kV Hi-Pot, and 24 spare toroids check.'}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-primary"
              style={{ fontSize: 12, padding: '6px 14px', background: '#ffffff', color: '#0f766e', fontWeight: 700, border: 'none' }}
              onClick={() => open(isPlasma ? 'reports/PCE-100-Factory-Acceptance-Test-Protocol.pdf' : 'reports/HFT-000-Factory-Acceptance-Test-Protocol.pdf')}
            >
              📄 Open FAT Protocol (PDF)
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: 12, padding: '6px 14px', background: 'rgba(255,255,255,0.15)', color: '#ffffff', borderColor: 'rgba(255,255,255,0.3)' }}
              onClick={() => open(isPlasma ? 'reports/PCE-100-Manufacturing-Assembly-SOP.pdf' : 'reports/HFT-000-Manufacturing-Assembly-SOP.pdf')}
            >
              📄 Open Assembly SOP (PDF)
            </button>
          </div>
        </div>



        <h3>Dimensional inspection and supplier evidence</h3>
        <p style={{ margin: '8px 0' }}>Plans, document reviews and supplied evidence. Physical inspection and customer acceptance remain separate.</p>
        {fileButtons(inspection)}
      </section>}
      {tab === 'Files' && <section style={card}><h3>Revision sources and documents</h3>
        {fileButtons(data.files.filter(f => !/\.(py|pyc)$/i.test(f.relative_path) && (!/\.(step|stp|fcstd)$/i.test(f.relative_path) || linkedSteps.some(s => s.relative_path === f.relative_path) || f.relative_path.startsWith('mechanical/core-assembly/'))))}
        <details style={{ marginTop: 18 }}><summary>Additional unlinked CAD retained from earlier work · not the core assembly model</summary>
          {fileButtons(steps.filter(f => !linkedSteps.some(s => s.relative_path === f.relative_path) && !f.relative_path.startsWith('mechanical/core-assembly/')))}
        </details>
      </section>}
      {tab === 'Lifecycle' && <section style={{ display: 'grid', gap: 12 }}><h3>Core and support assembly lifecycle</h3>{stages.map((s, i) => <article key={s.definition.id} style={card}><div style={{ ...row, justifyContent: 'space-between' }}><h4>{i + 1}. {s.definition.name}</h4><span className="badge badge-muted">{s.effective_status || s.status}</span></div>
        <p style={{ margin: '10px 0' }}>{s.definition.purpose}</p><p>{s.blockers.join(' · ')}</p>
        <div style={{ ...row, marginTop: 12 }}>
          {['NOT_STARTED', 'BLOCKED', 'FAILED'].includes(s.status) && <button className="btn btn-secondary" disabled={!editable || busy} onClick={() => run(() => api.applyStage(rid, s.definition.id, 'start'), 'Stage started.')}>Start stage</button>}
          {['IN_PROGRESS', 'AWAITING_REVIEW'].includes(s.status) && <>
            <button className="btn btn-secondary" disabled={!editable || busy} onClick={() => run(async () => { const pkg = await api.reviewPackage(rid, s.definition.id); setReview(pkg); setReviewer(''); setComments(''); }, 'Review package loaded.')}>Review stage</button>
            <button className="btn btn-primary" disabled={!editable || busy || s.blockers.length > 0} onClick={() => run(() => api.completeStage(rid, s.definition.id), 'Stage completed.')}>Complete stage</button>
          </>}
        </div></article>)}</section>}
      {review && <section style={{ ...card, borderColor: '#0f766e' }}><h3>Review: {review.stage.name}</h3><p>Manual reviewer attribution; identity is not authenticated. This decision does not grant manufacturing approval.</p>
        <p style={{ color: '#b91c1c', margin: '10px 0' }}>{review.safety_blockers?.join(' · ')}</p>
        <details><summary>Documents and evidence presented for review</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{JSON.stringify({ documents: review.document_hashes, evidence: review.evidence_hashes, missing: review.missing_information }, null, 2)}</pre></details>
        <form style={{ display: 'grid', gap: 10, marginTop: 12 }} onSubmit={e => { e.preventDefault(); run(async () => {
          await api.submitReview({ revision_id: rid, stage_id: review.stage.id, attempt: review.stage.attempt,
            reviewer_name: reviewer, comments, decision, expected_document_hashes: review.document_hashes,
            expected_evidence_hashes: review.evidence_hashes, expected_requirements_digest: review.requirements_package.digest,
            expected_specification_hash: review.revision.specification_hash, idempotency_key: crypto.randomUUID() }); setReview(null);
        }, 'Manual review recorded.'); }}>
          <label>Reviewer name<input required style={field} value={reviewer} onChange={e => setReviewer(e.target.value)} /></label>
          <label>Review comments<textarea required style={field} value={comments} onChange={e => setComments(e.target.value)} /></label>
          <label>Decision<select style={field} value={decision} onChange={e => setDecision(e.target.value as typeof decision)}><option value="CHANGES_REQUESTED">Changes requested</option><option value="REJECTED">Rejected</option><option value="APPROVED">Accept this engineering stage</option></select></label>
          <div style={row}><button className="btn btn-primary" disabled={busy || !editable}>Record review</button><button type="button" className="btn btn-secondary" onClick={() => setReview(null)}>Close review</button></div>
        </form></section>}
    </>}
  </main>;
}
