from pathlib import Path

p = Path('desktop/src/pages/ProjectDetail.tsx')
text = p.read_text(encoding='utf-8')

old_tab_defs = """const TAB_DEFS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'lifecycle', label: 'Lifecycle', icon: Activity },
  { id: 'specifications', label: 'Specifications', icon: Sliders },
  { id: 'calculations', label: 'Calculations', icon: Calculator },
  { id: 'simulations', label: 'Simulations', icon: Play },
  { id: 'designs', label: 'Designs', icon: Layers },
  { id: 'files', label: 'Revision Files', icon: FileText },
  { id: 'validation', label: 'Validation', icon: ShieldCheck },
  { id: 'revisions', label: 'Revisions', icon: History },
  { id: 'ecr', label: 'Changes (ECR)', icon: GitPullRequest },
  { id: 'reports', label: 'Reports', icon: FileBarChart },
] as const;"""

new_tab_defs = """const TAB_DEFS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'lifecycle', label: 'Lifecycle', icon: Activity },
  { id: 'specifications', label: 'Specifications', icon: Sliders },
  { id: 'calculations', label: 'Calculations', icon: Calculator },
  { id: 'simulations', label: 'Simulations', icon: Play },
  { id: 'designs', label: 'Designs', icon: Layers },
  { id: 'reports', label: 'Reports (PDF)', icon: FileBarChart },
  { id: 'files', label: 'Revision Files', icon: FileText },
  { id: 'validation', label: 'Validation', icon: ShieldCheck },
  { id: 'revisions', label: 'Revisions', icon: History },
  { id: 'ecr', label: 'Changes (ECR)', icon: GitPullRequest },
] as const;"""

old_nav = """          {/* 3. Modern Styled Tabs Strip */}
          <nav
            style={{
              display: 'flex',
              gap: '6px',
              background: '#f3f6fb',
              padding: '8px 12px 0 12px',
              borderRadius: '10px 10px 0 0',
              border: '1px solid var(--border)',
              borderBottom: 'none',
              overflowX: 'auto',
              scrollbarWidth: 'none',
            }}
          >"""

new_nav = """          {/* 3. Modern Styled Tabs Strip */}
          <nav
            style={{
              display: 'flex',
              gap: '4px',
              background: '#f3f6fb',
              padding: '8px 10px 0 10px',
              borderRadius: '10px 10px 0 0',
              border: '1px solid var(--border)',
              borderBottom: 'none',
              overflowX: 'auto',
              scrollbarWidth: 'thin',
            }}
          >"""

old_btn_style = """                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '10px 16px',"""

new_btn_style = """                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '8px 13px',"""

old_quick_actions = """                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => setTab('lifecycle')}
                      className="btn btn-secondary"
                      style={{ fontSize: '12px', padding: '6px 14px' }}
                    >
                      <Activity size={14} /> View Lifecycle Gates
                    </button>"""

new_quick_actions = """                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => setTab('reports')}
                      className="btn btn-primary"
                      style={{ fontSize: '12px', padding: '6px 14px', background: '#0369a1', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                    >
                      <FileBarChart size={14} /> Reports (PDF)
                    </button>
                    <button
                      onClick={() => setTab('lifecycle')}
                      className="btn btn-secondary"
                      style={{ fontSize: '12px', padding: '6px 14px' }}
                    >
                      <Activity size={14} /> View Lifecycle Gates
                    </button>"""

text_norm = text.replace('\r\n', '\n')
for old, new in [
    (old_tab_defs, new_tab_defs),
    (old_nav, new_nav),
    (old_btn_style, new_btn_style),
    (old_quick_actions, new_quick_actions),
]:
    old_n = old.replace('\r\n', '\n')
    new_n = new.replace('\r\n', '\n')
    if old_n in text_norm:
        text_norm = text_norm.replace(old_n, new_n)
        print(f"Replaced block successfully")
    else:
        print(f"Block not found: {old_n[:40]}...")

p.write_text(text_norm, encoding='utf-8')
print("Saved ProjectDetail.tsx")
