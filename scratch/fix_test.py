from pathlib import Path

path = Path("tests/integrations/test_copper_kicad_adapter.py")
content = path.read_text(encoding="utf-8")

old_text = """def test_mill_isolation_slot_with_iec60664_creepage(reference_project, adapter):
    \"\"\"Verify physical Edge.Cuts isolation slot milling with analytical IEC 60664-1 voltage input.\"\"\"
    pcb_path = reference_project["pcb"]
    res = adapter.mill_isolation_slot(pcb_path, working_voltage_v=400.0)"""

new_text = """def test_mill_isolation_slot_with_iec60664_creepage(tmp_path, adapter):
    \"\"\"Verify physical Edge.Cuts isolation slot milling with analytical IEC 60664-1 voltage input.\"\"\"
    proj_dir = tmp_path / "slot_proj"
    proj_dir.mkdir(parents=True, exist_ok=True)
    call_tool("project_create", {
        "name": "slot_proj",
        "dir": str(proj_dir),
        "board_size": [50.0, 35.0],
        "fab": "jlcpcb",
    })
    pcb_path = proj_dir / "slot_proj.kicad_pcb"
    res = adapter.mill_isolation_slot(pcb_path, working_voltage_v=400.0)"""

content_norm = content.replace("\r\n", "\n")
old_norm = old_text.replace("\r\n", "\n")
new_norm = new_text.replace("\r\n", "\n")

if old_norm in content_norm:
    content_norm = content_norm.replace(old_norm, new_norm)
    path.write_text(content_norm, encoding="utf-8")
    print("Success: Updated test_copper_kicad_adapter.py")
else:
    print("Error: Target not found")
