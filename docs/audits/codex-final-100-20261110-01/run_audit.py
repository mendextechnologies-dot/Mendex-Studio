"""Verification only: run frozen snapshots, retain raw outputs, never install/fix."""
from pathlib import Path
import json, os, subprocess, tempfile, time

E=Path(__file__).resolve().parent
P=r'C:\Mendex studio\.venv\Scripts\python.exe'
S={item['name']:Path(item['root']) for item in json.loads((E/'SNAPSHOTS.json').read_text())['items']}
out=[]
for name,deep in [('working',False),('working',True),('remediation',False),('remediation',True),('released',False)]:
 root=S[name];label=name+('-deep' if deep else '-short')
 temp=root/'.audit-tests' if deep else Path(tempfile.mkdtemp(prefix='m100-'))/'tests'
 env=os.environ.copy();env.update(PYTHONPATH=str(root/'src'),PYTHONDONTWRITEBYTECODE='1',QT_QPA_PLATFORM='offscreen',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
 command=[P,'-m','pytest','-q','-p','no:cacheprovider','--basetemp',str(temp)]
 start=time.monotonic();p=subprocess.run(command,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
 (E/(label+'.txt')).write_text('COMMAND: '+subprocess.list2cmdline(command)+'\nCWD: '+str(root)+'\nPYTHONPATH: '+env['PYTHONPATH']+'\n\n'+p.stdout,encoding='utf-8')
 result={'label':label,'snapshot':name,'command':command,'cwd':str(root),'log':label+'.txt','exit_code':p.returncode,'elapsed_s':round(time.monotonic()-start,3),'tail':p.stdout.splitlines()[-5:]}
 out.append(result);(E/'TEST_RESULTS.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
