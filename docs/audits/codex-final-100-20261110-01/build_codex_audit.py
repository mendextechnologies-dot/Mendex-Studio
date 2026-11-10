"""Create-only independent audit artifacts. Does not import application code."""
from pathlib import Path
from collections import Counter
import ast,hashlib,json,re,subprocess,zipfile,xml.etree.ElementTree as ET

E=Path(__file__).resolve().parent
REPO=E.parents[2]
snapshot=json.loads((E/'SNAPSHOTS.json').read_text())
S={x['name']:Path(x['root']) for x in snapshot['items']}
old=json.loads((S['working']/'docs/audits/final-verification-20261110-01/REQUIREMENTS.json').read_text(encoding='utf-8'))
rows=old['rows'];excluded=old['excluded']
assert len(rows)==271
OUT=REPO/'docs/audits/FINAL_IMPLEMENTATION_VERIFICATION_CODEX.md'
assert not OUT.exists(), 'Preserve existing audit; choose a new Codex-named filename'
def write(path,text):
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:f.write(text)
def ev(name):return f'[evidence: {name}](codex-final-100-20261110-01/{name})'

docs=[]
for key in ('working','remediation'):
    for p in sorted(S[key].rglob('*')):
        if p.is_file() and '.git' not in p.parts and '.audit-tests' not in p.parts and (p.suffix in ('.md','.txt','.docx') or p.name in ('pyproject.toml','requirements-lock.txt')):
            docs.append({'snapshot':key,'path':p.relative_to(S[key]).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
sources=[]
for label,file in [('G13','Mendex_Engineering_Validation_Platform_Master_Guide_v1_3.docx'),('G14-G15','Mendex_Engineering_Studio_Two_Agent_Execution_Plan_v1_5.docx')]:
    p=Path(r'C:\Users\Sagar\Downloads')/file
    with zipfile.ZipFile(p) as z:tree=ET.fromstring(z.read('word/document.xml'))
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    text='\n'.join(''.join(x.itertext()) for x in tree.findall('.//w:p',ns))
    write(E/(label+'.txt'),text)
    sources.append({'label':label,'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'extracted':label+'.txt'})
newer=REPO/'docs/audits/FINAL_IMPLEMENTATION_VERIFICATION_ANTIGRAVITY.md'
write(E/'DOCUMENT_REVIEW.json',json.dumps({'sources':sources,'reviewed_inventory':docs,'later_audit_reviewed':{'path':str(newer),'sha256':hashlib.sha256(newer.read_bytes()).hexdigest()},'missing_baseline':'Referenced detailed architecture/UI-UXv1.0 was not supplied/located; no signed newer specification found'},indent=2))
defs={}
for p in (S['working']/'src').rglob('*.py'):
    tree=ast.parse(p.read_text(encoding='utf-8-sig'))
    defs[p.relative_to(S['working']).as_posix()]={n.name:n.lineno for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
write(E/'CODE_REFERENCES.json',json.dumps(defs,indent=2))

# Live-provider activation is explicitly deferred; readiness is tested CORE-038.
live=next(x for x in rows if x['id']=='CORE-039');rows.remove(live)
excluded.append({'id':live['id'],'requirement':live['requirement'],'gap':'Advanced/live AI provider activation explicitly excluded by final foundation; provider-neutral UNAVAILABLE readiness is assessed in CORE-038. No approved instruction activates a provider.'})
for row in rows:
    row['evidence']=row['evidence'].replace('main-short.txt','working-short.txt').replace('main-deep.txt','working-deep.txt').replace('PROBES-latest.json','PROBES-main.json')
    if row['id']=='CORE-077':
        row.update(actual='Agent2 merge exists, but Codex f2be079/0312f5a repairs, schema v5, shared previews and recovery are not in current main0f299dd.',remaining='Review/integrate Codex remediation with current adapter changes; resolve conflicts; run all acceptance checks on the actual combined commit and obtain owner sign-off.',findings='F21')
    if row['id']=='CORE-060':row['evidence']='PROCESS_TREE.json; tests/adapters/test_safe_runner.py'
    if row['id']=='CORE-070':
        row.update(expected='Parsed native result summaries integrated with job/evidence/report browser; advanced plotting remains deferred',actual='Raw/log artifacts and standalone parsers exist; no complete parsed-native-result handoff to Studio report.',remaining='Bind validated parser output, units and raw source hashes to job/evidence/report. Advanced waveform plots are not required by the narrow accepted scope.',findings='F14')
    if row['id']=='NEW-002':
        row.update(actual='Current main0f299dd lacks both f2be079 and later0312f5a; remediation113-test tree is separate.',remaining='Review/integrate the tested remediation plus current adapter changes, then reverify; candidate code is not completion of main.',findings='F21')
    if not row['id'].startswith('TOOL-'):continue
    _,tool,dim=row['id'].split('-');tool=int(tool);dim=int(dim)
    if tool in (8,9,10,11,18):
        # Configuration-only is approved scope. Paid runtime is not mandatory.
        row.update(status='PASS',evidence='OPTIONAL_SCOPE.json; PROBES-main.json:tool_health; working-short.txt',findings='',remaining='None within configuration/unavailable scope; licensed operation excluded until separately adopted.')
        if dim==1:row['actual']='Exact approved ID/category/optional_paid catalog entry verified.'
        elif dim==2:row.update(expected='Truthful configuration-only availability and unknown runtime version',actual='NOT_CONFIGURED with no claimed runtime version or verified operations; no installed/licensed operation claim.')
        elif dim==3:row.update(expected='Visible optional license/platform review boundary without entitlement claims',actual='Review-only reference persists; it does not activate software or imply entitlement. Windows metadata is present; runtime compatibility not asserted.')
        elif dim==4:row.update(expected='Configuration-only typed descriptor/health and unsupported-operation boundary',actual='Typed wrapper returns valid health and empty capabilities; unsupported job is refused before execution.')
        elif dim==5:row['actual']='Settings/license review reference survives a new service instance.'
        elif dim==11:row['actual']='Actionable unavailable health and UNSUPPORTED refusal; no purchase, download or activation.'
        elif dim==12:row.update(expected='Configuration-only regression/manual coverage',actual='All five stubs tested for persisted settings, unchanged unconfigured state and refused execution; startup passes.')
    elif tool in (12,16):
        row['evidence']='NATIVE_VERSION_CHECKS.json; NATIVE_COMPONENT_SMOKES.json; INSTALLED_CONNECTOR_BOUNDARIES.json; working-short.txt'
        if dim==2:row.update(status='PARTIAL',actual='Installed native version/CLI works; legacy registry READY conflicts with v1.5 default NOT_INSTALLED and configured version=None.',findings='F12',remaining='Unify discovery/version/operation state and do not equate executable presence with qualified operation readiness.')
        elif dim==3:row.update(status='UNVERIFIED',actual='Windows native component launch succeeds; full installed-distribution compatibility/license review not completed.',findings='F22',remaining='Review exact installed distribution/version terms and supported operation constraints; no entitlement/legal approval inferred.')
        elif dim==9:row.update(status='FAIL',expected='Native operation execution within approved tool role (CAD/export or notebook), through Studio',actual='Direct CAD STEP/notebook execution succeeds; configured Studio v1.5 connector has no operations and execute unconditionally raises NOT_INSTALLED.',findings='F12',remaining='Implement and verify the actual Studio operation/collection path; installation is no longer the blocker for these two tools.')
        elif dim not in (1,5):
            row['actual']='Native component is now available and manually runs, but Studio wrapper remains an unavailable stub with no complete operation/results path.'

counts=Counter(x['status'] for x in rows)
percentage=round(counts['PASS']/len(rows)*100,2)

# id, priority, owner, files, established root cause / limitation, exact task
F={
'F01':('P0','Antigravity adapters; Codex acceptance gate','src/integrations/v15_connector.py:LTspiceV15Connector.verify/PythonV15Connector.verify; src/integrations/adapters/base.py:verify_executable; src/mendex_core/integration_service.py:verify','READY is based on existence/static version/evidence strings. A non-executable LTspice fake passes the real application gate; missing Python path passes; a fake FreeCAD path also becomes legacy READY with version=None. None of these fakes was executed.','Bind verification to actual effective binary/hash/version/operation and retained smoke evidence; invalidate after configuration/version changes; add application-level negative tests.'),
'F02':('P0','Antigravity','src/integrations/v15_connector.py:DatasetV15Connector.verify/execute','No-input/no-resource checksum operation returns READY/SUCCEEDED with empty outputs/evidence. It computes no checksum. The controller reports integrity of its metadata, not proof of a dataset operation.','Implement real validated checksum/import; reject missing resource/input; separate reference-only Princeton hub from executable/import operations; supply source/release/license evidence.'),
'F03':('P0','Antigravity scientific data; Codex preset UI','src/integrations/datasets/magnet_dataset.py:load_json; switchloss_db.py:load_csv; datasets/fixtures/**; src/mendex_ui/workspace_panels.py:SemiconductorWorkspacePanel','Missing fields are replaced with N87/25C/100kHz/0.1T/0loss; unrelated CSV becomes a blank MOSFET. Upstream sample measurement/license provenance is not established. This is unsupported provenance/defaulting, not conclusive proof of fixture fabrication.','Require schema/units/ranges/source metadata; reject malformed/unrelated data; quarantine or label synthetic fixtures; obtain upstream source/version/checksum/license evidence before scientific use/presets.'),
'F04':('P0','Antigravity','src/integrations/runners/safe_runner.py:validate_command/run','Explicit nonmatching allowlist is ignored; runner overwrites an outside-workdir log sentinel; communicate buffers output before truncation. These are reproduced boundary failures, not hypothetical risks.','Enforce effective executable allowlist and confined fresh log paths; stream/cap output/resources while executing; preserve existing logs. Keep proven shell-free and Windows tree timeout behavior.'),
'F05':('P1','Antigravity','src/integrations/parsers/kicad_parser.py:parse_kicad_drc_json','Malformed non-report text returns all issue counts0 because a catch-all token-count fallback accepts unknown report format.','Reject unknown/malformed reports; return failure/NOT_EVALUATED; test valid clean and failing reports, then native installed-version parsing.'),
'F06':('P1','Codex','src/mendex_core/service.py:generate_report/validation_summary','Separate reads combine an old report spec/hash with a newer PASS row/spec/hash during deterministic concurrent edit.','Review/integrate bb524bc/f2be079 frozen DB read fix; rerun interleaving, rules, runs and report regressions on accepted main.'),
'F07':('P1','Codex','src/mendex_core/integration_service.py:submit/_run','REQUEST.JSON staged raw input is overwritten by request.json under Windows case rules; job still succeeds and integrity is false.','Integrate collision/alias/reserved/device-name and staged-input mutation checks; reject before staging; retain raw bytes.'),
'F08':('P1','Codex','src/mendex_core/service.py:workspace_path/record_validation/generate_report','Nested UUID paths trigger13 deeper-root failures while short paths pass. This is a Windows application robustness limitation; no global registry change was made.','Integrate reviewed compact new paths with legacy preservation; add clear path-budget/third-party limits; verify realistic Windows roots without moving frozen evidence.'),
'F09':('P1','Antigravity','src/integrations/v15_connector.py:LTspiceV15Connector.execute/PythonV15Connector.execute/GitV15Connector','Execute uses constructor path/sys.executable/self.exe instead of effective verified configuration. Git operates in process cwd and reports2.45.2.windows.1 versus actual2.48.1.windows.1. timeout_s is cast to int.','Use actual verified binary/version and requested workspace; preserve precise deadlines; keep immutable execution configuration and accurate runtime metadata.'),
'F10':('P1','Codex recovery; Antigravity process hooks','src/mendex_core/integration_service.py:cancel/shutdown; src/integrations/v15_connector.py:PythonV15Connector.execute/GitV15Connector.execute','Current main has only per-process cooperative events and no durable interrupted-owner recovery. Python cancellation is observed after its script finishes; LTspice now forwards the event.','Review/integrate conservative0312f5a metadata recovery, including active/unknown-owner/raw preservation and native retry guards; fix native event/state forwarding and qualify bounded child cleanup/shutdown separately.'),
'F11':('P1','Codex','src/mendex_ui/window.py:StudioWindow.__init__; src/mendex_ui/integration_panels.py:JobsPanel.start; src/mendex_core/integration_service.py:__init__','UI registers19 adapters including demo; fresh service/CLI has only demo. Jobs form hardcodes synthetic-echo; registration exceptions are swallowed.','Compose reviewed adapters through shared services; expose supported native operation/input selection and actionable registration errors; verify UI/CLI parity and native end-to-end path.'),
'F12':('P1','Antigravity implementations; Codex integration','src/integrations/v15_connector.py:UninstalledToolV15Connector; src/integrations/adapters/base.py:execute; adapters/freecad.py,jupyter.py,kicad.py,femm.py,qucs_s.py,openmodelica.py','Six wrappers have empty operations/unconditional unavailable execution. FreeCAD/Jupyter are installed and pass direct native probes, yet v1.5 default says NOT_INSTALLED and configured execute still raises NOT_INSTALLED. Other four binaries remain absent; missing operation code is an independent defect.','Implement generic detect/verify/launch/execute/collect for required roles, unify legacy/v1.5 registry semantics, then test actual versions and failure paths; request absent installations separately.'),
'F13':('P1','Codex contract owner; Antigravity consumers','src/mendex_core/integration_contracts.py; src/integrations/contracts.py; src/integrations/v15_connector.py; both adapter registries','Frozen1.5.0 UUID/string-provenance boundary coexists with1.0 string-ID/dict-provenance contracts and fallback tuples. Wrappers pass tests but do not establish one agreed compatibility policy.','Review/version an explicit compatibility/retirement strategy; run real adapters against canonical frozen schemas; never silently mutate frozen contracts.'),
'F14':('P1','Antigravity parsing/raw outputs; Codex report/manifest','src/integrations/v15_connector.py:LTspiceV15Connector.execute; src/mendex_core/integration_service.py:_finalize/export_report; src/integrations/parsers/ltspice_parser.py','Actual RC .raw/.op.raw/.log are now collected and hashed. Runner command log is omitted, raw waveforms are labelled derived, and parser/units/summary are not bound to Studio job/report.','Preserve complete required raw/log evidence, correct labels, runtime/code/parser/config versions and validated parsed summary handoff. Advanced plotting remains deferred.'),
'F15':('P2','Codex','src/mendex_core/service.py; src/mendex_ui/window.py','Create/edit/save/reopen/revision locks work. Deletion is intentionally unavailable; full native source revision/diff management is absent.','Resolve retention/deletion/file-version scope explicitly; implement only approved safe lifecycle operations or obtain a documented deferral; preserve frozen/raw evidence.'),
'F16':('P2','Codex consolidation; Antigravity evidence','docs/IMPLEMENTATION_STATUS.md; docs/TOOL_COMPATIBILITY.md; docs/ADAPTER_TEST_EVIDENCE.md; docs/release-notes-v1.5.0.md; pyproject.toml; src/mendex_core/integration_store.py; previous audit reports','Historical/unmerged/disabled/completed statements conflict; Git version, dataset verification and native integration assertions overreach actual paths. Release notev1.5.0 differs from package0.1.0 and names incorrect DB tables. Green90 tests do not negate reproduced failures.','Publish commit/command/version/hash-bound evidence and explicit current scope; reconcile package/schema/status docs prospectively; preserve historical reports; obtain real owner acceptance.'),
'F17':('P2','Codex; independent operator/environment','src/mendex_ui/window.py; integration_panels.py; src/mendex_core/launch.py; scripts/verify_install.ps1; docs/manual-acceptance.md','Normal startup/navigation/synthetic UI workflow passes. Actual interactive editor handoff, comprehensive keyboard/menu/assistive-tech/DPI and independent clean-machine checks are not completed in this audit.','Complete approved manual editor/accessibility/operator/install/rollback qualification; retain observed evidence. No installation was performed here.'),
'F18':('P1','Codex baseline coordination; Antigravity model qualification','Referenced Detailed Software Architecture/UI-UXv1.0; src/integrations/calculations/power_losses.py,winding_losses.py,transformer_design.py; generators/**','Referenced detailed specification remains unavailable. Local formula/string/positive-value tests do not independently qualify model domains, units, assumptions or engineering tolerances.','Obtain/resolve missing baseline; document valid domains/units/source assumptions and independent reference cases within approved generic scope; keep unqualified models NOT_EVALUATED.'),
'F19':('P1','Codex forms/service; Antigravity generator binding','src/mendex_ui/workspace_panels.py:TransformerWorkspacePanel.set_revision/export_femm_script; SemiconductorWorkspacePanel.set_revision; DCDCWorkspacePanel.set_revision','Unspecified revision keeps old36V/400V/.5A/150kHz. Calculated turns change but FEMM scripts remain identical because fixed24/1000turns are exported.','Clear missing inputs/results on context change; bind exports to frozen actual inputs and reviewed generator semantics, or explicitly block unqualified exports as0312f5a does.'),
'F20':('P1','Codex shared-service/evidence boundary; Antigravity data/model','src/mendex_ui/workspace_panels.py; src/mendex_core/service.py; datasets/fixtures/switchloss_sample.csv','Current UI directly calls calculators/parsers/writes scripts without shared core/CLI or persisted calculation provenance. It produces numbers with no selected product and loads unqualified scientific presets.','Integrate/review0312f5a shared revision-bound previews, explicit assumptions/provenance, append-only snapshots, stale/tamper reporting and blocked unqualified presets/exports; never convert preview success to engineering PASS.'),
'F21':('P1','Codex integrator; Antigravity review','Current main0f299dd vs codex/acceptance-remediation0312f5a; src/mendex_core/service.py,integration_service.py,preview_service.py,job_ownership.py; src/mendex_ui/workspace_panels.py','Codex fixes exist and have passing component regressions but remain outside current application. Candidate full suite has an inherited installed-tool assertion failure. No owner sign-off of one combined acceptance tree exists.','Review and integrate Codex work with current adapter changes; resolve test/config/contract differences and remaining defects; run all checks on one immutable final tree; obtain owner walkthrough/sign-off.'),
'F22':('P2','Antigravity compatibility; external reviewer/environment','Tool compatibility/license/distribution metadata; source documentation referenced by per-tool rows','Exact installed-distribution/license/platform compatibility review or required external binary/configuration is unavailable/unperformed for this boundary. Installed component success does not establish every native operation or entitlement.','Supply exact official distribution/version/terms/configuration and reviewed compatibility evidence for adopted operations; install only with authorization. Optional paid runtime remains excluded.'),
}

for row in rows:
    if row['status']=='PASS':
        row.update(priority='—',responsible_agent='—',root_cause='No gap within this tested boundary')
        continue
    ids=[x for x in row.get('findings','').split(',') if x in F]
    if not ids:
        if row['status'] in ('BLOCKED','UNVERIFIED'):ids=['F18' if row['id']=='CORE-081' else 'F17' if row['id'].startswith('CORE-') else 'F22']
        elif row['id'].startswith('TOOL-'):ids=['F12']
        else:ids=['F16']
        row['findings']=','.join(ids)
    priorities=[F[x][0] for x in ids]
    row['priority']=min(priorities)
    row['responsible_agent']='; '.join(dict.fromkeys(F[x][1] for x in ids))
    row['root_cause']='; '.join(F[x][3] for x in ids)
    # Every non-PASS has exact source-family references even where old RTM used shorthand.
    row['affected_files']='; '.join(F[x][2] for x in ids)
    if row['status'] in ('BLOCKED','UNVERIFIED'):
        row['root_cause']='Boundary not fully tested/qualified; '+row['actual']+' See cited evidence for established implementation causes separately.'
    row['corrective_action']=row['remaining'] if row['remaining'] else '; '.join(F[x][4] for x in ids)

write(E/'REQUIREMENTS.json',json.dumps({'primary_source_commit':'0f299ddd92f96e128fa2ed16a8d7ba74e34110c7','total_applicable':len(rows),'counts':dict(counts),'verified_completion_percentage':percentage,'excluded_count':len(excluded),'rows':rows,'excluded':excluded,'method':'PASS/applicable, zero partial credit; explicit optional commercial configuration scope; live advanced AI excluded'},indent=2,ensure_ascii=False))

tools=[
('SwitchLossDB','dataset','FAIL','Metadata and fixtures exist; no-input checksum succeeds; unrelated CSV accepted; authentic upstream provenance unresolved.','F02/F03'),
('MagNet Dataset','research dataset','FAIL','No-input READY/SUCCEEDED and invented defaults for missing measurement fields.','F02/F03'),
('MagNet ML Benchmarks','benchmark','FAIL','No actual verified benchmark/import/checksum operation; shared no-op wrapper.','F02'),
('KiCad','application','PARTIAL','Binary not found: native test BLOCKED. Operation bodies absent and malformed-report parser returns zero: implementation defects.','F05/F12'),
('FEMM','application','PARTIAL','Binary not found: native test BLOCKED. Generator/string fixtures are not an implemented v1.5 execute/collect operation.','F12/F18'),
('MagNet — Princeton University','research hub/resource','PARTIAL','Reference exists; overlapping names unresolved; generic checksum/READY wrongly represents reference-only scope.','F02'),
('LTspice','application','PARTIAL','Actual26.1.1.0 RC run/raw collection passes; false health/configuration/parsed-report/native UI gaps persist.','F01/F09/F11/F14'),
('PLECS','optional commercial','PASS','Configuration/unavailable guard scope verified; licensed execution not adopted/tested.','Configuration scope only'),
('MATLAB / Simulink','optional commercial','PASS','Configuration/unavailable guard scope verified; licensed execution not adopted/tested.','Configuration scope only'),
('Ansys Maxwell','optional commercial','PASS','Configuration/unavailable guard scope verified; licensed execution not adopted/tested.','Configuration scope only'),
('Ansys Icepak','optional commercial','PASS','Configuration/unavailable guard scope verified; licensed execution not adopted/tested.','Configuration scope only'),
('FreeCAD','application','PARTIAL','Direct1.1.4 version and generic STEP export pass. Studio v1.5 wrapper declares no operation and still raises NOT_INSTALLED.','F01/F12'),
('Qucs-S','application','PARTIAL','Binary not found and no complete generic v1.5 execution path.','F12'),
('OpenModelica','application','PARTIAL','Binary not found; product-like generator does not supply a tested generic operation.','F12/F18'),
('Python','runtime','PARTIAL','Actual3.13.7 scripts execute; missing-path READY, ignored configuration and delayed cancellation.','F01/F09/F10'),
('Jupyter Notebook','notebook application','PARTIAL','Direct notebook execution passes (jupyter_core5.9.1/notebook7.6.5); Studio wrapper has no operation and says NOT_INSTALLED.','F12'),
('Git','developer tool','PARTIAL','CLI component executes; actual2.48.1.windows.1 vs reported2.45.2.windows.1, wrong configured workspace/binary.','F09'),
('SolidWorks','optional commercial','PASS','Configuration/unavailable guard scope verified; licensed execution not adopted/tested.','Configuration scope only'),
]

text=f'''# Final implementation verification — Codex independent audit

Date: **10 November 2026**. Repository: `mendextechnologies-dot/Mendex-Studio`. Audit only; no application fixes, feature development, installation or deployment.

## Decision

**NO — IMPLEMENTATION INCOMPLETE.** Current application source was frozen at **main0f299ddd92f96e128fa2ed16a8d7ba74e34110c7** (including the latest FreeCAD/Jupyter detection/test changes). The worktree overlay was empty at capture because those changes were committed during the initial inspection. Separate Codex remediation **0312f5af10bfe43a4c48091920dfe33559ff0b4c** is tested as a comparison only; it is not in main and receives no completion credit for main.

This decision concerns the Studio **framework**, not deferred product certification or physical safety. Reproduced false readiness, invalid data/check results, uncontrolled log/runner boundaries, report/input corruption, unintegrated work and missing operation bodies prevent complete framework acceptance. Missing installations are separately BLOCKED. A passing short-path suite does not negate these defects. Missing baseline documentation and unperformed qualification also limit exhaustive verification, but the result is not merely insufficient evidence: concrete implementation failures exist.

| Metric | Result |
|---|---:|
| Total applicable normalized requirements / verification checks | {len(rows)} |
| Passed | {counts['PASS']} |
| Partially implemented | {counts['PARTIAL']} |
| Failed | {counts['FAIL']} |
| Blocked | {counts['BLOCKED']} |
| Unverified | {counts['UNVERIFIED']} |
| Blocked + unverified | {counts['BLOCKED']+counts['UNVERIFIED']} |
| Explicitly excluded checks, outside denominator | {len(excluded)} |
| Verified completion | **{percentage:.2f}%** |
| Studio core readiness | Functional foundation; essential report/path/input/recovery defects remain on current main |
| Tool integration readiness | All18 registered;5 optional stubs pass limited scope;0 complete native/research Studio integrations accepted |
| End-to-end readiness | Synthetic UI flow passes; native UI→job→parsed evidence→report path remains incomplete |

Calculation: **{counts['PASS']} / {len(rows)} ×100 = {percentage:.2f}%**. Only PASS earns credit. These are granular normalized obligations plus explicit requested verification checks; repeated documents are deduplicated, while per-tool dimensions stay separate. This is not a percentage of files or development effort. Tool checks strongly weight the metric. Every non-PASS row has affected files, cause/limitation, priority, responsible agent and corrective action in the matrix/machine-readable data. Unknown requirements in a missing document cannot be counted as verified.

## Baselines, document conflicts and exclusions

G13 = supplied master guide filenamev1.3, internalv1.0 control and finalv1.2 three-day addendum. Its explicit narrow foundation supersedes earlier fully automated pilot/timeline claims. G14 = Next Stepsv1.4 body in suppliedv1.5 DOCX; G15 = two-agent§9 addendum. G15 supersedes earlier role assignment: Codex owns UI/services/contracts/DB/integrator; Antigravity owns adapters/runner/parsers/scientific data. Release-notes-v1.5.0, current checklists/handoffs, architecture/rules/contracts/README, previous audits and the separate Codex remediation document were reviewed. Source extracts/hash inventory: {ev('DOCUMENT_REVIEW.json')}; immutable source inventory: {ev('SOURCE_INDEX.json')}; function-line index: {ev('CODE_REFERENCES.json')}.

The referenced **Detailed Software Architecture/UI-UX Specificationv1.0 was not supplied or located**. Its full compliance is BLOCKED; do not assert that every unavailable clause is met. No newer signed specification/owner sign-off was found. A release note or an agent's provisional acceptance statement is not independent owner acceptance. Earlier records contain conflicting versions, completed labels and percentages; their contents are preserved rather than overwritten.

Explicit exclusions remain enterprise/cloud/ERP, CI/CD/deployment, hardware control, manufacturing/safety approval, product-specific design and advanced AI. Basic HTML/JSON reports are in scope; broader pilot DOCX/PDF/signing/advanced plots are deferred. Live AI provider activation is explicitly deferred; the required provider-neutral UNAVAILABLE readiness boundary is tested (CORE-038). This corrects the prior matrix's counting of live provider activation as an in-scope unverified feature; the excluded row is retained below, not silently dropped.

**Optional paid scope:** G14 phase6 and G15 allow configuration-only/unavailable stubs. Their active checks assess truthful unknown-version/license-review state, persisted settings, typed health/capability boundary, diagnostic/refusal and nonblocking startup. Actual paid licensing/runtime remains explicitly excluded until adopted; it is not counted BLOCKED against100% of a configuration-only scope and is never called operational. All five optional stubs were explicitly tested beyond file/class existence: {ev('OPTIONAL_SCOPE.json')}. Source/licensing qualification for mandatory research imports remains incomplete and separately assessed.

Earlier recommendations such as a richer standards-applicability visualization are retained as proposed backlog/owner scope decisions, not silently elevated into approved numerical compliance or certification functionality. The existing standards profile/rules remain metadata/guidance; no automatic standards approval is claimed. Native source-version/deletion requests and detailed UI readiness remain visible in their respective matrix rows and need explicit retention/scope decisions if deferred.

## Repository integration boundary

{ev('SNAPSHOTS.json')} identifies working/current-main, committed-main, separate remediation and released2055673. Current main already contains merge076d017, interactive UI and the later adapter search/test changes. It does **not** contain bb524bc/0312f5a: frozen report reads, Windows alias guards, compact paths, schema v5, traceable shared previews and conservative interrupted-owner recovery are separate candidate work. Both agents have remaining tasks. Candidate test success cannot establish that completed work is integrated into the current application.

The new detection commit extends search paths and changes the test to allow READY for now-installed FreeCAD/Jupyter. It does not implement their Studio execution bodies or bind READY to a smoke record. A fresh negative probe still makes a fake non-executable FreeCAD file READY/version=None: {ev('LEGACY_FALSE_READY.json')}. The file was never executed.

## Actual verification commands and outcomes

Environment observed: Windows11 build26300, Python3.13.7, Git2.48.1.windows.1. Existing interpreter: `C:/Mendex studio/.venv/Scripts/python.exe`. Each child used snapshot/src PYTHONPATH, PYTHONDONTWRITEBYTECODE=1, offscreen Qt and disabled pytest plugin autoload. No dependencies were installed or upgraded. Fresh source archives were locally git-initialized solely for tests that require a Git working directory; no global Git settings changed.

| Frozen tree | Command/path regime | Actual outcome |
|---|---|---|
| Current main0f299dd | pytest, short temp | **90 passed in10.04s** |
| Current main0f299dd | pytest, deep snapshot temp | **13 failed,77 passed in9.47s** |
| Separate remediation0312f5a | pytest, short temp | **112 passed,1 failed in12.93s** |
| Separate remediation0312f5a | pytest, deep temp | **112 passed,1 failed in13.30s** |
| Released2055673 | pytest, short temp | **28 passed in3.34s** |

Exact command pattern: existing interpreter `-m pytest -q -p no:cacheprovider --basetemp <fresh path>`; exact arguments, CWDs, elapsed times and stdout/stderr are retained in {ev('TEST_RESULTS.json')}, {ev('working-short.txt')}, {ev('working-deep.txt')}, {ev('remediation-short.txt')}, {ev('remediation-deep.txt')} and {ev('released-short.txt')}. The candidate failure is the inherited `test_missing_tools_never_false_ready` assertion after FreeCAD installation; current main's modified test now permits its READY state. Do not hide that candidate failure or treat relaxed expectations as verified integration. Core legacy tests run in current main and pass at short paths; full Windows compatibility does not pass.

All current/candidate/released desktop startup commands `python -m mendex_ui --root <fresh root> --smoke-test` exited0. Existing current `scripts/v15_codex_smoke.py` exited0 and exercised synthetic UI/job/cancel/report components: {ev('UI_RESULTS.json')}. Font-loaded screenshots were visually inspected: {ev('screenshots/jobs.png')}, {ev('screenshots/tool-center.png')}, {ev('screenshots/evidence.png')}. JobsPanel still offers only synthetic execution; the screenshot does not qualify native work.

Additional independent probes: {ev('targeted_verification.py')}, {ev('PROBES-main.json')}, {ev('verify_latest_ui.py')}, {ev('LATEST_UI_PROBES.json')}. The report race, raw input collision, fake readiness, no-op checksum, malformed parser/default measurements and outside log overwrite are reproduced against the frozen current tree. Only fresh audit-owned sentinels were overwritten. Existing user/raw evidence and application code were not changed.

Windows process-tree timeout actually kills a benign audit-owned child: {ev('PROCESS_TREE.json')}. This positive component is acknowledged. Python connector cancellation still waits for its benign script to finish; raw elapsed/event values are in PROBES-main.json. LTspice now forwards the cancel event; the Python issue is not generalized to that repaired call.

### Real native components, distinct from Studio integration

- **LTspice26.1.1.0:** exact existing generic RC fixture executes through the reviewed-registration hook; raw/log files collected and hashed. Independent file version: {ev('INSTALLED_LTSPICE_VERSION.json')}. Request/result/manifest/actual output hashes are in PROBES-main.json and `codex-final-100-20261110-01/native-rc/`. Software execution succeeds; parsed result/report/UI/config/readiness gaps remain. No engineering tolerance/physical validity is asserted.
- **FreeCAD1.1.4:** direct version command and generic1×1×1 software-fixture solid export both exit0; retained STEP starts ISO-10303-21. User/system config files are directed to a fresh scratch directory. This is generic component verification, not a product model or a Studio adapter job.
- **Jupyter:** version lists jupyter_core5.9.1, notebook7.6.5 and nbconvert7.17.2. A minimal notebook with a fixed software marker executes via nbconvert; output confirms the existing virtual-environment interpreter. Runtime/config directories are scratch paths. Nonfatal runtime warnings are retained; no notebook engine integration is inferred.
- FreeCAD/Jupyter native commands, scripts/notebooks, stdout/stderr and SHA-256 are retained in {ev('NATIVE_VERSION_CHECKS.json')}, {ev('NATIVE_COMPONENT_SMOKES.json')} and `codex-final-100-20261110-01/native-components/`. Their Studio v1.5 wrappers still declare zero operations and raise NOT_INSTALLED even when supplied an existing executable: {ev('INSTALLED_CONNECTOR_BOUNDARIES.json')}. These two tools are **installed with implementation gaps**, not blocked merely by absent binaries.

## All18 approved tools/resources

All18 catalog entries are verified present. Five optional commercial **configuration guards** pass their approved narrow scope. Zero native/research entries receive an unconditional fully operational Studio integration claim. Standalone success of installed components is acknowledged separately; Python/Git/Jupyter are not relabelled as physically validated engineering solvers.

| # | Tool/resource | Correct role | Status within scope | Actual result / remaining gap | Findings |
|---|---|---|---|---|---|
'''
for i,(name,role,status,result,f) in enumerate(tools,1):text+=f'| {i} | {name} | {role} | {status} | {result} | {f} |\n'
text+='''
For missing KiCad/FEMM/Qucs-S/OpenModelica, installation is an external BLOCKED check. Empty/unconditional-unavailable execute methods are independently FAIL checks. Commercial PASS means only configuration/unavailable scope; no licensed execution was attempted. Dataset/benchmark/reference entries are not executable installations. Per-tool checks follow below; simulation-inapplicable resource dimensions and optional unlicensed operation dimensions are explicitly excluded.

## Architecture, integrity and ownership findings

The main UI/CLI share StudioService for legacy products/specs/revisions/manual evidence, and v4 additive migration/backup behavior works in short-path regressions. Data-only plugin boundaries and unavailable default AI are useful foundations. Current engineering workbench calculations bypass that service and do not retain calculation provenance; the separate remediation branch addresses this but is unmerged. Multiple adapter registries/contract families and UI-only registration leave inconsistent availability and interfaces.

Main still has report reads across changing snapshots, case-sensitive reserved-name checks on Windows, incomplete native job recovery, hardcoded version/configuration behavior, loose parser defaults, and incomplete native operation bodies. These defects are framework correctness issues, independent of product-specific engineering certification.

Severity is tied to acceptance consequences: P0 for reproducible false verification, scientific data invention-by-default and execution/evidence boundary violations; P1 essential correctness/integration; P2 operational/UX/documentation/qualification. Other reports use different granularities/severities. Green90 tests are not evidence that P0 defects are absent. No agent-generated provisional acceptance statement substitutes for the owner's explicit approval.

'''
for fid,(priority,owner,files,cause,action) in F.items():
    text+=f'### {fid} — {priority}\n\n**Responsible agent:** {owner}.\n\n**Affected files/modules:** `{files}`.\n\n**Established cause / evidence limitation:** {cause}\n\n**Exact corrective action:** {action}\n\n'

text+='''## Requirement-by-requirement traceability

All rows assess the current application, not unmerged candidate code. PASS is restricted to the stated tested boundary. Every non-PASS lists its owner, priority, files, cause/limitation and exact next action; finding IDs link to the detailed explanations above. Root cause is marked as incomplete testing/external qualification for BLOCKED/UNVERIFIED rather than invented. Source labels G13/G14/G15 refer to the documents defined above; audit/user checks are explicitly included. Canonical machine-readable rows and totals: [REQUIREMENTS.json](codex-final-100-20261110-01/REQUIREMENTS.json).

| ID / requirement / source | Expected behavior | Actual result | Status | Evidence | Priority / responsible agent | Affected files / established cause | Exact corrective action |
|---|---|---|---|---|---|---|---|
'''
for row in rows:
    nonpass=row['status']!='PASS'
    cells=[row['id']+' — '+row['requirement']+' ('+row['source']+')',row['expected'],row['actual'],row['status'],row['evidence'],row['priority']+' / '+row['responsible_agent'],(row.get('affected_files',row['files'])+'; '+row['root_cause']) if nonpass else row['files'],(row['findings']+': ' if row.get('findings') else '')+(row.get('corrective_action',row['remaining']))]
    text+='| '+' | '.join(str(x).replace('|','/').replace('\n',' ') for x in cells)+' |\n'

text+='''
## Explicit exclusions / superseded scope

These checks are preserved but excluded from the denominator. They are not reclassified PASS. The current request's no-development/no-install/no-overwrite restrictions take precedence over embedded document implementation task briefs.

| ID | Excluded requirement/check | Explicit scope reason |
|---|---|---|
'''
for row in excluded:text+=f"| {row['id']} | {row['requirement']} | {row['gap']} |\n"

text+='''
## Exact agent-wise remaining work and dependencies

**Codex — can proceed independently once development is authorized:** review/integrate0312f5a/bb524bc (F06–F08,F19–F21), preserve old workspaces/raw evidence, and retain schema-v5 backup/downgrade behavior. Complete shared UI/CLI adapter composition, actionable hook errors and native operation/input selection after corrected adapter handoff (F11). Integrate safe interrupted-owner metadata recovery while leaving unknown/legacy/live owners untouched; native child shutdown remains separate (F10). Resolve contract compatibility/versioning with Antigravity (F13). Complete approved lifecycle/source-file/standards-scope decisions, accessibility/editor/operator checks and current documentation/versioning (F15–F18). A blocked unsafe export is truthful groundwork, not a completed qualified generator. Do not declare native export functionality complete merely because the candidate disables it.

**Antigravity — before acceptance:** fix bound health/version/configuration and negative readiness cases (F01,F09); replace no-op checksum/defaulting with authentic valid data/provenance (F02,F03); enforce executable/log/resource controls (F04); reject malformed reports (F05); implement required generic operation/collection bodies for the six incomplete wrappers, particularly already-installed FreeCAD/Jupyter (F12); forward cancellation/map statuses and supply child process evidence (F10); complete raw/log/parser/units/report handoff and independently reviewed calculation/generator assumptions (F14,F18,F19). Supply per-operation source/version/command/input/output/checksum/license constraints and failure tests; commercial runtime can remain excluded.

**Joint, dependency ordered:** freeze/resove the missing detailed baseline and scope; close P0 failures in parallel; review/version the shared boundary; integrate both workstreams on one branch; run contract→adapter→core/UI/integration/regression and targeted negative/deep-path/native end-to-end cases on that exact immutable tree. Request absent tools/installations only when necessary and authorized. Complete one authentic data workflow and required supported extended connector workflow, plus independent operator/workstation qualification and actual owner walkthrough/sign-off. Full verification requires every applicable row PASS or an explicit approved scope amendment, not silent deletion of blocked checks. Preserve all historical evidence.

## Explicit acceptance answers

1. **Is everything from the latest documentation implemented? NO.** Main lacks the separate Codex remediation and multiple required native/data operations.
2. **Are all mandatory features working? NO.** Current report/input/path correctness and truthful verification fail independent probes.
3. **Are required engineering integrations operational within documented scope? NO.** Optional configuration stubs pass their narrow scope; installed native components work in isolation, but required Studio operation/evidence/UI paths remain incomplete.
4. **Are there pending Codex or Antigravity tasks? YES.** Exact assigned actions appear per non-PASS row and in F01–F22/backlog above.
5. **Are there critical bugs or architectural issues? YES.** P0 false verification/data/runner boundaries and essential P1 integrity/integration defects are reproduced; missing external software is separately identified.
6. **Ready for formal framework acceptance? NO.** Useful working foundations are verified, but framework completion and integration are not. No industrial/product certification is required to reach this negative conclusion.

## Preservation and limits

Application code, dependencies, frozen contracts, released baselines and existing audit reports were not modified by this audit. No software was installed/upgraded, no global settings were changed, no CI/CD/deployment/hardware control or product-specific development was started. Fresh temporary workspaces and generic native/software fixtures were created solely for verification; raw actual outputs are retained with hashes. Prior user/raw evidence was not overwritten. New report filename includes CODEX as requested; other agents' reports are preserved. A later documentation-only commit may include reports/evidence; final source-delta observation identifies any later unverified application changes.

The missing detailed baseline, unavailable native applications and unperformed human/license/platform qualification remain limitations, not fabricated passes. The result is a functional implementation audit, not exhaustive penetration testing, legal advice or engineering-model certification. No fixes are authorized by this report.

**Final conclusion: NO — IMPLEMENTATION INCOMPLETE.**
'''
write(OUT,text)
print(json.dumps({'report':str(OUT),'total':len(rows),'counts':dict(counts),'excluded':len(excluded),'percentage':percentage},indent=2))
