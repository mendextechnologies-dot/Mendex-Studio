import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

export interface ThermalSizingCalculatorCardProps {
  revisionId: string;
  specification: Record<string, any>;
  onRefresh?: () => void;
}

export const ThermalSizingCalculatorCard: React.FC<ThermalSizingCalculatorCardProps> = ({
  revisionId,
  specification,
  onRefresh,
}) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Interactive controls state
  const [ambientTemp, setAmbientTemp] = useState<number>(() => {
    if (specification?.ambient_temperature_k) {
      return Math.round(specification.ambient_temperature_k - 273.15);
    }
    return 25;
  });
  const [mode, setMode] = useState<'auto' | 'manual'>('auto');
  const [customSwitchLoss, setCustomSwitchLoss] = useState<number>(2.5);
  const [customRthSa, setCustomRthSa] = useState<number>(8.0);
  const [customTraceCurrent, setCustomTraceCurrent] = useState<number>(10.0);
  const [customCuOz, setCustomCuOz] = useState<number>(1.0);
  const [customTargetDeltaT, setCustomTargetDeltaT] = useState<number>(10.0);
  const [isRecording, setIsRecording] = useState(false);

  const fetchThermalData = async (recordEvidence: boolean = false) => {
    setLoading(true);
    setError(null);
    try {
      const params: any = {
        revision_id: revisionId,
        ambient_temp_c: ambientTemp,
        record_evidence: recordEvidence,
      };

      if (mode === 'manual') {
        params.p_switch_loss_w = customSwitchLoss;
        params.r_th_sa_c_w = customRthSa;
        params.trace_current_a = customTraceCurrent;
        params.copper_thickness_oz = customCuOz;
        params.target_trace_delta_t_c = customTargetDeltaT;
      }

      const res = await api.calculateThermalSizing(params);
      setData(res);

      if (recordEvidence && res.record_id) {
        setNotification({
          type: 'success',
          message: `Formal electro-thermal calculation recorded into engineering evidence repository (Record ID: ${res.record_id.slice(0, 8)}…).`,
        });
        if (onRefresh) onRefresh();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to compute thermal sizing');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchThermalData(false);
  }, [revisionId, ambientTemp, mode, customSwitchLoss, customRthSa, customTraceCurrent, customCuOz, customTargetDeltaT]);

  const semi = data?.semiconductor;
  const diode = data?.secondary_diode;
  const mag = data?.magnetics;
  const trace = data?.ipc2152_trace;
  const summary = data?.summary;

  const getMeterColor = (temp: number, limit: number) => {
    if (temp <= limit * 0.85) return '#10b981'; // green
    if (temp <= limit) return '#f59e0b'; // amber
    return '#ef4444'; // red
  };

  return (
    <div
      style={{
        padding: 20,
        background: '#ffffff',
        borderRadius: 8,
        border: '1px solid #cbd5e1',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        marginBottom: 20,
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 20 }}>🌡️</span>
            <h4 style={{ fontSize: 16, fontWeight: 800, color: '#0f172a', margin: 0 }}>
              Semiconductor & Magnetic Thermal Sizing Calculator
            </h4>
          </div>
          <span style={{ fontSize: 11, color: '#64748b', marginTop: 4, display: 'inline-block' }}>
            Closed-Form Electro-Thermal Analysis per IPC-2152 (Traces) & IPC-9592B (Semiconductors)
          </span>
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {summary && (
            <span
              className={summary.compliance_status === 'COMPLIANT' ? 'badge badge-green' : 'badge badge-red'}
              style={{ padding: '4px 10px', fontSize: 11, fontWeight: 700 }}
            >
              {summary.compliance_status === 'COMPLIANT' ? '✓ THERMAL MARGINS OK' : '⚠️ MARGIN EXCEEDED'}
            </span>
          )}
          <span className="badge badge-blue">IPC-9592B (80% Tj)</span>
          <span className="badge badge-purple">IPC-2152</span>

          <button
            className="btn btn-secondary"
            onClick={() => fetchThermalData(false)}
            disabled={loading}
            style={{ fontSize: 12, padding: '6px 12px' }}
          >
            {loading ? '⏳ Calculating…' : '🔄 Refresh'}
          </button>

          <button
            className="btn btn-primary"
            onClick={() => {
              setIsRecording(true);
              fetchThermalData(true).finally(() => setIsRecording(false));
            }}
            disabled={loading || isRecording}
            style={{ fontSize: 12, padding: '6px 14px', background: '#0284c7', borderColor: '#0369a1' }}
          >
            {isRecording ? '📝 Recording…' : '📝 Record Evidence'}
          </button>
        </div>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div
          style={{
            padding: '10px 14px',
            borderRadius: 6,
            fontSize: 12,
            background: notification.type === 'success' ? '#ecfdf5' : '#fef2f2',
            border: `1px solid ${notification.type === 'success' ? '#a7f3d0' : '#fecaca'}`,
            color: notification.type === 'success' ? '#065f46' : '#991b1b',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span>{notification.message}</span>
          <button
            onClick={() => setNotification(null)}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontWeight: 700 }}
          >
            ×
          </button>
        </div>
      )}

      {error && (
        <div style={{ padding: '10px 14px', borderRadius: 6, fontSize: 12, background: '#fef2f2', color: '#991b1b' }}>
          {error}
        </div>
      )}

      {/* Controls Bar: Mode & Ambient Selector */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
          background: '#f8fafc',
          padding: '10px 14px',
          borderRadius: 6,
          border: '1px solid #e2e8f0',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#475569', textTransform: 'uppercase' }}>
            Operating Mode:
          </span>
          <div style={{ display: 'flex', background: '#e2e8f0', borderRadius: 4, padding: 2 }}>
            <button
              onClick={() => setMode('auto')}
              style={{
                fontSize: 11,
                padding: '4px 10px',
                border: 'none',
                borderRadius: 3,
                background: mode === 'auto' ? '#ffffff' : 'transparent',
                fontWeight: mode === 'auto' ? 700 : 500,
                color: mode === 'auto' ? '#0f172a' : '#64748b',
                cursor: 'pointer',
              }}
            >
              ⚡ Auto-Derived Envelope
            </button>
            <button
              onClick={() => setMode('manual')}
              style={{
                fontSize: 11,
                padding: '4px 10px',
                border: 'none',
                borderRadius: 3,
                background: mode === 'manual' ? '#ffffff' : 'transparent',
                fontWeight: mode === 'manual' ? 700 : 500,
                color: mode === 'manual' ? '#0f172a' : '#64748b',
                cursor: 'pointer',
              }}
            >
              🎛️ Interactive Tuner
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#475569', textTransform: 'uppercase' }}>
            Ambient Temp (Tamb):
          </span>
          {[25, 40, 55].map((temp) => (
            <button
              key={temp}
              onClick={() => setAmbientTemp(temp)}
              style={{
                fontSize: 11,
                padding: '3px 10px',
                border: ambientTemp === temp ? '1px solid #3b82f6' : '1px solid #cbd5e1',
                borderRadius: 4,
                background: ambientTemp === temp ? '#eff6ff' : '#ffffff',
                color: ambientTemp === temp ? '#1d4ed8' : '#475569',
                fontWeight: ambientTemp === temp ? 700 : 500,
                cursor: 'pointer',
              }}
            >
              {temp}°C {temp === 25 ? '(Lab)' : temp === 40 ? '(Ind)' : '(Enclosure)'}
            </button>
          ))}
        </div>
      </div>

      {/* Manual Tuning Sliders Panel */}
      {mode === 'manual' && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 14,
            background: '#f1f5f9',
            padding: 14,
            borderRadius: 6,
            border: '1px solid #cbd5e1',
          }}
        >
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span style={{ fontWeight: 600, color: '#334155' }}>Switch Dissipation:</span>
              <strong style={{ color: '#0f172a' }}>{customSwitchLoss.toFixed(1)} W</strong>
            </div>
            <input
              type="range"
              min="0.5"
              max="15.0"
              step="0.5"
              value={customSwitchLoss}
              onChange={(e) => setCustomSwitchLoss(parseFloat(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span style={{ fontWeight: 600, color: '#334155' }}>Heatsink Rth,sa:</span>
              <strong style={{ color: '#0f172a' }}>{customRthSa.toFixed(1)} °C/W</strong>
            </div>
            <input
              type="range"
              min="1.0"
              max="25.0"
              step="0.5"
              value={customRthSa}
              onChange={(e) => setCustomRthSa(parseFloat(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span style={{ fontWeight: 600, color: '#334155' }}>Trace Current:</span>
              <strong style={{ color: '#0f172a' }}>{customTraceCurrent.toFixed(1)} A</strong>
            </div>
            <input
              type="range"
              min="1.0"
              max="25.0"
              step="1.0"
              value={customTraceCurrent}
              onChange={(e) => setCustomTraceCurrent(parseFloat(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span style={{ fontWeight: 600, color: '#334155' }}>Target Trace ΔT / Cu Weight:</span>
              <strong style={{ color: '#0f172a' }}>{customTargetDeltaT}°C • {customCuOz}oz</strong>
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              {[10, 20, 30].map((dt) => (
                <button
                  key={dt}
                  onClick={() => setCustomTargetDeltaT(dt)}
                  style={{
                    fontSize: 10,
                    padding: '2px 8px',
                    borderRadius: 3,
                    border: '1px solid #cbd5e1',
                    background: customTargetDeltaT === dt ? '#2563eb' : '#ffffff',
                    color: customTargetDeltaT === dt ? '#ffffff' : '#475569',
                    cursor: 'pointer',
                  }}
                >
                  Δ{dt}°C
                </button>
              ))}
              {[1.0, 2.0].map((oz) => (
                <button
                  key={oz}
                  onClick={() => setCustomCuOz(oz)}
                  style={{
                    fontSize: 10,
                    padding: '2px 8px',
                    borderRadius: 3,
                    border: '1px solid #cbd5e1',
                    background: customCuOz === oz ? '#7c3aed' : '#ffffff',
                    color: customCuOz === oz ? '#ffffff' : '#475569',
                    cursor: 'pointer',
                  }}
                >
                  {oz}oz
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 3 Interactive Thermal Margin Meter Cards */}
      {data && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 14,
          }}
        >
          {/* Card 1: Primary Semiconductor MOSFET Tj */}
          {semi && (
            <div
              style={{
                borderRadius: 8,
                padding: 16,
                border: '1px solid #e2e8f0',
                background: '#ffffff',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h5 style={{ fontSize: 13, fontWeight: 800, color: '#0f172a', margin: 0 }}>
                    ⚡ Primary Switch Junction (Tj)
                  </h5>
                  <span
                    className={semi.status.includes('PASS') ? 'badge badge-green' : 'badge badge-red'}
                    style={{ fontSize: 10 }}
                  >
                    {semi.status}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: '#64748b', marginTop: 2 }}>
                  {semi.part_number} • Ploss = {semi.p_loss_w} W
                </div>

                {/* Big Metric Dial */}
                <div style={{ textAlign: 'center', margin: '14px 0 10px' }}>
                  <div
                    style={{
                      fontSize: 32,
                      fontWeight: 900,
                      color: getMeterColor(semi.t_junction_c, semi.t_j_limit_c),
                      lineHeight: 1,
                    }}
                  >
                    {semi.t_junction_c.toFixed(1)}°C
                  </div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#475569', marginTop: 4 }}>
                    {semi.thermal_margin_c >= 0 ? (
                      <span style={{ color: '#059669' }}>+{semi.thermal_margin_c.toFixed(1)}°C Margin</span>
                    ) : (
                      <span style={{ color: '#dc2626' }}>{semi.thermal_margin_c.toFixed(1)}°C Over Limit</span>
                    )}
                    <span style={{ color: '#94a3b8', fontWeight: 500 }}> (Derated: {semi.t_j_limit_c}°C)</span>
                  </div>
                </div>

                {/* Progress bar */}
                <div
                  style={{
                    width: '100%',
                    height: 8,
                    borderRadius: 4,
                    background: '#e2e8f0',
                    overflow: 'hidden',
                    marginBottom: 12,
                  }}
                >
                  <div
                    style={{
                      width: `${Math.min(100, Math.max(0, (semi.t_junction_c / semi.t_j_max_c) * 100))}%`,
                      height: '100%',
                      background: getMeterColor(semi.t_junction_c, semi.t_j_limit_c),
                      borderRadius: 4,
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>

                {/* Sizing Schedule Table */}
                <div style={{ fontSize: 11, color: '#334155', display: 'flex', flexDirection: 'column', gap: 5 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>Case Temp (Tc):</span>
                    <strong>{semi.t_case_c.toFixed(1)} °C</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>Req. Heatsink Rth,sa:</span>
                    <strong>≤ {semi.heatsink_required_c_w.toFixed(2)} °C/W</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>SMD Cu Area (2oz):</span>
                    <strong>{semi.pcb_copper_area_req_cm2.toFixed(1)} cm²</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>Thermal Vias (0.3mm):</span>
                    <strong>{semi.thermal_vias_recommended} Vias</strong>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Card 2: Magnetic Transformer / Inductor Hotspot */}
          {mag && (
            <div
              style={{
                borderRadius: 8,
                padding: 16,
                border: '1px solid #e2e8f0',
                background: '#ffffff',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h5 style={{ fontSize: 13, fontWeight: 800, color: '#0f172a', margin: 0 }}>
                    🧲 Transformer Hotspot (T1)
                  </h5>
                  <span
                    className={mag.status === 'PASS' ? 'badge badge-green' : 'badge badge-red'}
                    style={{ fontSize: 10 }}
                  >
                    {mag.status}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: '#64748b', marginTop: 2 }}>
                  {mag.insulation_class} • Ploss = {mag.p_total_w} W
                </div>

                {/* Big Metric Dial */}
                <div style={{ textAlign: 'center', margin: '14px 0 10px' }}>
                  <div
                    style={{
                      fontSize: 32,
                      fontWeight: 900,
                      color: getMeterColor(mag.t_hotspot_c, mag.t_class_max_c),
                      lineHeight: 1,
                    }}
                  >
                    {mag.t_hotspot_c.toFixed(1)}°C
                  </div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#475569', marginTop: 4 }}>
                    <span style={{ color: '#059669' }}>+{mag.thermal_margin_c.toFixed(1)}°C Margin</span>
                    <span style={{ color: '#94a3b8', fontWeight: 500 }}> (Class Max: {mag.t_class_max_c}°C)</span>
                  </div>
                </div>

                {/* Progress bar */}
                <div
                  style={{
                    width: '100%',
                    height: 8,
                    borderRadius: 4,
                    background: '#e2e8f0',
                    overflow: 'hidden',
                    marginBottom: 12,
                  }}
                >
                  <div
                    style={{
                      width: `${Math.min(100, Math.max(0, (mag.t_hotspot_c / mag.t_class_max_c) * 100))}%`,
                      height: '100%',
                      background: getMeterColor(mag.t_hotspot_c, mag.t_class_max_c),
                      borderRadius: 4,
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>

                {/* Sizing Schedule Table */}
                <div style={{ fontSize: 11, color: '#334155', display: 'flex', flexDirection: 'column', gap: 5 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>Surface Temp:</span>
                    <strong>{mag.t_surface_c.toFixed(1)} °C</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>Core Surface Area:</span>
                    <strong>{mag.surface_area_cm2} cm²</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>Core / Winding Loss:</span>
                    <strong>{mag.p_core_w} W / {mag.p_winding_w} W</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>Convection Rth,mag:</span>
                    <strong>{mag.r_th_mag_c_w.toFixed(2)} °C/W</strong>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Card 3: IPC-2152 Heavy Copper Power Trace Sizing */}
          {trace && (
            <div
              style={{
                borderRadius: 8,
                padding: 16,
                border: '1px solid #e2e8f0',
                background: '#ffffff',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h5 style={{ fontSize: 13, fontWeight: 800, color: '#0f172a', margin: 0 }}>
                    📏 IPC-2152 Power Trace Sizing
                  </h5>
                  <span className="badge badge-purple" style={{ fontSize: 10 }}>
                    {trace.copper_thickness_oz} oz ({trace.layer_name})
                  </span>
                </div>
                <div style={{ fontSize: 10, color: '#64748b', marginTop: 2 }}>
                  Target ΔT = {trace.target_delta_t_c}°C • I = {trace.current_a} A
                </div>

                {/* Big Metric Dial */}
                <div style={{ textAlign: 'center', margin: '14px 0 10px' }}>
                  <div style={{ fontSize: 32, fontWeight: 900, color: '#2563eb', lineHeight: 1 }}>
                    {trace.min_trace_width_mm.toFixed(2)} mm
                  </div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#475569', marginTop: 4 }}>
                    <span>Minimum Copper Width</span>
                    <span style={{ color: '#94a3b8', fontWeight: 500 }}> ({(trace.min_trace_width_mm * 39.37).toFixed(0)} mils)</span>
                  </div>
                </div>

                {/* Progress bar visual indicator */}
                <div
                  style={{
                    width: '100%',
                    height: 8,
                    borderRadius: 4,
                    background: '#e2e8f0',
                    overflow: 'hidden',
                    marginBottom: 12,
                  }}
                >
                  <div
                    style={{
                      width: `${Math.min(100, Math.max(10, (trace.min_trace_width_mm / 6.0) * 100))}%`,
                      height: '100%',
                      background: '#3b82f6',
                      borderRadius: 4,
                      transition: 'width 0.3s ease',
                    }}
                  />
                </div>

                {/* Sizing Schedule Table */}
                <div style={{ fontSize: 11, color: '#334155', display: 'flex', flexDirection: 'column', gap: 5 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>Cross-Section Area:</span>
                    <strong>{trace.cross_sectional_area_mils2.toFixed(1)} mils²</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>Trace Resistance:</span>
                    <strong>{trace.trace_resistance_m_ohm_per_meter.toFixed(2)} mΩ/m</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>Conduction Loss:</span>
                    <strong>{trace.conduction_loss_w_per_meter.toFixed(2)} W/m</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: '#64748b' }}>Standard Rule:</span>
                    <strong style={{ fontSize: 10 }}>IPC-2152 Universal Formula</strong>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
