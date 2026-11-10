"""Add independently tested concurrent delta to our new verification report only."""
from pathlib import Path
from collections import Counter
import json,re,hashlib,ast,subprocess

E=Path(__file__).resolve().parent
report=E/'FINAL_IMPLEMENTATION_VERIFICATION.md'
data=json.loads((E/'REQUIREMENTS.json').read_text(encoding='utf-8'))
assert data['total']==263, 'Apply this report-only delta exactly once'
rows=data['rows']
for row in rows:
    if row['id']=='CORE-002':
        row.update(status='PARTIAL',actual='Existing UI/CLI share StudioService, but latest workspace panels directly execute calculations/dataset parsing/script writes outside core service.',files='src/mendex_ui/workspace_panels.py; src/mendex_core/service.py',evidence='LATEST_UI_PROBES.json; latest UI source inspection',findings='F20',remaining='Route calculations, source selection and script export through the single core service used by UI and CLI; persist traceable records.')
extra=[
('NEW-005','Revision synchronization must clear unspecified inputs','Changing revision must not retain another revision input values','Empty Specification leaves36V/400V/.5A/150kHz from previous revision unchanged.','FAIL','F19'),
('NEW-006','Exported FEMM script must match selected inputs/calculated winding','Native export uses the frozen actual parameters and provenance','Calculated secondary turns change, but exported scripts have identical bytes; export supplies fixed24/1000turns.','FAIL','F19'),
('NEW-007','Interactive calculations use shared core service','UI/CLI use the same calculation/export/source boundary','workspace_panels.py imports/calls calculators and parsers and writes files directly; no equivalent traced core operation.','FAIL','F20'),
('NEW-008','Interactive numerical results retain provenance','Result bound to revision/hash/source/assumptions and review state','Panel returns numeric result with zero products and zero jobs, no stored calculation provenance.','FAIL','F20'),
('NEW-009','Preset research data must be qualified or clearly synthetic','Picker values carry genuine source/version/license/review classification','New semiconductor picker loads scientific fixture CSV directly; valid upstream evidence not demonstrated.','FAIL','F03,F20'),
('NEW-010','Engineering numerical domain and missing-input guards','Unsupported/unqualified assumptions cannot appear as evaluated engineering result','New controls exercise positive-value/form tests; independent domain, overflow, missing-source and engineering reference acceptance incomplete.','UNVERIFIED','F18,F20'),
('NEW-011','Release identity and status match delivered package','Release claims/version/migration documentation match accepted implementation','New v1.5.0 release note claims completion and different schema tables; pyproject package version remains0.1.0 and actual tables differ.','FAIL','F16'),
('NEW-012','Interactive workspace UI software behavior','New widgets construct, sync populated fields and export generic script strings','Four new UI tests pass as part of latest90-test short suite; this does not qualify numerical results or native execution.','PASS',''),
]
for rid,req,expected,actual,status,ids in extra:
    rows.append({'id':rid,'source':'docs/release-notes-v1.5.0.md; da008c1; G13 shared-service/evidence rules','requirement':req,'expected':expected,'actual':actual,'status':status,'files':'src/mendex_ui/workspace_panels.py; src/mendex_ui/window.py; tests/ui/test_workspace_panels.py'+('; pyproject.toml; src/mendex_core/integration_store.py' if rid=='NEW-011' else ''),'evidence':'LATEST_UI_PROBES.json; LATEST_TEST_RESULTS.json; latest-short.txt; LATEST_DELTA.json','findings':ids,'remaining':'Resolve cited findings and repeat negative/positive UI, service and evidence tests.' if ids else 'None within widget/software behavior boundary; engineering qualification is separate.'})
counts=Counter(x['status'] for x in rows)
old_total=data['total'];old_counts=data['counts'];old_pct=data['verified_completion_percentage']
data.update(primary_snapshot='main30cbb1508982d5f04be1629e400a6cc569fecf74',earlier_snapshot='7230079d972e34b504f09cf90c166f87bdf0a43a',total=len(rows),counts=dict(counts),verified_completion_percentage=round(counts['PASS']/len(rows)*100,2),latest_delta='LATEST_DELTA.json; LATEST_TEST_RESULTS.json; PROBES-latest.json; LATEST_UI_PROBES.json')
(E/'REQUIREMENTS.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')

text=report.read_text(encoding='utf-8')
text=text.replace('Primary target: `main` **7230079d972e34b504f09cf90c166f87bdf0a43a**, frozen before testing.','Primary acceptance target after concurrent-delta verification: `main` **30cbb1508982d5f04be1629e400a6cc569fecf74**. Initial frozen snapshot **7230079d972e34b504f09cf90c166f87bdf0a43a** was also tested. Only three application/test files changed in the delta; all backend, adapters, runner, parsers and frozen contracts are identical between those two main snapshots.')
for label,old,new in [('Active normalized requirements/verification checks',old_total,len(rows)),('PASS',old_counts['PASS'],counts['PASS']),('PARTIAL',old_counts['PARTIAL'],counts['PARTIAL']),('FAIL',old_counts['FAIL'],counts['FAIL']),('BLOCKED',old_counts['BLOCKED'],counts['BLOCKED']),('UNVERIFIED',old_counts['UNVERIFIED'],counts['UNVERIFIED']),('BLOCKED + UNVERIFIED',old_counts['BLOCKED']+old_counts['UNVERIFIED'],counts['BLOCKED']+counts['UNVERIFIED'])]:
    text=text.replace(f'| {label} | {old} |',f'| {label} | {new} |')
text=text.replace(f'**{old_pct:.2f}%**',f'**{data["verified_completion_percentage"]:.2f}%**')
text=text.replace(f"**{old_counts['PASS']} ÷ {old_total} ×100 = {old_pct:.2f}%**",f"**{counts['PASS']} ÷ {len(rows)} ×100 = {data['verified_completion_percentage']:.2f}%**")
text=text.replace('No newer approved specification was located. New calculation files/handoff claims are reviewed as implementation claims, not authorization to expand generic scope.','No newer signed specification was located. Concurrent commitda008c1 added release-notes-v1.5.0.md and interactive workbenches. Those new claims were read, the UI delta inspected/tested, and eight additional checks added below. A release note is not independent owner acceptance or authorization to expand generic engineering scope.')
text=text.replace('| Main7230079 | Short fresh temp |','| Latest main30cbb15 | Short fresh temp | **90 passed in10.31s** | Adds four interactive UI tests; negative acceptance probes still fail |\n| Latest main30cbb15 | Deep snapshot temp | **13 failed,77 passed in9.33s** | Original path defect persists |\n| Initial main7230079 | Short fresh temp |')
text=text.replace('Files/functions below refer to the frozen main source, not later uncommitted work.','Files/functions below refer to the initial frozen main source plus the separately frozen/tested30cbb15 UI delta, not later uncommitted work.')
text=text.replace('Scope: primary main snapshot only.','Scope: latest verified main30cbb15 plus unchanged-backend evidence from7230079; delta source hashes and complete test results are retained.')
text=text.replace('This independently generated report and evidence must be considered before acceptance.','This independently generated report and evidence must be considered before acceptance. The concurrent source delta was subsequently frozen at30cbb15, fully tested at short/deep paths, inspected, and reprobed; the earlier core failures still reproduce.')
text=text.replace('The original working tree had an untracked `src/mendex_ui/workspace_panels.py` at freeze time. Its hash is recorded in SNAPSHOTS.json; it imports calculators/generators directly, is not wired into the frozen tracked UI and has no completed acceptance evidence. It is not silently promoted into the reviewed release.','The original working tree had an untracked `src/mendex_ui/workspace_panels.py` at first freeze. Its original hash is in SNAPSHOTS.json. Concurrent commitda008c1 subsequently wired a revised file into the UI; that tracked delta was frozen at30cbb15, hash-indexed in LATEST_DELTA.json and tested here. It is no longer described as untracked in the final acceptance target. Widget operation is verified; direct calculator/data/export bypasses and unqualified numerical assumptions remain defects.')

newfindings='''### F19 — P1: latest revision inputs and native export diverge

**Responsible:** Codex UI/service integration; Antigravity generator contract review.

**Affected files:** `src/mendex_ui/workspace_panels.py:TransformerWorkspacePanel.set_revision/calculate/export_femm_script`; related `SemiconductorWorkspacePanel.set_revision` and `DCDCWorkspacePanel.set_revision` only update truthy fields.

**Observed and root cause:** an unspecified revision retains36V/400V/.5A/150kHz from the previous revision. Form setters skip null/zero fields. Calculated winding turns change when a synthetic input changes, but FEMM export remains byte-identical because export passes fixed24/1000turns. `LATEST_UI_PROBES.json` retains the reproduction. Exported winding parameters are therefore not traceably tied to the displayed calculation. No FEMM result is claimed.

**Required completion:** clear/disable unspecified fields on every revision switch, prevent stale result reuse, freeze selected source parameters and pass actual reviewed model values through service/generator contracts; add switching-null-revision and export-consistency regressions.

### F20 — P1: new workbenches bypass core/evidence and use unqualified presets

**Responsible:** Codex UI/core boundary; Antigravity scientific data/model provenance.

**Affected files:** `src/mendex_ui/workspace_panels.py` direct calculator/dataset imports and `Path.write_text` exports; `src/mendex_core/service.py` has no corresponding calculation/evidence operation; `src/integrations/datasets/fixtures/switchloss_sample.csv`.

**Observed and root cause:** panels calculate with no selected product/revision, populate semiconductor presets from scientific fixtures without upstream review, and display numerical outputs without a persisted input/hash/source/review record. Existing widget tests assert positive values/string existence, not engineering qualification. UI-specific math/script orchestration bypasses the mandatory shared core service and CLI parity. These facts do not establish that every formula is numerically wrong, but do defeat the claimed complete traceable engineering workflow.

**Required completion:** route calculations, data selection and exports through shared typed services; require/identify valid inputs, assumptions, domain and source, preserve immutable run/provenance records and raw/derived/review distinctions. Clearly mark synthetic/unqualified presets and outputs. Independently qualify models within approved generic scope before engineering evaluation.

'''
marker='## Requirement-by-requirement verification'
text=text.replace(marker,newfindings+marker,1)
start=text.index('| Requirement | Expected Behavior | Actual Result | Status | Evidence | Remaining Work |')
end=text.index('## Explicit exclusions and denominator controls',start)
table='| Requirement | Expected Behavior | Actual Result | Status | Evidence | Remaining Work |\n|---|---|---|---|---|---|\n'
for row in rows:
    cells=[row['id']+' — '+row['requirement']+' ('+row['source']+')',row['expected'],row['actual'],row['status'],row['files']+'; '+row['evidence'],(row['findings']+': ' if row['findings'] else '')+row['remaining']]
    table+='| '+' | '.join(str(c).replace('|','/').replace('\n',' ') for c in cells)+' |\n'
text=text[:start]+table+'\n'+text[end:]
delta='''## Latest concurrent-delta verification

The final acceptance snapshot is main30cbb15, including the concurrently committed interactive workbenches and release-notes-v1.5.0.md. [LATEST_DELTA.json](LATEST_DELTA.json) proves only window.py, workspace_panels.py and test_workspace_panels.py differ in application/tests from the initial7230079 snapshot. No core/runner/parser/adapter repair appeared in that delta. [LATEST_TEST_RESULTS.json](LATEST_TEST_RESULTS.json), [latest-short.txt](latest-short.txt) and [latest-deep.txt](latest-deep.txt) retain full commands/results. [PROBES-latest.json](PROBES-latest.json) reproduces false health, no-op checksum, parser defaults, runner boundary, report mismatch and case collision on the newer tree. [LATEST_UI_PROBES.json](LATEST_UI_PROBES.json) adds stale-revision and hardcoded-export checks. The newer UI's four tests pass, increasing the short suite to90;13 deep-path failures remain. The source now claims releasev1.5.0, while package metadata remainsv0.1.0 and the release note names DB tables that do not match integration_store.py. Reconcile these claims; do not treat a commit title or release note as acceptance.

The initial UI screenshot/native RC evidence remains applicable to the unchanged jobs/adapters path. New widget tests verify rendering/construction and populated-field updates, not absent-field reset, calculation provenance or native solver correctness. Shared-service and evidence rules still apply to the new panels.

'''
text=text.replace('## All18 tool/resource status',delta+'## All18 tool/resource status',1)
text=text.replace('1. Codex resolves the missing referenced baseline','0. Close latest F19/F20: clear unspecified revision inputs, bind exports to actual parameters, and route/provenance numerical results through the shared core.\n1. Codex resolves the missing referenced baseline',1)
report.write_text(text,encoding='utf-8',newline='\n')

latest=Path(json.loads((E/'LATEST_DELTA.json').read_text())['snapshot'])
paths=['docs/release-notes-v1.5.0.md','docs/implementation-checklist.md','FINAL_IMPLEMENTATION_VERIFICATION.md','src/mendex_ui/window.py','src/mendex_ui/workspace_panels.py','tests/ui/test_workspace_panels.py']
records=[]
for p in paths:
    q=latest/p
    item={'path':p,'sha256':hashlib.sha256(q.read_bytes()).hexdigest()}
    if q.suffix=='.py':item['definitions']={n.name:n.lineno for n in ast.walk(ast.parse(q.read_text(encoding='utf-8-sig'))) if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
    records.append(item)
with (E/'LATEST_SOURCE_REVIEW.json').open('x',encoding='utf-8') as f:json.dump(records,f,indent=2)
print(json.dumps({'total':data['total'],'counts':data['counts'],'percentage':data['verified_completion_percentage']},indent=2))
