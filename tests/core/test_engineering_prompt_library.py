import re
from pathlib import Path

from mendex_core.engineering_lifecycle.service import EngineeringLifecycleService
from mendex_core.mcp.server import MendexMCPServer


def test_generic_stage_prompts_match_real_lifecycle_and_tool_contracts(tmp_path):
    root = Path(__file__).resolve().parents[2] / "engineering-workflows"
    server = MendexMCPServer(tmp_path)
    names = {tool["name"] for tool in server.tools_schema}
    prompts = sorted((root / "stages").glob("*.md"))
    stages = EngineeringLifecycleService.default_definition().stages
    assert len(prompts) == len(stages) == 9
    sections = ("Purpose", "Required inputs", "Questions for the engineer", "Supported engineering tools", "MCP/CLI operations", "Expected artifacts", "Structured records to persist", "Validation rules", "Evidence requirements", "Completion criteria", "Human review requirements", "Error handling", "Next-stage recommendations")
    for prompt, stage in zip(prompts, stages):
        text = prompt.read_text(encoding="utf-8")
        assert f"`{stage.id}`" in text
        assert all("## " + section in text for section in sections)
    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        referenced = re.findall(r"mcp:([a-z_]+)", text)
        assert set(referenced) <= names, (path, set(referenced) - names)
        assert not any(code in text for code in ("SV-1000", "KC100", "SpectraVolt"))
    assert len(list((root / "templates").glob("*.md"))) == 6
