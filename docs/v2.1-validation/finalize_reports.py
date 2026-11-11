"""Append final coverage limits, verify local links, and hash retained evidence."""
from pathlib import Path
import hashlib, json, re, subprocess, xml.etree.ElementTree as ET
D=Path(__file__).parent.resolve();E=D/'evidence';R=D.parents[1]
def append(name,text):
    p=D/name
    p.write_text(p.read_text(encoding='utf-8')+'\n'+text.strip()+'\n',encoding='utf-8')
probe=json.loads((E/'probes.json').read_text())
before=probe['existing_data_before']['returned'];after={}
for name in ['products','workspaces','engineering_designs','reports']:
    for p in (R/name).rglob('*'):
        if p.is_file():after[str(p.relative_to(R))]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
for p in (R/'.mendex').glob('*'):
    if p.is_file():after[str(p.relative_to(R))]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
integrity={'scope':'Existing products, workspaces, engineering_designs, reports, top-level .mendex files; excludes historical .mendex subdirectories','compared_files':len(before),'removed':[k for k in before if k not in after],'modified':[k for k in before if k in after and before[k]!=after[k]],'added':[k for k in after if k not in before]}
(E/'final-integrity.json').write_text(json.dumps(integrity,indent=2),encoding='utf-8')
note='''Source-snapshot limitation: `src/integrations/adapters/git_adapter.py` became modified after the initial git-status snapshot during this audit. The audit did not edit it; the concurrent delta is retained in [concurrent-source-change.patch](evidence/concurrent-source-change.patch). Other pytest processes were already present on the workstation; they were not stopped. Consequently this run is evidence for the live working tree, not an atomic immutable checkout. Final source hashes are retained in [source-hashes.json](evidence/source-hashes.json); a stable-snapshot regression rerun is required after remediation.'''
for f in ['01_ARCHITECTURE_AUDIT.md','12_AUTOMATED_TEST_RESULTS.md','15_FINAL_INDEPENDENT_SIGNOFF.md']:append(f,note)
for f in ['02_APPLICATION_CLEANUP_AUDIT.md','15_FINAL_INDEPENDENT_SIGNOFF.md']:
    append(f,'Final preservation check: [final-integrity.json](evidence/final-integrity.json) compares '+str(len(before))+' existing files through completion. Removed: '+str(len(integrity['removed']))+'; modified: '+str(len(integrity['modified']))+'; added: '+str(len(integrity['added']))+'. Historical scratch/backups are excluded as stated in the manifest.')
    append(f,'The changed existing file is `.mendex/studio.sqlite3`; the new file is `reports/workflow_report_8481499b.html`. This supersedes any inference that all existing metadata remained unchanged through completion. Product/revision/native artifact hashes in the comparison stayed unchanged and no existing file was removed. A separate Studio process was running by the final check. The workflow report title matches the suite\'s Skin Depth Engineering Dossier fixture; the retained report node also has a current-directory fallback when workspace_path is absent, so an automated-test side effect cannot be excluded. The audit did not restore or delete these files. Attribution of concurrent metadata writes is NOT_EVALUATED.')
rows=[]
purposes={'switchlossdb':'Optional loss-data ingestion; unresolved release provenance','magnet-dataset':'Optional magnetic research data ingestion','magnet-ml-benchmarks':'Optional research benchmark','magnet-princeton':'Optional research portal; overlaps MagNet records','kicad':'Required native EDA/PCB checking','femm':'Required magnetics solver','ltspice':'Required circuit solver','plecs':'Optional licensed simulation stub','matlab-simulink':'Optional licensed analysis stub','ansys-maxwell':'Optional licensed magnetics stub','ansys-icepak':'Optional licensed thermal stub','solidworks':'Optional licensed mechanical stub','freecad':'Optional bobbin/STEP generation','qucs-s':'Optional alternate simulation frontend','openmodelica':'Optional system modeling','python':'Required local execution runtime','jupyter':'Optional notebook analysis','git':'Optional version-control integration'}
for item in json.loads((E/'catalog.json').read_text()):
    d=item['descriptor'];h=item['health'];tid=d['tool_id']
    classification='Unsupported (unconfigured commercial stub)' if h.get('state')=='NOT_CONFIGURED' else 'Configured but unverified'
    if tid=='python':classification='Required and operational (this local audit runtime)'
    if tid in ['switchlossdb','magnet-dataset','magnet-ml-benchmarks','magnet-princeton']:classification='Configured but unverified (metadata, not qualified dataset)'
    rows.append('| '+tid+' | '+h.get('state','ERROR')+' | '+classification+' | '+purposes.get(tid,'Purpose not established')+' |')
append('09_ENGINEERING_TOOLS_VALIDATION.md','''Complete catalog classification from [catalog.json](evidence/catalog.json), using in-memory registered existing connectors and actual detection. DETECTED does not mean independently operational. Required tools with demonstrated failures retain their FAIL qualification above.

| Integration | Detected state | Audit classification | Documented purpose |
|---|---|---|---|
'''+ '\n'.join(rows)+'''

ngspice is outside the 18-item core catalog and remains optional/configured-but-unverified in this independent audit. No connector has enough usage evidence here to justify automatic removal. Commercial availability/licensing has not been inferred from paths or registration.''')
append('10_WORKSPACE_SYNC_VALIDATION.md','''A separate controlled software fixture reproduced an additional real persistence race: `RUNNING` → `FAILED` immediately after a second client attaches → `SUCCEEDED` after the original worker completes. `_recover_interrupted_jobs` does not distinguish a live worker in another client from an interrupted session. This is F16 in the remediation plan. The fixture is explicitly synthetic and grants no engineering simulation evidence.''')
append('11_SECURITY_AND_RECOVERY.md','''The recovery fixture confirms a defect, not a recovery PASS: opening a second StudioService marks the first client's live RUNNING job FAILED/INTERRUPTED. The first worker subsequently changes it to SUCCEEDED. The future-map inspection used a mismatched key representation, so that one diagnostic is unverified; the persisted before/after/eventual states themselves reproduce the race. See F16.''')
xml=ET.parse(E/'pytest.xml')
failed=[];skipped=[]
for c in xml.iter('testcase'):
    ident=c.attrib.get('classname','')+'::'+c.attrib.get('name','')
    if c.find('failure') is not None:failed.append(ident)
    if c.find('skipped') is not None:skipped.append((ident,c.find('skipped').attrib.get('message','')))
append('12_AUTOMATED_TEST_RESULTS.md','''Final process exit: **1**. Console wall duration: **799.19 seconds (13m 19s)**; JUnit duration 799.005 seconds. Total 227; passed 222; failed 3; skipped 2; collection/execution errors 0. Pytest has no separate BLOCKED outcomes here (0 recorded); manual blocked/NOT_EVALUATED steps are enumerated in report 13.

Failed tests (actual KiCad subprocess timeouts; no fixes made):

'''+ '\n'.join('- `'+f+'`' for f in failed)+'''

Skipped tests:

'''+ '\n'.join('- `'+f+'`: '+reason for f,reason in skipped)+'''

The skip messages are misleading: LTspice and FEMM are installed and were separately executed in this audit. These tests instantiate the base IntegrationService without attaching the reviewed native adapters, then skip when verification is not READY. They do not prove tool absence and do not qualify native operations. This is an automated-coverage gap.''')
append('15_FINAL_INDEPENDENT_SIGNOFF.md','Final regression result: **222 passed, 3 failed, 2 skipped / 227 tests, 13m 19s**. Both real CLI AI clients connect but fail the required public simulation. Full VS Code and disconnected-network acceptance remain NOT_EVALUATED. Sixteen prioritized findings are documented; P0 failures prevent signoff.')
# Verify local markdown references actually resolve (anchors ignored).
broken=[]
for md in D.glob('*.md'):
    for link in re.findall(r'\]\(([^)]+)\)',md.read_text(encoding='utf-8')):
        if link.startswith(('http:','https:','#')):continue
        target=(md.parent/link.split('#')[0]).resolve()
        if not target.exists():broken.append({'document':md.name,'link':link})
required=[f'{i:02}_' for i in range(1,16)]
report_files=sorted(p.name for p in D.glob('[0-9][0-9]_*.md'))
qa={'reports':report_files,'report_count':len(report_files),'broken_local_links':broken,'test_summary':json.loads((E/'test-summary.json').read_text())['totals'],'preservation':integrity}
(E/'report-qa.json').write_text(json.dumps(qa,indent=2),encoding='utf-8')
hashes={}
for p in sorted(E.rglob('*')):
    if p.is_file() and p.name!='evidence-sha256.json':hashes[str(p.relative_to(E))]=hashlib.sha256(p.read_bytes()).hexdigest()
(E/'evidence-sha256.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
print(json.dumps({'reports':len(report_files),'broken_links':broken,'preservation':integrity,'hashed_evidence_files':len(hashes)},indent=2))
