"""Standardized Model Context Protocol (MCP) Server for Mendex Engineering Core v2.1.

JSON-RPC 2.0 stdio server compliant with Anthropic MCP Specification (2024-11-05).
Compatible with:
- OpenAI Codex (VS Code)
- Anthropic Claude Code CLI
- Claude Desktop
- Cursor / Windsurf / Antigravity
"""
from __future__ import annotations

import io
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, TextIO, Union

from ..controller import MendexEngineeringController

logger = logging.getLogger("mendex_mcp")


class MendexMCPServer:
    """Standardized, agent-independent MCP Server."""

    PROTOCOL_VERSION = "2024-11-05"
    SERVER_NAME = "mendex-engineering-mcp"
    SERVER_VERSION = "2.1.0"

    def __init__(self, data_root: Optional[Union[str, Path]] = None):
        self.controller = MendexEngineeringController(data_root)
        self.tools_schema = self._build_tools_schema()

    def _build_tools_schema(self) -> List[Dict[str, Any]]:
        from ..engineering_lifecycle.api import tool_schemas
        from ..engineering_records.api import tool_schemas as record_schemas
        from ..engineering_reviews.api import tool_schemas as review_schemas
        schemas = tool_schemas() + record_schemas() + review_schemas() + [
            # 0. Engineering Projects (Primary v2.1 Concept)
            {
                "name": "list_projects",
                "description": "Lists all authoritative engineering projects and active baseline revisions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "create_project",
                "description": "Creates a new authoritative engineering project with baseline specifications and storage.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Project full title"},
                        "code": {"type": "string", "description": "Project code (e.g. PRJ-001)"},
                        "category": {"type": "string", "description": "Project category ('dc_dc_converter', 'magnetics', 'semiconductor', 'pcb')"},
                        "owner": {"type": "string", "description": "Lead engineer or team name"},
                        "description": {"type": "string", "description": "High-level project description"},
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "get_project",
                "description": "Retrieves comprehensive engineering project status, specifications, revisions, and evidence.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID or code"},
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "get_project_specifications",
                "description": "Retrieves electrical specifications and physical hash for an engineering project.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID or code"},
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "save_project_specification",
                "description": "Persists validated operating specifications to an engineering project.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID or code"},
                        "spec_data": {"type": "object", "description": "Electrical specification object containing vin_nom_v, vout_v, etc."},
                    },
                    "required": ["project_id", "spec_data"],
                },
            },
            {
                "name": "delete_project",
                "description": "Deletes an engineering project, its revisions, jobs, and workspace files.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID or code to delete"},
                    },
                    "required": ["project_id"],
                },
            },
            # 1. Workspaces
            {
                "name": "list_workspaces",
                "description": "Lists all active engineering workspaces and product workspaces.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
            {
                "name": "create_workspace",
                "description": "Creates a new engineering workspace for design generation, simulation, and artifacts.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Workspace title"},
                        "description": {"type": "string", "description": "Workspace description (optional)"},
                        "product_id": {"type": "string", "description": "Associated product UUID (optional)"},
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "get_workspace_status",
                "description": "Returns status, directories, design counts, and simulation history of a workspace.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace_id": {"type": "string", "description": "Workspace UUID"},
                    },
                    "required": ["workspace_id"],
                },
            },

            # Products & Systems
            {
                "name": "list_products",
                "description": "Lists all authoritative engineering products stored in SQLite.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
            {
                "name": "create_product",
                "description": "Creates a new authoritative engineering product and initial baseline revision.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Product code (e.g. SV-1000)"},
                        "name": {"type": "string", "description": "Product full title"},
                        "category": {"type": "string", "description": "Product category ('dc_dc_converter', 'magnetics', 'semiconductor', 'pcb')"},
                        "owner": {"type": "string", "description": "Lead engineer or team name"},
                        "description": {"type": "string", "description": "High-level product description"},
                    },
                    "required": ["code", "name"],
                },
            },
            {
                "name": "delete_product",
                "description": "Deletes an engineering product, its revisions, and directory contents.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product UUID or product code to delete"}
                    },
                    "required": ["product_id"],
                },
            },

            # 2. Specifications
            {
                "name": "validate_specification",
                "description": "Validates electrical operating parameters against SI schema and physical constraints.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "spec_data": {
                            "type": "object",
                            "description": "Electrical specification object containing vin_nom_v, vout_v, iout_a, etc.",
                        },
                    },
                    "required": ["spec_data"],
                },
            },
            {
                "name": "save_specification",
                "description": "Persists an updated electrical specification to a product revision.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "revision_id": {"type": "string", "description": "Product revision UUID"},
                        "spec_data": {"type": "object", "description": "Electrical specification object"},
                    },
                    "required": ["revision_id", "spec_data"],
                },
            },

            # 3. Design Synthesis
            {
                "name": "generate_design",
                "description": "Synthesizes candidate converter topologies, sizes components, and generates native CAD artifacts (.kicad_sch, .kicad_pcb, .asc, .net, .step).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace_id": {"type": "string", "description": "Target workspace UUID"},
                        "title": {"type": "string", "description": "Design title"},
                        "category": {"type": "string", "description": "Converter category (e.g. 'dc_dc_converter', 'isolated_dc_dc', 'inverter')", "default": "dc_dc_converter"},
                        "vin_nom": {"type": "number", "description": "Nominal input voltage (V)"},
                        "vin_min": {"type": "number", "description": "Minimum input voltage (V, optional)"},
                        "vin_max": {"type": "number", "description": "Maximum input voltage (V, optional)"},
                        "vout": {"type": "number", "description": "Regulated output voltage (V)"},
                        "iout": {"type": "number", "description": "Rated load current (A)"},
                        "fsw_hz": {"type": "number", "description": "Switching frequency (Hz, default 100000)"},
                        "ripple_v": {"type": "number", "description": "Maximum output ripple (V, default 0.05)"},
                        "isolation_v": {"type": "number", "description": "Galvanic isolation test voltage (V, optional)"},
                        "generate_artifacts": {"type": "boolean", "description": "Generate native CAD files (default true)"},
                        "product_id": {"type": "string", "description": "Optional associated product UUID"},
                    },
                    "required": ["workspace_id", "title", "vin_nom", "vout", "iout"],
                },
            },
            {
                "name": "get_design",
                "description": "Retrieves synthesized engineering design details, component values, and topology.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "design_id": {"type": "string", "description": "Design UUID"},
                    },
                    "required": ["design_id"],
                },
            },
            {
                "name": "list_design_candidates",
                "description": "Lists all candidate topologies synthesized for an engineering design with feasibility scores.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "design_id": {"type": "string", "description": "Design UUID"},
                    },
                    "required": ["design_id"],
                },
            },

            # 4. Analytical Calculations
            {
                "name": "run_engineering_calculations",
                "description": "Executes first-principles deterministic engineering calculations: 'dowell' (winding losses), 'losses' (MOSFET switching/conduction), 'steinmetz' (core loss), or 'flyback' (transformer sizing).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "calc_type": {
                            "type": "string",
                            "enum": ["dowell", "losses", "steinmetz", "flyback"],
                            "description": "Type of calculation to execute",
                        },
                        "params": {
                            "type": "object",
                            "description": "Parameters for the calculation",
                        },
                    },
                    "required": ["calc_type", "params"],
                },
            },

            # 5. Simulations
            {
                "name": "run_simulation",
                "description": "Executes headless industrial simulation (LTspice transient or FEMM magnetics) on generated netlists.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace_id": {"type": "string", "description": "Workspace UUID"},
                        "tool": {
                            "type": "string",
                            "enum": ["ltspice", "femm"],
                            "default": "ltspice",
                            "description": "Simulation tool",
                        },
                        "netlist_name": {"type": "string", "description": "Optional specific netlist (.net / .cir) or script (.lua) filename"},
                        "duration_s": {"type": "number", "default": 0.002, "description": "Simulation duration in seconds"},
                    },
                    "required": ["workspace_id"],
                },
            },
            {
                "name": "list_simulations",
                "description": "Lists simulation jobs and execution status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace_id": {"type": "string", "description": "Optional filter by workspace UUID"},
                    },
                },
            },

            # 6. Artifacts
            {
                "name": "list_design_artifacts",
                "description": "Lists all CAD schematics (.kicad_sch), PCB layouts (.kicad_pcb), SPICE netlists (.asc/.net), 3D STEP solids (.step), and simulation waveforms (.raw) in a workspace.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace_id": {"type": "string", "description": "Workspace UUID"},
                    },
                    "required": ["workspace_id"],
                },
            },
            {
                "name": "open_artifact",
                "description": "Opens a native design artifact in the host's specialized CAD application (KiCad, LTspice, or FreeCAD).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace_id": {"type": "string", "description": "Workspace UUID"},
                        "relative_path": {"type": "string", "description": "Artifact relative path inside workspace"},
                    },
                    "required": ["workspace_id", "relative_path"],
                },
            },

            # 7. Tools
            {
                "name": "list_tools",
                "description": "Lists external host engineering tools (LTspice, KiCad, FEMM, FreeCAD) and their operational status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
            {
                "name": "check_tool",
                "description": "Performs a live diagnostic health check on an engineering tool.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tool_id": {"type": "string", "description": "Tool identifier (e.g. 'ltspice', 'kicad', 'femm')"},
                    },
                    "required": ["tool_id"],
                },
            },
            {
                "name": "open_tool_file",
                "description": "Launches a native tool directly with a specified engineering file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tool_id": {"type": "string", "description": "Tool identifier"},
                        "file_path": {"type": "string", "description": "Path to target file"},
                    },
                    "required": ["tool_id", "file_path"],
                },
            },

            # 8. Revisions & Validation
            {
                "name": "list_revisions",
                "description": "Lists all revision snapshots and specification hashes for a product.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product UUID"},
                    },
                    "required": ["product_id"],
                },
            },
            {
                "name": "create_revision",
                "description": "Creates a new immutable revision baseline for a product.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product UUID"},
                        "label": {"type": "string", "description": "Revision label (e.g. 'Rev B')"},
                    },
                    "required": ["product_id", "label"],
                },
            },
            {
                "name": "get_validation_summary",
                "description": "Returns formal engineering validation summary and gate status for a revision.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "revision_id": {"type": "string", "description": "Product revision UUID"},
                    },
                    "required": ["revision_id"],
                },
            },

            # 9. Reporting
            {
                "name": "generate_engineering_report",
                "description": "Generates a formal, immutable engineering dossier report (HTML + JSON snapshot with SHA-256).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "revision_id": {"type": "string", "description": "Product revision UUID (optional; defaults to first active)"},
                    },
                },
            },
        ]

        from ..design.requests import DesignGenerationRequest
        for tool in schemas:
            if tool["name"] == "generate_design":
                tool["inputSchema"] = DesignGenerationRequest.model_json_schema()
        return schemas

    def handle_request(self, message: Any) -> Optional[Dict[str, Any]]:
        """Processes a single JSON-RPC 2.0 message and returns response dict (or None for notifications)."""
        if not isinstance(message, dict):
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: Expected a JSON object.",
                },
            }

        msg_id = message.get("id")
        method = message.get("method")

        # Notification (no id)
        if msg_id is None and "id" not in message:
            if method in ("initialized", "notifications/initialized"):
                logger.info("MCP client initialized.")
            return None

        # 1. Initialize
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": self.PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {},
                    },
                    "serverInfo": {
                        "name": self.SERVER_NAME,
                        "version": self.SERVER_VERSION,
                    },
                },
            }

        # 2. Ping
        if method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {},
            }

        # 3. List Tools
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": self.tools_schema,
                },
            }

        # 4. Call Tool
        if method == "tools/call":
            params = message.get("params")
            if not isinstance(params, dict):
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: 'params' must be an object.",
                    },
                }

            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            if not isinstance(tool_args, dict):
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: 'arguments' must be an object.",
                    },
                }

            try:
                res_data = self._dispatch_tool(tool_name, tool_args)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(res_data, indent=2),
                            }
                        ],
                        "isError": False,
                    },
                }
            except Exception as exc:
                logger.exception("Error executing MCP tool '%s'", tool_name)
                from ..engineering_lifecycle.api import OPERATIONS
                from ..engineering_records.api import OPERATIONS as RECORD_OPERATIONS
                error_text = f"Error executing tool '{tool_name}': {str(exc)}"
                if tool_name in OPERATIONS or tool_name in RECORD_OPERATIONS:
                    error_text = json.dumps({"schema_version": "3.1.0", "error": getattr(exc, "code", "INVALID_INPUT"), "message": str(exc)})
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": error_text,
                            }
                        ],
                        "isError": True,
                    },
                }

        # Method not found
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not found.",
            },
        }

    def _dispatch_tool(self, name: str, args: Dict[str, Any]) -> Any:
        ctrl = self.controller

        from ..engineering_lifecycle.api import OPERATIONS, dispatch
        if name in OPERATIONS:
            return dispatch(ctrl.service, name, args)

        from ..engineering_records.api import OPERATIONS as RECORD_OPERATIONS, dispatch as record_dispatch
        if name in RECORD_OPERATIONS:
            return record_dispatch(ctrl.service, name, args)

        from ..engineering_reviews.api import OPERATIONS as REVIEW_OPERATIONS, dispatch as review_dispatch
        if name in REVIEW_OPERATIONS:
            return review_dispatch(ctrl.service, name, args)

        if name == "list_workspaces":
            return ctrl.list_workspaces()
        elif name == "create_workspace":
            return ctrl.create_workspace(
                name=args["name"],
                description=args.get("description", ""),
                product_id=args.get("product_id"),
            )
        # Project tools
        elif name == "list_projects":
            return ctrl.list_projects()
        elif name == "create_project":
            return ctrl.create_project(
                name=args["name"],
                code=args.get("code"),
                category=args.get("category", "dc_dc_converter"),
                owner=args.get("owner", "Engineer"),
                description=args.get("description", ""),
            )
        elif name == "get_project":
            return ctrl.get_project(args["project_id"])
        elif name == "get_project_specifications":
            return ctrl.get_project_specifications(args["project_id"])
        elif name == "save_project_specification":
            return ctrl.save_project_specification(args["project_id"], args["spec_data"])
        elif name == "delete_project":
            return ctrl.delete_project(args["project_id"])
        elif name == "get_workspace_status":
            return ctrl.get_workspace_status(args["workspace_id"])
        elif name == "list_products":
            return ctrl.list_products()
        elif name == "create_product":
            return ctrl.create_product(
                code=args["code"],
                name=args["name"],
                category=args.get("category", "dc_dc_converter"),
                owner=args.get("owner", "Engineer"),
                description=args.get("description", ""),
            )
        elif name == "delete_product":
            return ctrl.delete_product(args["product_id"])
        elif name == "validate_specification":
            return ctrl.validate_specification(args["spec_data"])
        elif name == "save_specification":
            return ctrl.save_specification(args["revision_id"], args["spec_data"])
        elif name == "generate_design":
            from ..design.requests import DesignGenerationRequest
            return ctrl.generate_design(**DesignGenerationRequest.model_validate(args).model_dump())
        elif name == "get_design":
            return ctrl.get_design(args["design_id"])
        elif name == "list_design_candidates":
            return ctrl.list_design_candidates(args["design_id"])
        elif name == "run_engineering_calculations":
            return ctrl.run_calculation(args["calc_type"], args.get("params", {}))
        elif name == "run_simulation":
            return ctrl.run_simulation(
                workspace_id=args.get("project_id") or args.get("workspace_id"),
                tool=args.get("tool", "ltspice"),
                netlist_name=args.get("netlist_name"),
                duration_s=float(args.get("duration_s", 0.002)),
            )
        elif name == "list_simulations":
            return ctrl.list_simulations(args.get("project_id") or args.get("workspace_id"))
        elif name == "list_design_artifacts":
            return ctrl.list_design_artifacts(args["workspace_id"])
        elif name == "open_artifact":
            return ctrl.open_artifact(args["workspace_id"], args["relative_path"])
        elif name == "list_tools":
            return ctrl.list_tools()
        elif name == "check_tool":
            return ctrl.check_tool(args["tool_id"])
        elif name == "open_tool_file":
            return ctrl.open_tool_file(args["tool_id"], args["file_path"])
        elif name == "list_revisions":
            return ctrl.list_revisions(args["product_id"])
        elif name == "create_revision":
            return ctrl.create_revision(args["product_id"], args["label"])
        elif name == "get_validation_summary":
            return ctrl.get_validation_summary(args["revision_id"])
        elif name == "generate_engineering_report":
            return ctrl.generate_report(args.get("revision_id"))
        else:
            raise ValueError(f"Unknown MCP tool '{name}'")

    def run_stdio(self, input_stream: Optional[TextIO] = None, output_stream: Optional[TextIO] = None) -> None:
        """Runs the MCP server over standard input/output until EOF."""
        in_stream = input_stream or sys.stdin
        out_stream = output_stream or sys.stdout

        for line in in_stream:
            line_str = line.strip()
            if not line_str:
                continue
            try:
                request = json.loads(line_str)
                if isinstance(request, list):
                    if not request:
                        resp = {
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {
                                "code": -32600,
                                "message": "Invalid Request: empty batch.",
                            },
                        }
                        out_stream.write(json.dumps(resp) + "\n")
                        out_stream.flush()
                        continue
                    batch_responses = []
                    for item in request:
                        try:
                            sub_res = self.handle_request(item)
                            if sub_res is not None:
                                batch_responses.append(sub_res)
                        except Exception as item_exc:
                            batch_responses.append({
                                "jsonrpc": "2.0",
                                "id": getattr(item, "get", lambda k: None)("id") if isinstance(item, dict) else None,
                                "error": {
                                    "code": -32603,
                                    "message": f"Internal error: {str(item_exc)}",
                                },
                            })
                    if batch_responses:
                        out_stream.write(json.dumps(batch_responses) + "\n")
                        out_stream.flush()
                else:
                    response = self.handle_request(request)
                    if response is not None:
                        out_stream.write(json.dumps(response) + "\n")
                        out_stream.flush()
            except json.JSONDecodeError as exc:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(exc)}",
                    },
                }
                out_stream.write(json.dumps(err_resp) + "\n")
                out_stream.flush()
            except Exception as exc:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal server error: {str(exc)}",
                    },
                }
                out_stream.write(json.dumps(err_resp) + "\n")
                out_stream.flush()
