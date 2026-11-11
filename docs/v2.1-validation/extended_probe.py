"""Additional real native, boundary, offline-process and recovery probes."""
from pathlib import Path
import ctypes, hashlib, json, os, shutil, socket, sqlite3, subprocess, sys, time, traceback
from uuid import uuid4
E=Path(__file__).parent.resolve()/'evidence';R=E.parents[2]
sys.path.insert(0,str(R/'src'))
p=json.loads((E/'probes.json').read_text());ROOT=Path(p['context']['root']);ws=p['context']['workspace_cli'];did=p['context']['design_id']
out={}
def probe(name,fn):
    start=time.monotonic()
    try: out[name]={'returned':fn()}
    except Exception as exc: out[name]={'exception':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    out[name]['duration_s']=time.monotonic()-start
    (E/'extended.json').write_text(json.dumps(out,indent=2,default=str),encoding='utf-8');print(name,flush=True)
from mendex_core.controller import MendexEngineeringController
from mendex_core.mcp.server import MendexMCPServer
from mendex_core.design.ltspice_runner import LTspiceRunner
from integrations.adapters.kicad import KiCadAdapter
from integrations.adapters.femm import FEMMAdapter
from integrations.contracts import JobRequest
c=MendexEngineeringController(ROOT);server=MendexMCPServer(ROOT);wsdir=ROOT/'workspaces'/ws
for operation,ext in [('erc','.kicad_sch'),('drc','.kicad_pcb')]:
    source=next(wsdir.rglob('*'+ext))
    probe('real_kicad_'+operation,lambda operation=operation,source=source:KiCadAdapter().execute(JobRequest(job_id=str(uuid4()),workspace_id=ws,tool_id='kicad',operation=operation,input_paths=[str(source)],timeout_s=40),E/('native-kicad-'+operation)).model_dump(mode='json'))
probe('real_femm_adapter',lambda:FEMMAdapter().execute(JobRequest(job_id=str(uuid4()),workspace_id=ws,tool_id='femm',operation='solve_2d_magnetic',parameters={'primary_turns':24,'secondary_turns':12,'primary_current_a':1,'frequency_hz':1000},timeout_s=35),E/'native-femm').model_dump(mode='json'))
(wsdir/'audit_contract.lua').write_text('-- Harmless audit contract input only\n',encoding='utf-8')
probe('femm_public_dispatch',lambda:c.run_simulation(ws,'femm'))
outside=E/'outside-write-canary';outside.mkdir(exist_ok=True)
probe('outside_root_generate',lambda:c.generate_design(str(outside),'Harmless outside root write proof',generate_artifacts=True))
(wsdir/'harmless.cmd').write_text('@echo off\n',encoding='ascii')
probe('shell_file_rejection',lambda:c.open_artifact(ws,'harmless.cmd'))
probe('invalid_config_path',lambda:c.service.configure_tool('ltspice',str(E/'missing-executable.exe')))
# Record real missing-executable and missing-input behavior without changing host installations.
missing=E/'nonexistent-input.net'
probe('missing_solver',lambda:LTspiceRunner(str(E/'missing.exe')).is_available)
probe('missing_netlist',lambda:LTspiceRunner().run_simulation(missing).model_dump(mode='json'))
# A tiny real native timeout run; no replacement/mocked solver output.
net=next(wsdir.rglob('*.net'))
timeout_dir=E/('timeout-input-'+str(uuid4()));timeout_dir.mkdir()
timeout_net=timeout_dir/net.name;shutil.copy2(net,timeout_net)
probe('real_solver_timeout',lambda:LTspiceRunner().run_simulation(timeout_net,timeout_s=0.0001).model_dump(mode='json'))
probe('jobs_after_timeout',lambda:c.list_simulations(ws))
# Hash tracking against a copied audit-native input, no frozen evidence is modified.
from mendex_core.design.sync import CrossToolSyncService
design=c.design_service.get_design(did)
artifact=design.get_active_revision().artifacts[0].model_copy(deep=True)
copy=E/'editable-hash-canary.net';copy.write_bytes((ROOT/artifact.path).read_bytes());artifact.path=str(copy)
probe('external_hash_before',lambda:CrossToolSyncService.check_artifact_status(artifact,ROOT))
copy.write_bytes(copy.read_bytes()+b'\n* harmless external audit change\n')
probe('external_hash_after',lambda:CrossToolSyncService.check_artifact_status(artifact,ROOT))
copy.unlink()
probe('external_hash_missing',lambda:CrossToolSyncService.check_artifact_status(artifact,ROOT))
# No OS network changes. This establishes only Python socket-denied local operation.
original=socket.socket.connect
def deny(*args,**kwargs): raise OSError('Independent audit process denies network sockets')
socket.socket.connect=deny
probe('socket_denied_calculation',lambda:MendexEngineeringController(ROOT).run_calculation('losses',{}))
probe('socket_denied_workspaces',lambda:MendexEngineeringController(ROOT).list_workspaces())
probe('socket_denied_report',lambda:MendexEngineeringController(ROOT).generate_report())
socket.socket.connect=original
# Native window launches on audit artifacts; process dispatch is weaker than document acceptance.
for tool,ext in [('ltspice','.asc'),('kicad_sch','.kicad_sch'),('kicad_pcb','.kicad_pcb')]:
    source=next(wsdir.rglob('*'+ext))
    probe('native_open_'+tool,lambda tool=tool,source=source:c.open_tool_file(tool,str(source)))
from mendex_core.launch import find_vscode
probe('vscode_open',lambda:subprocess.run([str(find_vscode()),'--reuse-window',str(R)],capture_output=True,text=True,timeout=20).returncode)
time.sleep(3)
def windows():
    found=[]
    @ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
    def callback(hwnd,unused):
        if ctypes.windll.user32.IsWindowVisible(hwnd):
            n=ctypes.windll.user32.GetWindowTextLengthW(hwnd);buf=ctypes.create_unicode_buffer(n+1);ctypes.windll.user32.GetWindowTextW(hwnd,buf,n+1)
            if any(x in buf.value.lower() for x in ['kicad','ltspice','mendex','generic','independent','femm','schematic','pcb editor']): found.append({'hwnd':int(hwnd),'title':buf.value})
        return True
    ctypes.windll.user32.EnumWindows(callback,0)
    return found
probe('native_visible_windows',windows)
from PySide6.QtWidgets import QApplication
app=QApplication([])
for i,w in enumerate(out['native_visible_windows']['returned']):
    if any(x in w['title'].lower() for x in ['kicad','ltspice','schematic','pcb editor']): app.primaryScreen().grabWindow(w['hwnd']).save(str(E/f'native-window-{i}.png'))
