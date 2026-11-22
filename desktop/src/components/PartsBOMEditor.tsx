import React, { useState } from 'react';

interface Dimension {
  name: string;
  nominal_m: number | null;
  minimum_m: number | null;
  maximum_m: number | null;
  source: string;
}

interface Part {
  reference: string;
  description: string;
  quantity: number;
  material_requirement: string;
  source: string;
  notes: string;
  cad_relative_path: string | null;
  dimensions: Dimension[];
  [key: string]: any;
}

interface PartsBOMEditorProps {
  parts: Part[];
  update: (patch: { parts: Part[] }) => void;
  editable: boolean;
  steps: Array<{ relative_path: string }>;
  open: (path: string) => void;
  busy: boolean;
}

export function PartsBOMEditor({
  parts,
  update,
  editable,
  steps,
  open,
  busy,
}: PartsBOMEditorProps) {
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<Record<number, boolean>>(() => {
    // Expand the first two parts by default, others collapsed for a clean view
    const initial: Record<number, boolean> = {};
    parts.forEach((_, i) => {
      initial[i] = i < 3;
    });
    return initial;
  });

  const toggleExpand = (idx: number) => {
    setExpanded(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const expandAll = () => {
    const all: Record<number, boolean> = {};
    parts.forEach((_, i) => {
      all[i] = true;
    });
    setExpanded(all);
  };

  const collapseAll = () => {
    setExpanded({});
  };

  const handlePartFieldChange = (partIndex: number, field: string, value: any) => {
    const updated = parts.map((p, idx) => {
      if (idx !== partIndex) return p;
      return {
        ...p,
        [field]: field === 'quantity' ? (value === '' ? 1 : Number(value)) : value,
      };
    });
    update({ parts: updated });
  };

  const handleDimensionFieldChange = (
    partIndex: number,
    dimIndex: number,
    field: string,
    value: string
  ) => {
    const updated = parts.map((p, pIdx) => {
      if (pIdx !== partIndex) return p;
      const dims = (p.dimensions || []).map((d, dIdx) => {
        if (dIdx !== dimIndex) return d;
        if (field.endsWith('_m')) {
          const numVal = value === '' ? null : Number(value) / 1000;
          return { ...d, [field]: numVal };
        }
        return { ...d, [field]: value };
      });
      return { ...p, dimensions: dims };
    });
    update({ parts: updated });
  };

  const addDimension = (partIndex: number) => {
    const updated = parts.map((p, idx) => {
      if (idx !== partIndex) return p;
      return {
        ...p,
        dimensions: [
          ...(p.dimensions || []),
          {
            name: '',
            nominal_m: null,
            minimum_m: null,
            maximum_m: null,
            source: p.source || '',
          },
        ],
      };
    });
    // Ensure expanded
    setExpanded(prev => ({ ...prev, [partIndex]: true }));
    update({ parts: updated });
  };

  const removeDimension = (partIndex: number, dimIndex: number) => {
    const updated = parts.map((p, pIdx) => {
      if (pIdx !== partIndex) return p;
      return {
        ...p,
        dimensions: (p.dimensions || []).filter((_, dIdx) => dIdx !== dimIndex),
      };
    });
    update({ parts: updated });
  };

  const addPart = () => {
    const newIndex = parts.length;
    const newPart: Part = {
      reference: `PART_${newIndex + 1}`,
      description: '',
      quantity: 1,
      material_requirement: '',
      source: '',
      notes: '',
      cad_relative_path: null,
      dimensions: [],
    };
    update({ parts: [...parts, newPart] });
    setExpanded(prev => ({ ...prev, [newIndex]: true }));
  };

  const removePart = (partIndex: number) => {
    if (!window.confirm(`Are you sure you want to remove part ${parts[partIndex]?.reference || partIndex + 1}?`)) {
      return;
    }
    const updated = parts.filter((_, idx) => idx !== partIndex);
    update({ parts: updated });
  };

  // Filtered parts based on search
  const filteredIndices = parts
    .map((p, idx) => ({ p, idx }))
    .filter(({ p }) => {
      if (!search.trim()) return true;
      const q = search.toLowerCase();
      return (
        p.reference.toLowerCase().includes(q) ||
        p.description.toLowerCase().includes(q) ||
        p.material_requirement.toLowerCase().includes(q) ||
        p.notes.toLowerCase().includes(q)
      );
    });

  // Calculate summary metrics
  const totalParts = parts.length;
  const totalQuantity = parts.reduce((sum, p) => sum + (p.quantity || 0), 0);
  const totalDimensions = parts.reduce((sum, p) => sum + (p.dimensions?.length || 0), 0);
  const totalLinkedCAD = parts.filter(p => !!p.cad_relative_path).length;

  const calculateToleranceBadge = (d: Dimension) => {
    if (d.nominal_m == null) return null;
    const nom = d.nominal_m * 1000;
    const min = d.minimum_m != null ? d.minimum_m * 1000 : null;
    const max = d.maximum_m != null ? d.maximum_m * 1000 : null;

    if (min != null && max != null) {
      const lower = Number((nom - min).toFixed(3));
      const upper = Number((max - nom).toFixed(3));
      if (Math.abs(lower - upper) < 0.001) {
        return `± ${upper} mm`;
      }
      return `-${lower} / +${upper} mm`;
    }
    if (min != null) return `≥ ${min} mm`;
    if (max != null) return `≤ ${max} mm`;
    return 'Nominal only';
  };

  return (
    <section
      style={{
        background: '#ffffff',
        border: '1px solid #dce3ed',
        borderRadius: 10,
        padding: 20,
        boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 12,
          borderBottom: '1px solid #e2e8f0',
          paddingBottom: 16,
          marginBottom: 16,
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <h3 style={{ margin: 0, fontSize: 18, color: '#0f172a', fontWeight: 700 }}>
              Parts &amp; Supply Bill of Materials (BOM)
            </h3>
            <span
              style={{
                background: '#e0f2fe',
                color: '#0369a1',
                fontSize: 11,
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 12,
              }}
            >
              {totalParts} Sourced Items
            </span>
          </div>
          <p style={{ margin: '4px 0 0', fontSize: 13, color: '#64748b' }}>
            Sourced components, raw material specifications, drawing tolerances, and native 3D CAD STEP links.
          </p>
        </div>

        {/* Quick summary stats */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <span
            style={{
              background: '#f8fafc',
              border: '1px solid #cbd5e1',
              padding: '4px 10px',
              borderRadius: 6,
              fontSize: 12,
              color: '#334155',
            }}
          >
            📦 <strong>{totalQuantity}</strong> Total Hardware Count
          </span>
          <span
            style={{
              background: '#f8fafc',
              border: '1px solid #cbd5e1',
              padding: '4px 10px',
              borderRadius: 6,
              fontSize: 12,
              color: '#334155',
            }}
          >
            📐 <strong>{totalDimensions}</strong> Dimensions Sourced
          </span>
          <span
            style={{
              background: '#f8fafc',
              border: '1px solid #cbd5e1',
              padding: '4px 10px',
              borderRadius: 6,
              fontSize: 12,
              color: '#334155',
            }}
          >
            🔗 <strong>{totalLinkedCAD}</strong> CAD STEP Linked
          </span>
        </div>
      </div>

      {/* Filter and control actions */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 10,
          marginBottom: 16,
        }}
      >
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flex: '1 1 280px', maxWidth: 420 }}>
          <input
            type="search"
            placeholder="🔍 Filter parts by reference, description, or material..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '7px 12px',
              border: '1px solid #cbd5e1',
              borderRadius: 6,
              fontSize: 12,
              color: '#1e293b',
              background: '#ffffff',
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={expandAll}
            style={{ fontSize: 11, padding: '5px 10px' }}
          >
            Expand All
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={collapseAll}
            style={{ fontSize: 11, padding: '5px 10px' }}
          >
            Collapse All
          </button>
          {editable && (
            <button
              type="button"
              className="btn btn-primary"
              onClick={addPart}
              style={{ fontSize: 12, padding: '6px 14px', fontWeight: 600 }}
            >
              + Add Sourced Part
            </button>
          )}
        </div>
      </div>

      {/* Parts List */}
      <div style={{ display: 'grid', gap: 12 }}>
        {!filteredIndices.length && (
          <div
            style={{
              padding: 32,
              textAlign: 'center',
              background: '#f8fafc',
              border: '1px dashed #cbd5e1',
              borderRadius: 8,
              color: '#64748b',
              fontSize: 13,
            }}
          >
            No parts matching "{search}".
          </div>
        )}

        {filteredIndices.map(({ p, idx: originalIndex }) => {
          const isExpanded = !!expanded[originalIndex];
          const hasCAD = !!p.cad_relative_path;

          return (
            <article
              key={originalIndex}
              style={{
                border: isExpanded ? '1.5px solid #94a3b8' : '1px solid #e2e8f0',
                borderRadius: 8,
                background: '#ffffff',
                boxShadow: isExpanded ? '0 4px 6px -1px rgba(0,0,0,0.05)' : 'none',
                transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
                overflow: 'hidden',
              }}
            >
              {/* Card Header (clickable to expand/collapse) */}
              <header
                onClick={() => toggleExpand(originalIndex)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 14px',
                  background: isExpanded ? '#f8fafc' : '#ffffff',
                  borderBottom: isExpanded ? '1px solid #e2e8f0' : 'none',
                  cursor: 'pointer',
                  userSelect: 'none',
                  gap: 12,
                  flexWrap: 'wrap',
                }}
              >
                {/* Left group */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                  <span
                    style={{
                      fontSize: 12,
                      color: '#64748b',
                      transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                      transition: 'transform 0.15s ease',
                      display: 'inline-block',
                    }}
                  >
                    ▶
                  </span>

                  {/* Reference Tag */}
                  <span
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontWeight: 700,
                      fontSize: 12,
                      color: '#ffffff',
                      background: '#0f766e',
                      padding: '3px 8px',
                      borderRadius: 4,
                      letterSpacing: '0.5px',
                    }}
                  >
                    {p.reference || `PART_${originalIndex + 1}`}
                  </span>

                  {/* Description */}
                  <strong style={{ fontSize: 14, color: '#0f172a' }}>
                    {p.description || 'Untitled Component'}
                  </strong>

                  {/* Quantity Badge */}
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: '#0369a1',
                      background: '#f0f9ff',
                      border: '1px solid #bae6fd',
                      padding: '2px 8px',
                      borderRadius: 12,
                    }}
                  >
                    Qty: {p.quantity}
                  </span>

                  {/* Material Tag */}
                  {p.material_requirement && (
                    <span
                      style={{
                        fontSize: 11,
                        color: '#475569',
                        background: '#f1f5f9',
                        border: '1px solid #e2e8f0',
                        padding: '2px 8px',
                        borderRadius: 4,
                        maxWidth: 240,
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                      title={p.material_requirement}
                    >
                      🧪 {p.material_requirement}
                    </span>
                  )}

                  {/* Linked CAD Tag */}
                  {hasCAD ? (
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        color: '#059669',
                        background: '#ecfdf5',
                        border: '1px solid #a7f3d0',
                        padding: '2px 8px',
                        borderRadius: 4,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4,
                      }}
                    >
                      📦 {p.cad_relative_path?.split('/').pop()}
                    </span>
                  ) : (
                    <span
                      style={{
                        fontSize: 11,
                        color: '#94a3b8',
                        background: '#f8fafc',
                        border: '1px dashed #cbd5e1',
                        padding: '2px 6px',
                        borderRadius: 4,
                      }}
                    >
                      No CAD linked
                    </span>
                  )}
                </div>

                {/* Right group */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 12, color: '#64748b' }}>
                    📐 {p.dimensions?.length || 0} dimensions
                  </span>

                  {hasCAD && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ fontSize: 11, padding: '3px 8px' }}
                      disabled={busy}
                      onClick={e => {
                        e.stopPropagation();
                        open(p.cad_relative_path!);
                      }}
                      title="Open 3D STEP part in FreeCAD"
                    >
                      Open CAD
                    </button>
                  )}

                  {editable && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{
                        fontSize: 11,
                        padding: '3px 8px',
                        color: '#b91c1c',
                        borderColor: '#fca5a5',
                      }}
                      onClick={e => {
                        e.stopPropagation();
                        removePart(originalIndex);
                      }}
                      title="Delete part from BOM"
                    >
                      🗑️
                    </button>
                  )}
                </div>
              </header>

              {/* Card Body (Visible when expanded) */}
              {isExpanded && (
                <div style={{ padding: 16 }}>
                  {/* General Part Attributes Grid */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                      gap: 12,
                      marginBottom: 16,
                      background: '#f8fafc',
                      padding: 14,
                      borderRadius: 8,
                      border: '1px solid #e2e8f0',
                    }}
                  >
                    <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 700, color: '#475569', marginBottom: 4 }}>
                        REFERENCE CODE *
                      </label>
                      <input
                        aria-label={`Part ${originalIndex + 1} reference`}
                        required
                        disabled={!editable}
                        type="text"
                        value={p.reference}
                        onChange={e => handlePartFieldChange(originalIndex, 'reference', e.target.value)}
                        placeholder="e.g. BASE, LIMB, CORE"
                        style={{
                          width: '100%',
                          padding: '6px 10px',
                          border: '1px solid #cbd5e1',
                          borderRadius: 4,
                          fontSize: 13,
                          fontFamily: 'JetBrains Mono, monospace',
                          color: '#0f172a',
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 700, color: '#475569', marginBottom: 4 }}>
                        DESCRIPTION *
                      </label>
                      <input
                        aria-label={`Part ${originalIndex + 1} description`}
                        required
                        disabled={!editable}
                        type="text"
                        value={p.description}
                        onChange={e => handlePartFieldChange(originalIndex, 'description', e.target.value)}
                        placeholder="e.g. PTFE cylindrical limb"
                        style={{
                          width: '100%',
                          padding: '6px 10px',
                          border: '1px solid #cbd5e1',
                          borderRadius: 4,
                          fontSize: 13,
                          color: '#0f172a',
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 700, color: '#475569', marginBottom: 4 }}>
                        QUANTITY *
                      </label>
                      <input
                        aria-label={`Part ${originalIndex + 1} quantity`}
                        required
                        disabled={!editable}
                        type="number"
                        min="1"
                        step="1"
                        value={p.quantity}
                        onChange={e => handlePartFieldChange(originalIndex, 'quantity', e.target.value)}
                        style={{
                          width: '100%',
                          padding: '6px 10px',
                          border: '1px solid #cbd5e1',
                          borderRadius: 4,
                          fontSize: 13,
                          color: '#0f172a',
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 700, color: '#475569', marginBottom: 4 }}>
                        MATERIAL REQUIREMENT
                      </label>
                      <input
                        aria-label={`Part ${originalIndex + 1} material_requirement`}
                        disabled={!editable}
                        type="text"
                        value={p.material_requirement}
                        onChange={e => handlePartFieldChange(originalIndex, 'material_requirement', e.target.value)}
                        placeholder="e.g. PTFE, Ferroxcube 3F4, 304 SS"
                        style={{
                          width: '100%',
                          padding: '6px 10px',
                          border: '1px solid #cbd5e1',
                          borderRadius: 4,
                          fontSize: 13,
                          color: '#0f172a',
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 700, color: '#475569', marginBottom: 4 }}>
                        SOURCE DOCUMENT / CALLOUT *
                      </label>
                      <input
                        aria-label={`Part ${originalIndex + 1} source`}
                        required
                        disabled={!editable}
                        type="text"
                        value={p.source}
                        onChange={e => handlePartFieldChange(originalIndex, 'source', e.target.value)}
                        placeholder="e.g. HFT-000 BOM item 1; HFT-01 PDF"
                        style={{
                          width: '100%',
                          padding: '6px 10px',
                          border: '1px solid #cbd5e1',
                          borderRadius: 4,
                          fontSize: 13,
                          color: '#0f172a',
                        }}
                      />
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 700, color: '#475569', marginBottom: 4 }}>
                        ENGINEERING NOTES
                      </label>
                      <input
                        aria-label={`Part ${originalIndex + 1} notes`}
                        disabled={!editable}
                        type="text"
                        value={p.notes}
                        onChange={e => handlePartFieldChange(originalIndex, 'notes', e.target.value)}
                        placeholder="e.g. 530 x 357 x 20 mm; counterbored for M8"
                        style={{
                          width: '100%',
                          padding: '6px 10px',
                          border: '1px solid #cbd5e1',
                          borderRadius: 4,
                          fontSize: 13,
                          color: '#0f172a',
                        }}
                      />
                    </div>

                    <div style={{ gridColumn: '1 / -1' }}>
                      <label style={{ display: 'block', fontSize: 11, fontWeight: 700, color: '#475569', marginBottom: 4 }}>
                        LINKED NATIVE CAD MODEL (STEP / FCSTD)
                      </label>
                      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                        <select
                          disabled={!editable}
                          value={p.cad_relative_path || ''}
                          onChange={e => handlePartFieldChange(originalIndex, 'cad_relative_path', e.target.value || null)}
                          style={{
                            flex: 1,
                            padding: '6px 10px',
                            border: '1px solid #cbd5e1',
                            borderRadius: 4,
                            fontSize: 13,
                            color: '#0f172a',
                            background: '#ffffff',
                          }}
                        >
                          <option value="">(Not linked to 3D CAD model)</option>
                          {steps.map(f => (
                            <option key={f.relative_path} value={f.relative_path}>
                              {f.relative_path}
                            </option>
                          ))}
                        </select>
                        {hasCAD && (
                          <button
                            type="button"
                            className="btn btn-secondary"
                            disabled={busy}
                            onClick={() => open(p.cad_relative_path!)}
                            style={{ whiteSpace: 'nowrap', fontSize: 12, padding: '6px 12px' }}
                          >
                            📦 Launch in FreeCAD
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Sourced Dimensions Table */}
                  <div style={{ marginTop: 8 }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: 8,
                        flexWrap: 'wrap',
                        gap: 8,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <h4 style={{ margin: 0, fontSize: 13, color: '#0f172a', fontWeight: 700 }}>
                          📐 Sourced Dimensions &amp; Manufacturing Tolerances
                        </h4>
                        <span style={{ fontSize: 11, color: '#64748b' }}>
                          (All values displayed in mm · SI storage in meters)
                        </span>
                      </div>

                      {editable && (
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={() => addDimension(originalIndex)}
                          style={{ fontSize: 11, padding: '4px 10px' }}
                        >
                          + Add Dimension
                        </button>
                      )}
                    </div>

                    {(!p.dimensions || p.dimensions.length === 0) ? (
                      <div
                        style={{
                          background: '#f8fafc',
                          border: '1px dashed #cbd5e1',
                          borderRadius: 6,
                          padding: '12px 16px',
                          textAlign: 'center',
                          color: '#64748b',
                          fontSize: 12,
                        }}
                      >
                        No individual dimensions recorded for this part.{' '}
                        {editable && (
                          <button
                            type="button"
                            onClick={() => addDimension(originalIndex)}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: '#0284c7',
                              cursor: 'pointer',
                              fontWeight: 600,
                              textDecoration: 'underline',
                              padding: 0,
                            }}
                          >
                            Add first dimension
                          </button>
                        )}
                      </div>
                    ) : (
                      <div style={{ overflowX: 'auto', border: '1px solid #e2e8f0', borderRadius: 6 }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                          <thead>
                            <tr style={{ background: '#f1f5f9', borderBottom: '1px solid #cbd5e1', color: '#475569' }}>
                              <th style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, width: '20%' }}>
                                Dimension
                              </th>
                              <th style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, width: '13%' }}>
                                Nominal (mm) *
                              </th>
                              <th style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, width: '12%' }}>
                                Min Limit (mm)
                              </th>
                              <th style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, width: '12%' }}>
                                Max Limit (mm)
                              </th>
                              <th style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, width: '13%' }}>
                                Tolerance Band
                              </th>
                              <th style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, width: '25%' }}>
                                Drawing / Source Callout *
                              </th>
                              {editable && (
                                <th style={{ padding: '8px 10px', textAlign: 'center', fontWeight: 600, width: '5%' }}>
                                  Action
                                </th>
                              )}
                            </tr>
                          </thead>
                          <tbody>
                            {p.dimensions.map((d, dIdx) => {
                              const tolBadge = calculateToleranceBadge(d);
                              return (
                                <tr
                                  key={dIdx}
                                  style={{
                                    borderBottom: '1px solid #f1f5f9',
                                    background: dIdx % 2 === 0 ? '#ffffff' : '#fcfcfd',
                                  }}
                                >
                                  {/* Dimension Name */}
                                  <td style={{ padding: '6px 8px' }}>
                                    <input
                                      aria-label={`Part ${originalIndex + 1} dimension ${dIdx + 1} name`}
                                      required
                                      disabled={!editable}
                                      type="text"
                                      placeholder="e.g. length, OD, width"
                                      value={d.name}
                                      onChange={e => handleDimensionFieldChange(originalIndex, dIdx, 'name', e.target.value)}
                                      style={{
                                        width: '100%',
                                        padding: '5px 8px',
                                        fontSize: 12,
                                        border: '1px solid #cbd5e1',
                                        borderRadius: 4,
                                        color: '#0f172a',
                                      }}
                                    />
                                  </td>

                                  {/* Nominal */}
                                  <td style={{ padding: '6px 8px' }}>
                                    <input
                                      aria-label={`Part ${originalIndex + 1} dimension ${dIdx + 1} nominal_m`}
                                      required
                                      disabled={!editable}
                                      type="number"
                                      step="any"
                                      placeholder="mm"
                                      value={d.nominal_m == null ? '' : Number((d.nominal_m * 1000).toFixed(4))}
                                      onChange={e => handleDimensionFieldChange(originalIndex, dIdx, 'nominal_m', e.target.value)}
                                      style={{
                                        width: '100%',
                                        padding: '5px 8px',
                                        fontSize: 12,
                                        fontFamily: 'JetBrains Mono, monospace',
                                        fontWeight: 600,
                                        border: '1px solid #cbd5e1',
                                        borderRadius: 4,
                                        color: '#0f172a',
                                      }}
                                    />
                                  </td>

                                  {/* Minimum */}
                                  <td style={{ padding: '6px 8px' }}>
                                    <input
                                      aria-label={`Part ${originalIndex + 1} dimension ${dIdx + 1} minimum_m`}
                                      disabled={!editable}
                                      type="number"
                                      step="any"
                                      placeholder="min mm"
                                      value={d.minimum_m == null ? '' : Number((d.minimum_m * 1000).toFixed(4))}
                                      onChange={e => handleDimensionFieldChange(originalIndex, dIdx, 'minimum_m', e.target.value)}
                                      style={{
                                        width: '100%',
                                        padding: '5px 8px',
                                        fontSize: 12,
                                        fontFamily: 'JetBrains Mono, monospace',
                                        border: '1px solid #cbd5e1',
                                        borderRadius: 4,
                                        color: '#475569',
                                      }}
                                    />
                                  </td>

                                  {/* Maximum */}
                                  <td style={{ padding: '6px 8px' }}>
                                    <input
                                      aria-label={`Part ${originalIndex + 1} dimension ${dIdx + 1} maximum_m`}
                                      disabled={!editable}
                                      type="number"
                                      step="any"
                                      placeholder="max mm"
                                      value={d.maximum_m == null ? '' : Number((d.maximum_m * 1000).toFixed(4))}
                                      onChange={e => handleDimensionFieldChange(originalIndex, dIdx, 'maximum_m', e.target.value)}
                                      style={{
                                        width: '100%',
                                        padding: '5px 8px',
                                        fontSize: 12,
                                        fontFamily: 'JetBrains Mono, monospace',
                                        border: '1px solid #cbd5e1',
                                        borderRadius: 4,
                                        color: '#475569',
                                      }}
                                    />
                                  </td>

                                  {/* Tolerance spread badge */}
                                  <td style={{ padding: '6px 8px' }}>
                                    <span
                                      style={{
                                        display: 'inline-block',
                                        fontSize: 11,
                                        fontFamily: 'JetBrains Mono, monospace',
                                        color: tolBadge === 'Nominal only' ? '#64748b' : '#047857',
                                        background: tolBadge === 'Nominal only' ? '#f1f5f9' : '#ecfdf5',
                                        border: `1px solid ${tolBadge === 'Nominal only' ? '#e2e8f0' : '#a7f3d0'}`,
                                        padding: '3px 6px',
                                        borderRadius: 4,
                                        whiteSpace: 'nowrap',
                                      }}
                                    >
                                      {tolBadge || '—'}
                                    </span>
                                  </td>

                                  {/* Sourced Callout / Document */}
                                  <td style={{ padding: '6px 8px' }}>
                                    <input
                                      aria-label={`Part ${originalIndex + 1} dimension ${dIdx + 1} source`}
                                      required
                                      disabled={!editable}
                                      type="text"
                                      placeholder="e.g. HFT-01 PDF sheet 1"
                                      value={d.source}
                                      onChange={e => handleDimensionFieldChange(originalIndex, dIdx, 'source', e.target.value)}
                                      style={{
                                        width: '100%',
                                        padding: '5px 8px',
                                        fontSize: 12,
                                        border: '1px solid #cbd5e1',
                                        borderRadius: 4,
                                        color: '#0f172a',
                                      }}
                                    />
                                  </td>

                                  {/* Action */}
                                  {editable && (
                                    <td style={{ padding: '6px 8px', textAlign: 'center' }}>
                                      <button
                                        type="button"
                                        onClick={() => removeDimension(originalIndex, dIdx)}
                                        style={{
                                          background: 'transparent',
                                          border: 'none',
                                          color: '#ef4444',
                                          cursor: 'pointer',
                                          padding: '4px 6px',
                                          borderRadius: 4,
                                          fontSize: 13,
                                        }}
                                        title="Remove dimension"
                                      >
                                        🗑️
                                      </button>
                                    </td>
                                  )}
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </article>
          );
        })}
      </div>

      {/* Footer Add Part button */}
      {editable && (
        <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-start' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={addPart}
            style={{ fontSize: 13, padding: '8px 16px', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 6 }}
          >
            ➕ Add Another Sourced Part
          </button>
        </div>
      )}
    </section>
  );
}
