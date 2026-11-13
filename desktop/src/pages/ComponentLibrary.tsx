import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { usePolling } from '../usePolling';
import { Cpu, Box, Database } from 'lucide-react';

export const ComponentLibrary: React.FC = () => {
  const { data, error } = usePolling(api.components);
  const [activeTab, setActiveTab] = useState<'semis' | 'cores' | 'materials'>('semis');



  if (!data) {
    return <div style={{ padding: '24px', color: 'var(--text-muted)' }}>{error || 'Loading components library?'}</div>;
  }

  const { components, cores, materials } = data;

  return (
    <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
      {error && <p role="alert">{error}. Displayed records may be stale.</p>}
      <div>
        <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc' }}>
          Component & Materials Library
        </h2>
        <p style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
          Seeded reference library. Manufacturer ratings and source assertions require independent verification.
        </p>
      </div>

      <div style={{ display: 'flex', gap: '8px' }}>
        <button
          onClick={() => setActiveTab('semis')}
          className={`btn ${activeTab === 'semis' ? 'btn-primary' : 'btn-secondary'}`}
        >
          <Cpu size={14} /> Semiconductors ({components ? components.length : 0})
        </button>
        <button
          onClick={() => setActiveTab('cores')}
          className={`btn ${activeTab === 'cores' ? 'btn-primary' : 'btn-secondary'}`}
        >
          <Box size={14} /> Magnetic Cores ({cores ? cores.length : 0})
        </button>
        <button
          onClick={() => setActiveTab('materials')}
          className={`btn ${activeTab === 'materials' ? 'btn-primary' : 'btn-secondary'}`}
        >
          <Database size={14} /> Magnetic Materials ({materials ? materials.length : 0})
        </button>
      </div>

      {activeTab === 'semis' && (
        <div className="card">
          <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-dim)' }}>
                <th style={{ padding: '10px 12px' }}>Part Number</th>
                <th style={{ padding: '10px 12px' }}>Manufacturer</th>
                <th style={{ padding: '10px 12px' }}>Category</th>
                <th style={{ padding: '10px 12px' }}>Package</th>
                <th style={{ padding: '10px 12px' }}>Key Ratings</th>
              </tr>
            </thead>
            <tbody>
              {components && components.map((c: any) => (
                <tr key={c.id} style={{ borderBottom: '1px solid #1a1e2f' }}>
                  <td style={{ padding: '10px 12px', fontWeight: 700, color: '#60a5fa' }}>{c.part_number}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{c.manufacturer}</td>
                  <td style={{ padding: '10px 12px' }}><span className="badge badge-blue">{c.category}</span></td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-dim)' }}>{c.package_type}</td>
                  <td style={{ padding: '10px 12px', fontSize: '11px', color: '#93c5fd' }}>
                    {Object.entries(c.parameters || {}).map(([k, v]) => `${k}: ${v}`).join(' · ')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'cores' && (
        <div className="card">
          <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-dim)' }}>
                <th style={{ padding: '10px 12px' }}>Core Geometry</th>
                <th style={{ padding: '10px 12px' }}>Ae (mm²)</th>
                <th style={{ padding: '10px 12px' }}>le (mm)</th>
                <th style={{ padding: '10px 12px' }}>Ve (mm³)</th>
                <th style={{ padding: '10px 12px' }}>Material</th>
              </tr>
            </thead>
            <tbody>
              {cores && cores.map((core: any) => (
                <tr key={core.id} style={{ borderBottom: '1px solid #1a1e2f' }}>
                  <td style={{ padding: '10px 12px', fontWeight: 700, color: '#34d399' }}>{core.name || core.id}</td>
                  <td style={{ padding: '10px 12px' }}>{core.cross_section_ae_mm2 ?? 78.5}</td>
                  <td style={{ padding: '10px 12px' }}>{core.magnetic_path_le_mm ?? 31.5}</td>
                  <td style={{ padding: '10px 12px' }}>{core.volume_ve_mm3 ?? 2470}</td>
                  <td style={{ padding: '10px 12px', color: '#fbbf24' }}>{core.material || 'TDK N87'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'materials' && (
        <div className="card">
          <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-dim)' }}>
                <th style={{ padding: '10px 12px' }}>Material Name</th>
                <th style={{ padding: '10px 12px' }}>Family</th>
                <th style={{ padding: '10px 12px' }}>Initial μi</th>
                <th style={{ padding: '10px 12px' }}>Bsat (T)</th>
                <th style={{ padding: '10px 12px' }}>Curie Temp (°C)</th>
              </tr>
            </thead>
            <tbody>
              {materials && materials.map((m: any) => (
                <tr key={m.id} style={{ borderBottom: '1px solid #1a1e2f' }}>
                  <td style={{ padding: '10px 12px', fontWeight: 700, color: '#f8fafc' }}>{m.name}</td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{m.material_family}</td>
                  <td style={{ padding: '10px 12px' }}>{m.initial_permeability ?? 2200}</td>
                  <td style={{ padding: '10px 12px', color: '#34d399', fontWeight: 600 }}>{m.saturation_flux_density_t ?? 0.39} T</td>
                  <td style={{ padding: '10px 12px', color: 'var(--text-dim)' }}>{m.curie_temperature_c ?? 210}°C</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
