"""Read-only application verification harness; writes fresh audit/test artifacts."""
from pathlib import Path
import os, subprocess, json, tempfile, time

E = Path(__file__).resolve().parent
PY = Path(r'C:\Mendex studio\.venv\Scripts\python.exe')
S = {x['name']:Path(x['snapshot']) for x in json.loads((E/'SNAPSHOTS.json').read_text())['snapshots'] if 'snapshot' in x}
results=[]
for label,snapshot,deep in [('main-short','main',False),('main-deep','main',True),('codex-short','codex',False),('released-short','released',False)]:
    root=S[snapshot]
    temp=root/'.audit-tests' if deep else Path(tempfile.mkdtemp(prefix='fv-'))/'tests'
    env=os.environ.copy();env.update(PYTHONPATH=str(root/'src'),PYTHONDONTWRITEBYTECODE='1',QT_QPA_PLATFORM='offscreen',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    args=[str(PY),'-m','pytest','-q','-p','no:cacheprovider','--basetemp',str(temp)]
    started=time.monotonic()
    process=subprocess.run(args,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
    (E/(label+'.txt')).write_text('COMMAND: '+subprocess.list2cmdline(args)+'\nCWD: '+str(root)+'\nPYTHONPATH: '+env['PYTHONPATH']+'\n\n'+process.stdout,encoding='utf-8')
    item=dict(label=label,commit_snapshot=snapshot,command=args,cwd=str(root),exit_code=process.returncode,elapsed_s=round(time.monotonic()-started,3),log=label+'.txt',tail=process.stdout.splitlines()[-4:])
    results.append(item);(E/'TEST_RESULTS.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(item),flush=True)
