import React, { useEffect, useId, useRef, useState } from 'react';
import { rpcCall } from '../api/client';
import { Activity, Cpu, SlidersHorizontal, Upload, Download, Plus, ArrowRight, BarChart3, Settings2 } from 'lucide-react';
import './PowerThermalAnalysis.css';

type Row = Record<string, number | string | null>;
type DeviceResult = {
  name: string; source: string; thermal_source: string; boundary: string;
  operating_point: Row; load_sweep: Row[]; frequency_sweep: Row[]; boundary_sweep: Row[];
  load_cycle: { status: string; reason?: string; points?: Row[]; note?: string };
  thermal_impedance: Row[];
  lifetime: { status: string; reason?: string; damage_fraction?: number; equivalent_profile_blocks_to_damage_one?: number; note?: string };
};
type Result = { request_sha256: string; revision_id: string; specification_sha256: string; inputs: any; warnings: string[]; devices: DeviceResult[] };
type ComponentContext = { component_hash: string; components: { reference: string; mpn: string; manufacturer: string; status: string; reason: string }[]; problems: string[]; note: string };
type Series = { name: string; rows: Row[] };
const colors = ['#0369a1', '#b45309', '#7c3aed', '#047857', '#be123c'];
const inputStyle: React.CSSProperties = { padding: '10px 12px', border: '1px solid #dce4ee', borderRadius: 7, fontSize: 13, minHeight: 40, background: '#fff', color: '#0f172a', width: '100%', boxSizing: 'border-box' };
const buttonStyle: React.CSSProperties = { padding: '9px 13px', border: '1px solid #dce4ee', borderRadius: 7, fontSize: 12, fontWeight: 600, background: '#fff', color: '#0f172a', cursor: 'pointer' };

function download(name: string, body: string, type: string) {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const a = document.createElement('a'); a.href = url; a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function csvCell(value: unknown) { return `"${String(value ?? '').replace(/"/g, '""')}"`; }
function exportCSV(result: Result) {
  const rows: unknown[][] = [['request_sha256', 'revision_id', 'qualification', 'device', 'analysis', 'x', 'status', 'reason', 'conduction_w', 'switching_w', 'device_loss_w', 'represented_system_loss_w', 'efficiency_pct', 'junction_temp_c', 'impedance_k_w']];
  for (const d of result.devices) {
    const groups: [string, Row[]][] = [['operating_point', [d.operating_point]], ['load', d.load_sweep], ['frequency', d.frequency_sweep], ['boundary', d.boundary_sweep], ['load_cycle', d.load_cycle.points ?? [{ status: d.load_cycle.status, reason: d.load_cycle.reason ?? '' }]], ['thermal_impedance', d.thermal_impedance]];
    for (const [kind, data] of groups) for (const r of data) rows.push([result.request_sha256, result.revision_id, 'NOT_EVALUATED', d.name, kind, r.x ?? r.time_s, r.status ?? 'COMPUTED', r.reason, r.conduction_w, r.switching_w, r.device_loss_w, r.represented_system_loss_w, r.efficiency_pct, r.junction_temp_c, r.impedance_k_w]);
  }
  download('power-thermal-results.csv', rows.map(r => r.map(csvCell).join(',')).join('\r\n'), 'text/csv');
}

function Curve({ title, xLabel, yLabel, xKey, yKey, series }: { title: string; xLabel: string; yLabel: string; xKey: string; yKey: string; series: Series[] }) {
  const ref = useRef<SVGSVGElement>(null);
  const [rangeMin, setRangeMin] = useState(''); const [rangeMax, setRangeMax] = useState('');
  const [cursorA, setCursorA] = useState<number | null>(null); const [cursorB, setCursorB] = useState<number | null>(null);
  const [hover, setHover] = useState<number | null>(null);
  const all = series.flatMap(s => s.rows.filter(r => typeof r[xKey] === 'number' && typeof r[yKey] === 'number'));
  if (!all.length) return <div style={{ padding: 16, border: '1px dashed #cbd5e1' }}><strong>{title}</strong><p>No evaluated data for this chart. See model-range messages below.</p></div>;
  const xs = all.map(r => Number(r[xKey]));
  const x0 = rangeMin !== '' && Number.isFinite(Number(rangeMin)) ? Number(rangeMin) : Math.min(...xs);
  const x1 = rangeMax !== '' && Number.isFinite(Number(rangeMax)) ? Number(rangeMax) : Math.max(...xs);
  const visible = all.filter(r => Number(r[xKey]) >= x0 && Number(r[xKey]) <= x1);
  const ys = visible.map(r => Number(r[yKey]));
  const lo = Math.min(...ys, ...(ys.length ? [] : [0])); const hi = Math.max(...ys, ...(ys.length ? [] : [1]));
  const padding = (hi - lo || Math.abs(hi) * 0.1 || 1) * 0.12;
  const y0 = lo - padding, y1 = hi + padding;
  const px = (x: number) => 80 + (x - x0) / (x1 - x0 || 1) * 770;
  const py = (y: number) => 240 - (y - y0) / (y1 - y0) * 205;
  const eventX = (e: React.MouseEvent<SVGSVGElement>) => { const box = e.currentTarget.getBoundingClientRect(); return x0 + (((e.clientX - box.left) / box.width * 900 - 80) / 770) * (x1 - x0); };
  return <article style={{ background: '#fff', padding: 14, border: '1px solid #dbe2ea', borderRadius: 8 }}>
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
      <strong>{title}</strong><button type="button" style={buttonStyle} onClick={() => ref.current && download(`${title.replace(/\W+/g, '-')}.svg`, new XMLSerializer().serializeToString(ref.current), 'image/svg+xml')}>Export SVG</button>
    </div>
    <div style={{ display: 'flex', gap: 10, marginTop: 10, alignItems: 'center', flexWrap: 'wrap' }}>
      <label>Zoom from <input aria-label={`${title} x minimum`} type="number" value={rangeMin} onChange={e => setRangeMin(e.target.value)} style={{ ...inputStyle, width: 100 }} /></label>
      <label>to <input aria-label={`${title} x maximum`} type="number" value={rangeMax} onChange={e => setRangeMax(e.target.value)} style={{ ...inputStyle, width: 100 }} /></label>
      <button type="button" style={buttonStyle} onClick={() => { setRangeMin(''); setRangeMax(''); setCursorA(null); setCursorB(null); }}>Reset</button>
      <small>Click plot twice to measure Δx.</small>
    </div>
    {x1 < x0 ? <p role="alert">Maximum must exceed minimum.</p> : <svg ref={ref} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 295" role="img" aria-label={title} style={{ width: '100%', background: '#fff', cursor: 'crosshair' }} onMouseMove={e => setHover(eventX(e))} onMouseLeave={() => setHover(null)} onClick={e => { const x = eventX(e); if (x < x0 || x > x1) return; if (cursorA === null || cursorB !== null) { setCursorA(x); setCursorB(null); } else setCursorB(x); }}>
      <rect width="900" height="295" fill="white" />
      <text x="80" y="18" fontSize="13" fill="#0f172a">{title} — analytical estimate</text>
      {Array.from({ length: 5 }, (_, i) => { const y = y0 + (y1 - y0) * i / 4; return <g key={i}><line x1="80" x2="850" y1={py(y)} y2={py(y)} stroke="#e2e8f0" /><text x="72" y={py(y) + 4} textAnchor="end" fontSize="11" fill="#475569">{y.toPrecision(4)}</text></g>; })}
      <line x1="80" y1="35" x2="80" y2="240" stroke="#64748b" /><line x1="80" y1="240" x2="850" y2="240" stroke="#64748b" />
      <text x="465" y="286" textAnchor="middle" fontSize="12" fill="#334155">{xLabel}</text><text transform="translate(15 140) rotate(-90)" textAnchor="middle" fontSize="12" fill="#334155">{yLabel}</text>
      {Array.from({ length: 5 }, (_, i) => <text key={i} x={80 + i * 770 / 4} y="260" textAnchor="middle" fontSize="11" fill="#475569">{(x0 + (x1 - x0) * i / 4).toPrecision(4)}</text>)}
      {series.map((s, i) => { let active = false; let path = ''; const dots: { x: number; y: number }[] = []; for (const r of [...s.rows].sort((a, b) => Number(a[xKey]) - Number(b[xKey]))) { const x = r[xKey], y = r[yKey]; if (typeof x !== 'number' || typeof y !== 'number' || x < x0 || x > x1) { active = false; continue; } path += `${active ? 'L' : 'M'}${px(x)},${py(y)} `; active = true; dots.push({ x, y }); } return <g key={s.name}><path d={path} fill="none" stroke={colors[i % colors.length]} strokeWidth="2" />{dots.length < 150 && dots.map((p, j) => <circle key={j} cx={px(p.x)} cy={py(p.y)} r="2.5" fill={colors[i % colors.length]} />)}</g>; })}
      {[cursorA, cursorB, hover].map((x, i) => x !== null && x >= x0 && x <= x1 && <line key={i} x1={px(x)} x2={px(x)} y1="35" y2="240" stroke={i === 2 ? '#94a3b8' : '#be123c'} strokeDasharray="4 3" />)}
    </svg>}
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>{series.map((s, i) => <span key={s.name} style={{ color: colors[i % colors.length], fontSize: 12 }}>● {s.name}{hover !== null && (() => { const points = s.rows.filter(r => typeof r[xKey] === 'number' && typeof r[yKey] === 'number'); const p = points.reduce<Row | null>((a, b) => !a || Math.abs(Number(b[xKey]) - hover) < Math.abs(Number(a[xKey]) - hover) ? b : a, null); return p ? `: ${Number(p[yKey]).toPrecision(5)} at ${Number(p[xKey]).toPrecision(5)}` : ''; })()}</span>)}</div>
    {cursorA !== null && cursorB !== null && <p style={{ fontSize: 12 }}>A: {cursorA.toPrecision(5)} · B: {cursorB.toPrecision(5)} · Δx: {(cursorB - cursorA).toPrecision(5)} ({xLabel})</p>}
  </article>;
}

// Blank template: missing ratings/models are never filled with illustrative vendor data.
const blankDevice = () => ({ name: '', mpn: null, manufacturer: null, component_reference: null, source: '', gate_conditions: '', loss_scope: '', reference_voltage_v: null, frequency_min_hz: null, frequency_max_hz: null, max_junction_temp_c: null, loss_points: [], thermal_source: '', boundary: 'ambient', foster: [], fatigue: null });
const emptyRequest = () => ({ schema_version: '1.0', assumptions: [''], devices: [blankDevice()], operating_point: { voltage_v: null, gate_conditions: '', current_a: null, output_power_w: null, duty_cycle: null, frequency_hz: null, boundary_temp_c: null, other_losses_w: null, quantity: 1 }, sweeps: { load_factors: [0.25, 0.5, 0.75, 1], frequencies_hz: [], boundary_temperatures_c: [] }, load_cycle: [], repeat_cycles: 1, samples_per_segment: 10, thermal_cycles: [], cycle_count_source: null });

function checkFormShape(value: any) {
  const object = (v: any) => v !== null && typeof v === 'object' && !Array.isArray(v);
  if (!object(value) || !object(value.operating_point) || !object(value.sweeps) || !Array.isArray(value.devices) || !value.devices.length || value.devices.length > 5
    || !value.devices.every((d: any) => object(d) && ['name', 'source', 'gate_conditions', 'loss_scope', 'thermal_source', 'boundary'].every(k => typeof d[k] === 'string'))
    || !Array.isArray(value.assumptions) || !value.assumptions.every((s: unknown) => typeof s === 'string')) {
    throw new Error('Import a complete analysis request with 1–5 device objects, text source fields, assumptions, operating_point and sweeps. Use Export inputs for a blank template.');
  }
  return value;
}

export function PowerThermalAnalysisCard({ revisionId, contextVersion = '', stages = [], readOnly = false, onRecorded }: { revisionId: string; contextVersion?: string; stages?: { id: string; name: string }[]; readOnly?: boolean; onRecorded?: () => void }) {
  const [form, setForm] = useState<any>(emptyRequest); const [jsonText, setJsonText] = useState('');
  const [result, setResult] = useState<Result | null>(null); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const [setup, setSetup] = useState<'operating' | 'devices' | 'sweeps' | 'advanced'>('operating');
  const importInput = useRef<HTMLInputElement>(null);
  const instanceId = useId();
  const lossInputs = useRef<Record<number, HTMLInputElement | null>>({});
  const [tab, setTab] = useState<'load' | 'frequency' | 'boundary' | 'profile' | 'impedance'>('load');
  const generation = useRef(0);
  const [recordStage, setRecordStage] = useState(''); const [recordSource, setRecordSource] = useState(''); const [recordReason, setRecordReason] = useState('');
  const [saving, setSaving] = useState(false); const [recordMessage, setRecordMessage] = useState('');
  const receipt = useRef<{ signature: string; key: string } | null>(null);
  const [automatic, setAutomatic] = useState(true);
  const [context, setContext] = useState<ComponentContext | null>(null);
  const [contextError, setContextError] = useState('');
  const contextHash = useRef('');
  const autoTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => { generation.current++; setForm(emptyRequest()); setResult(null); setError(''); setJsonText(''); setBusy(false); setSaving(false); setRecordMessage(''); setRecordStage(''); setSetup('operating'); receipt.current = null; setContext(null); contextHash.current = ''; }, [revisionId]);
  const edit = (next: any) => { generation.current++; setForm(next); setResult(null); setError(''); setBusy(false); setSaving(false); setRecordMessage(''); };
  const updateDevice = (index: number, key: string, value: unknown) => edit({ ...form, devices: form.devices.map((d: any, i: number) => i === index ? { ...d, [key]: value } : d) });
  useEffect(() => {
    let current = true;
    rpcCall<ComponentContext>('power_analysis_context', { revision_id: revisionId }).then(next => {
      if (!current) return;
      setContextError('');
      if (contextHash.current !== next.component_hash) {
        contextHash.current = next.component_hash;
        generation.current++; setResult(null); setBusy(false); setContext(next);
        setForm((previous: any) => previous.devices.some((d: any) => d.component_reference)
          ? { ...previous, expected_component_hash: next.component_hash } : previous);
      }
    }).catch(e => { if (current) { generation.current++; setContext(null); contextHash.current = ''; setResult(null); setContextError(String(e)); } });
    return () => { current = false; };
  }, [revisionId, contextVersion]);
  useEffect(() => {
    const op = form.operating_point;
    const ready = form.assumptions?.every((v: string) => v.trim()) && form.assumptions.length > 0
      && Object.entries(op).every(([key, value]) => key === 'gate_conditions' ? typeof value === 'string' && value.trim() : typeof value === 'number' && Number.isFinite(value))
      && form.devices.every((d: any) => d.source?.trim() && d.name?.trim() && d.thermal_source?.trim() && d.gate_conditions?.trim() && d.loss_scope?.trim()
        && d.reference_voltage_v > 0 && d.frequency_min_hz > 0 && d.frequency_max_hz > 0 && typeof d.max_junction_temp_c === 'number' && d.loss_points?.length >= 4 && d.foster?.length > 0)
      && form.sweeps.load_factors?.length && form.sweeps.frequencies_hz?.length && form.sweeps.boundary_temperatures_c?.length;
    if (!automatic || !ready || (form.devices.some((d: any) => d.component_reference) && !context)) return;
    autoTimer.current = setTimeout(() => void run(), 500);
    return () => { if (autoTimer.current) clearTimeout(autoTimer.current); };
  }, [form, automatic, revisionId, context?.component_hash]);
  useEffect(() => () => { generation.current++; if (autoTimer.current) clearTimeout(autoTimer.current); }, []);
  async function run() {
    if (autoTimer.current) clearTimeout(autoTimer.current);
    setBusy(true); setError(''); setResult(null); const token = ++generation.current;
    try { const parameters = form.devices.some((d: any) => d.component_reference) ? { ...form, expected_component_hash: context?.component_hash } : { ...form, expected_component_hash: null };
      const response = await rpcCall<Result>('analyze_power_thermal', { revision_id: revisionId, parameters });
      if (token === generation.current) { setResult(response); if (JSON.stringify(response.inputs.devices) !== JSON.stringify(form.devices)) setForm((previous: any) => ({ ...previous, devices: response.inputs.devices })); }
    }
    catch (e) { if (token === generation.current) setError(e instanceof Error ? e.message : String(e)); }
    finally { if (token === generation.current) setBusy(false); }
  }
  async function record() {
    if (!result || readOnly) return;
    const token = generation.current; setSaving(true); setRecordMessage('');
    const payload = { revision_id: revisionId, stage_id: recordStage, expected_input_hash: result.specification_sha256,
      source: recordSource, reason: recordReason, calculation: 'power_thermal', parameters: result.inputs, assumptions: result.inputs.assumptions };
    const signature = JSON.stringify(payload);
    if (!receipt.current || receipt.current.signature !== signature) receipt.current = { signature, key: crypto.randomUUID() };
    try { const response = await rpcCall<{ record_id: string; status: string; error?: string }>('record_power_thermal', { ...payload, idempotency_key: receipt.current.key });
      if (token === generation.current) { setRecordMessage(`Calculation record ${response.record_id}: ${response.status}. Engineering NOT_EVALUATED.${response.error ? ` ${response.error}` : ''}`); onRecorded?.(); }
    } catch (e) { if (token === generation.current) setRecordMessage(String(e)); }
    finally { if (token === generation.current) setSaving(false); }
  }
  async function importRequest(file: File) { const token = generation.current; try { if (file.size > 250000) throw new Error('Analysis import exceeds 250 kB'); const value = checkFormShape(JSON.parse(await file.text())); if (token === generation.current) edit(value); } catch (e) { if (token === generation.current) setError(String(e)); } }
  const format = (value: unknown, suffix = '') => typeof value === 'number' ? `${value.toFixed(3)}${suffix}` : '—';
  const group = tab === 'load' ? 'load_sweep' : tab === 'frequency' ? 'frequency_sweep' : 'boundary_sweep';
  const xLabel = tab === 'load' ? 'Load factor (current and output power scaled)' : tab === 'frequency' ? 'Switching frequency (Hz)' : 'Boundary temperature (°C; per-device ambient/case)';
  const series = (key: 'load_sweep' | 'frequency_sweep' | 'boundary_sweep') => result!.devices.map(d => ({ name: `${d.name} (${d.boundary})`, rows: d[key] }));
  return <section className="pta-workspace">
    <header className="pta-header">
      <div className="pta-heading"><span className="pta-app-icon"><Activity size={24} strokeWidth={1.8} /></span><div><div className="pta-eyebrow">ENGINEERING ANALYSIS</div><h3>Power Loss &amp; Thermal</h3><p>Compare device losses, efficiency and junction temperature.</p></div></div>
      <div className="pta-header-tools">
        <label className="pta-auto-toggle"><input type="checkbox" checked={automatic} onChange={e => { generation.current++; setBusy(false); setAutomatic(e.target.checked); }} /><span className="pta-switch" /><span>Auto update</span></label>
        <span className="pta-estimate-badge">Calculated estimates</span>
      </div>
    </header>
    <div className="pta-toolbar">
      <span className="pta-toolbar-caption"><span className={busy ? 'pta-status-dot is-busy' : 'pta-status-dot'} />{busy ? 'Updating analysis?' : automatic ? 'Updates as you edit' : 'Manual calculation'}</span>
      <div className="pta-toolbar-actions">
        <input ref={importInput} type="file" accept=".json" aria-label="Import power analysis JSON" hidden onChange={e => { const f = e.target.files?.[0]; if (f) void importRequest(f); e.target.value = ''; }} />
        <button type="button" style={buttonStyle} onClick={() => importInput.current?.click()}><Upload size={14} /> Import setup</button>
        <button type="button" style={buttonStyle} onClick={() => download('power-analysis-inputs.json', JSON.stringify(form, null, 2), 'application/json')}><Download size={14} /> Export setup</button>
        <button type="button" style={buttonStyle} disabled={form.devices.length >= 5} onClick={() => { edit({ ...form, devices: [...form.devices, blankDevice()] }); setSetup('devices'); }}><Plus size={14} /> Add device</button>
      </div>
    </div>
    {contextError && <p className="pta-alert" role="alert">Revision component synchronization unavailable: {contextError}</p>}
    {context?.problems.map((problem, i) => <p className="pta-alert" key={i} role="alert">Component data: {problem}</p>)}
    <div className="pta-body">
      <div className="pta-editor">
        <div className="pta-steps" role="tablist" aria-label="Analysis setup">
          {([['operating', 'Conditions'], ['devices', 'Devices'], ['sweeps', 'Sweeps'], ['advanced', 'Advanced']] as const).map(([key, title], i) => <button key={key} type="button" role="tab" id={`${instanceId}-${key}-tab`} aria-controls={`${instanceId}-${key}-panel`} aria-selected={setup === key} tabIndex={setup === key ? 0 : -1} onKeyDown={event => { const keys = ['operating', 'devices', 'sweeps', 'advanced'] as const; const next = event.key === 'ArrowRight' ? (i + 1) % 4 : event.key === 'ArrowLeft' ? (i + 3) % 4 : event.key === 'Home' ? 0 : event.key === 'End' ? 3 : -1; if (next < 0) return; event.preventDefault(); setSetup(keys[next]); (event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next])?.focus(); }} onClick={() => setSetup(key)}><span>{String(i + 1).padStart(2, '0')}</span>{title}</button>)}
        </div>
        <div className="pta-setup-panel" role="tabpanel" id={`${instanceId}-operating-panel`} aria-labelledby={`${instanceId}-operating-tab`} tabIndex={0} hidden={setup !== 'operating'}>    <div className="pta-section-title"><span className="pta-section-icon"><SlidersHorizontal size={17} /></span><div><h4>Operating conditions</h4><p>Define the electrical working point and cooling boundary.</p></div></div>
    <label className="pta-wide-field">Gate-drive conditions <span className="pta-optional">Match the device model</span><input value={form.operating_point.gate_conditions ?? ''} style={inputStyle} onChange={e => edit({ ...form, operating_point: { ...form.operating_point, gate_conditions: e.target.value } })} /></label>
    <div className="pta-field-grid pta-operating-grid">
      {[
        ['voltage_v', 'Switched voltage', 'V'], ['current_a', 'On-state current', 'A'],
        ['output_power_w', 'Output power', 'W'], ['duty_cycle', 'Duty cycle', '0?1'],
        ['frequency_hz', 'Switching frequency', 'Hz'], ['boundary_temp_c', 'Boundary temperature', '?C'],
        ['other_losses_w', 'Other system losses', 'W'], ['quantity', 'Identical device count', 'pcs'],
      ].map(([key, label, unit]) => <label key={key}>{label}<div className="pta-unit-input"><input type="number" step={key === 'quantity' ? '1' : 'any'} value={form.operating_point[key] ?? ''} placeholder="?" onChange={e => edit({ ...form, operating_point: { ...form.operating_point, [key]: e.target.value === '' ? null : Number(e.target.value) } })} /><span>{unit}</span></div></label>)}
    </div>
    <label style={{ display: 'block', marginTop: 12 }}>Engineering assumptions <span className="pta-optional">One per line</span><textarea placeholder="Record operating assumptions and model limitations?" rows={3} value={(form.assumptions ?? []).join('\n')} onChange={e => edit({ ...form, assumptions: e.target.value.split('\n') })} style={inputStyle} /></label>
<button className="pta-next" type="button" onClick={() => setSetup('devices')}>Continue to device models <ArrowRight size={14} /></button></div>
        <div className="pta-setup-panel" role="tabpanel" id={`${instanceId}-devices-panel`} aria-labelledby={`${instanceId}-devices-tab`} tabIndex={0} hidden={setup !== 'devices'}>    <div className="pta-section-title"><span className="pta-section-icon"><Cpu size={17} /></span><div><h4>Device models</h4><p>Attach sourced electrical and thermal data to each comparison device.</p></div></div>
    {form.devices.map((device: any, index: number) => <details className="pta-device" key={index} open={index === 0} style={{ marginBottom: 12, padding: 16, border: '1px solid #dbe2ea', borderRadius: 6 }}>
      <summary><span className="pta-device-number">{String(index + 1).padStart(2, '0')}</span><span>{device.name || 'New device model'}<small>{device.mpn || 'Add a part number and model data'}</small></span><span className="pta-device-count">{device.loss_points?.length ?? 0} data points</span></summary>
      <label>Component link<select style={inputStyle} value={device.component_reference ?? ''} onChange={e => updateDevice(index, 'component_reference', e.target.value || null)}>
        <option value="">Standalone comparison model</option>
        {device.component_reference && !context?.components.some(c => c.reference === device.component_reference) && <option value={device.component_reference}>{device.component_reference} — removed / unavailable</option>}
        {context?.components.map(c => <option key={c.reference} value={c.reference}>{c.reference}: {c.manufacturer} {c.mpn || 'missing part number'} {c.status !== 'AVAILABLE' ? '(identity conflict)' : ''}</option>)}
      </select></label>
      {device.component_reference && <p style={{ fontSize: 12 }}>Follows saved BOM/core design updates through the app's existing refresh. An exact sourced replacement model is required; unsaved native editor changes must first be imported. {context?.note}</p>}
      <div className="pta-field-grid pta-identity-grid">
        <label>Part number (MPN)<input value={device.mpn ?? ''} style={inputStyle} onChange={e => updateDevice(index, 'mpn', e.target.value || null)} /></label>
        <label>Manufacturer<input value={device.manufacturer ?? ''} style={inputStyle} onChange={e => updateDevice(index, 'manufacturer', e.target.value || null)} /></label>
      </div>
      <div className="pta-field-grid pta-model-grid">
        {['name', 'source', 'gate_conditions', 'loss_scope', 'thermal_source'].map(key => <label key={key}>{({ name: 'Display name', source: 'Loss-data source', gate_conditions: 'Gate-drive conditions', loss_scope: 'Included / excluded losses', thermal_source: 'Thermal-data source', reference_voltage_v: 'Reference voltage ? V', frequency_min_hz: 'Minimum frequency ? Hz', frequency_max_hz: 'Maximum frequency ? Hz', max_junction_temp_c: 'Junction limit ? ?C' } as Record<string, string>)[key]}<input value={device[key] ?? ''} style={inputStyle} onChange={e => updateDevice(index, key, e.target.value)} /></label>)}
        {['reference_voltage_v', 'frequency_min_hz', 'frequency_max_hz', 'max_junction_temp_c'].map(key => <label key={key}>{({ name: 'Display name', source: 'Loss-data source', gate_conditions: 'Gate-drive conditions', loss_scope: 'Included / excluded losses', thermal_source: 'Thermal-data source', reference_voltage_v: 'Reference voltage ? V', frequency_min_hz: 'Minimum frequency ? Hz', frequency_max_hz: 'Maximum frequency ? Hz', max_junction_temp_c: 'Junction limit ? ?C' } as Record<string, string>)[key]}<input type="number" step="any" value={device[key] ?? ''} style={inputStyle} onChange={e => updateDevice(index, key, e.target.value === '' ? null : Number(e.target.value))} /></label>)}
        <label>Thermal boundary<select value={device.boundary} style={inputStyle} onChange={e => updateDevice(index, 'boundary', e.target.value)}><option value="ambient">Fixed ambient</option><option value="case">Fixed case</option></select></label>
      </div>
      <div style={{ marginTop: 10, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <input ref={node => { lossInputs.current[index] = node; }} type="file" hidden aria-label={`Import device ${index + 1} loss table`} accept=".csv" onChange={async e => { const file = e.target.files?.[0]; e.target.value = ''; if (!file) return; const token = generation.current; try { const r = await rpcCall<{ loss_points: unknown[] }>('import_power_loss_csv', { text: await file.text() }); if (token === generation.current) updateDevice(index, 'loss_points', r.loss_points); } catch (err) { if (token === generation.current) setError(String(err)); } }} /><button type="button" style={buttonStyle} onClick={() => lossInputs.current[index]?.click()}><Upload size={14} /> Import loss table</button>
        <span>{device.loss_points?.length ?? 0} loss grid points · {device.foster?.length ?? 0} thermal branches</span>
        <button type="button" style={buttonStyle} onClick={() => download('loss-table-template.csv', 'current_a,junction_temp_c,on_voltage_v,e_on_j,e_off_j\r\n', 'text/csv')}>CSV template</button>
        {form.devices.length > 1 && <button type="button" style={buttonStyle} onClick={() => edit({ ...form, devices: form.devices.filter((_: unknown, i: number) => i !== index) })}>Remove</button>}
      </div>
<details className="pta-disclosure"><summary>Thermal impedance model <span className="pta-optional">Foster coefficients</span></summary>      <JSONField label={`Device ${index + 1} Foster branches`} value={device.foster ?? []} onApply={value => updateDevice(index, 'foster', value)} /></details>
      <button type="button" style={buttonStyle} onClick={() => edit({ ...form, model_library: [...(form.model_library ?? []), { ...device, component_reference: null }] })}>Keep this model for component replacements</button>
    </details>)}
    <details><summary>Replacement model library ({form.model_library?.length ?? 0})</summary><p>Add complete sourced models with exact part numbers/manufacturers. Models travel with exported inputs and recorded calculations.</p><JSONField label="Replacement model library" value={form.model_library ?? []} onApply={value => edit({ ...form, model_library: value })} /></details>
<button className="pta-next" type="button" onClick={() => setSetup('sweeps')}>Set comparison ranges <ArrowRight size={14} /></button></div>
        <div className="pta-setup-panel" role="tabpanel" id={`${instanceId}-sweeps-panel`} aria-labelledby={`${instanceId}-sweeps-tab`} tabIndex={0} hidden={setup !== 'sweeps'}>    <div className="pta-section-title"><span className="pta-section-icon"><BarChart3 size={17} /></span><div><h4>Sweeps &amp; load profile</h4><p>Choose the operating ranges to compare in your graphs.</p></div></div>
    <div className="pta-field-grid pta-sweep-grid">
      <JSONField label="Load factors" value={form.sweeps.load_factors} onApply={v => edit({ ...form, sweeps: { ...form.sweeps, load_factors: v } })} />
      <JSONField label="Frequencies (Hz)" value={form.sweeps.frequencies_hz} onApply={v => edit({ ...form, sweeps: { ...form.sweeps, frequencies_hz: v } })} />
      <JSONField label="Boundary temperatures (°C)" value={form.sweeps.boundary_temperatures_c} onApply={v => edit({ ...form, sweeps: { ...form.sweeps, boundary_temperatures_c: v } })} />
    </div>
<details className="pta-disclosure"><summary>Mission profile <span className="pta-optional">Optional</span></summary>    <JSONField label="Load-cycle segments" value={form.load_cycle ?? []} onApply={v => edit({ ...form, load_cycle: v })} />
    <p style={{ fontSize: 12 }}>Each segment needs duration_s, current_a, output_power_w, frequency_hz, duty_cycle and other_losses_w. Profile starts cold at the fixed boundary; refine samples_per_segment in advanced settings to check numerical convergence.</p>
</details></div>
        <div className="pta-setup-panel" role="tabpanel" id={`${instanceId}-advanced-panel`} aria-labelledby={`${instanceId}-advanced-tab`} tabIndex={0} hidden={setup !== 'advanced'}><div className="pta-section-title"><span className="pta-section-icon"><Settings2 size={17} /></span><div><h4>Advanced configuration</h4><p>Model conventions, full request editing and import requirements.</p></div></div>    <details className="pta-disclosure" open><summary>Model requirements and advanced request editor</summary>
      <p>Loss CSV headers: <code>current_a,junction_temp_c,on_voltage_v,e_on_j,e_off_j</code>, with optional <code>voltage_v</code>. For voltage interpolation, supply a complete voltage × current × temperature grid with at least two voltages. Single-voltage tables stay valid only at their reference voltage. No extrapolation is performed.</p>
      <p>Foster JSON: an array of objects containing <code>resistance_k_w</code> and <code>tau_s</code>. It must fit the complete junction-to-fixed-ambient or junction-to-fixed-case path. No shared heatsink or mutual heating is modeled. Load profiles use loss-averaged steps, not individual switching pulses.</p>
      <p>Advanced JSON also supports load_cycle, repeat_cycles, samples_per_segment, thermal_cycles and sourced fatigue curves. See docs/POWER_THERMAL_ANALYSIS.md for their contracts. No automatic rainflow counting or vendor lifetime model is supplied.</p>
      <button type="button" style={buttonStyle} onClick={() => setJsonText(JSON.stringify(form, null, 2))}>Copy current form into editor</button>
      <textarea aria-label="Advanced power analysis request" rows={12} value={jsonText} onChange={e => setJsonText(e.target.value)} style={{ ...inputStyle, marginTop: 10, fontFamily: 'monospace' }} />
      <button type="button" style={buttonStyle} onClick={() => { try { edit(checkFormShape(JSON.parse(jsonText))); } catch (e) { setError(String(e)); } }}>Apply JSON</button>
    </details>
</div>
      </div>
      <aside className="pta-sidebar">
        <div className="pta-sidebar-title"><SlidersHorizontal size={15} /><span>Working point</span></div>
        <dl className="pta-point-summary">
          {[['Voltage', form.operating_point.voltage_v, 'V'], ['Current', form.operating_point.current_a, 'A'], ['Frequency', typeof form.operating_point.frequency_hz === 'number' && form.operating_point.frequency_hz >= 1000 ? form.operating_point.frequency_hz / 1000 : form.operating_point.frequency_hz, form.operating_point.frequency_hz >= 1000 ? 'kHz' : 'Hz'], ['Boundary', form.operating_point.boundary_temp_c, '?C']].map(([label, value, unit]) => <div key={String(label)}><dt>{label}</dt><dd>{typeof value === 'number' ? new Intl.NumberFormat('en', { maximumFractionDigits: 3 }).format(value) : '?'}<small>{unit}</small></dd></div>)}
        </dl>
        <div className="pta-summary-row"><span>Comparison devices</span><strong>{form.devices.length} / 5</strong></div>
        <div className="pta-summary-row"><span>Loss tables attached</span><strong>{form.devices.filter((d: any) => d.loss_points?.length).length}</strong></div>
        <button className="pta-calculate" type="button" disabled={busy} onClick={() => void run()}><Activity size={16} />{busy ? 'Calculating?' : 'Calculate & compare'}</button>
        <div className="pta-qualification"><span>Engineering status</span><strong>Not evaluated</strong><p>Model estimates require independent engineering verification.</p></div>
      </aside>
    </div>
    {!result && !error && <div className="pta-empty"><span><BarChart3 size={26} strokeWidth={1.6} /></span><div><strong>Your comparison starts here</strong><p>Complete the conditions and attach a sourced device model to generate loss and temperature graphs.</p></div></div>}
    {error && <pre role="alert" style={{ whiteSpace: 'pre-wrap', color: '#b91c1c', background: '#fff1f2', padding: 12 }}>{error}</pre>}
    {result && <div className="pta-results"><div className="pta-results-heading"><BarChart3 size={18} /><h4>Analysis results</h4></div>
      <p><strong>Calculated — engineering qualification NOT_EVALUATED.</strong> Input SHA-256: <code style={{ overflowWrap: 'anywhere' }}>{result.request_sha256}</code></p>
      <div style={{ display: 'flex', gap: 10 }}><button type="button" style={buttonStyle} onClick={() => download('power-thermal-analysis.json', JSON.stringify(result, null, 2), 'application/json')}>Export full JSON</button><button type="button" style={buttonStyle} onClick={() => exportCSV(result)}>Export results CSV</button></div>
      <details style={{ marginTop: 14 }}><summary>Record this calculation against a lifecycle stage</summary>
        <p>This appends a calculation record using the current specification hash. It does not complete a stage or approve the design.</p>
        <label>Active stage<select style={inputStyle} value={recordStage} onChange={e => setRecordStage(e.target.value)}><option value="">Select an active stage</option>{stages.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
        <label>Record source / engineer attribution<input style={inputStyle} value={recordSource} onChange={e => setRecordSource(e.target.value)} /></label>
        <label>Reason for recording<input style={inputStyle} value={recordReason} onChange={e => setRecordReason(e.target.value)} /></label>
        <button type="button" style={buttonStyle} disabled={saving || readOnly || !recordStage || !recordSource.trim() || !recordReason.trim()} onClick={() => void record()}>{saving ? 'Recording…' : 'Record calculation'}</button>
        {(readOnly || !stages.length) && <p>Recording needs an editable draft revision and a current IN_PROGRESS lifecycle stage. Preview and download remain available.</p>}
        {recordMessage && <p role="status" style={{ overflowWrap: 'anywhere' }}>{recordMessage}</p>}
      </details>
      <div style={{ overflowX: 'auto', marginTop: 14 }}><table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}><thead><tr>{['Device', 'Conduction / device', 'Switching / device', 'Total / device', 'Represented efficiency', 'Junction temperature', 'Calculation'].map(h => <th key={h} style={{ padding: 8, borderBottom: '1px solid #cbd5e1' }}>{h}</th>)}</tr></thead><tbody>{result.devices.map(d => <tr key={d.name}><td style={{ padding: 8 }}>{d.name}</td><td>{format(d.operating_point.conduction_w, ' W')}</td><td>{format(d.operating_point.switching_w, ' W')}</td><td>{format(d.operating_point.device_loss_w, ' W')}</td><td>{format(d.operating_point.efficiency_pct, '%')}</td><td>{format(d.operating_point.junction_temp_c, ' °C')}</td><td>{d.operating_point.status}{d.operating_point.reason && `: ${d.operating_point.reason}`}</td></tr>)}</tbody></table></div>
      <h4>Conduction and switching loss breakdown</h4>
      {result.devices.map((d, i) => { const p = d.operating_point; if (p.status !== 'COMPUTED') return null; const total = Number(p.device_loss_w); return <div key={d.name} style={{ marginBottom: 10 }}><span>{d.name}</span><div style={{ display: 'flex', height: 24, maxWidth: 600, background: '#f1f5f9' }}><div title={`Conduction: ${p.conduction_w} W`} style={{ width: `${total ? Number(p.conduction_w) / total * 100 : 0}%`, background: colors[i], minWidth: 0 }} /><div title={`Switching: ${p.switching_w} W`} style={{ flex: 1, background: colors[i], opacity: 0.4 }} /></div><small>Solid: conduction {format(p.conduction_w, ' W')} · Light: switching {format(p.switching_w, ' W')}</small></div>; })}
      <div className="pta-graph-tabs" role="group" aria-label="Analysis graph selection" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, margin: '18px 0' }}>{([['load', 'Load sweep'], ['frequency', 'Frequency sweep'], ['boundary', 'Ambient / case sweep'], ['profile', 'Load-cycle profile'], ['impedance', 'Thermal impedance']] as const).map(([key, label]) => <button type="button" key={key} style={{ ...buttonStyle, background: tab === key ? '#e0f2fe' : '#fff' }} onClick={() => setTab(key)}>{label}</button>)}</div>
      <div style={{ display: 'grid', gap: 14 }}>
        {(tab === 'load' || tab === 'frequency' || tab === 'boundary') && <>
          <Curve key={`${result.request_sha256}-${tab}-eff`} title="Represented system efficiency" xLabel={xLabel} yLabel="Efficiency (%)" xKey="x" yKey="efficiency_pct" series={series(group)} />
          <Curve key={`${result.request_sha256}-${tab}-loss`} title="Device power loss" xLabel={xLabel} yLabel="Loss per device (W)" xKey="x" yKey="device_loss_w" series={series(group)} />
          <Curve key={`${result.request_sha256}-${tab}-temp`} title="Junction temperature" xLabel={xLabel} yLabel="Temperature (°C)" xKey="x" yKey="junction_temp_c" series={series(group)} />
        </>}
        {tab === 'profile' && <><Curve key={`${result.request_sha256}-profile-t`} title="Load-cycle junction temperature" xLabel="Time (s)" yLabel="Temperature (°C)" xKey="time_s" yKey="junction_temp_c" series={result.devices.map(d => ({ name: d.name, rows: d.load_cycle.points ?? [] }))} /><Curve key={`${result.request_sha256}-profile-p`} title="Load-cycle device loss" xLabel="Time (s)" yLabel="Power (W)" xKey="time_s" yKey="device_loss_w" series={result.devices.map(d => ({ name: d.name, rows: d.load_cycle.points ?? [] }))} /></>}
        {tab === 'impedance' && <Curve key={`${result.request_sha256}-zth`} title="Complete-path thermal impedance" xLabel="Time (s)" yLabel="Thermal impedance (K/W)" xKey="time_s" yKey="impedance_k_w" series={result.devices.map(d => ({ name: `${d.name} → ${d.boundary}`, rows: d.thermal_impedance }))} />}
      </div>
      <h4>Fatigue / lifetime estimate</h4>{result.devices.map(d => <p key={d.name}><strong>{d.name}:</strong> {d.lifetime.status === 'COMPUTED' ? `Miner damage ${d.lifetime.damage_fraction?.toPrecision(5)}; equivalent supplied profile blocks to damage one: ${d.lifetime.equivalent_profile_blocks_to_damage_one?.toPrecision(5)}. ${d.lifetime.note}` : `NOT_EVALUATED — ${d.lifetime.reason}`}</p>)}
      <details><summary>Model limits, sources and unevaluated points</summary><ul>{result.warnings.map(w => <li key={w}>{w}</li>)}</ul>{result.devices.map(d => <div key={d.name}><strong>{d.name}</strong><p>Loss data: {d.source} · Thermal model: {d.thermal_source}</p>{(['load_sweep', 'frequency_sweep', 'boundary_sweep'] as const).map(k => d[k].filter(r => r.status === 'NOT_EVALUATED').map((r, i) => <p key={`${k}-${i}`}>{k}, {r.x}: {r.reason}</p>))}{d.load_cycle.status !== 'COMPUTED' && <p>Load cycle: {d.load_cycle.reason}</p>}</div>)}</details>
    </div>}
  </section>;
}

function JSONField({ label, value, onApply }: { label: string; value: unknown; onApply: (value: any) => void }) {
  const [text, setText] = useState(JSON.stringify(value)); const [error, setError] = useState('');
  useEffect(() => { setText(JSON.stringify(value)); setError(''); }, [value]);
  return <div className="pta-json-field" style={{ marginTop: 10 }}><label>{label}<textarea aria-label={label} rows={2} style={{ ...inputStyle, fontFamily: 'monospace' }} value={text} onChange={e => setText(e.target.value)} /></label><button type="button" style={buttonStyle} onClick={() => { try { const parsed = JSON.parse(text); if (!Array.isArray(parsed)) throw new Error('Enter a JSON array'); onApply(parsed); setError(''); } catch (e) { setError(String(e)); } }}>Apply {label}</button>{error && <p role="alert" style={{ color: '#b91c1c' }}>{error}</p>}</div>;
}
