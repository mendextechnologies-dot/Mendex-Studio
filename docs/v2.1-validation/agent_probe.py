"""Actual independent client attempts with process-scoped MCP configuration."""
from pathlib import Path
import json, os, shutil, subprocess, sys, time
E=Path(__file__).parent.resolve()/'evidence';R=E.parents[2]
python=str(R/'.venv/Scripts/python.exe')
env=os.environ.copy();env['PYTHONPATH']=str(R/'src')
results={}
for agent in ['codex','claude']:
    root=E/(agent+'-data');root.mkdir(exist_ok=True)
    config={'mcpServers':{'mendex':{'command':python,'args':['-m','mendex_core.mcp','--root',str(root)],'env':{'PYTHONPATH':str(R/'src')}}}}
    path=E/(agent+'-mcp.json');path.write_text(json.dumps(config,indent=2),encoding='utf-8')
    prompt=('Independent Mendex audit, actual MCP invocation required. Use ONLY the mendex MCP tools; do not use shell, file editing, other servers, subagents or repair code. '
      'List available Mendex tools, list workspaces, create a workspace named "'+agent+' independent reference", validate {"vin_nom_v":24,"vout_v":5,"iout_a":4}, '
      'generate a supported buck design in that workspace with title Generic reference, vin_nom=24,vout=5,iout=4, retrieve it and candidates, '
      'run engineering losses calculation with params {}, request LTspice simulation, retrieve simulation history. '
      'Attempt design revision history and report only if identifiers are actually available from your own created records. '
      'Do not use other workspaces. Stop dependent operations at blockers, report exact tool errors and IDs. No manufacturing/design approvals. '
      'Return evidence for every attempted step and mark unavailable steps NOT_EVALUATED. Do not claim VS Code GUI verification from this CLI session.')
    if agent=='codex':
        command=[shutil.which('codex'),'exec','--ephemeral','--ignore-user-config','--skip-git-repo-check','-C',str(root),'--json','-s','read-only',
           '-c','mcp_servers.mendex.command='+json.dumps(python),
           '-c','mcp_servers.mendex.args='+json.dumps(['-m','mendex_core.mcp','--root',str(root)]),
           '-c','mcp_servers.mendex.env.PYTHONPATH='+json.dumps(str(R/'src')),prompt]
    else:
        exe=Path(os.environ['APPDATA'])/'npm/node_modules/@anthropic-ai/claude-code/bin/claude.exe'
        command=[str(exe),'-p',prompt,'--mcp-config',str(path),'--strict-mcp-config','--tools','','--allowedTools','mcp__mendex__*','--output-format','stream-json','--verbose','--no-session-persistence']
    start=time.monotonic()
    with (E/(agent+'-stdout.jsonl')).open('w',encoding='utf-8') as stdout,(E/(agent+'-stderr.log')).open('w',encoding='utf-8') as stderr:
        p=subprocess.Popen(command,cwd=root,env=env,stdout=stdout,stderr=stderr)
        try: code=p.wait(timeout=150)
        except subprocess.TimeoutExpired:
            p.kill();p.wait();code='TIMEOUT_150S'
    results[agent]={'command':command,'exit_code':code,'duration_s':round(time.monotonic()-start,3),'scope':'Actual CLI client; VS Code interactive session NOT_EVALUATED'}
    (E/'agents.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(agent,code,flush=True)
