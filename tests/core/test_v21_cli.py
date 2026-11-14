"""Unit and integration tests for Mendex Core CLI v2.1."""
import json
import pytest
from mendex_core.cli import main


def test_cli_legacy_products(tmp_path, capsys):
    exit_code = main(["--root", str(tmp_path), "products"])
    assert exit_code in (0, None)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)


def test_cli_workspace_subcommands(tmp_path, capsys):
    # Create workspace
    exit_code = main(["--root", str(tmp_path), "workspace", "create", "PowerStage1", "--description", "CLI Workspace"])
    assert exit_code in (0, None)
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "CREATED"
    ws_id = out["workspace_id"]

    # List workspaces
    exit_code = main(["--root", str(tmp_path), "workspace", "list"])
    assert exit_code in (0, None)
    workspaces = json.loads(capsys.readouterr().out)
    assert any(w["workspace_id"] == ws_id for w in workspaces)

    # Workspace status
    exit_code = main(["--root", str(tmp_path), "workspace", "status", ws_id])
    assert exit_code in (0, None)
    status = json.loads(capsys.readouterr().out)
    assert status["workspace_id"] == ws_id
    assert status["directory_exists"] is True


def test_cli_specification_validate(tmp_path, capsys):
    spec = {
        "vin_min_v": 18.0,
        "vin_nom_v": 24.0,
        "vin_max_v": 32.0,
        "vout_v": 5.0,
        "iout_a": 4.0,
        "switching_frequency_hz": 100000.0,
    }
    exit_code = main(["--root", str(tmp_path), "specification", "validate", json.dumps(spec)])
    assert exit_code in (0, None)
    res = json.loads(capsys.readouterr().out)
    assert res["valid"] is True


def test_cli_calculations(tmp_path, capsys):
    # Dowell
    exit_code = main(["--root", str(tmp_path), "calculate", "dowell", "--freq", "100000", "--layers", "2", "--wire-dia", "0.5", "--porosity", "0.85", "--rdc", "0.05", "--temp", "100"])
    assert exit_code in (0, None)
    res = json.loads(capsys.readouterr().out)
    assert res["calculation"] == "dowell_ac_winding_factor"
    assert res["f_r"] >= 1.0

    # Losses
    exit_code = main(["--root", str(tmp_path), "calculate", "losses", "--rdson", "0.02", "--irms", "3.5", "--freq", "150000", "--duty", "0.45", "--eon", "15e-6", "--eoff", "10e-6"])
    assert exit_code in (0, None)
    res = json.loads(capsys.readouterr().out)
    assert res["calculation"] == "semiconductor_losses"
    assert res["p_total_w"] > 0

    # Steinmetz
    exit_code = main(["--root", str(tmp_path), "calculate", "steinmetz", "--freq", "100000", "--bmax", "0.2", "--volume", "1e-5", "--k", "1.5", "--alpha", "1.3", "--beta", "2.5"])
    assert exit_code in (0, None)
    res = json.loads(capsys.readouterr().out)
    assert res["calculation"] == "steinmetz_core_loss"
    assert res["total_core_loss_w"] > 0

    # Flyback
    exit_code = main(["--root", str(tmp_path), "calculate", "flyback", "--vin-min", "18", "--vin-nom", "24", "--vout", "12", "--iout", "2.5", "--freq", "100000", "--dmax", "0.45", "--eff", "0.88", "--bmax", "0.25", "--ae", "125"])
    assert exit_code in (0, None)
    res = json.loads(capsys.readouterr().out)
    assert res["calculation"] == "flyback_transformer_design"
    assert res["primary_turns"] > 0


def test_cli_design_synthesis(tmp_path, capsys):
    # 1. Create workspace
    main(["--root", str(tmp_path), "workspace", "create", "DesignCLI"])
    ws_id = json.loads(capsys.readouterr().out)["workspace_id"]

    # 2. Generate design
    exit_code = main([
        "--root", str(tmp_path),
        "design", "generate",
        "--workspace", ws_id,
        "--title", "Buck 24V-5V",
        "--fsw", "100000",
        "--ripple", "0.05",
        "--vin-nom", "24.0",
        "--vout", "5.0",
        "--iout", "4.0",
    ])
    assert exit_code in (0, None)
    gen_res = json.loads(capsys.readouterr().out)
    assert gen_res["status"] == "SYNTHESIZED"
    design_id = gen_res["design_id"]

    # 3. Show design
    exit_code = main(["--root", str(tmp_path), "design", "show", design_id])
    assert exit_code in (0, None)
    show_res = json.loads(capsys.readouterr().out)
    assert show_res["design_id"] == design_id
    assert len(show_res["components"]) > 0

    # 4. List candidates
    exit_code = main(["--root", str(tmp_path), "design", "candidates", design_id])
    assert exit_code in (0, None)
    cands_res = json.loads(capsys.readouterr().out)
    assert len(cands_res) > 0

    # 5. List artifacts
    exit_code = main(["--root", str(tmp_path), "artifact", "list", "--workspace", ws_id])
    assert exit_code in (0, None)
    arts_res = json.loads(capsys.readouterr().out)
    assert len(arts_res) >= 2


def test_cli_tool_commands(tmp_path, capsys):
    exit_code = main(["--root", str(tmp_path), "tool", "list"])
    assert exit_code in (0, None)
    tools = json.loads(capsys.readouterr().out)
    assert len(tools) >= 3

    tool_id = tools[0]["tool_id"]
    exit_code = main(["--root", str(tmp_path), "tool", "check", tool_id])
    assert exit_code in (0, None)
    chk = json.loads(capsys.readouterr().out)
    assert "status" in chk
