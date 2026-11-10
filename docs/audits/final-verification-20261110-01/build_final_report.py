"""Generate verification documentation only; create-only output files."""
from pathlib import Path
from collections import Counter
import ast, hashlib, json, re, subprocess, zipfile, xml.etree.ElementTree as ET

E=Path(__file__).resolve().parent
BASE=E.parents[2]
MAIN=BASE/'.mendex/qa/final-verification-20261110-01/main'
CODEX=BASE/'.mendex/qa/final-verification-20261110-01/codex'
OLD=Path(r'C:\Mendex studio audit\docs\audits\evidence\REQUIREMENTS.json')
original=json.loads(OLD.read_text(encoding='utf-8'))['rows']
evidence='docs/audits/final-verification-20261110-01/'
def write(path,text):
    if Path(path).exists() and Path(path).read_text(encoding='utf-8') == text:
        return  # Preserve identical evidence from this generator's earlier run.
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:f.write(text)
def link(name):return f'[{name}]({name})'

sources=[]
for key,path in [('G13',Path(r'C:\Users\Sagar\Downloads\Mendex_Engineering_Validation_Platform_Master_Guide_v1_3.docx')),('G14-G15',Path(r'C:\Users\Sagar\Downloads\Mendex_Engineering_Studio_Two_Agent_Execution_Plan_v1_5.docx'))]:
    with zipfile.ZipFile(path) as z:tree=ET.fromstring(z.read('word/document.xml'))
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    text='\n'.join(''.join(p.itertext()) for p in tree.findall('.//w:p',ns))
    write(E/(key+'.txt'),text)
    sources.append({'label':key,'source':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'paragraphs':len(tree.findall('.//w:p',ns))})
docs=[]
for p in sorted(MAIN.rglob('*')):
    if p.is_file() and '.git' not in p.parts and (p.suffix in ('.md','.txt','.docx') or p.name in ('pyproject.toml','requirements-lock.txt')) and '.audit-tests' not in p.parts:
        docs.append({'path':p.relative_to(MAIN).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
write(E/'DOCUMENT_BASELINE.json',json.dumps({'sources':sources,'repository_documents':docs,'missing':'Referenced Detailed Software Architecture/UI-UX Specification v1.0 not supplied or located; no newer approved specification located','approval_limit':'Plan labels/implementation claims are not signed acceptance records'},indent=2))
refs={}
for p in (MAIN/'src').rglob('*.py'):
    tree=ast.parse(p.read_text(encoding='utf-8-sig'))
    refs[p.relative_to(MAIN).as_posix()]={n.name:n.lineno for n in ast.walk(tree) if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))}
write(E/'CODE_REFERENCES.json',json.dumps(refs,indent=2))

findings=[
('F01','P0','Antigravity; Codex verification acceptance','False READY for missing/non-executable binaries','src/integrations/v15_connector.py:LTspiceV15Connector.verify, PythonV15Connector.verify; src/mendex_core/integration_service.py:verify','A fake non-executable .exe is accepted as READY by the real application gate; missing Python path also READY. No fake binary was executed.','Existence/static version and evidence URI strings substitute for actual configured-binary/version/operation smoke proof.','Probe real effective binary/version safely; bind readiness to retained operation-specific smoke evidence/configuration hash; invalidate on change; reject fake and missing paths.'),
('F02','P0','Antigravity','Dataset checksum operation is a no-op','src/integrations/v15_connector.py:DatasetV15Connector.verify/execute','No resource or input: READY and SUCCEEDED, outputs=[], evidence_paths=[], controller integrity=true. All four research entries share this connector.','execute returns a literal successful JobResult without loading data or computing/checking a checksum.','Implement real validated resource/import/checksum workflow; reject no-input requests; keep research hub reference-only; resolve MagNet overlap and upstream license/version provenance.'),
('F03','P0','Antigravity','Scientific fields silently invented when absent','src/integrations/datasets/magnet_dataset.py:load_json; switchloss_db.py:load_csv; datasets/fixtures/**','Empty MagNet row becomes N87,25C,100kHz,0.1T,sinusoidal,0loss. Unrelated CSV becomes a blank MOSFET record. Shipped scientific fixtures have no demonstrated upstream release/measurement chain.','Parser defaults and ignored unknown fields replace required scientific inputs; supplied source/license strings do not establish provenance. Origin fabrication is not conclusively established.','Require schema/units/ranges/source metadata; reject missing/unrelated content; quarantine or label synthetic fixtures; provide authentic upstream release/checksum/license evidence before scientific use.'),
('F04','P0','Antigravity','Runner allowlist and resource/log boundaries incomplete','src/integrations/runners/safe_runner.py:validate_command/run','Explicit nonmatching allowlist still accepts Python; outside-workdir log overwrites a fresh audit sentinel. communicate buffers output before5MiB truncation.','allowlist_patterns never consulted; log path unconfined and opened with w; capture limit applied after buffering.','Enforce executable allowlist, confined write-once logs and streaming byte/resource limits. Keep verified shell-free execution and Windows tree termination.'),
('F05','P1','Antigravity','Malformed KiCad report appears clean','src/integrations/parsers/kicad_parser.py:parse_kicad_drc_json','Text THIS IS NOT A KICAD REPORT returns all issue counts0.','Catch-all text fallback counts a token without verifying a report format.','Reject malformed/unknown schemas; report failure/NOT_EVALUATED; verify valid nonzero and zero reports with native KiCad when available.'),
('F06','P1','Codex','Report snapshot race remains on main','src/mendex_core/service.py:generate_report/validation_summary','Frozen report specification has vout=None and old hash, while a displayed PASS row has vout24 and a different hash.','Separate reads of revision/product/validation/rules can span a concurrent edit.','Review and integrate f2be079 report transaction fix into the acceptance tree; rerun deterministic interleaving and frozen rule/run tests. Main currently lacks it.'),
('F07','P1','Codex','Windows reserved case collision overwrites staged input','src/mendex_core/integration_service.py:submit/_run','REQUEST.JSON is overwritten by request.json; job SUCCEEDED with evidence_integrity=false and changed staged raw bytes.','Reserved-name comparison is case-sensitive on a case-insensitive filesystem; input bytes not checked before success.','Review/integrate f2be079 collision/raw-input checks; reject device/trailing-dot/case aliases and duplicates before staging; test success cannot accompany modified inputs.'),
('F08','P1','Codex','Windows long-root regression','src/mendex_core/service.py:workspace_path/record_validation/generate_report; src/mendex_core/evidence.py','Main short86 pass; deep13 fail/73 pass due path creation/read failures including WinError206. Codex short/deep96 pass.','Repeated product/revision/evidence UUID directory nesting exceeds legacy Windows path limits at realistic nested roots.','Integrate reviewed compact-path mitigation from f2be079 with legacy compatibility; add explicit path-budget errors/third-party qualification. Do not move frozen baseline files automatically.'),
('F09','P1','Antigravity','Execution does not honor verified configuration/workspace/version consistently','src/integrations/v15_connector.py:LTspiceV15Connector.execute, PythonV15Connector.execute, GitV15Connector','LTspice uses constructor path, Python uses sys.executable, Git uses self.exe and process cwd. Git claims2.45.2.windows.1 vs actual2.48.1.windows.1. Timeouts cast to int.','Execution/configuration and health use different sources; static tested versions; request context not uniformly consumed.','Bind execution to effective verified settings and requested workdir; query actual versions; preserve fractional deadlines and terminal statuses.'),
('F10','P1','Antigravity; Codex queue/recovery','Native cancellation/recovery incomplete','src/integrations/v15_connector.py:PythonV15Connector.execute/GitV15Connector.execute; src/mendex_core/integration_service.py:cancel/shutdown','Python cancel event set0.15s, returns after1.278s with ExecutionCancelled, after script completion. LTspice now forwards the event. No interrupted-job reconciliation.','Python/Git omit cancel_event; service has cooperative per-process events, no durable process/session lease/recovery.','Forward cancel/deadlines and map runner states; define safe owner/session-based interrupted-job recovery and bounded shutdown without marking another process job abandoned.'),
('F11','P1','Codex','Native integration is UI-startup-only and job form remains synthetic','src/mendex_ui/window.py:StudioWindow.__init__; src/mendex_ui/integration_panels.py:JobsPanel.start; src/mendex_core/integration_service.py:__init__','UI adds18 connectors, but CLI/service default has only studio-demo. Start button constructs studio-demo/synthetic-echo. Registration exceptions are silently swallowed.','Registration is placed after panel construction in UI rather than a shared composition boundary; no operation/tool selector or diagnostics on hook failure.','Register reviewed connectors through shared services; expose supported tool/operation/input selection; report hook errors; verify UI and CLI native job parity.'),
('F12','P1','Antigravity','Six native adapter operation bodies missing, independently of installation','src/integrations/v15_connector.py:UninstalledToolV15Connector; src/integrations/adapters/base.py:execute; kicad.py; femm.py; freecad.py; qucs_s.py; openmodelica.py; jupyter.py','v1.5 supported_operations=[] and execute always raises FileNotFoundError, even for a configured file. Legacy classes mainly declare candidates/operations and inherit NotImplementedError.','Unavailable stub/generator is used in place of a generic execution/collection implementation.','Implement approved generic version-specific operations; then request/install external prerequisites separately and run native positive/negative smoke tests. Missing binary is BLOCKED; missing code is FAIL.'),
('F13','P1','Codex interface owner; Antigravity consumers','Duplicate contract/registry families remain','src/mendex_core/integration_contracts.py; src/integrations/contracts.py; src/integrations/v15_connector.py; src/integrations/adapters/registry.py; src/mendex_core/adapters/registry.py','Schema1.5 UUID/string-provenance boundary coexists with schema1.0 string IDs/dict provenance and fallback tuples. Wrapper tests pass but not one agreed real-adapter boundary.','New parallel contracts/packages were introduced without a documented accepted compatibility/retirement strategy.','Agree a reviewed compatibility/versioning strategy; test every real connector against frozen schemas; never silently mutate frozen baselines.'),
('F14','P1','Antigravity raw/parse evidence; Codex manifest/report metadata','Native evidence/report path remains partial','src/integrations/v15_connector.py:LTspiceV15Connector.execute; src/mendex_core/integration_service.py:_run/_finalize/export_report; src/integrations/parsers/ltspice_parser.py','RC .raw/.op.raw/.log now collected and hashed: improvement confirmed. Runner log is omitted; raw waveforms are labelled derived; parsing/units/waveform summary not integrated into JobResult/report.','Collector now scans recursively but orchestration categorizes outputs generically and trusts declared evidence; no native parsed-result pipeline.','Retain command/runner logs and every required raw artifact; distinguish raw/derived accurately; bind environment/parser/code versions and validated parsed summaries to report without engineering approval claims.'),
('F15','P2','Codex','Incomplete workspace lifecycle/native source management','src/mendex_core/service.py; src/mendex_ui/window.py','Create/edit/save/reopen/revision locks work. Delete is intentionally unavailable; native CAD source version/diff and revision-copy workflows absent.','Foundation supplies filesystem paths and metadata snapshots only.','Resolve lifecycle/retention acceptance scope; implement only approved delete/archive/source-management operations while preserving frozen/raw evidence.'),
('F16','P2','Codex; Antigravity evidence inputs','Documentation and acceptance claims do not match current state','docs/IMPLEMENTATION_STATUS.md; docs/INTEGRATIONS.md; docs/known-limitations.md; docs/TOOL_COMPATIBILITY.md; docs/ADAPTER_TEST_EVIDENCE.md; docs/V15_INTEGRATION_HANDOFF.md; docs/audits/**','Some docs say unmerged/disabled; main has merge/UI registration. Agent2 claims57 tests and old OS/Git; final-main suite86. Prior audit percentages count partial completion differently. No consolidated owner acceptance found.','Historical statements are not clearly distinguished from current acceptance; raw evidence/commit binding incomplete.','Update current status/checklist prospectively, preserve historical evidence; publish exact commits/commands/raw hashes/limits and owner walkthrough outcome. Recompute only strict verified percentages.'),
('F17','P2','Codex','UX/editor/clean-machine qualification incomplete','src/mendex_ui/window.py; integration_panels.py; src/mendex_core/launch.py; scripts/verify_install.ps1; docs/manual-acceptance.md','14 pages and synthetic UI smoke pass. Menus/keyboard/assistive-tech/high-DPI and real VS Code interactive handoff not requalified; fresh install/second machine not run.','Offscreen fixture tests and launch mocks cannot establish operator or deployment-machine acceptance.','Complete documented manual accessibility/editor/operator checks; arrange approved clean-machine qualification. No install performed during verification.'),
('F18','P1','Codex baseline coordination; Antigravity model validity','Missing referenced specification and unqualified calculation/model claims','G14§1 reference to detailed architecture/UI-UXv1.0; src/integrations/calculations/power_losses.py, winding_losses.py, transformer_design.py; src/integrations/generators/**','Referenced detailed spec not supplied/located. Skin-depth/Dowell/flyback helpers have local unit tests, not independently approved engineering domain/units/assumptions. Flyback models/defaults require generic-scope review.','Missing requirements baseline; partial numerical coverage and undocumented engineering assumptions are not engineering qualification.','Obtain/resolve missing approved baseline; document reference domains/units/tolerances and independent benchmarks; quarantine unqualified outputs and product-specific work outside generic scope.'),
]

byid={x[0]:x for x in findings}
mapping={'IMPLEMENTED & VERIFIED':'PASS','IMPLEMENTED BUT UNVERIFIED':'UNVERIFIED','PARTIALLY IMPLEMENTED':'PARTIAL','NOT IMPLEMENTED':'FAIL','BLOCKED':'BLOCKED'}
rows=[];excluded=[]
core_updates={
12:('FAIL','Deletion is intentionally unavailable; create/edit/reopen works.','F15'),
14:('PARTIAL','Filesystem paths/specification snapshots exist; native CAD version/diff absent.','F15'),
21:('UNVERIFIED','Basic navigation/widgets tested; complete menu/keyboard/accessibility/DPI acceptance not performed.','F17'),
22:('PARTIAL','Synthetic work is asynchronous; native cancellation/shutdown not uniformly bounded.','F10'),
29:('FAIL','Invalid DRC text and missing scientific fields produce clean/default numerical values.','F03,F05'),
32:('FAIL','REQUEST.JSON staged input is overwritten; main job still succeeds.','F07'),
34:('FAIL','Main report combines old input snapshot with newer PASS row.','F06'),
36:('UNVERIFIED','Shared launcher/mocks pass; real interactive editor handoff not repeated.','F17'),
39:('UNVERIFIED','Provider-neutral unavailable interface tested; no live provider configured/tested. Advanced AI is excluded; this row is connection-readiness verification only, not a demand to enable it.','F17'),
41:('PARTIAL','Structured service errors exist; UI registration failures are swallowed and health claims misleading.','F01,F11'),
42:('FAIL','13 deeper-root failures, versus86 short-root passes.','F08'),
44:('BLOCKED','No approved clean second workstation/operator available; installation would change environment.','F17'),
46:('PARTIAL','Checklist exists but completion/state statements conflict with measured main.','F16'),
50:('PARTIAL','Independent verification report produced; no owner-signed acceptance matrix.','F16'),
52:('FAIL','Fake binary and missing path become READY at application boundary.','F01'),
54:('PARTIAL','Codex freeze intact; duplicate Agent2 contracts and fallback types persist.','F13'),
58:('PARTIAL','Traversal/size guards pass; case-insensitive reserved collisions remain on main.','F07'),
59:('FAIL','Explicit nonmatching executable allowlist is ignored.','F04'),
60:('PASS','Benign parent/child timeout kills child; shell=False confirmed.',''),
61:('FAIL','Runner writes outside cwd, overwrites sentinel, buffers output before truncation.','F04'),
62:('PARTIAL','Synthetic timeout/cancel/retry pass; Python cancellation waits for completion.','F09,F10'),
63:('FAIL','No durable interrupted-job/process ownership reconciliation.','F10'),
64:('PARTIAL','UI registers connectors; default service/CLI does not, and Jobs.start is hardcoded synthetic.','F11'),
65:('PASS','Existing synthetic UI→job→evidence→draft report script passes.',''),
66:('PARTIAL','Native RC raw/log files now collected; runner command log omitted and completeness not operation-enforced.','F14'),
67:('PARTIAL','Hashes/review state present; native raw .raw files labelled derived.','F14'),
68:('PARTIAL','Per-job code/runtime/parser/configuration verification record not uniformly bound.','F09,F14'),
70:('PARTIAL','Raw headers/log parser exists; parsed result/waveform/report integration incomplete.','F05,F14'),
71:('PARTIAL','Python/Git components execute; configuration/workspace/version/cancellation defects persist.','F09,F10'),
72:('FAIL','No valid source/license/checksum-backed scientific import; no-input checksum job succeeds.','F02,F03'),
74:('PASS','Separate worktrees exist; current snapshot boundaries recorded. Untracked UI is not accepted code.',''),
75:('PARTIAL','Multiple adapter registries and incompatible contract families remain.','F13'),
76:('PARTIAL','Agent2 source and handoff merged; documented environment/raw verification assertions not consistently reproducible.','F16'),
77:('PARTIAL','Merge076d017 exists; tested Codex repairs f2be079 are not in main; no consolidated acceptance.','F06,F07,F08,F16'),
78:('PARTIAL','Product-like generator/calculator defaults require review against generic-only scope. No product development done in verification.','F18'),
79:('UNVERIFIED','Local formula/unit tests pass; no independent approved reference/domain/units qualification for engineering output.','F18'),
80:('PARTIAL','Current measured main86, Codex96 and Windows build26300/Git2.48.1 conflict with historical claims.','F16'),
81:('BLOCKED','Referenced detailed architecture/UI-UXv1.0 not located; cannot assert complete coverage of unknown requirements.','F18'),
}
coretests={
5:'tests/core/test_service.py',6:'tests/core/test_completion.py',7:'tests/core/test_service.py',8:'tests/core/test_completion.py',9:'tests/core/test_service.py',10:'tests/core/test_completion.py',11:'tests/core/test_service.py',15:'tests/core/test_service.py',16:'tests/core/test_day2.py; tests/integration/test_v15_jobs.py',17:'tests/integration/test_restore.py',18:'UI_RESULTS.json',19:'tests/ui/test_v15_panels.py; screenshots/jobs.png',20:'tests/ui/test_window.py',28:'tests/core/test_completion.py',30:'tests/core/test_day2.py',31:'tests/core/test_day2.py',33:'tests/core/test_day2.py',38:'tests/core/test_completion.py',51:'tests/contracts/test_v15_contracts.py; tests/adapters/test_tool_detection.py',53:'tests/contracts/test_v15_contracts.py',55:'tests/integration/test_v15_jobs.py',56:'tests/integration/test_v15_jobs.py',57:'tests/integration/test_v15_jobs.py',60:'PROCESS_TREE.json',65:'UI_RESULTS.json; screenshots/jobs.png',69:'tests/ui/test_v15_panels.py; tests/integration/test_v15_jobs.py',73:'tests/adapters/test_commercial_stubs.py; UI_RESULTS.json'}
for old in original:
    if old['status']=='NOT APPLICABLE':excluded.append(old);continue
    code=old['code'].replace('[C]','[main]').replace('[A]','[main]').replace('[R/C/A/X]','[snapshots]')
    code=code.replace('integration_reports.py','integration_service.py:export_report').replace('config/rules.json','config/engineering-rules.json')
    row={'id':old['id'],'source':old['source'],'requirement':old['requirement'],'expected':old['requirement'],'status':mapping[old['status']],'files':code,'actual':'Tested within stated component boundary; does not qualify external/native engineering operation.','evidence':'main-short.txt; source inspection','remaining':'None within stated component boundary','findings':''}
    if old['id'].startswith('CORE-'):
        num=int(old['id'][-3:])
        if row['status']!='PASS':
            row['actual']='Implementation is incomplete within this boundary.'
            row['remaining']=old['gap']
        if num in core_updates:
            status,actual,ids=core_updates[num];row.update(status=status,actual=actual,findings=ids,remaining='; '.join(byid[i][7] for i in ids.split(',') if i))
            row['evidence']='PROBES-main.json; main-short.txt; source inspection'
        elif row['status']=='PASS':row['evidence']=coretests.get(num,'main-short.txt; UI_RESULTS.json; source inspection')
        if num==60:row['evidence']='PROCESS_TREE.json; tests/adapters/test_safe_runner.py'
        if num==65:row['evidence']='UI_RESULTS.json; screenshots/jobs.png'
        if num==42:row['evidence']='main-deep.txt; CODEX_DEEP_RESULT.json'
        if num==18:row['evidence']='UI_RESULTS.json'
        if num in (4,):row.update(findings='F13',actual='Frozen wrappers work, but three contract forms remain incompatible.',remaining=byid['F13'][7])
    rows.append(row)

# Reassess all tool dimensions using current evidence, not prior audit statuses.
for row in rows:
    if not row['id'].startswith('TOOL-'):continue
    _,tool,dim=row['id'].split('-');tool=int(tool);dim=int(dim)
    row['evidence']='PROBES-main.json:tool_health; tests/adapters/test_tool_detection.py; main-short.txt'
    if dim==1:
        row.update(status='PASS',actual='All18 exact catalog IDs/categories and resource/software distinction verified.',remaining='None within catalog scope');continue
    if tool in (8,9,10,11,18):
        if dim==5:row.update(status='PASS',actual='Optional settings/reference fields persist; startup succeeds without paid software.',remaining='None within configuration-only scope')
        elif dim in (2,3):row.update(status='BLOCKED',actual='Licensed binary/version/entitlement unavailable; not operationally tested.',remaining='Only if licensed execution is adopted: provide approved installation and per-version smoke evidence.')
        else:row.update(status='PARTIAL',actual='Optional unavailable/configuration stub tested; installed license handling/diagnostics not qualified.',findings='F16',remaining='Keep truthful optional state; document exact configured/license-reviewed capabilities before any execution claim.')
        continue
    if tool in (1,2,3,6):
        if dim==2:row.update(status='FAIL',actual='No resource supplied; hardcoded1.0-dataset and READY assertion.',findings='F02',remaining=byid['F02'][7])
        elif dim==3:row.update(status='BLOCKED',actual='Upstream release/source/license and distribution rights not established by fixture strings.',findings='F03',remaining='Provide authentic upstream release/license/checksum/provenance or preserve synthetic/reference-only classification.')
        elif dim in (7,8):row.update(status='FAIL',actual='No-input checksum SUCCEEDED; malformed scientific rows accepted/defaulted.',findings='F02,F03',remaining=byid['F02'][7]+' '+byid['F03'][7])
        else:row.update(status='PARTIAL',actual='Metadata/fixture scaffolding exists; no valid upstream scientific import/report path.',findings='F02,F03',remaining='Implement valid schema/provenance/import/failure handling; do not claim engineering validity from fixtures.')
        continue
    if tool in (4,5,12,13,14,16):
        if dim in (2,3,9):row.update(status='BLOCKED',actual='Native installation/version test unavailable on this workstation.',remaining='Approved external installation/version/license review and safe native smoke; operation-code gaps remain separate.')
        elif dim==5:row.update(status='PASS',actual='Manual path settings persist; unavailable tool state does not crash startup.',remaining='Runtime qualification is separate from settings persistence.')
        elif dim in (6,7):row.update(status='FAIL',actual='No supported v1.5 launch/execution body; empty operations and unconditional unavailable exception.',findings='F12',remaining=byid['F12'][7])
        elif dim==10:row.update(status='FAIL',actual='No integrated native parsed result/report operation.'+(' Malformed DRC gives zero issues.' if tool==4 else ''),findings='F05,F12' if tool==4 else 'F12',remaining='Implement strict native parsing/collection/report handoff, then verify with real version-specific outputs.')
        else:row.update(status='PARTIAL',actual='Candidate paths, unavailable wrapper, generators or unit fixtures only.',findings='F12',remaining='Implement and verify operation/error contracts; installation alone will not add missing code.')
        continue
    # Installed LTspice, Python and Git.
    if dim==2:row.update(status='FAIL',actual='Version/health self-assertion is not bound to effective configured executable; Git reported version differs from actual.',findings='F01,F09',remaining=byid['F01'][7]+' '+byid['F09'][7])
    elif dim==3:row.update(status='UNVERIFIED',actual='Windows execution observed; installed-distribution license/compatibility constraints not independently qualified.',remaining='Retain exact installed-distribution terms/version/OS qualification; no legal approval inferred.')
    elif dim==5:row.update(status='FAIL',actual='Stored path configuration is not the executable consistently used by execute().',findings='F09',remaining=byid['F09'][7])
    elif dim==6 and tool==7:row.update(status='FAIL',actual='Headless batch works, but no distinct configured native-editor launch operation required by core connector scope.',findings='F12',remaining='Implement/review safe native launch if retained in accepted scope; batch execution is verified separately.')
    elif dim==6:row.update(status='PASS',actual='Actual Python/Git subprocess CLI launch exercised in existing tests; does not validate settings/workspace semantics.',remaining='None within subprocess-launch boundary')
    elif dim in (7,9) and tool==7:row.update(status='PASS',actual='Installed26.1.1.0 executes exact existing RC test fixture; raw/log outputs retained and hashed. Software smoke only.',evidence='PROBES-main.json:native_rc; native-rc/*; INSTALLED_LTSPICE_VERSION.json',remaining='No engineering qualification implied; UI/parsing/evidence metadata remain separate gaps.')
    elif dim==10:row.update(status='PARTIAL',actual='No complete accepted operation-result parsing→Studio report path; standalone parser/CLI outputs only.',findings='F14',remaining=byid['F14'][7])
    else:row.update(status='PARTIAL',actual='Installed execution components have passing tests, but configuration/cancel/evidence/contract defects remain.',findings='F09,F10,F13,F14',remaining='Resolve cited findings and run operation-specific positive/negative/native UI/CLI tests.')

# Newly observed acceptance boundaries/claims, separate from the older RTM.
extra=[
('NEW-001','G15 §§9.2,9.9; current verification §6','Shared UI/CLI adapter composition','Same reviewed adapters available through shared service without constructing UI','UI19 entries including demo; fresh service/CLI1 entry only.','FAIL','src/mendex_ui/window.py; src/mendex_core/integration_service.py','PROBES-main.json:ui','F11'),
('NEW-002','Latest Codex remediation milestone f2be079','Completed fixes integrated into accepted main','Accepted main contains tested snapshot/collision/path fixes','f2be079 tested separately96; main7230079 lacks its fixes.','FAIL','src/mendex_core/service.py; integration_service.py; git ancestry','SNAPSHOTS.json; PROBES-main.json; PROBES-codex.json; TEST_RESULTS.json','F06,F07,F08'),
('NEW-003','Agent2 c6180f7 implementation claims','Skin-depth/Dowell/flyback calculation qualification','Reference domains/units/assumptions and numerical robustness established before engineering use','Local tests pass; independent approved engineering references and operating-domain tests absent.','UNVERIFIED','src/integrations/calculations/winding_losses.py; transformer_design.py; power_losses.py','tests/adapters/test_magnetics.py; main-short.txt; source inspection','F18'),
('NEW-004','G15 §9.9; current verification §6','No swallowed adapter-registration failures','Registration failures produce actionable diagnostics without inconsistent capability state','StudioWindow catches all registration exceptions and passes silently.','PARTIAL','src/mendex_ui/window.py:StudioWindow.__init__','Source inspection; PROBES-main.json:ui','F11'),
]
for i,src,req,expected,actual,status,files,ev,ids in extra:
    rows.append(dict(id=i,source=src,requirement=req,expected=expected,actual=actual,status=status,files=files,evidence=ev,findings=ids,remaining='; '.join(byid[x][7] for x in ids.split(','))))

counts=Counter(x['status'] for x in rows)
percentage=round(counts['PASS']/len(rows)*100,2)
write(E/'REQUIREMENTS.json',json.dumps({'primary_snapshot':'main7230079','counts':dict(counts),'total':len(rows),'verified_completion_percentage':percentage,'excluded_count':len(excluded),'method':'PASS/active normalized checks; zero credit for PARTIAL/FAIL/BLOCKED/UNVERIFIED; no candidate-branch fixes credited to main','rows':rows,'excluded':excluded},indent=2,ensure_ascii=False))

tools=[
('SwitchLossDB','Dataset','FAIL','Metadata/fixtures; checksum no-op and unrelated CSV accepted; source/license unresolved.','F02,F03'),
('MagNet Dataset','Research dataset','FAIL','No-input READY/SUCCEEDED; missing fields default to scientific values.','F02,F03'),
('MagNet ML Benchmarks','Benchmark','FAIL','Generic no-op checksum wrapper; no verified benchmark/import results.','F02'),
('KiCad','Executable','PARTIAL','Not installed: native tests BLOCKED. Missing operation body and malformed-parser zero result are implementation defects.','F05,F12'),
('FEMM','Executable','PARTIAL','Not installed: native test BLOCKED. Candidate paths/generator do not supply working v1.5 execution/collection.','F12,F18'),
('MagNet — Princeton University','Research hub/resource','PARTIAL','Catalog/reference exists; generic READY/checksum operation misrepresents research-only scope; overlap unresolved.','F02'),
('LTspice','Executable','PARTIAL','Actual26.1.1.0 RC execution/raw collection verified. False READY, config binding, parser/UI/metadata gaps remain.','F01,F09,F11,F14'),
('PLECS','Optional commercial','PASS','Configuration/unavailable guard scope only; licensed execution BLOCKED and not claimed.',''),
('MATLAB / Simulink','Optional commercial','PASS','Configuration/unavailable guard scope only; licensed execution BLOCKED and not claimed.',''),
('Ansys Maxwell','Optional commercial','PASS','Configuration/unavailable guard scope only; licensed execution BLOCKED and not claimed.',''),
('Ansys Icepak','Optional commercial','PASS','Configuration/unavailable guard scope only; licensed execution BLOCKED and not claimed.',''),
('FreeCAD','Executable','PARTIAL','Not installed: native tests BLOCKED. Missing operation body; script generator not verified CAD workflow.','F12'),
('Qucs-S','Executable','PARTIAL','Not installed: native tests BLOCKED. No generic execution operation.','F12'),
('OpenModelica','Executable','PARTIAL','Not installed: native tests BLOCKED. Generator/default model does not replace connector execution.','F12,F18'),
('Python','Runtime','PARTIAL','Actual3.13.7 scripts execute; missing-path READY, ignored settings and delayed cancellation remain.','F01,F09,F10'),
('Jupyter Notebook','Notebook application','PARTIAL','Adapter reports not installed: native test BLOCKED. No notebook launch/execute operation.','F12'),
('Git','Developer tool','PARTIAL','Actual2.48.1.windows.1 vs hardcoded2.45.2.windows.1; executable/workspace configuration ignored.','F09'),
('SolidWorks','Optional commercial','PASS','Configuration/unavailable guard scope only; licensed execution BLOCKED and not claimed.',''),
]

header=f'''# Final implementation verification — Mendex Engineering Studio

Date: **10 November 2026**. Mode: **verification only**. Primary target: `main` **7230079d972e34b504f09cf90c166f87bdf0a43a**, frozen before testing. Comparison candidate: Codex **f2be079d3eb89625d2ae45778958fceb57d1d75f**. Released regression baseline: **205567373799444b74c68d04c8eb4435de3cac05**.

## Acceptance decision

**NOT YET VERIFIED — official acceptance as complete: NO.** Verification cannot establish exhaustive compliance with the missing referenced detailed architecture/UI-UX specification, unavailable native software, unconfigured external providers and unperformed independent-machine/operator checks. More decisively, the tested main snapshot has reproducible implementation failures. These defects are sufficient to reject complete acceptance even before blocked checks are resolved. This is not merely a request to install tools.

The working framework includes useful product/specification/revision persistence, migration and backup handling, fourteen-page desktop navigation, manual validation, synthetic jobs, evidence browser and draft reports. A real installed LTspice RC software smoke succeeds and now collects raw output. This does not establish a complete native UI workflow, truthful health verification or engineering qualification. No product, calculation, physical safety, manufacturing or production approval is issued.

| Metric | Count |
|---|---:|
| Active normalized requirements/verification checks | {len(rows)} |
| PASS | {counts['PASS']} |
| PARTIAL | {counts['PARTIAL']} |
| FAIL | {counts['FAIL']} |
| BLOCKED | {counts['BLOCKED']} |
| UNVERIFIED | {counts['UNVERIFIED']} |
| BLOCKED + UNVERIFIED | {counts['BLOCKED']+counts['UNVERIFIED']} |
| Explicitly excluded/deferred checks, outside denominator | {len(excluded)} |
| Strict verified completion | **{percentage:.2f}%** |

Calculation: **{counts['PASS']} ÷ {len(rows)} ×100 = {percentage:.2f}%**. PARTIAL contributes zero; blocked/unverified in-scope checks remain in the denominator. These are normalized obligations and explicit user verification checks, not a sentence count or percentage of code. Tool-specific checks make this metric integration-heavy. Earlier85.2%/94% readiness claims used different/unsupported denominators or partial credit and are not reproduced here. No percentage can prove coverage of an unavailable baseline.

## Baseline review and scope conflicts

- G13: supplied master filenamev1.3 has internalv1.0 control and finalv1.2 three-day foundation addendum. Earlier10–18week pilot/full CAD/enterprise claims are superseded for the foundation, not silently counted as delivered.
- G14/G15: supplied v1.5 DOCX contains Next Stepsv1.4 §§1–8 and two-agent execution§9. v1.5 assigns Codex UI/services/contracts/DB/integrator and Antigravity adapters/runner/parsers/data; this supersedes earlier role assignments. Implementation claims are not independent acceptance evidence.
- Referenced Detailed Software Architecture/UI-UXv1.0 was not located in the supplied relevant documents or repository. No newer approved specification was located. New calculation files/handoff claims are reviewed as implementation claims, not authorization to expand generic scope.
- CI/CD, deployment, hardware control, manufacturing/safety approval, enterprise cloud/ERP, product-specific design and advanced AI remain excluded. Basic HTML/JSON reporting is in scope; broader pilot DOCX/PDF/signed dossiers are deferred by the foundation addendum. Optional commercial configuration/unavailable behavior is legitimate scope; actual licensed operation is never represented as tested.
- Existing READMEs/status/handoff notes conflict: some still say unmerged/disabled while main contains merge076d017 and UI auto-registration7230079. Actual source/runtime observations govern this report. No owner-approved deferral or signature is inferred.

Full source extracts/hashes and document inventory: {link('DOCUMENT_BASELINE.json')}; code/snapshot hashes: {link('SOURCE_INDEX.json')}; function line indexes: {link('CODE_REFERENCES.json')}. AGENTS, architecture, engineering rules and contracts were read before verification. All tracked source/service/UI/DB/integration/config/script/test areas were inventoried and inspected, with extra scrutiny of changed and acceptance-critical functions; inventory alone does not establish behavior.

## Reproducible test results

| Tree | Path regime | Actual result | Meaning |
|---|---|---|---|
| Main7230079 | Short fresh temp | **86 passed in15.85s** | Existing suite passes; targeted negative probes expose omitted acceptance cases |
| Main7230079 | Deep snapshot temp | **13 failed,73 passed in16.19s** | Windows path-length/file-creation regression, not erased by short-path success |
| Codexf2be079 | Short fresh temp | **96 passed in18.02s** | Candidate includes earlier Codex repair regressions; not credited to main |
| Codexf2be079 | Deep snapshot temp | **96 passed in18.95s** | Compact-path mitigation verified in candidate; arbitrary/third-party path limits still not qualified |
| Released2055673 | Short fresh temp | **28 passed in2.56s** | Reproduces released baseline; main also runs legacy tests successfully at short paths |

Existing interpreter: `C:/Mendex studio/.venv/Scripts/python.exe`, Python3.13.7, Windows11 build26300, Git2.48.1.windows.1. Each process used its snapshot/src PYTHONPATH, PYTHONDONTWRITEBYTECODE=1, offscreen Qt and disabled pytest plugin autoload. Test command: existing interpreter `-m pytest -q -p no:cacheprovider --basetemp <fresh root>`. Exact absolute commands, CWDs, return codes, durations and raw failure logs: {link('TEST_RESULTS.json')}, {link('CODEX_DEEP_RESULT.json')}, {link('main-short.txt')}, {link('main-deep.txt')}, {link('codex-short.txt')}, {link('codex-deep.txt')}, {link('released-short.txt')}.

All three `python -m mendex_ui --root <fresh root> --smoke-test` commands exited0. Main's existing `scripts/v15_codex_smoke.py` exited0 and exercised synthetic UI→job→evidence→draft report. Commands/results: {link('UI_RESULTS.json')}; screenshots: {link('screenshots/jobs.png')}, {link('screenshots/evidence.png')}, {link('screenshots/tool-center.png')}. An initial custom offscreen screenshot without the script's explicit Segoe font rendered missing glyphs; it is not used as proof of a product font defect. The existing supported smoke script's font-loaded screenshots were visually inspected.

Targeted verification is additional to existing tests: {link('targeted_verification.py')}, {link('PROBES-main.json')}, {link('PROBES-codex.json')}. The fake executable was never executed. Only fresh audit-owned sentinels/fixtures were overwritten during negative tests. A benign Python parent/child timeout actually killed the child (Windows process status checked): {link('PROCESS_TREE.json')}. Python connector cancellation set at0.15s was acknowledged only after1.278s. LTspice currently forwards cancel_event; do not generalize the Python defect to that repaired call.

Native LTspice file version26.1.1.0 was read independently: {link('INSTALLED_LTSPICE_VERSION.json')}. The exact existing RC test fixture was reused, not a new product model. Actual job SUCCEEDED, .raw/.op.raw/.log artifacts are retained with SHA-256 in {link('PROBES-main.json')} and `docs/audits/final-verification-20261110-01/native-rc/`. The earlier nested-output discovery defect has improved: waveform files are now declared and hashed. Remaining gaps include runner log omission, raw-vs-derived labels, effective configuration and parser/report/UI handoff. No waveform numerical correctness, validated transformer behavior or engineering PASS is asserted.

## All18 tool/resource status

Every catalog entry is present. **Five optional commercial entries pass only their allowed configuration/unavailable guard scope. Zero complete native/research integrations qualify for an unconditional fully operational Studio claim.** Installed LTspice/Python/Git execution components are useful but partial. Six missing native applications block real smoke tests and independently contain missing operation code. Four research labels are resources, not installers; they do not have a valid completed data workflow.

| # | Tool/resource | Scope | Verification status | Actual result / limits | Findings |
|---|---|---|---|---|---|
'''
for i,(name,kind,status,result,ids) in enumerate(tools,1):header+=f'| {i} | {name} | {kind} | {status} | {result} | {ids or "No execution acceptance implied"} |\n'

header+='''
The twelve audit dimensions per tool are normalized in TOOL-xx-yy rows below; resource launch/simulation and optional unlicensed execution checks are excluded where not applicable. Some tool-level commercial guard summaries are PASS while installed-license dimension rows remain BLOCKED: these assess different scopes, not contradictory operational claims. Native installation discovery is adapter-observed; an application could exist at an unconfigured nonstandard path. No unavailable paid tool was run or licensed.

## Findings, exact affected files, owners and acceptance tasks

Files/functions below refer to the frozen main source, not later uncommitted work. Function line numbers are in CODE_REFERENCES.json. P0 stops acceptance because truthful status, scientific-data integrity or execution boundaries are compromised; P1 is essential correctness/integration; P2 is important operational/UX/handoff work. Every FAIL row maps to a finding/task; unavailable external software is BLOCKED separately from absent operation bodies.

'''
for fid,priority,owner,title,files,actual,cause,task in findings:
    header+=f'### {fid} — {priority}: {title}\n\n**Responsible:** {owner}.\n\n**Affected files:** `{files}`.\n\n**Observed:** {actual}\n\n**Root cause where established:** {cause}\n\n**Required completion task:** {task}\n\n'

header+='''## Requirement-by-requirement verification

Scope: primary main snapshot only. Each requirement cell includes its ID and source. PASS rows are component-boundary assertions; no unavailable tool is marked working because a class or screen exists. References to test source names mean those tests were executed in main-short unless a separate evidence file is named. FAIL/PARTIAL rows include exact source-family references and finding IDs for priority/owner/root cause/task. Source paths are relative to the snapshot root; Antigravity/Codex indicate responsibility, not separate acceptance trees.

| Requirement | Expected Behavior | Actual Result | Status | Evidence | Remaining Work |
|---|---|---|---|---|---|
'''
for row in rows:
    cells=[row['id']+' — '+row['requirement']+' ('+row['source']+')',row['expected'],row['actual'],row['status'],row['files']+'; '+row['evidence'],(row['findings']+': ' if row['findings'] else '')+row['remaining']]
    header+='| '+' | '.join(str(c).replace('|','/').replace('\n',' ') for c in cells)+' |\n'

header+='''
## Explicit exclusions and denominator controls

The following prior normalized checks are explicitly outside the applicable scope and are not reclassified PASS. Advanced pilot/enterprise capabilities need a future approved phase; optional paid execution requires separately licensed/tested adoption. They are retained here so scope has not silently disappeared.

| ID | Excluded/deferred check | Scope reason |
|---|---|---|
'''
for row in excluded:header+=f"| {row['id']} | {row['requirement']} | {row['gap']} |\n"

header+='''
## Exact path to100% verified completion

1. Codex resolves the missing referenced baseline and freezes an agreed requirement/operation scope. Provide explicit owner-approved deferrals instead of treating missing software or partial code as completion. If additional requirements emerge, expand this matrix before calculating100%.
2. Antigravity closes F01–F05 with real bound health/smoke evidence, valid dataset schemas/source/license/checksums, enforced executable/log/resource boundaries and strict malformed-output handling. Codex tests rejection at the application acceptance boundary.
3. Codex reviews/integrates f2be079 into the actual acceptance branch for F06–F08, preserving legacy/frozen evidence. Run interleaving, collision/mutation, deep-root, migration and backup regressions on that tree; add path-budget diagnostics rather than claiming unlimited Windows paths.
4. Antigravity fixes effective binary/version/workspace, fractional timeout/cancellation and terminal-state semantics (F09/F10). Codex implements durable owner/session-based recovery/bounded shutdown and shared UI/CLI registration/real operation selection (F10/F11).
5. Antigravity implements missing approved native operation bodies and collection/parsing (F12/F14), supplies official compatibility/license research and requests required external installations separately. After environment authorization, test each claimed operation on its installed version; keep optional commercial runtime excluded unless adopted. Complete one verified extended connector and one authentic dataset workflow required by G14 phase4.
6. Codex and Antigravity settle contract/registry compatibility through reviewed/versioned interfaces (F13). Preserve frozen schemas and raw evidence. Retain exact command/versions/configuration/code/parser provenance and correct raw/derived labels for all native results and reports.
7. Resolve lifecycle/source-management, documentation and calculation-qualification boundaries (F15/F16/F18). Complete manual editor/accessibility/DPI/operator and approved clean-machine acceptance (F17). Keep advanced AI unavailable unless separately configured/reviewed; the required provider-neutral default interface already passes its narrow scope.
8. Rerun unit, contract, adapter, UI, integration, regression and targeted negative/native smoke tests against one immutable proposed acceptance commit. Require every active row PASS with retained evidence; blocked checks do not disappear from the denominator. Publish truthful known limits and obtain actual owner walkthrough/sign-off. No development or installation has been performed by this verification.

## Preservation, limitations and final answer

Only the new report, evidence JSON/logs/screenshots, read-only verification helpers and fresh temporary test artifacts were written. Application sources, dependency manifests, frozen contracts, existing audit reports and user/raw evidence were not edited. No installs/upgrades/global settings, product development, hardware operations, CI/CD or deployments occurred. Immutable committed snapshots were extracted and locally git-initialized solely for Git-cwd tests. This verification does not authorize any subsequent fix.

The original working tree had an untracked `src/mendex_ui/workspace_panels.py` at freeze time. Its hash is recorded in SNAPSHOTS.json; it imports calculators/generators directly, is not wired into the frozen tracked UI and has no completed acceptance evidence. It is not silently promoted into the reviewed release. Any later commits/uncommitted changes require a delta verification; they do not automatically close these findings. Snapshot source hashes and final worktree observation provide the boundary.

**Answer: NOT YET VERIFIED. The Studio framework must not officially be accepted as complete.** The frozen main has independently reproduced failures, not just missing external licenses. A usable foundation and passing short-path suites are confirmed;100% implementation and verification are not.
'''
header=header.replace('## Preservation, limitations and final answer','## Preservation, limitations and final answer\n\nA separate root-level FINAL_IMPLEMENTATION_VERIFICATION.md was created concurrently by another process after this run started. It is preserved without modification. Its zero-failure and higher-completion assertions are not supported by the frozen-main negative/deep-path probes retained here; denominators also differ. This independently generated report and evidence must be considered before acceptance. No report is automatically preferred because it was committed last.')
write(E/'FINAL_IMPLEMENTATION_VERIFICATION.md',header)
print(json.dumps({'total':len(rows),'counts':dict(counts),'excluded':len(excluded),'percentage':percentage},indent=2))
