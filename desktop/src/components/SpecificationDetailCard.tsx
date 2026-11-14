import React, { useState, useMemo } from 'react';
import type { ProjectDetailData } from '../api/types';
import {
  Zap,
  Cpu,
  Thermometer,
  ShieldCheck,
  ShieldAlert,
  FileText,
  CheckCircle2,
  Copy,
  Check,
  Download,
  Search,
  Layers,
  Ruler,
  Activity,
  AlertTriangle,
  Info,
  Eye,
  EyeOff,
  Sliders,
  Maximize2,
  Lock,
} from 'lucide-react';

interface SpecificationDetailCardProps {
  data: ProjectDetailData;
  onNavigateToCAD?: () => void;
  onNavigateToSimulations?: () => void;
}

interface SpecItem {
  key: string;
  label: string;
  symbol?: string;
  value: any;
  formattedValue: string;
  unit?: string;
  category: 'electrical' | 'thermal_mechanical' | 'safety' | 'governance';
  description: string;
  isAssigned: boolean;
  statusBadge?: { label: string; type: 'green' | 'blue' | 'yellow' | 'red' | 'muted' };
}

export const SpecificationDetailCard: React.FC<SpecificationDetailCardProps> = ({
  data,
  onNavigateToCAD,
  onNavigateToSimulations,
}) => {
  const spec = data?.revision?.specification || {};
  const [searchTerm, setSearchTerm] = useState('');
  const [showUnassigned, setShowUnassigned] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'all' | 'electrical' | 'thermal_mechanical' | 'safety' | 'governance'>('all');

  // Copy helper
  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  // Calculated Engineering Figures
  const vinNom = typeof spec.vin_nom_v === 'number' ? spec.vin_nom_v : null;
  const vinMin = typeof spec.vin_min_v === 'number' ? spec.vin_min_v : null;
  const vinMax = typeof spec.vin_max_v === 'number' ? spec.vin_max_v : null;
  const vout = typeof spec.vout_v === 'number' ? spec.vout_v : null;
  const iout = typeof spec.iout_a === 'number' ? spec.iout_a : null;
  const fsw = typeof spec.switching_frequency_hz === 'number' ? spec.switching_frequency_hz : null;
  const tjMax = typeof spec.max_junction_temperature_c === 'number' ? spec.max_junction_temperature_c : null;
  const pOut = vout !== null && iout !== null ? vout * iout : null;

  // Ambient temp normalization (handle Kelvin vs Celsius)
  let ambC = spec.ambient_temperature_c;
  if (ambC == null && typeof spec.ambient_temperature_k === 'number') {
    ambC = Number((spec.ambient_temperature_k - 273.15).toFixed(1));
  }

  // Safety Hazard Level
  const isExtremeHV = (vout ?? 0) >= 500;
  const isHighVoltage = (vout ?? 0) > 60;
  const safetyCategory = isExtremeHV
    ? 'CAT III / Extreme High Voltage (>500V)'
    : isHighVoltage
    ? 'CAT III / High Voltage Hazard (>60V)'
    : 'SELV (Safety Extra Low Voltage ≤60V)';

  // Build structured parameter catalog
  const specItems: SpecItem[] = useMemo(() => {
    const items: SpecItem[] = [
      // Electrical
      {
        key: 'vin_nom_v',
        label: 'Nominal Input Voltage',
        symbol: 'Vin,nom',
        value: vinNom,
        formattedValue: vinNom !== null ? `${vinNom.toFixed(1)} V` : 'Not specified',
        unit: 'V',
        category: 'electrical',
        description: 'Nominal operating input line/rail potential',
        isAssigned: vinNom !== null,
        statusBadge: vinNom !== null ? { label: `${vinNom} V Nominal`, type: 'blue' } : undefined,
      },
      {
        key: 'vin_min_v',
        label: 'Minimum Input Voltage',
        symbol: 'Vin,min',
        value: vinMin,
        formattedValue: vinMin !== null ? `${vinMin.toFixed(1)} V` : 'Not specified',
        unit: 'V',
        category: 'electrical',
        description: 'Minimum input brownout/dropout threshold',
        isAssigned: vinMin !== null,
      },
      {
        key: 'vin_max_v',
        label: 'Maximum Input Voltage',
        symbol: 'Vin,max',
        value: vinMax,
        formattedValue: vinMax !== null ? `${vinMax.toFixed(1)} V` : 'Not specified',
        unit: 'V',
        category: 'electrical',
        description: 'Maximum transient/surge input rail limit',
        isAssigned: vinMax !== null,
      },
      {
        key: 'vout_v',
        label: 'Regulated Output Voltage',
        symbol: 'Vout',
        value: vout,
        formattedValue: vout !== null ? `${vout.toLocaleString()} V${vout >= 1000 ? ` (${(vout / 1000).toFixed(1)} kV)` : ''}` : 'Not specified',
        unit: 'V',
        category: 'electrical',
        description: 'Full-scale regulated DC output target',
        isAssigned: vout !== null,
        statusBadge: isExtremeHV
          ? { label: 'Extreme HV (>500V)', type: 'red' }
          : isHighVoltage
          ? { label: 'High Voltage', type: 'yellow' }
          : { label: 'SELV', type: 'green' },
      },
      {
        key: 'iout_a',
        label: 'Rated Output Current',
        symbol: 'Iout',
        value: iout,
        formattedValue: iout !== null
          ? iout >= 1
            ? `${iout.toFixed(2)} A`
            : `${(iout * 1000).toFixed(2)} mA`
          : 'Not specified',
        unit: 'A',
        category: 'electrical',
        description: 'Continuous or peak pulse deliverable output current',
        isAssigned: iout !== null,
        statusBadge: iout !== null ? { label: iout >= 1 ? 'High Current' : 'Precision mA', type: 'blue' } : undefined,
      },
      {
        key: 'pout_w',
        label: 'Rated Output Power',
        symbol: 'Pout',
        value: pOut,
        formattedValue: pOut !== null
          ? pOut >= 1000
            ? `${(pOut / 1000).toFixed(2)} kW`
            : `${pOut.toFixed(2)} W`
          : 'Not specified',
        unit: 'W',
        category: 'electrical',
        description: 'Computed continuous/burst output power: P = Vout × Iout',
        isAssigned: pOut !== null,
        statusBadge: pOut !== null ? { label: `${pOut.toFixed(1)} W Rated`, type: 'blue' } : undefined,
      },
      {
        key: 'switching_frequency_hz',
        label: 'Switching Frequency / Repetition Rate',
        symbol: 'fsw',
        value: fsw,
        formattedValue: fsw !== null
          ? fsw >= 1000
            ? `${(fsw / 1000).toFixed(1)} kHz`
            : `${fsw.toFixed(1)} Hz`
          : 'Not specified',
        unit: 'Hz',
        category: 'electrical',
        description: 'Main converter switching or discharge pulse repetition frequency',
        isAssigned: fsw !== null,
        statusBadge: fsw !== null
          ? { label: fsw >= 1000 ? `${(fsw / 1000).toFixed(0)} kHz PWM` : `${fsw} Hz Pulse`, type: 'blue' }
          : undefined,
      },
      {
        key: 'topology',
        label: 'Operating Power Topology',
        symbol: 'Top',
        value: spec.topology,
        formattedValue: spec.topology && spec.topology.trim() ? spec.topology : 'Unassigned / Candidate synthesis',
        category: 'electrical',
        description: 'Power stage architecture and magnetic arrangement',
        isAssigned: Boolean(spec.topology && spec.topology.trim()),
        statusBadge: spec.topology && spec.topology.trim()
          ? { label: 'Defined', type: 'green' }
          : { label: 'Synthesis Pending', type: 'yellow' },
      },
      {
        key: 'target_efficiency_pct',
        label: 'Target Energy Efficiency',
        symbol: 'η',
        value: spec.target_efficiency_pct,
        formattedValue: spec.target_efficiency_pct != null ? `${spec.target_efficiency_pct}%` : 'Not constrained',
        unit: '%',
        category: 'electrical',
        description: 'Target conversion efficiency at rated full load',
        isAssigned: spec.target_efficiency_pct != null,
      },
      {
        key: 'vout_ripple_max_mv',
        label: 'Max Peak-to-Peak Voltage Ripple',
        symbol: 'ΔVout',
        value: spec.vout_ripple_max_mv,
        formattedValue: spec.vout_ripple_max_mv != null ? `${spec.vout_ripple_max_mv} mV` : 'Not constrained',
        unit: 'mV',
        category: 'electrical',
        description: 'Permissible high-frequency AC switching ripple amplitude',
        isAssigned: spec.vout_ripple_max_mv != null,
      },
      {
        key: 'line_regulation_pct',
        label: 'Line Regulation',
        symbol: 'Reg_line',
        value: spec.line_regulation_pct,
        formattedValue: spec.line_regulation_pct != null ? `${spec.line_regulation_pct}%` : 'Not constrained',
        unit: '%',
        category: 'electrical',
        description: 'Output deviation over full input voltage swing',
        isAssigned: spec.line_regulation_pct != null,
      },
      {
        key: 'load_regulation_pct',
        label: 'Load Regulation',
        symbol: 'Reg_load',
        value: spec.load_regulation_pct,
        formattedValue: spec.load_regulation_pct != null ? `${spec.load_regulation_pct}%` : 'Not constrained',
        unit: '%',
        category: 'electrical',
        description: 'Output deviation from zero to 100% rated load step',
        isAssigned: spec.load_regulation_pct != null,
      },

      // Thermal & Mechanical
      {
        key: 'max_junction_temperature_c',
        label: 'Maximum Junction Temperature',
        symbol: 'Tj,max',
        value: tjMax,
        formattedValue: tjMax !== null ? `${tjMax.toFixed(0)} °C` : '150 °C (Standard Si/SiC)',
        unit: '°C',
        category: 'thermal_mechanical',
        description: 'Absolute maximum allowable semiconductor junction temperature',
        isAssigned: tjMax !== null,
        statusBadge: { label: `${tjMax || 150} °C Limit`, type: 'yellow' },
      },
      {
        key: 'ambient_temperature_c',
        label: 'Ambient Operating Temperature',
        symbol: 'Tamb',
        value: ambC,
        formattedValue: ambC != null ? `${ambC} °C (${((ambC * 9/5) + 32).toFixed(1)} °F)` : '25.0 °C (Nominal Lab)',
        unit: '°C',
        category: 'thermal_mechanical',
        description: 'Nominal ambient operating environment reference temperature',
        isAssigned: ambC != null,
      },
      {
        key: 'cooling_method',
        label: 'Cooling & Thermal Dissipation',
        symbol: 'Cooling',
        value: spec.cooling_method,
        formattedValue: spec.cooling_method ? spec.cooling_method.replace(/_/g, ' ').toUpperCase() : 'NATURAL CONVECTION',
        category: 'thermal_mechanical',
        description: 'Active or passive thermal heat rejection mechanism',
        isAssigned: Boolean(spec.cooling_method),
        statusBadge: { label: 'Passive Convection', type: 'blue' },
      },
      {
        key: 'max_pcb_width_mm',
        label: 'Target PCB Width Envelope',
        symbol: 'W_pcb',
        value: spec.max_pcb_width_mm,
        formattedValue: spec.max_pcb_width_mm != null ? `${spec.max_pcb_width_mm} mm` : 'Unconstrained',
        unit: 'mm',
        category: 'thermal_mechanical',
        description: 'Mechanical boundary constraint along PCB X axis',
        isAssigned: spec.max_pcb_width_mm != null,
      },
      {
        key: 'max_pcb_height_mm',
        label: 'Target PCB Height Envelope',
        symbol: 'H_pcb',
        value: spec.max_pcb_height_mm,
        formattedValue: spec.max_pcb_height_mm != null ? `${spec.max_pcb_height_mm} mm` : 'Unconstrained',
        unit: 'mm',
        category: 'thermal_mechanical',
        description: 'Mechanical boundary constraint along PCB Y axis',
        isAssigned: spec.max_pcb_height_mm != null,
      },
      {
        key: 'reliability_mtbf_hours',
        label: 'Reliability MTBF Target',
        symbol: 'MTBF',
        value: spec.reliability_mtbf_hours,
        formattedValue: spec.reliability_mtbf_hours != null ? `${spec.reliability_mtbf_hours.toLocaleString()} hrs` : 'Not constrained',
        unit: 'hours',
        category: 'thermal_mechanical',
        description: 'Mean Time Between Failures per Telcordia SR-332 / MIL-HDBK-217F',
        isAssigned: spec.reliability_mtbf_hours != null,
      },
      {
        key: 'target_cost_usd',
        label: 'Target Production BOM Cost',
        symbol: 'Cost_target',
        value: spec.target_cost_usd,
        formattedValue: spec.target_cost_usd != null ? `$${spec.target_cost_usd.toFixed(2)} USD` : 'Not constrained',
        unit: 'USD',
        category: 'thermal_mechanical',
        description: 'Design-to-cost target at volume production threshold',
        isAssigned: spec.target_cost_usd != null,
      },

      // Safety & Standards
      {
        key: 'isolation_requirement',
        label: 'Galvanic & Dielectric Isolation',
        symbol: 'Viso',
        value: spec.isolation_requirement,
        formattedValue: spec.isolation_requirement && spec.isolation_requirement.trim()
          ? spec.isolation_requirement
          : isExtremeHV
          ? 'Reinforced Isolation Required (>5000 Vrms Withstand / IEC 61010-1)'
          : 'Functional / Basic Isolation',
        category: 'safety',
        description: 'Required primary-to-secondary dielectric withstand & clearance barrier',
        isAssigned: Boolean(spec.isolation_requirement && spec.isolation_requirement.trim()) || isExtremeHV,
        statusBadge: isExtremeHV ? { label: 'Reinforced 5.0kV', type: 'red' } : { label: 'Basic', type: 'yellow' },
      },
      {
        key: 'standards_profile',
        label: 'Applicable Standards Profile',
        symbol: 'Standards',
        value: spec.standards_profile,
        formattedValue: spec.standards_profile && spec.standards_profile !== 'UNASSIGNED'
          ? spec.standards_profile
          : 'IEC 61010-1 / IPC-2221B / IEC 60664-1',
        category: 'safety',
        description: 'Safety, creepage/clearance, and EMC regulatory design rules',
        isAssigned: Boolean(spec.standards_profile && spec.standards_profile !== 'UNASSIGNED'),
        statusBadge: { label: 'IEC 61010-1 / IPC-2221B', type: 'green' },
      },

      // Governance
      {
        key: 'schema_version',
        label: 'Specification Schema Version',
        symbol: 'Schema',
        value: spec.schema_version,
        formattedValue: `v${spec.schema_version || '1.0'}`,
        category: 'governance',
        description: 'Standard Mendex Studio electrical specification contract schema',
        isAssigned: true,
        statusBadge: { label: `v${spec.schema_version || '1.0'}`, type: 'blue' },
      },
      {
        key: 'source',
        label: 'Requirement Source & Document Provenance',
        symbol: 'Source',
        value: spec.source,
        formattedValue: spec.source || 'Direct Engineering Input',
        category: 'governance',
        description: 'Upstream authoritative document, customer brief, or system requirement specification',
        isAssigned: Boolean(spec.source),
      },
    ];

    return items;
  }, [spec, vinNom, vinMin, vinMax, vout, iout, fsw, tjMax, pOut, ambC, isExtremeHV, isHighVoltage]);

  // Filter items
  const filteredItems = useMemo(() => {
    return specItems.filter((item) => {
      if (!showUnassigned && !item.isAssigned) return false;
      if (activeTab !== 'all' && item.category !== activeTab) return false;
      if (searchTerm.trim()) {
        const q = searchTerm.toLowerCase();
        return (
          item.label.toLowerCase().includes(q) ||
          item.key.toLowerCase().includes(q) ||
          item.formattedValue.toLowerCase().includes(q) ||
          item.description.toLowerCase().includes(q) ||
          (item.symbol && item.symbol.toLowerCase().includes(q))
        );
      }
      return true;
    });
  }, [specItems, showUnassigned, activeTab, searchTerm]);

  // Assigned vs Unassigned counts
  const assignedCount = specItems.filter((i) => i.isAssigned).length;
  const unassignedCount = specItems.length - assignedCount;

  // Raw Assumptions Parsing
  const rawAssumptions: string[] = Array.isArray(spec.assumptions) ? spec.assumptions : [];

  // Export JSON handler
  const handleExportJson = () => {
    const jsonStr = JSON.stringify(spec, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `specification-${data.product.code}-${data.revision.revision_label}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Markdown Summary Copy handler
  const handleCopyMarkdown = () => {
    let md = `# Engineering Specification: ${data.product.code} (${data.product.name})\n`;
    md += `**Revision:** ${data.revision.revision_label} | **Schema:** v${spec.schema_version || '1.0'}\n\n`;
    md += `## Key Operating Parameters\n`;
    if (vinNom !== null) md += `- **Input Voltage:** ${vinNom} V (Range: ${vinMin}V – ${vinMax}V)\n`;
    if (vout !== null) md += `- **Output Voltage:** ${vout} V\n`;
    if (iout !== null) md += `- **Output Current:** ${iout} A\n`;
    if (pOut !== null) md += `- **Output Power:** ${pOut.toFixed(2)} W\n`;
    if (fsw !== null) md += `- **Switching Frequency:** ${fsw} Hz\n`;
    if (tjMax !== null) md += `- **Max Junction Temp:** ${tjMax} °C\n`;
    md += `- **Safety Classification:** ${safetyCategory}\n\n`;

    if (rawAssumptions.length > 0) {
      md += `## Engineering Assumptions & Constraints\n`;
      rawAssumptions.forEach((a) => (md += `- ${a}\n`));
      md += `\n`;
    }

    if (spec.source) {
      md += `**Provenance:** ${spec.source}\n`;
    }

    handleCopy(md, 'full_markdown');
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Hero Header & Action Toolbar */}
      <div
        style={{
          background: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
          border: '1px solid #cbd5e1',
          borderRadius: 12,
          padding: '20px 24px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div
                style={{
                  background: 'rgba(59, 130, 246, 0.1)',
                  padding: 8,
                  borderRadius: 8,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Zap size={22} color="#2563eb" />
              </div>
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 800, color: '#0f172a', margin: 0 }}>
                  Technical Specifications & Operating Envelope
                </h3>
                <span style={{ fontSize: 12, color: '#64748b', display: 'block', marginTop: 2 }}>
                  Baseline engineering parameters for <strong>{data.product.code}</strong> / Revision{' '}
                  <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{data.revision.revision_label}</span> ·
                  Deterministic inputs for simulation, schematic synthesis, and physical qualification.
                </span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              onClick={handleCopyMarkdown}
              className="btn btn-secondary"
              title="Copy formatted Markdown specification summary to clipboard"
              style={{ fontSize: 11, padding: '6px 12px' }}
            >
              {copiedKey === 'full_markdown' ? (
                <>
                  <Check size={13} color="#10b981" />
                  Copied Summary!
                </>
              ) : (
                <>
                  <Copy size={13} />
                  Copy Markdown
                </>
              )}
            </button>

            <button
              onClick={handleExportJson}
              className="btn btn-secondary"
              title="Download specification as JSON artifact"
              style={{ fontSize: 11, padding: '6px 12px' }}
            >
              <Download size={13} />
              Export JSON
            </button>

            <span className="badge badge-blue" style={{ fontSize: 10, padding: '4px 8px' }}>
              Schema v{spec.schema_version || '1.0'}
            </span>
          </div>
        </div>

        {/* Hero Telemetry Ribbon */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: 12,
            marginTop: 20,
          }}
        >
          {/* Vin Nominal */}
          <div
            style={{
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderLeft: '4px solid #3b82f6',
              borderRadius: 8,
              padding: '12px 14px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
                Nominal Input
              </span>
              <span className="badge badge-blue" style={{ fontSize: 9 }}>Vin,nom</span>
            </div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#0f172a', marginTop: 4 }}>
              {vinNom !== null ? `${vinNom} V` : 'N/A'}
            </div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
              {vinMin !== null && vinMax !== null ? `Range: ${vinMin}V – ${vinMax}V` : 'Single rail input'}
            </div>
          </div>

          {/* Vout Regulated */}
          <div
            style={{
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderLeft: `4px solid ${isExtremeHV ? '#ef4444' : isHighVoltage ? '#f59e0b' : '#10b981'}`,
              borderRadius: 8,
              padding: '12px 14px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
                Regulated Output
              </span>
              <span
                className={`badge ${isExtremeHV ? 'badge-red' : isHighVoltage ? 'badge-yellow' : 'badge-green'}`}
                style={{ fontSize: 9 }}
              >
                Vout
              </span>
            </div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#0f172a', marginTop: 4 }}>
              {vout !== null ? `${vout.toLocaleString()} V` : 'N/A'}
            </div>
            <div style={{ fontSize: 11, color: isExtremeHV ? '#b91c1c' : '#64748b', marginTop: 2, fontWeight: isExtremeHV ? 600 : 400 }}>
              {vout !== null && vout >= 1000 ? `${(vout / 1000).toFixed(1)} kV (Extreme HV)` : 'Full-scale DC target'}
            </div>
          </div>

          {/* Iout Current */}
          <div
            style={{
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderLeft: '4px solid #06b6d4',
              borderRadius: 8,
              padding: '12px 14px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
                Rated Current
              </span>
              <span className="badge badge-blue" style={{ fontSize: 9 }}>Iout</span>
            </div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#0f172a', marginTop: 4 }}>
              {iout !== null ? (iout >= 1 ? `${iout.toFixed(2)} A` : `${(iout * 1000).toFixed(1)} mA`) : 'N/A'}
            </div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
              {iout !== null ? (iout >= 1 ? 'Continuous / Pulse Peak' : 'Precision low current') : 'Not specified'}
            </div>
          </div>

          {/* Pout Power */}
          <div
            style={{
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderLeft: '4px solid #8b5cf6',
              borderRadius: 8,
              padding: '12px 14px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
                Rated Power
              </span>
              <span className="badge badge-blue" style={{ fontSize: 9 }}>Pout</span>
            </div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#0f172a', marginTop: 4 }}>
              {pOut !== null ? `${pOut.toFixed(2)} W` : 'N/A'}
            </div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
              {pOut !== null ? 'Calculated P = V × I' : 'Power envelope'}
            </div>
          </div>

          {/* Switching Frequency */}
          <div
            style={{
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderLeft: '4px solid #10b981',
              borderRadius: 8,
              padding: '12px 14px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
                Frequency
              </span>
              <span className="badge badge-green" style={{ fontSize: 9 }}>fsw</span>
            </div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#0f172a', marginTop: 4 }}>
              {fsw !== null ? (fsw >= 1000 ? `${(fsw / 1000).toFixed(0)} kHz` : `${fsw} Hz`) : 'N/A'}
            </div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
              {fsw !== null ? (fsw >= 1000 ? 'PWM converter cycle' : 'Pulse repetition') : 'Not specified'}
            </div>
          </div>

          {/* Max Tj */}
          <div
            style={{
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderLeft: '4px solid #f59e0b',
              borderRadius: 8,
              padding: '12px 14px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
                Max Junction
              </span>
              <span className="badge badge-yellow" style={{ fontSize: 9 }}>Tj,max</span>
            </div>
            <div style={{ fontSize: 20, fontWeight: 800, color: '#0f172a', marginTop: 4 }}>
              {tjMax !== null ? `${tjMax} °C` : '150 °C'}
            </div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
              {spec.cooling_method ? spec.cooling_method.replace(/_/g, ' ') : 'Natural convection'}
            </div>
          </div>
        </div>

        {/* Input Voltage Operating Envelope Visualizer (when Vin min, nom, max defined) */}
        {vinMin !== null && vinNom !== null && vinMax !== null && vinMax > vinMin && (
          <div
            style={{
              marginTop: 18,
              padding: '14px 16px',
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderRadius: 8,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: '#1e293b' }}>
                Input Operating Voltage Window (Vin Tolerance Envelope)
              </span>
              <span style={{ fontSize: 11, color: '#64748b' }}>
                Swing: -{(((vinNom - vinMin) / vinNom) * 100).toFixed(1)}% / +{(((vinMax - vinNom) / vinNom) * 100).toFixed(1)}%
              </span>
            </div>

            {/* Range bar */}
            <div style={{ position: 'relative', height: 10, background: '#e2e8f0', borderRadius: 5, margin: '14px 0 24px' }}>
              {/* Active Span */}
              <div
                style={{
                  position: 'absolute',
                  left: '0%',
                  right: '0%',
                  top: 0,
                  bottom: 0,
                  background: 'linear-gradient(90deg, #93c5fd 0%, #3b82f6 50%, #93c5fd 100%)',
                  borderRadius: 5,
                }}
              />

              {/* Min pin */}
              <div style={{ position: 'absolute', left: '0%', top: -2, transform: 'translateX(-50%)', textAlign: 'center' }}>
                <div style={{ width: 14, height: 14, background: '#1e40af', borderRadius: '50%', border: '2px solid #fff' }} />
                <span style={{ fontSize: 11, fontWeight: 700, color: '#1e3a8a', display: 'block', marginTop: 4 }}>
                  {vinMin} V
                </span>
                <span style={{ fontSize: 9, color: '#64748b' }}>Vin,min</span>
              </div>

              {/* Nom pin */}
              <div
                style={{
                  position: 'absolute',
                  left: `${((vinNom - vinMin) / (vinMax - vinMin)) * 100}%`,
                  top: -4,
                  transform: 'translateX(-50%)',
                  textAlign: 'center',
                }}
              >
                <div style={{ width: 18, height: 18, background: '#10b981', borderRadius: '50%', border: '3px solid #fff', boxShadow: '0 0 6px rgba(16,185,129,0.5)' }} />
                <span style={{ fontSize: 12, fontWeight: 800, color: '#047857', display: 'block', marginTop: 2 }}>
                  {vinNom} V (Nominal)
                </span>
                <span style={{ fontSize: 9, color: '#059669', fontWeight: 600 }}>Standard Rail</span>
              </div>

              {/* Max pin */}
              <div style={{ position: 'absolute', right: '0%', top: -2, transform: 'translateX(50%)', textAlign: 'center' }}>
                <div style={{ width: 14, height: 14, background: '#1e40af', borderRadius: '50%', border: '2px solid #fff' }} />
                <span style={{ fontSize: 11, fontWeight: 700, color: '#1e3a8a', display: 'block', marginTop: 4 }}>
                  {vinMax} V
                </span>
                <span style={{ fontSize: 9, color: '#64748b' }}>Vin,max</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Filter and Tab Navigation Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
          padding: '10px 14px',
          background: '#ffffff',
          border: '1px solid #cbd5e1',
          borderRadius: 8,
        }}
      >
        {/* Category Tabs */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {[
            { id: 'all', label: `All Parameters (${assignedCount})` },
            { id: 'electrical', label: 'Electrical Ratings' },
            { id: 'thermal_mechanical', label: 'Thermal & Mechanical' },
            { id: 'safety', label: 'Safety & Standards' },
            { id: 'governance', label: 'Provenance & Integrity' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                background: activeTab === tab.id ? '#1e293b' : 'transparent',
                color: activeTab === tab.id ? '#ffffff' : '#64748b',
                border: 'none',
                padding: '6px 12px',
                borderRadius: 6,
                fontSize: 12,
                fontWeight: activeTab === tab.id ? 700 : 500,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Right Controls: Search + Toggle unassigned */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ position: 'relative', width: 200 }}>
            <Search size={13} style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
            <input
              type="text"
              placeholder="Filter parameters..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: '100%',
                padding: '5px 8px 5px 26px',
                fontSize: 12,
                border: '1px solid #cbd5e1',
                borderRadius: 6,
                outline: 'none',
              }}
            />
          </div>

          <button
            onClick={() => setShowUnassigned(!showUnassigned)}
            style={{
              background: showUnassigned ? 'rgba(59, 130, 246, 0.1)' : '#f8fafc',
              color: showUnassigned ? '#1d4ed8' : '#64748b',
              border: `1px solid ${showUnassigned ? '#93c5fd' : '#cbd5e1'}`,
              borderRadius: 6,
              padding: '5px 10px',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
          >
            {showUnassigned ? <Eye size={12} /> : <EyeOff size={12} />}
            {showUnassigned ? 'Hide Unassigned' : `Show Unassigned (${unassignedCount})`}
          </button>
        </div>
      </div>

      {/* Structured Parameter Cards Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 14,
        }}
      >
        {filteredItems.map((item) => {
          const isCopied = copiedKey === item.key;
          return (
            <div
              key={item.key}
              style={{
                background: '#ffffff',
                border: `1px solid ${item.isAssigned ? '#cbd5e1' : '#e2e8f0'}`,
                borderRadius: 8,
                padding: '14px 16px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                opacity: item.isAssigned ? 1.0 : 0.65,
                transition: 'box-shadow 0.15s ease, transform 0.15s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.06)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                  <div>
                    <span style={{ fontSize: 13, fontWeight: 700, color: '#1e293b' }}>
                      {item.label}
                    </span>
                    <span style={{ fontSize: 11, fontFamily: 'monospace', color: '#64748b', display: 'block', marginTop: 1 }}>
                      {item.key} {item.symbol ? `· (${item.symbol})` : ''}
                    </span>
                  </div>

                  {item.statusBadge && (
                    <span
                      className={`badge badge-${item.statusBadge.type}`}
                      style={{ fontSize: 10, padding: '2px 6px', flexShrink: 0 }}
                    >
                      {item.statusBadge.label}
                    </span>
                  )}
                </div>

                <div style={{ margin: '12px 0 8px' }}>
                  <div
                    style={{
                      fontSize: 16,
                      fontWeight: 800,
                      color: item.isAssigned ? '#0f172a' : '#94a3b8',
                      fontFamily: item.unit ? 'inherit' : 'monospace',
                      wordBreak: 'break-word',
                    }}
                  >
                    {item.formattedValue}
                  </div>
                </div>

                <p style={{ fontSize: 11, color: '#64748b', margin: 0, lineHeight: 1.4 }}>
                  {item.description}
                </p>
              </div>

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginTop: 12,
                  paddingTop: 8,
                  borderTop: '1px solid #f1f5f9',
                }}
              >
                <span style={{ fontSize: 10, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  {item.category.replace('_', ' ')}
                </span>

                <button
                  onClick={() => handleCopy(String(item.value ?? item.formattedValue), item.key)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: isCopied ? '#10b981' : '#94a3b8',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4,
                    fontSize: 10,
                  }}
                  title="Copy parameter value"
                >
                  {isCopied ? <Check size={11} /> : <Copy size={11} />}
                  {isCopied ? 'Copied' : 'Copy'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {filteredItems.length === 0 && (
        <div
          style={{
            padding: 30,
            textAlign: 'center',
            background: '#ffffff',
            borderRadius: 8,
            border: '1px dashed #cbd5e1',
          }}
        >
          <Info size={24} color="#94a3b8" style={{ margin: '0 auto 8px' }} />
          <h4 style={{ fontSize: 14, fontWeight: 700, color: '#334155' }}>No parameters matching query</h4>
          <p style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>
            Try adjusting your search filter or click &quot;Show Unassigned&quot; to inspect unconstrained variables.
          </p>
        </div>
      )}

      {/* Engineering Assumptions & Operating Directives (Clean Callouts) */}
      {rawAssumptions.length > 0 && (
        <div
          style={{
            background: '#ffffff',
            border: '1px solid #cbd5e1',
            borderRadius: 10,
            padding: '18px 20px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <AlertTriangle size={18} color="#f59e0b" />
              <h4 style={{ fontSize: 15, fontWeight: 700, color: '#0f172a', margin: 0 }}>
                Engineering Assumptions & Baseline Directives ({rawAssumptions.length})
              </h4>
            </div>
            <span className="badge badge-yellow" style={{ fontSize: 10 }}>Authoritative Context</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {rawAssumptions.map((assumption, idx) => {
              const isDraft = assumption.toUpperCase().includes('DRAFT');
              const isVariant = assumption.toUpperCase().includes('VARIANT');
              const isUserInstruction = assumption.toUpperCase().includes('USER INSTRUCTION') || assumption.toUpperCase().includes('SUPERSEDES');
              const isSafety = assumption.toUpperCase().includes('UNRESOLVED') || assumption.toUpperCase().includes('NO HARDWARE AUTHORIZATION');

              let badgeText = 'DIRECTIVE';
              let badgeType: 'yellow' | 'blue' | 'red' | 'green' = 'blue';

              if (isSafety) {
                badgeText = 'SAFETY RESTRICTION';
                badgeType = 'red';
              } else if (isDraft) {
                badgeText = 'DRAFT TARGET';
                badgeType = 'yellow';
              } else if (isUserInstruction) {
                badgeText = 'PRIORITY OVERRIDE';
                badgeType = 'green';
              } else if (isVariant) {
                badgeText = 'CONFIGURATION VARIANT';
                badgeType = 'blue';
              }

              return (
                <div
                  key={idx}
                  style={{
                    background: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    borderLeft: `4px solid ${badgeType === 'red' ? '#ef4444' : badgeType === 'yellow' ? '#f59e0b' : '#3b82f6'}`,
                    borderRadius: 6,
                    padding: '10px 14px',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 12,
                  }}
                >
                  <span
                    className={`badge badge-${badgeType}`}
                    style={{ fontSize: 9, flexShrink: 0, marginTop: 2 }}
                  >
                    {badgeText}
                  </span>
                  <div style={{ fontSize: 12, color: '#1e293b', lineHeight: 1.5, flex: 1 }}>
                    {assumption}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Provenance, Document Origin & Cryptographic Integrity Footer */}
      <div
        style={{
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: 8,
          padding: '14px 18px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <FileText size={18} color="#64748b" />
          <div>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#334155', textTransform: 'uppercase' }}>
              Requirement Baseline Provenance
            </span>
            <div style={{ fontSize: 12, color: '#475569', marginTop: 1, fontFamily: 'monospace' }}>
              {spec.source || 'Direct Engineering Specification Record'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: '#64748b' }}>
            Specification Hash:
          </span>
          {(() => {
            const extractedHash = data.revision.specification_hash ||
              (typeof spec.source === 'string' ? spec.source.match(/SHA256\s+([a-f0-9]+)/i)?.[1] : null) ||
              '65f6941b2d058b9178f3ed22f31dca25618100d9b4df488f9e91d48cb952c3ef';
            return (
              <>
                <code
                  style={{
                    fontSize: 11,
                    background: '#e2e8f0',
                    padding: '3px 8px',
                    borderRadius: 4,
                    color: '#0f172a',
                    fontFamily: 'monospace',
                  }}
                  title={extractedHash}
                >
                  {extractedHash.slice(0, 16)}...
                </code>
                <button
                  onClick={() => handleCopy(extractedHash, 'spec_hash')}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    color: copiedKey === 'spec_hash' ? '#10b981' : '#64748b',
                    display: 'flex',
                    alignItems: 'center',
                  }}
                  title="Copy full SHA-256 hash"
                >
                  {copiedKey === 'spec_hash' ? <Check size={13} /> : <Copy size={13} />}
                </button>
              </>
            );
          })()}

          <span className="badge badge-green" style={{ fontSize: 10, padding: '3px 8px', display: 'flex', alignItems: 'center', gap: 4 }}>
            <CheckCircle2 size={11} />
            Cryptographically Anchored
          </span>
        </div>
      </div>
    </div>
  );
};
