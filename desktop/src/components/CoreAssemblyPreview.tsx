import React, { useEffect, useRef, useState } from 'react';
import { api } from '../api/client';

type Pose = { yaw: number; elevation: number; zoom: number };
const initial: Pose = { yaw: 40, elevation: 25, zoom: 1 };
const color = (hex: string) => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255);

function AssemblyCanvas({ model }: { model: any }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const draw = useRef<() => void>(() => {});
  const drag = useRef<{ x: number; y: number } | null>(null);
  const [pose, setPose] = useState(initial);
  const [hidden, setHidden] = useState<string[]>([]);
  const [error, setError] = useState('');
  const poseRef = useRef(pose); poseRef.current = pose;
  const hiddenRef = useRef(hidden); hiddenRef.current = hidden;
  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const gl = element.getContext('webgl', { antialias: true, preserveDrawingBuffer: true });
    if (!gl) { setError('Interactive 3D is unavailable on this device. Open the assembled native CAD model below.'); return; }
    const compile = (kind: number, source: string) => {
      const shader = gl.createShader(kind)!; gl.shaderSource(shader, source); gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader) || '3D shader failed');
      return shader;
    };
    const vertex = compile(gl.VERTEX_SHADER, `
      attribute vec3 position; attribute vec3 normal;
      uniform mat4 model; uniform mat3 camera; uniform vec3 center;
      uniform float scale; uniform float aspect; varying float shade;
      void main() {
        vec3 p = camera * ((model * vec4(position, 1.0)).xyz - center);
        vec3 n = normalize(camera * mat3(model) * normal);
        shade = 0.42 + 0.58 * abs(dot(n, normalize(vec3(-0.3, 0.5, 0.9))));
        gl_Position = vec4(p.x * scale / aspect, p.y * scale, -p.z * scale * 0.3, 1.0);
      }`);
    const fragment = compile(gl.FRAGMENT_SHADER, `precision mediump float;
      uniform vec3 tint; varying float shade;
      void main() { gl_FragColor = vec4(tint * shade, 1.0); }`);
    const program = gl.createProgram()!;
    gl.attachShader(program, vertex); gl.attachShader(program, fragment); gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) { setError('The 3D renderer could not initialize.'); return; }
    gl.useProgram(program); gl.enable(gl.DEPTH_TEST);
    const attributes = { position: gl.getAttribLocation(program, 'position'), normal: gl.getAttribLocation(program, 'normal') };
    const locations = Object.fromEntries(['model', 'camera', 'center', 'scale', 'aspect', 'tint'].map(x => [x, gl.getUniformLocation(program, x)]));
    const buffers: Record<string, { buffer: WebGLBuffer; count: number }> = {};
    for (const [name, value] of Object.entries(model.prototypes) as [string, any][]) {
      const vertices: number[] = [];
      for (const triangle of value.triangles) {
        const [a, b, c] = triangle.map((i: number) => value.positions_m[i]);
        const u = b.map((v: number, i: number) => v - a[i]), v = c.map((x: number, i: number) => x - a[i]);
        const n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
        const length = Math.hypot(...n) || 1;
        for (const p of [a, b, c]) vertices.push(...p, ...n.map(x => x / length));
      }
      const buffer = gl.createBuffer()!; gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertices), gl.STATIC_DRAW);
      buffers[name] = { buffer, count: vertices.length / 6 };
    }
    const [minimum, maximum] = model.bounds_m;
    const center = minimum.map((n: number, i: number) => (n + maximum[i]) / 2);
    const size = Math.max(...minimum.map((n: number, i: number) => maximum[i] - n));
    draw.current = () => {
      const ratio = window.devicePixelRatio || 1;
      element.width = Math.max(1, Math.round(element.clientWidth * ratio));
      element.height = Math.max(1, Math.round(element.clientHeight * ratio));
      gl.viewport(0, 0, element.width, element.height);
      gl.clearColor(0.055, 0.085, 0.13, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.useProgram(program);
      const { yaw, elevation, zoom } = poseRef.current;
      const y = yaw * Math.PI / 180, e = elevation * Math.PI / 180;
      const right = [Math.cos(y), Math.sin(y), 0];
      const up = [-Math.sin(y) * Math.sin(e), Math.cos(y) * Math.sin(e), Math.cos(e)];
      const depth = [Math.sin(y) * Math.cos(e), -Math.cos(y) * Math.cos(e), Math.sin(e)];
      gl.uniformMatrix3fv(locations.camera, false, new Float32Array([right[0], up[0], depth[0], right[1], up[1], depth[1], right[2], up[2], depth[2]]));
      gl.uniform3fv(locations.center, center); gl.uniform1f(locations.scale, 1.8 / size * zoom);
      gl.uniform1f(locations.aspect, element.width / element.height);
      for (const instance of model.instances) {
        if (hiddenRef.current.includes(instance.prototype)) continue;
        const prototype = buffers[instance.prototype];
        gl.bindBuffer(gl.ARRAY_BUFFER, prototype.buffer);
        gl.enableVertexAttribArray(attributes.position); gl.vertexAttribPointer(attributes.position, 3, gl.FLOAT, false, 24, 0);
        gl.enableVertexAttribArray(attributes.normal); gl.vertexAttribPointer(attributes.normal, 3, gl.FLOAT, false, 24, 12);
        const m = instance.transform;
        gl.uniformMatrix4fv(locations.model, false, new Float32Array([0, 1, 2, 3].flatMap(column => [m[0][column], m[1][column], m[2][column], m[3][column]])));
        gl.uniform3fv(locations.tint, color(instance.color));
        gl.drawArrays(gl.TRIANGLES, 0, prototype.count);
      }
    };
    const resize = new ResizeObserver(() => draw.current()); resize.observe(element);
    draw.current();
    return () => { resize.disconnect(); draw.current = () => {};
      Object.values(buffers).forEach(b => gl.deleteBuffer(b.buffer)); gl.deleteProgram(program); gl.deleteShader(vertex); gl.deleteShader(fragment); };
  }, [model]);
  useEffect(() => { draw.current(); }, [pose, hidden]);
  return <>
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
      {[['Isometric', initial], ['End view', { yaw: 90, elevation: 0, zoom: 1 }], ['Side view', { yaw: 0, elevation: 0, zoom: 1 }], ['Top view', { yaw: 0, elevation: 90, zoom: 1 }]].map(([label, view]) =>
        <button type="button" key={String(label)} className="btn btn-secondary" onClick={() => setPose(view as Pose)}>{String(label)}</button>)}
      <button type="button" className="btn btn-secondary" onClick={() => setPose(p => ({ ...p, zoom: Math.min(3, p.zoom * 1.15) }))}>Zoom in</button>
      <button type="button" className="btn btn-secondary" onClick={() => setPose(p => ({ ...p, zoom: Math.max(.4, p.zoom / 1.15) }))}>Zoom out</button>
    </div>
    {error && <p role="alert">{error}</p>}
    <canvas ref={canvas} aria-label="Interactive reconstructed transformer core assembly" style={{ width: '100%', height: 480, borderRadius: 9, touchAction: 'none', cursor: 'grab', background: '#0e1622' }}
      onPointerDown={e => { drag.current = { x: e.clientX, y: e.clientY }; e.currentTarget.setPointerCapture(e.pointerId); }}
      onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}
      onPointerMove={e => { if (!drag.current) return; const dx = e.clientX - drag.current.x, dy = e.clientY - drag.current.y;
        drag.current = { x: e.clientX, y: e.clientY }; setPose(p => ({ ...p, yaw: p.yaw + dx * .5, elevation: Math.max(-85, Math.min(85, p.elevation + dy * .4)) })); }} />
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginTop: 10 }}>{Object.keys(model.prototypes).map(name =>
      <label key={name}><input type="checkbox" checked={!hidden.includes(name)} onChange={() => setHidden(previous => previous.includes(name) ? previous.filter(x => x !== name) : [...previous, name])} /> {name} ({model.part_counts[name] ?? 0})</label>)}</div>
    <p style={{ color: '#52627a', marginTop: 8, fontSize: 12 }}>Drag to orbit. Part colors distinguish geometry; they do not certify material or finish.</p>
  </>;
}

export function CoreAssemblyPreview({ revisionId, designHash }: { revisionId: string; designHash?: string | null }) {
  const [model, setModel] = useState<any>(null);
  const [viewMode, setViewMode] = useState<'render' | 'orbit'>('render');
  const [error, setError] = useState('');
  useEffect(() => {
    let cancelled = false;
    setModel(null);
    setError('');
    api.coreAssemblyPreview(revisionId)
      .then(data => {
        if (!cancelled) {
          setModel(data);
          setViewMode('orbit');
        }
      })
      .catch(e => {
        if (!cancelled) setError(String(e));
      });
    return () => { cancelled = true; };
  }, [revisionId, designHash]);

  const open = async (path: string) => {
    try {
      setError('');
      await api.openFile(revisionId, path);
    } catch (e) {
      setError(String(e));
    }
  };

  const isPlasma = Boolean(model?.title?.toLowerCase().includes('plasma') || model?.title?.toLowerCase().includes('pce'));
  const [minBound, maxBound] = model?.bounds_m || [[0, 0, 0], [0, 0, 0]];
  const dimX = ((maxBound[0] - minBound[0]) * 1000).toFixed(0);
  const dimY = ((maxBound[1] - minBound[1]) * 1000).toFixed(0);
  const dimZ = ((maxBound[2] - minBound[2]) * 1000).toFixed(0);

  return (
    <section style={{ background: 'var(--bg-card, white)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 10 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 16 }}>{model?.title || 'Complete Combined Assembly · 3D CAD'}</h3>
          <p style={{ margin: '4px 0 0', color: '#52627a', fontSize: 12 }}>
            {model?.instances ? `Master 3D solid model assembly comprising ${model.instances.length} physical components · Nominal Envelope ${dimX} × ${dimY} × ${dimZ} mm` : 'Interactive 3D reconstruction synthesized from nominal STEP CAD.'}
          </p>
        </div>
        {model?.preview_image_base64 && (
          <div style={{ display: 'inline-flex', borderRadius: 6, border: '1px solid #cbd5e1', overflow: 'hidden' }}>
            <button
              type="button"
              className={`btn ${viewMode === 'render' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ borderRadius: 0, padding: '5px 12px', fontSize: 12 }}
              onClick={() => setViewMode('render')}
            >
              🖼️ Photorealistic CAD Render
            </button>
            <button
              type="button"
              className={`btn ${viewMode === 'orbit' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ borderRadius: 0, padding: '5px 12px', fontSize: 12 }}
              onClick={() => setViewMode('orbit')}
            >
              🔄 Interactive 3D WebGL Orbit
            </button>
          </div>
        )}
      </div>

      {error && <p role="alert" style={{ color: '#b91c1c' }}>{error}</p>}

      {!model ? (
        <p>Loading recorded assembly geometry…</p>
      ) : !model.available ? (
        <p role="status">{model.reason}</p>
      ) : (
        <>
          {viewMode === 'render' && model.preview_image_base64 ? (
            <div style={{ position: 'relative', width: '100%', background: '#0e1622', borderRadius: 9, overflow: 'hidden', border: '1px solid #1e293b' }}>
              <img
                src={model.preview_image_base64}
                alt="Complete combined 3D CAD core and support assembly"
                style={{ width: '100%', maxHeight: 520, objectFit: 'contain', display: 'block', margin: '0 auto' }}
              />
              <div style={{
                position: 'absolute',
                bottom: 12,
                left: 12,
                right: 12,
                background: 'rgba(15, 23, 42, 0.85)',
                backdropFilter: 'blur(6px)',
                padding: '8px 14px',
                borderRadius: 6,
                color: '#e2e8f0',
                fontSize: 11.5,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: 8,
              }}>
                <span>
                  <strong>{model.title || (isPlasma ? 'PCE-100 Master Assembly' : 'HFT-000 Master Assembly')}</strong> · {model.instances?.length || 0} Components
                </span>
                <span style={{ color: '#38bdf8', fontWeight: 600 }}>
                  Dimensions: {dimX} × {dimY} × {dimZ} mm
                </span>
              </div>
            </div>
          ) : (
            <AssemblyCanvas model={model} />
          )}

          {/* Master 3D CAD Deliverables Actions */}
          <div style={{
            marginTop: 16,
            padding: 14,
            background: '#f8fafc',
            border: '1.5px solid #0f766e',
            borderRadius: 8,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12, marginBottom: 10 }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 13, color: '#0f766e' }}>
                  🚀 Master Combined 3D CAD Deliverables ({model.instances?.length || 0} Solids · Envelope {dimX}×{dimY}×{dimZ} mm)
                </div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                  {isPlasma
                    ? '1 SS 430 Interface Flange · 1 ETP Copper Chamber Body · 1 1/4" Cooling Coil · 1 Electrode · 2 Boron Nitride Discs · 1 Waveguide'
                    : '48 Toroidal Ferrite Cores · 45 PTFE Spacers · 3 Glass-Filled Limbs · 2 Upright Supports · 1 Base Plate'}
                </div>
              </div>

              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 600 }}
                  onClick={() => open(model.exploded_step || (isPlasma ? 'mechanical/core-assembly/a-pce100/PCE-100-complete-assembly.step' : 'mechanical/core-assembly/a-2ce3be18/HFT-000-exploded-assembly.step'))}
                  title="Opens exploded 3D model with components visibly spaced and labeled"
                >
                  💥 Open Exploded Assembly (Separated Parts)
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6 }}
                  onClick={() => open(model.native_files?.step || (isPlasma ? 'mechanical/core-assembly/a-pce100/PCE-100-complete-assembly.step' : 'mechanical/core-assembly/a-2ce3be18/HFT-000-core-assembly.step'))}
                  title="Opens full combined nominal assembly in FreeCAD 3D View"
                >
                  📦 Open Assembled STEP (.step)
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6 }}
                  onClick={() => open(model.native_files?.freecad || (isPlasma ? 'mechanical/core-assembly/a-pce100/PCE-100-complete-assembly.FCStd' : 'mechanical/core-assembly/a-2ce3be18/HFT-000-core-assembly.FCStd'))}
                  title="Opens FreeCAD Project (.FCStd)"
                >
                  🛠️ Open FreeCAD Project (.FCStd)
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6, borderColor: '#0f766e', color: '#0f766e', fontWeight: 600 }}
                  onClick={() => open(isPlasma ? 'reports/PCE-100-Plasma-Chamber-Specification-Catalog.pdf' : 'reports/HFT-000-Core-Assembly-Specification-Catalog.pdf')}
                  title="Opens complete 8-page technical specification and parts catalog PDF"
                >
                  📄 Download Specification PDF (8 Pages)
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6, borderColor: '#059669', color: '#059669', fontWeight: 600 }}
                  onClick={() => open(isPlasma ? 'reports/PCE-01-Autonomous-Manufacturing-Drawing.pdf' : 'reports/HFT-02-Autonomous-Manufacturing-Drawing.pdf')}
                  title="Opens autonomous AI-generated 2D manufacturing drawing (ISO A3 vector PDF with sections and GD&T)"
                >
                  📐 AI 2D Drawing (TechDraw PDF)
                </button>
                {isPlasma ? (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6, borderColor: '#0284c7', color: '#0284c7', fontWeight: 600 }}
                    onClick={() => open('reports/PCE-100-Thermal-and-Hydraulic-Cooling-Analysis.json')}
                    title="Opens 3.0 Bar Thermal & Hydraulic Cooling Analysis (JSON)"
                  >
                    🔥 Thermal &amp; Hydraulic Cooling (JSON)
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: 12, padding: '7px 14px', display: 'inline-flex', alignItems: 'center', gap: 6, borderColor: '#4f46e5', color: '#4f46e5', fontWeight: 600 }}
                    onClick={() => open('reports/HFT-000-FEMM-Magnetic-FEA-Report.pdf')}
                    title="Opens FEMM 4.2 magnetic simulation and 0.5mm Litz wire report (PDF)"
                  >
                    ⚡ Open FEMM FEA Report (PDF)
                  </button>
                )}
              </div>
            </div>

            <div style={{
              fontSize: 11,
              color: '#475569',
              background: '#f1f5f9',
              padding: '6px 10px',
              borderRadius: 6,
              border: '1px solid #e2e8f0',
              display: 'flex',
              alignItems: 'center',
              gap: 6
            }}>
              <span>💡</span>
              <span>
                <strong>FreeCAD 3D Viewport Note:</strong> STEP files automatically open directly into an active 3D view with all solids visible. When opening <code>.FCStd</code>, if FreeCAD shows a gray canvas, press <strong>Ctrl+N</strong> or click <strong>View → Create new view</strong> to initialize the 3D window.
              </span>
            </div>
          </div>

          <details style={{ marginTop: 12 }}>
            <summary style={{ cursor: 'pointer', fontSize: 12, color: '#64748b' }}>
              Geometry sources, placement assumptions and omitted items
            </summary>
            <ul style={{ margin: '8px 0 0 18px', fontSize: 11.5, color: '#52627a' }}>
              {[...model.assumptions, ...model.omissions].map((item: string) => (
                <li key={item} style={{ marginTop: 5 }}>{item}</li>
              ))}
            </ul>
          </details>
        </>
      )}
    </section>
  );
}
