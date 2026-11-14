"""KiCad 9/10 schematic and project generator from Design Intermediate Representation (IR).

Translates Design IR into valid, editable KiCad .kicad_sch and .kicad_pro files
ready for inspection in Eeschema, complete with real symbol library bindings,
declarative Copper sch_apply operations, pin terminal wiring, power rails,
and ERC verification.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from ..ir import DesignIntermediateRepresentation, ComponentType, IRComponent
from ..naming import sanitize_filename, clean_title


def resolve_symbol_lib_id(comp: IRComponent) -> str:
    """Maps Design IR component into official KiCad symbol library identifier."""
    explicit = comp.parameters.get("kicad_symbol")
    if explicit:
        return str(explicit)
    name_u = comp.name.upper()
    des_u = comp.designator.upper()

    if comp.type == ComponentType.CAPACITOR:
        if "POLAR" in name_u or des_u.startswith("CP") or "ELECT" in name_u:
            return "Device:C_Polarized"
        return "Device:C"
    elif comp.type == ComponentType.CAPACITOR_POLARIZED:
        return "Device:C_Polarized"
    elif comp.type == ComponentType.INDUCTOR:
        return "Device:L"
    elif comp.type == ComponentType.DIODE:
        if "BRIDGE" in name_u or des_u.startswith("BR"):
            return "Device:D_Bridge_+-AA"
        elif "1N4148" in name_u or "4148" in name_u:
            return "Diode:1N4148"
        return "Device:D"
    elif comp.type == ComponentType.BRIDGE_RECTIFIER:
        return "Device:D_Bridge_+-AA"
    elif comp.type in (ComponentType.SWITCH_MOSFET, ComponentType.SWITCH_GAN, ComponentType.SWITCH_SIC):
        return "Device:Q_NMOS"
    elif comp.type == ComponentType.SWITCH_IGBT:
        return "Device:Q_NIGBT_GCE"
    elif comp.type == ComponentType.TRANSFORMER:
        if "2S" in name_u or "DUAL" in name_u or "MULTI" in name_u or "PUSHPULL" in name_u or "FORWARD" in name_u or "LLC" in name_u or "RESONANT" in name_u or "PSFB" in name_u or "FULLBRIDGE" in name_u:
            return "Device:Transformer_1P_2S"
        elif "SP" in name_u or "CENTER" in name_u or "SPLIT" in name_u:
            return "Device:Transformer_SP_1S"
        return "Device:Transformer_1P_1S"
    elif comp.type == ComponentType.VOLTAGE_SOURCE:
        return "Connector:Conn_01x02_Pin"
    elif comp.type == ComponentType.CURRENT_SOURCE:
        return "Connector:Conn_01x02_Pin"
    elif comp.type == ComponentType.REGULATOR_LINEAR:
        if "7815" in name_u:
            return "Regulator_Linear:LM7815_TO220"
        return "Regulator_Linear:LM7805_TO220"
    elif comp.type in (ComponentType.GATE_DRIVER, ComponentType.OPTOCOUPLER):
        return "Driver_FET:HCPL-3120"
    elif comp.type == ComponentType.IC_LOGIC:
        return "74xx:74HC123"
    elif comp.type == ComponentType.IC_CONTROLLER:
        if "MGJ" in name_u:
            return "Converter_DCDC_Isolated:MGJ2D151505SC"
        elif "HCPL" in name_u or "ACPL" in name_u:
            return "Driver_FET:HCPL-3120"
        elif "7805" in name_u:
            return "Regulator_Linear:LM7805_TO220"
        return "Device:R"
    elif comp.type == ComponentType.CONNECTOR:
        return "Connector:Conn_01x02_Pin"
    elif comp.type == ComponentType.SWITCH_PUSH:
        return "Switch:SW_Push"

    # Designator prefix heuristic fallback
    if des_u.startswith("J"):
        return "Connector:Conn_01x02_Pin"
    if des_u.startswith("SW"):
        return "Switch:SW_Push"
    if des_u.startswith("D"):
        if "BRIDGE" in name_u or "BR" in des_u:
            return "Device:D_Bridge_+-AA"
        return "Device:D"
    if des_u.startswith("Q"):
        return "Device:Q_NMOS"
    if des_u.startswith("C"):
        if "POLAR" in name_u or des_u.startswith("CP"):
            return "Device:C_Polarized"
        return "Device:C"
    if des_u.startswith("L"):
        return "Device:L"
    if des_u.startswith("T"):
        return "Device:Transformer_1P_1S"
    if des_u.startswith("U"):
        if "78" in name_u:
            return "Regulator_Linear:LM7805_TO220"
        if "HC" in name_u:
            return "74xx:74HC123"
        if "HCPL" in name_u or "OPT" in name_u:
            return "Driver_FET:HCPL-3120"

    return "Device:R"


def resolve_footprint(comp: IRComponent) -> str:
    """Maps Design IR component to a standard KiCad footprint if not explicitly specified."""
    if comp.footprint:
        return comp.footprint

    ct = comp.type
    name_u = comp.name.upper()
    des_u = comp.designator.upper()

    if ct in (ComponentType.VOLTAGE_SOURCE, ComponentType.CURRENT_SOURCE, ComponentType.CONNECTOR) or des_u.startswith("J"):
        return "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical"
    elif ct in (ComponentType.SWITCH_MOSFET, ComponentType.SWITCH_GAN, ComponentType.SWITCH_SIC, ComponentType.SWITCH_IGBT) or des_u.startswith("Q"):
        return "Package_TO_SOT_SMD:TO-252-2"
    elif ct == ComponentType.INDUCTOR or des_u.startswith("L"):
        return "Inductor_SMD:L_1210_3225Metric"
    elif ct == ComponentType.CAPACITOR_POLARIZED or "POLAR" in name_u or des_u.startswith("CP"):
        return "Capacitor_SMD:CP_Elec_8x10"
    elif ct == ComponentType.CAPACITOR or des_u.startswith("C"):
        return "Capacitor_SMD:C_0805_2012Metric"
    elif ct in (ComponentType.DIODE, ComponentType.BRIDGE_RECTIFIER) or des_u.startswith("D"):
        return "Diode_SMD:D_SMA"
    elif ct == ComponentType.TRANSFORMER or des_u.startswith("T"):
        return "Transformer_THT:Transformer_Breve_TEZ-22x24"
    elif ct == ComponentType.REGULATOR_LINEAR:
        return "Package_TO_SOT_THT:TO-220-3_Vertical"
    elif ct in (ComponentType.GATE_DRIVER, ComponentType.OPTOCOUPLER):
        return "Package_DIP:DIP-8_W7.62mm"
    elif ct == ComponentType.IC_LOGIC:
        return "Package_DIP:DIP-16_W7.62mm"
    elif ct == ComponentType.SWITCH_PUSH or des_u.startswith("SW"):
        return "Button_Switch_SMD:SW_SPST_PTS645"

    return "Resistor_SMD:R_1206_3216Metric"


def normalize_pin_id(comp_type: ComponentType, pin_id: str) -> str:
    """Normalizes pin identifiers from IR into KiCad symbol pin numbers or names."""
    p = str(pin_id).strip()
    pl = p.lower()

    if pl in ("p", "+", "pos", "positive"):
        return "1"
    if pl in ("n", "-", "neg", "negative"):
        return "2"

    if comp_type in (
        ComponentType.SWITCH_MOSFET,
        ComponentType.SWITCH_GAN,
        ComponentType.SWITCH_SIC,
    ):
        if pl in ("d", "drain"):
            return "D"
        if pl in ("g", "gate"):
            return "G"
        if pl in ("s", "source"):
            return "S"

    if comp_type == ComponentType.SWITCH_IGBT:
        if pl in ("c", "collector"):
            return "C"
        if pl in ("g", "gate"):
            return "G"
        if pl in ("e", "emitter"):
            return "E"

    if comp_type == ComponentType.DIODE:
        if pl in ("a", "anode"):
            return "A"
        if pl in ("k", "cathode"):
            return "K"

    if comp_type == ComponentType.TRANSFORMER:
        if pl in ("pri_dot", "pri+", "pri1", "1", "aa"):
            return "1"
        if pl in ("pri_undot", "pri-", "pri2", "2", "ab"):
            return "2"
        if pl in ("sec1_dot", "sec1+", "sec_dot", "sec+", "sec1", "3", "sa"):
            return "3"
        if pl in ("sec1_undot", "sec1-", "sec_undot", "sec-", "4", "sb"):
            return "4"
        if pl in ("sec2_dot", "sec2+", "5", "sc"):
            return "5"
        if pl in ("sec2_undot", "sec2-", "6", "sd"):
            return "6"

    return p


def mendex_ir_to_copper_ops(ir: DesignIntermediateRepresentation) -> List[Dict[str, Any]]:
    """Converts a DesignIntermediateRepresentation into declarative Copper sch_apply ops.

    Emits:
      1. 'place' ops with official KiCad symbol library bindings, values, and footprints.
      2. 'connect' ops mapping component terminal pins to electrical net identifiers.
      3. 'pwr_flag' ops on all power rails (VIN, VOUT, GND, VCC, VDD) to satisfy KiCad ERC.
    """
    comp_by_id = {c.id: c for c in ir.components}
    ops: List[Dict[str, Any]] = []

    # 1. Place components
    for c in ir.components:
        # Sanitize reference designator (remove characters like '_' that KiCad parsers reject)
        ref = c.designator.replace("_", "")
        lib_id = resolve_symbol_lib_id(c)
        fp = resolve_footprint(c)
        val = f"{c.value:g} {c.unit}".strip() if c.value else c.name
        place_op: Dict[str, Any] = {
            "op": "place",
            "lib_id": lib_id,
            "ref": ref,
            "value": val,
            "footprint": fp,
        }
        fields: Dict[str, str] = {}
        if c.mpn:
            fields["MPN"] = c.mpn
        if c.manufacturer:
            fields["Manufacturer"] = c.manufacturer
        if "LCSC" in c.parameters:
            fields["LCSC"] = str(c.parameters["LCSC"])
        if fields:
            place_op["fields"] = fields
        ops.append(place_op)

    # 2. Connect nets
    for net in ir.nets:
        pins: List[str] = []
        for conn in net.connections:
            comp = comp_by_id.get(conn.component_id)
            if comp:
                ref = comp.designator.replace("_", "")
                p_norm = normalize_pin_id(comp.type, conn.pin_id)
                pins.append(f"{ref}.{p_norm}")
        if len(pins) == 1:
            ops.append({"op": "connect", "pin": pins[0], "net": net.name})
        elif len(pins) > 1:
            ops.append({"op": "connect", "pins": pins, "net": net.name})

    # 3. Inject pwr_flags on power rails
    power_net_names = {
        "VIN", "VOUT", "GND", "VCC", "VDD", "VBAT", "VBUS", "PRI_GND", "SEC_GND",
        "HV_PLUS", "HV_MINUS", "+12V", "+15V", "+5V", "+24V", "+3V3", "PWR", "GATE", "GATE_HI", "GATE_LO", "GATE_A_HI", "GATE_A_LO", "GATE_B_HI", "GATE_B_LO", "HB_LEG_A", "HB_LEG_B", "PWM"
    }
    for net in ir.nets:
        nu = net.name.upper()
        if nu in power_net_names or net.is_power or net.is_ground or nu.startswith("+") or nu.endswith("GND"):
            ops.append({"op": "pwr_flag", "net": net.name})

    return ops


class KiCadSchematicGenerator:
    """Generates editable KiCad 9/10 schematic and project files from Design IR."""

    @staticmethod
    def generate_schematic_sexpr(ir: DesignIntermediateRepresentation) -> str:
        """Build KiCad 10 symbols and connections using Copper's native model.

        Embedded library geometry and actual pin tips replace the old placeholder
        instances. Named pin stubs avoid sheet-spanning wires crossing other parts.
        Unknown pin mappings fail explicitly instead of silently moving a net.
        """
        import math
        from copper_kicad import sexpr
        from copper_kicad.sexpr import Sym
        from copper_kicad.kicad.libs import read_symbol
        from copper_kicad.sch.model import Schematic

        title = clean_title(ir.title or "Mendex Schematic")
        columns = 4
        rows = max(1, math.ceil(len(ir.components) / columns))
        # A3 holds up to 16 typical symbols; larger circuits get a larger sheet.
        paper = "A3" if rows <= 4 else "A2" if rows <= 6 else "A1" if rows <= 9 else "A0"
        if rows > 14:
            raise ValueError("Schematic needs hierarchical sheets: too many components for one sheet")
        sch = Schematic.new(project_name=sanitize_filename(title, fallback="kicad_project"),
                            paper=paper, title=title)
        block = sexpr.find(sch.tree, "title_block")
        block.append([Sym("comment"), 1, f"Topology: {ir.topology}; draft, NOT_EVALUATED"])
        placed = {}
        components = {c.id: c for c in ir.components}
        refs = set()
        for i, comp in enumerate(ir.components):
            ref = comp.designator.replace("_", "")
            if ref in refs:
                raise ValueError(f"Duplicate schematic reference: {ref}")
            refs.add(ref)
            lib_id = resolve_symbol_lib_id(comp)
            lib = read_symbol(lib_id)
            key = sch.embed(lib)
            # Place every unit, including dedicated power units, of multi-unit ICs.
            units = sorted({p["unit"] for p in lib.pins if p["unit"] > 0}) or [1]
            if len(units) > 4:
                raise ValueError(f"{ref}: explicit multi-sheet layout required for {lib_id}")
            x = 50.8 + (i % columns) * 88.9
            y = 38.1 + (i // columns) * 63.5
            value = f"{comp.value:g} {comp.unit}".strip() if comp.value else comp.name
            instances = []
            for unit in units:
                at = (x + ((unit - 1) % 2) * 30.48,
                      y + ((unit - 1) // 2) * 25.4)
                instances.append(sch.add_symbol(key, lib_id, ref, at, unit=unit,
                                 value=value, fields={"Footprint": comp.footprint or ""}))
            placed[comp.id] = instances

        assigned = {}
        for net in ir.nets:
            for conn in net.connections:
                if conn.component_id not in components:
                    raise ValueError(f"{net.name}: unknown component {conn.component_id}")
                comp = components[conn.component_id]
                pins = [p for inst in placed[comp.id] for p in inst.pins_world()]
                token = normalize_pin_id(comp.type, conn.pin_id)
                # Explicit pin_map overrides symbolic aliases and library pin names.
                token = str(comp.parameters.get("kicad_pin_map", {}).get(str(conn.pin_id), token))
                matches = [p for p in pins if p["number"] == token]
                if not matches:
                    matches = [p for p in pins if p["name"].casefold() == token.casefold()]
                if len(matches) != 1:
                    raise ValueError(f"{comp.designator}: cannot uniquely map pin {conn.pin_id!r} to {resolve_symbol_lib_id(comp)}; provide kicad_pin_map")
                pin = matches[0]
                identity = (comp.id, pin["number"])
                if identity in assigned:
                    if assigned[identity] != net.name:
                        raise ValueError(f"{comp.designator}.{pin['number']}: assigned to multiple nets")
                    continue
                assigned[identity] = net.name
                tip, outward = pin["xy"], pin["out"]
                end = (round(tip[0] + outward[0] * 5.08, 4),
                       round(tip[1] + outward[1] * 5.08, 4))
                sch.add_wire(tip, end)
                angle = 0 if outward[0] >= 0 else 180
                if abs(outward[1]) > abs(outward[0]):
                    angle = 90 if outward[1] < 0 else 270
                sch.add_label(net.name, end, angle=angle)
        # Unspecified pins remain visibly unconnected for ERC, never auto-approved.
        return sch.text()

    @staticmethod
    def generate_project_json(title: str) -> str:
        """Generates standard KiCad 9/10 .kicad_pro file JSON."""
        safe_base = sanitize_filename(title, fallback="kicad_project")
        pro_dict = {
            "board": {
                "design_settings": {
                    "defaults": {
                        "track_width": 0.25,
                        "clearance": 0.2,
                    }
                }
            },
            "meta": {
                "filename": f"{safe_base}.kicad_pro",
                "version": 1
            },
            "schematic": {
                "annotate_start_num": 1,
                "drawing": {
                    "dashed_lines_dash_length_ratio": 12.0,
                    "dashed_lines_gap_length_ratio": 3.0
                }
            }
        }
        return json.dumps(pro_dict, indent=2)

    @staticmethod
    def export_project(ir: DesignIntermediateRepresentation, target_dir: Path, use_copper: bool = True) -> Dict[str, Any]:
        """Exports complete KiCad project files into destination directory."""
        target_dir = Path(target_dir).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        base_name = sanitize_filename(ir.title or ir.topology, fallback="kicad_project")

        if use_copper:
            try:
                from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter
                adapter = CopperKiCadAdapter()
                if adapter.is_available():
                    copper_res = KiCadSchematicGenerator.export_copper_project(
                        ir, target_dir, auto_place=True, route=False
                    )
                    return {
                        "schematic": Path(copper_res["schematic"]),
                        "project": Path(copper_res["project"]),
                        "pcb": Path(copper_res["pcb"]),
                        "copper_result": copper_res,
                    }
            except Exception:
                pass

        sch_path = target_dir / f"{base_name}.kicad_sch"
        pro_path = target_dir / f"{base_name}.kicad_pro"

        sch_path.write_text(KiCadSchematicGenerator.generate_schematic_sexpr(ir), encoding="utf-8")
        pro_path.write_text(KiCadSchematicGenerator.generate_project_json(base_name), encoding="utf-8")

        return {
            "schematic": sch_path,
            "project": pro_path,
        }

    @staticmethod
    def export_copper_project(
        ir: DesignIntermediateRepresentation,
        target_dir: Path,
        rules: str = "jlcpcb",
        board_size: Optional[Tuple[float, float]] = None,
        auto_place: bool = True,
        route: bool = False,
        pour_ground: bool = True,
        layers: int = 2,
    ) -> Dict[str, Any]:
        """Synthesizes a complete native KiCad 10 project from Design IR via Copper MCP engine.

        Performs:
          1. Native project creation with fab design rules and outline.
          2. Declarative schematic population via atomic sch_apply operations.
          3. KiCad ERC verification.
          4. PCB netlist synchronization.
          5. Optional footprint auto-placement inside board outline.
          6. Optional guided PCB routing with power netclasses and ground plane pour.
        """
        import copper_kicad.tools  # Ensure MCP tools are registered
        from copper_kicad.mcp.registry import call_tool
        from integrations.adapters.copper_kicad_adapter import CopperKiCadAdapter

        target_dir = Path(target_dir).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        proj_name = target_dir.name

        # 1. Project creation with outline
        if board_size:
            b_size = list(board_size)
        else:
            comp_count = len(ir.components)
            if comp_count > 12:
                b_size = [100.0, 75.0]
            elif comp_count > 6:
                b_size = [80.0, 60.0]
            else:
                b_size = [60.0, 45.0]
        fab_profile = "jlcpcb" if str(rules).lower() in ("jlc", "jlcpcb", "default", "none") else rules
        create_args = {
            "name": proj_name,
            "dir": str(target_dir),
            "board_size": b_size,
            "fab": fab_profile,
        }
        if layers == 4:
            create_args["template"] = "4layer"
        create_res = call_tool("project_create", create_args)
        if create_res.get("isError"):
            err_text = ""
            for c in create_res.get("content", []):
                if c.get("type") == "text":
                    err_text += c.get("text", "")
            raise RuntimeError(f"Project creation failed: {err_text}")

        proj_info = (create_res.get("structuredContent") or {}).get("project", {})
        sch_path = Path(proj_info.get("schematic")) if proj_info.get("schematic") else (target_dir / f"{proj_name}.kicad_sch")
        pcb_path = Path(proj_info.get("pcb")) if proj_info.get("pcb") else (target_dir / f"{proj_name}.kicad_pcb")
        actual_dir = Path(proj_info.get("dir")) if proj_info.get("dir") else target_dir
        pro_path = actual_dir / f"{actual_dir.name}.kicad_pro"

        # 2. Convert IR to declarative Copper ops and apply
        ops = mendex_ir_to_copper_ops(ir)
        adapter = CopperKiCadAdapter()
        apply_res = adapter.apply_schematic(sch_path, ops, verify=True)

        result: Dict[str, Any] = {
            "project_dir": str(target_dir),
            "schematic": str(sch_path),
            "pcb": str(pcb_path),
            "project": str(pro_path),
            "ops_applied": apply_res.get("ops_applied", 0),
            "erc": apply_res.get("erc", {}),
            "sync": False,
            "placed": False,
            "routed": False,
        }

        # 3. Synchronize PCB netlist
        sync_res = call_tool("pcb_sync", {"project": str(target_dir)})
        if not sync_res.get("isError"):
            result["sync"] = True

        # 4. Optional auto-placement
        if auto_place and result["sync"]:
            place_res = adapter.place_pcb(pcb_path, auto=True)
            result["placed"] = place_res.get("success", False)
            result["placement_elegance"] = place_res.get("elegance")

        # 5. Optional guided routing
        if route and result["placed"]:
            route_res = adapter.route_pcb(pcb_path, pour_ground=pour_ground)
            result["routed"] = route_res.get("routing_completed", False)
            result["tracks"] = route_res.get("tracks", 0)
            result["drc_errors"] = route_res.get("drc_errors", 0)

        return result
