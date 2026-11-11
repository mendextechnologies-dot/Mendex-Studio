"""Read-only numerical cross-check plus actual Studio loading of preserved raw output."""
import hashlib, json, os, sqlite3, sys, traceback
from pathlib import Path
E=Path(__file__).parent.resolve()/'evidence';R=E.parents[2]
sys.path.insert(0,str(R/'src'));os.environ.pop('QT_QPA_PLATFORM',None)
p=json.loads((E/'probes.json').read_text());root=Path(p['context']['root']);raw=Path(p['real_ltspice_lower_core']['returned']['raw_file_path'])
lines=raw.read_text(encoding='utf-8').splitlines();vars=[];values=[];mode=''
for line in lines:
    if line=='Variables:':mode='vars';continue
    if line=='Values:':mode='values';continue
    if mode=='vars':vars.append(line.split()[1])
    elif mode=='values' and line.strip(): values.append(line.split())
n=len(vars);samples=[]
for i in range(0,len(values),n):
    rows=values[i:i+n]
    if len(rows)==n:samples.append([float(rows[0][1])]+[float(r[0]) for r in rows[1:]])
vindex=next(i for i,v in enumerate(vars) if v.lower()=='v(vout)');ss=samples[int(len(samples)*.7):]
out={'raw_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'raw_variables':vars,'raw_points':len(samples),'independent_vout_mean_v':sum(r[vindex] for r in ss)/len(ss),'independent_vout_ripple_v':max(r[vindex] for r in ss)-min(r[vindex] for r in ss),'current_peaks_by_signal_a':{name:max(abs(r[i]) for r in samples) for i,name in enumerate(vars) if name.upper().startswith('I(')},'runner_reported_i_peak_a':p['real_ltspice_lower_core']['returned']['i_peak_a']}
db=R/'.mendex/studio.sqlite3'
with sqlite3.connect('file:'+db.as_posix()+'?mode=ro',uri=True) as con:
    tables=[r[0] for r in con.execute("select name from sqlite_master where type='table'")]
    out['existing_database_readonly']={'schema_version':con.execute('pragma user_version').fetchone()[0],'integrity':con.execute('pragma integrity_check').fetchone()[0],'table_counts':{t:con.execute('select count(*) from "'+t+'"').fetchone()[0] for t in tables}}
from PySide6.QtWidgets import QApplication,QLabel
from PySide6.QtCore import QTimer
from mendex_core.service import StudioService
from mendex_ui.window import StudioWindow
app=QApplication([]);w=StudioWindow(StudioService(root));w.resize(1440,960);w.show()
def run():
    try:
        w.navigation.setCurrentRow(2);app.processEvents()
        viewer=w.simulation_center.waveform_viewer
        out['loaded_preserved_raw']=viewer.load_raw_file(raw)
        out['displayed_signals']=list(viewer.series_map)
        out['workspace_selector_count']=w.simulation_center.combo_ws.count()
        out['persisted_jobs_count']=len(w.service.integrations.list_jobs())
        out['display_scope']='Manual RAW load into Studio, not a public CLI/MCP persisted job association'
        app.processEvents();w.grab().save(str(E/'ui-real-waveforms.png'))
    except Exception:out['ui_error']=traceback.format_exc()
    finally:
        (E/'results.json').write_text(json.dumps(out,indent=2),encoding='utf-8');w.close();app.quit()
QTimer.singleShot(1000,run);app.exec()
