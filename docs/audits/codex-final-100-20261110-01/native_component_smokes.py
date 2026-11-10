"""Generic native component probes, not Studio adapter qualification/design work."""
from pathlib import Path
import hashlib,json,os,subprocess,tempfile

E=Path(__file__).resolve().parent
root=Path(tempfile.mkdtemp(prefix='m100native-'))
results=[]
def run(tool,args,env=None):
    item={'tool':tool,'command':args,'cwd':str(root),'scope':'Direct native software component; NOT Studio adapter/UI integration'}
    try:
        p=subprocess.run(args,cwd=root,env=env,stdin=subprocess.DEVNULL,capture_output=True,text=True,errors='replace',timeout=40,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        item.update(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
    except Exception as exc:item['error']=repr(exc)
    return item

step=root/'synthetic-cube.step'
script=root/'generic_component.py'
script.write_text('import FreeCAD as App, Part\n'+
                  'doc=App.newDocument("MendexSoftwareFixture")\n'+
                  'obj=doc.addObject("PartDesign::Feature","GenericBox")\n'+
                  'obj.Shape=Part.makeBox(1,1,1)\n'+
                  'doc.recompute()\n'+
                  'Part.export([obj],'+repr(str(step))+')\n'+
                  'App.closeDocument(doc.Name)\n',encoding='utf-8')
cad=run('FreeCAD',[r'C:\Program Files\FreeCAD 1.1\bin\freecadcmd.exe','--user-cfg',str(root/'user.cfg'),'--system-cfg',str(root/'system.cfg'),str(script)])
cad['output_exists']=step.is_file()
cad['step_header_valid']=step.is_file() and step.read_text(errors='replace').startswith('ISO-10303-21;')
results.append(cad)

notebook=root/'software-fixture.ipynb'
nb={'cells':[{'cell_type':'code','execution_count':None,'id':'software-fixture','metadata':{},'outputs':[],
              'source':['import sys\n','print("MENDEX_SOFTWARE_FIXTURE")\n','print(sys.executable)']}],
    'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python'}},
    'nbformat':4,'nbformat_minor':5}
notebook.write_text(json.dumps(nb),encoding='utf-8')
env=os.environ.copy();env.update(JUPYTER_RUNTIME_DIR=str(root/'jupyter-runtime'),JUPYTER_CONFIG_DIR=str(root/'jupyter-config'))
jupyter=run('Jupyter',[r'C:\Mendex studio\.venv\Scripts\jupyter.exe','nbconvert','--execute','--to','notebook','--ExecutePreprocessor.timeout=15','--output','executed.ipynb',str(notebook)],env)
executed=root/'executed.ipynb'
jupyter['output_exists']=executed.is_file()
if executed.is_file():
    parsed=json.loads(executed.read_text(encoding='utf-8'))
    jupyter['cell_outputs']=parsed['cells'][0]['outputs']
    jupyter['expected_marker_found']='MENDEX_SOFTWARE_FIXTURE' in json.dumps(jupyter['cell_outputs'])
results.append(jupyter)

dest=E/'native-components';dest.mkdir()
for item in (script,step,notebook,executed):
    if item.is_file():
        data=item.read_bytes();(dest/item.name).write_bytes(data)
        results.append({'artifact':item.name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
with (E/'NATIVE_COMPONENT_SMOKES.json').open('x',encoding='utf-8') as f:json.dump({'root':str(root),'results':results},f,indent=2)
print(json.dumps(results,indent=2))
