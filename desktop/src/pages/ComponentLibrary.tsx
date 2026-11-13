import React, { useState } from 'react';
import { api } from '../api/client';
import { usePolling } from '../usePolling';
import { Cpu, Box, Database, Search, ExternalLink } from 'lucide-react';
import type { ComponentRecord, LibraryReference, LibraryCatalog } from '../api/types';

const cell: React.CSSProperties = { padding: '12px', borderBottom: '1px solid var(--border)', verticalAlign: 'top' };
const unknown = 'Unknown';
export const quantity = (value: number | null | undefined, unit = '') =>
  value == null ? unknown : `${value.toLocaleString()}${unit ? ` ${unit}` : ''}`;

function Source({ record }: { record: LibraryReference }) {
  const source = record.datasheet_url;
  return <div style={{ minWidth: 170 }}>
    <span className="badge badge-muted">{record.verification_status}</span>
    {source && /^https:\/\//i.test(source) ? <a href={source} target="_blank" rel="noopener noreferrer"
      style={{ display: 'flex', gap: 4, marginTop: 8, color: 'var(--primary)' }}>
      Manufacturer source <ExternalLink size={12} />
    </a> : <div style={{ marginTop: 8, color: 'var(--text-muted)' }}>Source required</div>}
    <div style={{ marginTop: 6, fontSize: 11, color: 'var(--text-muted)' }}>
      {record.source_checked_on ? `Source consulted ${record.source_checked_on}` : 'Numeric data pending source review'}
    </div>
  </div>;
}

function Ratings({ part }: { part: ComponentRecord }) {
  const ratings = [
    ['Voltage', part.voltage_rating_v, 'V'], ['Current', part.current_rating_a, 'A'],
    ['Power', part.power_rating_w, 'W'], ['RDS(on)', part.rds_on_ohm, '?'],
    ['ESR', part.esr_ohm, '?'],
  ] as const;
  const known = ratings.filter(([, value]) => value != null);
  return <>{known.length ? known.map(([label, value, unit]) =>
    <div key={label}>{label}: {quantity(value, unit)}</div>) : <span style={{ color: 'var(--text-muted)' }}>Ratings not transcribed</span>}
    <details style={{ marginTop: 8 }}><summary style={{ cursor: 'pointer', color: 'var(--primary)' }}>Conditions & models</summary>
      <p style={{ margin: '8px 0', maxWidth: 420, lineHeight: 1.6 }}>{part.conditions || 'Operating conditions require review.'}</p>
      <div>SPICE model: {part.spice_model_name || 'Not installed / not qualified'}</div>
      <div>CAD symbol: {part.kicad_symbol || 'Not assigned'}</div>
      <div>Footprint: {part.kicad_footprint || 'Not assigned'}</div>
    </details>
  </>;
}

export const ComponentLibraryView: React.FC<{ data: LibraryCatalog | null; error?: string | null; initialTab?: 'components' | 'cores' | 'materials' }> = ({ data, error, initialTab = 'components' }) => {
  const [activeTab, setActiveTab] = useState(initialTab);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');
  const [kind, setKind] = useState('all');
  if (!data) return <div style={{ padding: 24 }} role={error ? 'alert' : 'status'}>{error || 'Loading component library?'}</div>;

  const matches = (...values: Array<string | null | undefined>) => values.join(' ').toLowerCase().includes(query.trim().toLowerCase());
  const components = data.components.filter(c => (category === 'all' || category === c.category)
    && (kind === 'all' || c.record_kind === kind) && matches(c.mpn, c.manufacturer, c.description, c.category));
  const materials = data.materials.filter(m => matches(m.name, m.manufacturer, m.material_type));
  const cores = data.cores.filter(c => matches(c.name, c.manufacturer, c.geometry_type));
  const categories = new Map(data.categories.map(c => [c.id, c.label]));
  const count = activeTab === 'components' ? components.length : activeTab === 'materials' ? materials.length : cores.length;

  return <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 20, overflowY: 'auto' }}>
    {error && <p role="alert">{error}. Displayed records may be stale.</p>}
    <div><h2 style={{ fontSize: 20, marginBottom: 6 }}>Component & Materials Library</h2>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.7 }}>{data.provenance_note}</p>
    </div>
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
      <button onClick={() => setActiveTab('components')} className={`btn btn-${activeTab === 'components' ? 'primary' : 'secondary'}`} aria-pressed={activeTab === 'components'}><Cpu size={14} /> Components ({data.components.length})</button>
      <button onClick={() => setActiveTab('cores')} className={`btn btn-${activeTab === 'cores' ? 'primary' : 'secondary'}`} aria-pressed={activeTab === 'cores'}><Box size={14} /> Core Geometries ({data.cores.length})</button>
      <button onClick={() => setActiveTab('materials')} className={`btn btn-${activeTab === 'materials' ? 'primary' : 'secondary'}`} aria-pressed={activeTab === 'materials'}><Database size={14} /> Magnetic Materials ({data.materials.length})</button>
    </div>
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
      <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}><Search size={16} />
        <input className="library-input" aria-label="Search library" placeholder="Search part, manufacturer or description" value={query} onChange={e => setQuery(e.target.value)} style={{ width: 310, maxWidth: '100%' }} />
      </label>
      {activeTab === 'components' && <>
        <select className="library-input" aria-label="Component category" value={category} onChange={e => setCategory(e.target.value)}>
          <option value="all">All categories ({data.components.length})</option>
          {data.categories.map(c => <option key={c.id} value={c.id}>{c.label} ({data.components.filter(p => p.category === c.id).length})</option>)}
        </select>
        <select className="library-input" aria-label="Reference type" value={kind} onChange={e => setKind(e.target.value)}>
          <option value="all">Parts & product families</option><option value="PART">Parts</option><option value="FAMILY">Product families</option>
        </select>
      </>}
      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{count} matching references</span>
    </div>
    <div className="card" style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: 12 }}>
        <thead style={{ color: 'var(--text-muted)', background: 'var(--bg-app)' }}><tr>
          {(activeTab === 'components' ? ['Part / family', 'Manufacturer & package', 'Category', 'Reference ratings', 'Source & qualification']
            : activeTab === 'materials' ? ['Material & family', 'Initial ?i', 'Flux density (T)', 'Curie temperature (?C)', 'Conditions & source']
            : ['Core geometry', 'Ae (mm?)', 'le (mm)', 'Ve (mm?)', 'Identity & source']).map(label => <th key={label} scope="col" style={cell}>{label}</th>)}
        </tr></thead>
        <tbody>
          {activeTab === 'components' && components.map(c => <tr key={c.id}>
            <td style={cell}><strong style={{ color: 'var(--primary)' }}>{c.mpn}</strong><div style={{ margin: '6px 0' }}><span className="badge badge-blue">{c.record_kind === 'FAMILY' ? 'Product family' : 'Part reference'}</span>
              {c.lifecycle_status !== 'UNKNOWN' && <span className="badge badge-yellow">{c.lifecycle_status}</span>}</div><div style={{ maxWidth: 260, lineHeight: 1.5 }}>{c.description}</div></td>
            <td style={cell}>{c.manufacturer}<div style={{ marginTop: 8, color: 'var(--text-muted)' }}>{c.package || (c.record_kind === 'FAMILY' ? 'Select package variant' : 'Package not transcribed')}</div></td>
            <td style={cell}>{categories.get(c.category) || c.category}</td>
            <td style={cell}><Ratings part={c} /></td><td style={cell}><Source record={c} /></td>
          </tr>)}
          {activeTab === 'materials' && materials.map(m => <tr key={m.id}>
            <td style={cell}><strong>{m.name}</strong><div style={{ marginTop: 6 }}>{m.manufacturer}</div><div style={{ color: 'var(--text-muted)', marginTop: 6 }}>{m.material_type}</div></td>
            <td style={cell}>{quantity(m.initial_permeability_ui)}</td><td style={cell}>{quantity(m.saturation_flux_t)}</td>
            <td style={cell}>{m.curie_temp_c == null ? unknown : `${m.curie_temp_qualifier}${quantity(m.curie_temp_c)}`}</td>
            <td style={cell}><p style={{ maxWidth: 450, marginBottom: 12, lineHeight: 1.6 }}>{m.conditions}</p><Source record={m} /></td>
          </tr>)}
          {activeTab === 'cores' && cores.map(c => <tr key={c.id}>
            <td style={cell}><strong>{c.name}</strong><div style={{ marginTop: 6 }}>{c.geometry_type}</div></td>
            <td style={cell}>{quantity(c.ae_mm2)}</td><td style={cell}>{quantity(c.le_mm)}</td><td style={cell}>{quantity(c.ve_mm3)}</td>
            <td style={cell}><div>{c.manufacturer}</div><p style={{ maxWidth: 450, margin: '8px 0', lineHeight: 1.6 }}>{c.conditions}</p><Source record={c} /></td>
          </tr>)}
          {count === 0 && <tr><td colSpan={5} style={{ ...cell, padding: 32, textAlign: 'center' }}>
            No references match this selection. Categories with zero entries are supported but have no sourced records yet.
          </td></tr>}
        </tbody>
      </table>
    </div>
    <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Reference data is not a design approval. Unknown values are never substituted. Product-family entries require an exact ordering code before selection.</p>
  </div>;
};

export const ComponentLibrary: React.FC = () => {
  const { data, error } = usePolling(api.components);
  return <ComponentLibraryView data={data} error={error} />;
};
