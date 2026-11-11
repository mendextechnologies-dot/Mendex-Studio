"""Retry authorized audit tools using process-scoped per-server approval policy."""
import json, os, subprocess, time
from pathlib import Path
E=Path(__file__).parent.resolve()/'evidence'
entry=json.loads((E/'agents.json').read_text())['codex']
cmd=entry['command']
cmd[-1:-1]=['-c','mcp_servers.mendex.default_tools_approval_mode="approve"','-c','mcp_servers.mendex.enabled_tools=["list_tools","list_workspaces","create_workspace","validate_specification","generate_design","get_design","list_design_candidates","run_engineering_calculations","run_simulation","list_simulations","get_workspace_status","get_validation_summary","list_revisions","generate_engineering_report"]']
env=os.environ.copy();env['PYTHONPATH']=str(E.parents[2]/'src')
start=time.monotonic()
with (E/'codex-retry-stdout.jsonl').open('w',encoding='utf-8') as out,(E/'codex-retry-stderr.log').open('w',encoding='utf-8') as err:
    p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=out,stderr=err,env=env)
    try: code=p.wait(150)
    except subprocess.TimeoutExpired: p.kill();p.wait();code='TIMEOUT_150S'
(E/'codex-retry.json').write_text(json.dumps({'command':cmd,'exit_code':code,'duration_s':time.monotonic()-start,'policy_scope':'Only isolated audit MCP tools, no launch or saved configuration change'},indent=2),encoding='utf-8')
