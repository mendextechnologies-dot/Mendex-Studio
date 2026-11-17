path = 'desktop/src/components/RequirementsTraceabilityMatrixCard.tsx'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Hero Card
old_hero = """      <div
        className="card"
        style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.7) 100%)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          borderRadius: 8,
          padding: 20,
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.25)',
        }}
      >"""

new_hero = """      <div
        className="card"
        style={{
          background: '#ffffff',
          border: '1px solid var(--border)',
          borderRadius: 8,
          padding: 20,
          boxShadow: '0 1px 3px rgba(23, 32, 51, 0.05)',
        }}
      >"""

# 2. Hero Icon
old_icon = """              <div
                style={{
                  background: 'rgba(59, 130, 246, 0.2)',
                  borderRadius: 6,
                  padding: 8,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#60a5fa',
                }}
              >"""

new_icon = """              <div
                style={{
                  background: '#eff6ff',
                  border: '1px solid #bfdbfe',
                  borderRadius: 8,
                  padding: 10,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#1d4ed8',
                }}
              >"""

# 3. KPI Grid
old_kpi = """        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
            gap: 12,
            marginTop: 18,
            paddingTop: 16,
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
          }}
        >
          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '10px 14px', borderRadius: 6 }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Tracked Requirements</span>
            <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4, color: '#f8fafc' }}>{metrics.total}</div>
          </div>

          <div style={{ background: 'rgba(16, 185, 129, 0.05)', padding: '10px 14px', borderRadius: 6, borderLeft: '3px solid #10b981' }}>
            <span style={{ fontSize: 11, color: '#10b981', textTransform: 'uppercase', letterSpacing: 0.5 }}>Verified / Compliant</span>
            <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4, color: '#10b981' }}>
              {metrics.passed} <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--text-muted)' }}>({metrics.completionRate}%)</span>
            </div>
          </div>

          <div style={{ background: 'rgba(148, 163, 184, 0.05)', padding: '10px 14px', borderRadius: 6, borderLeft: '3px solid #94a3b8' }}>
            <span style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: 0.5 }}>Pending Verification</span>
            <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4, color: '#94a3b8' }}>{metrics.inProgress}</div>
          </div>

          <div style={{ background: 'rgba(59, 130, 246, 0.05)', padding: '10px 14px', borderRadius: 6, borderLeft: '3px solid #3b82f6' }}>
            <span style={{ fontSize: 11, color: '#60a5fa', textTransform: 'uppercase', letterSpacing: 0.5 }}>Mandatory Gates</span>
            <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4, color: '#60a5fa' }}>{metrics.mandatory}</div>
          </div>

          <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '10px 14px', borderRadius: 6 }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>Sourced Snapshots</span>
            <div style={{ fontSize: 22, fontWeight: 800, marginTop: 4, color: '#e2e8f0' }}>{rawRequirements.length}</div>
          </div>
        </div>"""

new_kpi = """        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
            gap: 12,
            marginTop: 18,
            paddingTop: 16,
            borderTop: '1px solid var(--border)',
          }}
        >
          <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: 6, border: '1px solid #e2e8f0' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5 }}>Tracked Requirements</span>
            <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4, color: '#0f172a' }}>{metrics.total}</div>
          </div>

          <div style={{ background: '#ecfdf5', padding: '10px 14px', borderRadius: 6, border: '1px solid #a7f3d0', borderLeft: '4px solid #10b981' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#047857', textTransform: 'uppercase', letterSpacing: 0.5 }}>Verified / Compliant</span>
            <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4, color: '#047857' }}>
              {metrics.passed} <span style={{ fontSize: 12, fontWeight: 500, color: '#065f46' }}>({metrics.completionRate}%)</span>
            </div>
          </div>

          <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: 6, border: '1px solid #e2e8f0', borderLeft: '4px solid #94a3b8' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#475569', textTransform: 'uppercase', letterSpacing: 0.5 }}>Pending Verification</span>
            <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4, color: '#334155' }}>{metrics.inProgress}</div>
          </div>

          <div style={{ background: '#eff6ff', padding: '10px 14px', borderRadius: 6, border: '1px solid #bfdbfe', borderLeft: '4px solid #3b82f6' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#1d4ed8', textTransform: 'uppercase', letterSpacing: 0.5 }}>Mandatory Gates</span>
            <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4, color: '#1d4ed8' }}>{metrics.mandatory}</div>
          </div>

          <div style={{ background: '#f8fafc', padding: '10px 14px', borderRadius: 6, border: '1px solid #e2e8f0' }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5 }}>Sourced Snapshots</span>
            <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4, color: '#0f172a' }}>{rawRequirements.length}</div>
          </div>
        </div>"""

# 4. Progress bar background
old_pb = """          <div style={{ width: '100%', height: 6, background: 'rgba(255, 255, 255, 0.1)', borderRadius: 3, overflow: 'hidden' }}>"""
new_pb = """          <div style={{ width: '100%', height: 6, background: '#e2e8f0', borderRadius: 3, overflow: 'hidden' }}>"""

# 5. Expanded row
old_exp = """                      {/* Expanded Traceability Detail Row */}
                      {isExpanded && (
                        <tr style={{ background: 'rgba(15, 23, 42, 0.4)', borderTop: '1px dashed var(--border)' }}>
                          <td colSpan={5} style={{ padding: '16px 24px' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
                              {/* Left block: Specification Mapping */}
                              <div style={{ background: 'rgba(0, 0, 0, 0.2)', padding: 12, borderRadius: 6, border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                                <div style={{ fontSize: 11, fontWeight: 700, color: '#60a5fa', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                                  📐 Active Specification Mapping
                                </div>
                                <div style={{ fontSize: 12, lineHeight: 1.6 }}>
                                  <div><strong>Target Parameter:</strong> {r.target_value != null ? `${r.target_value} ${r.unit}` : 'Unassigned'}</div>
                                  <div><strong>Mapped Field:</strong> <code>{r.specification_field || 'None'}</code></div>
                                  <div><strong>Active Spec Value:</strong> {r.linked_spec_value != null ? `${r.linked_spec_value} ${r.unit || ''}` : 'Not populated'}</div>
                                  <div style={{ marginTop: 4 }}>
                                    <strong>Status:</strong>{' '}
                                    {r.spec_match_status === 'MATCH' ? (
                                      <span style={{ color: '#10b981', fontWeight: 600 }}>✓ Specification Matched</span>
                                    ) : (
                                      <span style={{ color: '#f59e0b', fontWeight: 600 }}>⚠️ Separate ERS Variant</span>
                                    )}
                                  </div>
                                </div>
                              </div>

                              {/* Right block: Complete Provenance Citation */}
                              <div style={{ background: 'rgba(0, 0, 0, 0.2)', padding: 12, borderRadius: 6, border: '1px solid rgba(255, 255, 255, 0.05)' }}>
                                <div style={{ fontSize: 11, fontWeight: 700, color: '#a78bfa', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                                  📜 Sourced Baseline Provenance
                                </div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5, wordBreak: 'break-word' }}>
                                  {r.source || 'No external document citation available.'}
                                </div>"""

new_exp = """                      {/* Expanded Traceability Detail Row */}
                      {isExpanded && (
                        <tr style={{ background: '#f8fafc', borderTop: '1px solid #e2e8f0' }}>
                          <td colSpan={5} style={{ padding: '16px 24px' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
                              {/* Left block: Specification Mapping */}
                              <div style={{ background: '#ffffff', padding: 14, borderRadius: 6, border: '1px solid #cbd5e1' }}>
                                <div style={{ fontSize: 11, fontWeight: 700, color: '#1d4ed8', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                                  📐 Active Specification Mapping
                                </div>
                                <div style={{ fontSize: 12, color: '#0f172a', lineHeight: 1.6 }}>
                                  <div><strong style={{ color: '#334155' }}>Target Parameter:</strong> {r.target_value != null ? `${r.target_value} ${r.unit}` : 'Unassigned'}</div>
                                  <div><strong style={{ color: '#334155' }}>Mapped Field:</strong> <code>{r.specification_field || 'None'}</code></div>
                                  <div><strong style={{ color: '#334155' }}>Active Spec Value:</strong> {r.linked_spec_value != null ? `${r.linked_spec_value} ${r.unit || ''}` : 'Not populated'}</div>
                                  <div style={{ marginTop: 4 }}>
                                    <strong style={{ color: '#334155' }}>Status:</strong>{' '}
                                    {r.spec_match_status === 'MATCH' ? (
                                      <span style={{ color: '#047857', fontWeight: 600 }}>✓ Specification Matched</span>
                                    ) : (
                                      <span style={{ color: '#b45309', fontWeight: 600 }}>⚠️ Separate ERS Variant</span>
                                    )}
                                  </div>
                                </div>
                              </div>

                              {/* Right block: Complete Provenance Citation */}
                              <div style={{ background: '#ffffff', padding: 14, borderRadius: 6, border: '1px solid #cbd5e1' }}>
                                <div style={{ fontSize: 11, fontWeight: 700, color: '#6b21a8', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                                  📜 Sourced Baseline Provenance
                                </div>
                                <div style={{ fontSize: 12, color: '#334155', lineHeight: 1.5, wordBreak: 'break-word' }}>
                                  {r.source || 'No external document citation available.'}
                                </div>"""

for old, new, label in [
    (old_hero, new_hero, 'hero'),
    (old_icon, new_icon, 'icon'),
    (old_kpi, new_kpi, 'kpi'),
    (old_pb, new_pb, 'progress_bar'),
    (old_exp, new_exp, 'expanded'),
]:
    # Normalize CRLF
    old_norm = old.replace('\r\n', '\n')
    text_norm = text.replace('\r\n', '\n')
    if old_norm in text_norm:
        text_norm = text_norm.replace(old_norm, new.replace('\r\n', '\n'), 1)
        print(f'Replaced {label}')
        text = text_norm
    else:
        print(f'Failed to match {label}')

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print('Done updating RTM')
