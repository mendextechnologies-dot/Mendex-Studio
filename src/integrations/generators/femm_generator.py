from __future__ import annotations
from pathlib import Path


def generate_femm_transformer_script(
    core_type: str = "EE",
    primary_turns: int = 24,
    secondary_turns: int = 1000,
    primary_current_a: float = 2.5,
    air_gap_mm: float = 0.5,
    frequency_hz: float = 100000.0,
    output_ans_path: str = "temp_transformer.ans",
    results_txt_path: str = "results.txt",
) -> str:
    """Generates a headless Lua script for FEMM 4.2 to model a high-frequency transformer

    with dimensionally accurate closed ferrite geometry, physical air gap, primary and
    secondary windings, and Dirichlet A=0 outer boundary.
    Extracts magnetizing inductance, flux linkage, and peak core flux density.
    """
    safe_res = str(results_txt_path).replace("\\", "/")
    fem_name = "temp_transformer.fem"

    # Core dimension presets (in mm): (r_post, r_shell_in, r_shell_out, z_window, z_total)
    presets = {
        "ETD34": (5.4, 13.15, 17.1, 12.1, 17.3),
        "ETD49": (8.15, 18.25, 24.9, 18.2, 24.9),
        "EE25": (3.5, 9.0, 12.5, 8.0, 12.5),
        "EE": (5.4, 13.15, 17.1, 12.1, 17.3),
    }
    c_key = core_type.upper().strip()
    r_post, r_shell_in, r_shell_out, z_window, z_total = presets.get(c_key, presets["EE"])

    g = max(0.01, float(air_gap_mm))
    g_half = round(g / 2.0, 4)

    # Window and winding positions
    h_w = round(max(1.0, z_window - 3.1), 2)
    w_window = r_shell_in - r_post
    w_pri = round(max(0.8, w_window * 0.25), 2)
    w_sec = round(max(0.8, w_window * 0.45), 2)
    r_pri_in = round(r_post + 1.1, 2)
    r_pri_out = round(r_pri_in + w_pri, 2)
    r_sec_in = round(r_pri_out + 1.0, 2)
    r_sec_out = round(min(r_shell_in - 0.95, r_sec_in + w_sec), 2)

    r_outer_box = round(r_shell_out * 2.6, 1)
    z_outer_box = round(z_total * 2.6, 1)

    nodes = set()
    node_list = []
    def add_node(r, z):
        pt = (round(float(r), 4), round(float(z), 4))
        if pt not in nodes:
            nodes.add(pt)
            node_list.append(pt)
        return pt

    segments = set()
    segment_list = []
    def add_segment(r1, z1, r2, z2, bdry="<None>"):
        p1 = add_node(r1, z1)
        p2 = add_node(r2, z2)
        if p1 == p2:
            return
        edge = (min(p1, p2), max(p1, p2))
        if edge not in segments:
            segments.add(edge)
            segment_list.append((p1[0], p1[1], p2[0], p2[1], bdry))

    def add_rect(r1, z1, r2, z2, bdry="<None>"):
        add_segment(r1, z1, r2, z1, bdry)
        add_segment(r2, z1, r2, z2, bdry)
        add_segment(r2, z2, r1, z2, bdry)
        add_segment(r1, z2, r1, z1, bdry)

    # Center leg upper (Ferrite)
    add_rect(0, g_half, r_post, z_window)
    # Air gap (Air)
    add_rect(0, -g_half, r_post, g_half)
    # Center leg lower (Ferrite)
    add_rect(0, -z_window, r_post, -g_half)

    # Top yoke (Ferrite)
    add_segment(0, z_window, r_post, z_window)
    add_segment(r_post, z_window, r_shell_in, z_window)
    add_segment(r_shell_in, z_window, r_shell_out, z_window)
    add_segment(r_shell_out, z_window, r_shell_out, z_total)
    add_segment(r_shell_out, z_total, 0, z_total)
    add_segment(0, z_total, 0, z_window)

    # Bottom yoke (Ferrite)
    add_segment(0, -z_window, r_post, -z_window)
    add_segment(r_post, -z_window, r_shell_in, -z_window)
    add_segment(r_shell_in, -z_window, r_shell_out, -z_window)
    add_segment(r_shell_out, -z_window, r_shell_out, -z_total)
    add_segment(r_shell_out, -z_total, 0, -z_total)
    add_segment(0, -z_total, 0, -z_window)

    # Outer leg / shell (Ferrite)
    add_segment(r_shell_in, -z_window, r_shell_in, z_window)
    add_segment(r_shell_out, -z_window, r_shell_out, z_window)

    # Primary winding (Copper)
    add_rect(r_pri_in, -h_w, r_pri_out, h_w)

    # Secondary winding (Copper)
    add_rect(r_sec_in, -h_w, r_sec_out, h_w)

    # Outer boundary box with Dirichlet A=0
    add_segment(0, z_total, 0, z_outer_box)
    add_segment(0, z_outer_box, r_outer_box, z_outer_box, "A_zero")
    add_segment(r_outer_box, z_outer_box, r_outer_box, -z_outer_box, "A_zero")
    add_segment(r_outer_box, -z_outer_box, 0, -z_outer_box, "A_zero")
    add_segment(0, -z_outer_box, 0, -z_total)

    blocks = [
        (round(r_post / 2.0, 2), round(z_window / 2.0, 2), "Ferrite_N87", "<None>", 0),
        (round(r_post / 2.0, 2), 0.0, "Air", "<None>", 0),
        (round(r_post / 2.0, 2), round(-z_window / 2.0, 2), "Ferrite_N87", "<None>", 0),
        (round((r_shell_in + r_post) / 2.0, 2), round((z_window + z_total) / 2.0, 2), "Ferrite_N87", "<None>", 0),
        (round((r_shell_in + r_post) / 2.0, 2), round(-(z_window + z_total) / 2.0, 2), "Ferrite_N87", "<None>", 0),
        (round((r_shell_in + r_shell_out) / 2.0, 2), 0.0, "Ferrite_N87", "<None>", 0),
        (round((r_pri_in + r_pri_out) / 2.0, 2), 0.0, "Copper", "Primary", primary_turns),
        (round((r_sec_in + r_sec_out) / 2.0, 2), 0.0, "Copper", "Secondary", secondary_turns),
        (round((r_pri_out + r_sec_in) / 2.0, 2), 0.0, "Air", "<None>", 0),
        (round(r_outer_box * 0.7, 2), round(z_outer_box * 0.7, 2), "Air", "<None>", 0),
    ]

    lines = [
        "-- FEMM 4.2 Headless Magnetic Simulation Script",
        "-- Generated by Mendex Engineering Studio v2.0 (Closed Core FEA)",
        "newdocument(0)",
        f'mi_probdef({frequency_hz}, "millimeters", "axi", 1e-8, 0, 30)',
        "",
        "-- Materials",
        'mi_addmaterial("Air", 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0)',
        'mi_addmaterial("Ferrite_N87", 2200, 2200, 0, 0, 0, 0, 0, 1, 0, 0, 0)',
        'mi_addmaterial("Copper", 1, 1, 0, 0, 58, 0, 0, 1, 0, 0, 0)',
        "",
        "-- Circuits",
        f'mi_addcircprop("Primary", {primary_current_a}, 1)',
        'mi_addcircprop("Secondary", 0.0, 1)',
        "",
        "-- Boundary Condition A=0",
        'mi_addboundprop("A_zero", 0, 0, 0, 0, 0, 0, 0, 0, 0)',
        "",
        "-- Nodes",
    ]

    for r, z in node_list:
        lines.append(f"mi_addnode({r}, {z})")

    lines.append("\n-- Segments")
    for r1, z1, r2, z2, bdry in segment_list:
        lines.append(f"mi_addsegment({r1}, {z1}, {r2}, {z2})")
        if bdry and bdry != "<None>":
            mid_r = (r1 + r2) / 2.0
            mid_z = (z1 + z2) / 2.0
            lines.append(f"mi_selectsegment({mid_r}, {mid_z})")
            lines.append(f'mi_setsegmentprop("{bdry}", 1, 1, 0, 0, "<None>")')
            lines.append("mi_clearselected()")

    lines.append("\n-- Block Labels")
    for r, z, mat, circ, turns in blocks:
        lines.append(f"mi_addblocklabel({r}, {z})")
        lines.append(f"mi_selectlabel({r}, {z})")
        lines.append(f'mi_setblockprop("{mat}", 1, 0, "{circ}", 0, 0, {turns})')
        lines.append("mi_clearselected()")

    r_sample = round(r_post / 2.0, 2)
    lines.extend([
        "",
        "-- Solve and Analyze",
        f'mi_saveas("{fem_name}")',
        "mi_analyze(1)",
        "mi_loadsolution()",
        "",
        "-- Sample peak flux density across center leg",
        "b_max = 0",
        f"for z_s = {g_half + 1.0}, {z_window - 1.0}, 2.0 do",
        f"    vals = mo_getpointvalues({r_sample}, z_s)",
        f"    if type(vals) == 'table' then b1 = vals[2]; b2 = vals[3] else a, b1, b2 = mo_getpointvalues({r_sample}, z_s) end",
        "    b_mag = sqrt(b1^2 + b2^2)",
        "    if b_mag > b_max then b_max = b_mag end",
        "end",
        "",
        "-- Extract circuit properties & metrics to text file",
        'i_pri, v_pri, flx_pri = mo_getcircuitproperties("Primary")',
        'i_sec, v_sec, flx_sec = mo_getcircuitproperties("Secondary")',
        f'res_fp = openfile("{safe_res}", "w")',
        'write(res_fp, "primary_current=" .. tostring(i_pri) .. "\\n")',
        'write(res_fp, "primary_flux_linkage=" .. tostring(flx_pri) .. "\\n")',
        "if i_pri ~= 0 then",
        "    ind_pri = flx_pri / i_pri",
        '    write(res_fp, "primary_inductance_h=" .. tostring(ind_pri) .. "\\n")',
        "end",
        'write(res_fp, "secondary_flux_linkage=" .. tostring(flx_sec) .. "\\n")',
        'write(res_fp, "peak_b_pk_tesla=" .. tostring(b_max) .. "\\n")',
        'write(res_fp, "saturation_margin_pct=" .. tostring(((0.39 - b_max) / 0.39) * 100) .. "\\n")',
        "closefile(res_fp)",
        "",
        "quit()",
    ])

    return "\n".join(lines)


def generate_femm_inductor_script(
    core_type: str = "Toroid",
    turns: int = 15,
    current_a: float = 1.0,
    air_gap_mm: float = 0.2,
    frequency_hz: float = 100000.0,
    results_txt_path: str = "results.txt",
) -> str:
    """Generates an automated FEMM 4.2 Lua script for discrete power inductors (e.g. buck L1).

    Solves 2D axisymmetric magnetic field with explicit winding excitation and A=0 boundary.
    """
    safe_res = str(results_txt_path).replace("\\", "/")
    return f"""-- FEMM 4.2 Inductor Magnetic FEA Script
-- Generated by Mendex Engineering Studio v2.0
newdocument(0)
mi_probdef({frequency_hz}, "millimeters", "axi", 1e-8, 0, 30)

-- Core and Winding Materials
mi_addmaterial("Air", 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0)
mi_addmaterial("Ferrite_N87", 2200, 2200, 0, 0, 0, 0, 0, 1, 0, 0, 0)
mi_addmaterial("Copper", 1, 1, 0, 0, 58, 0, 0, 1, 0, 0, 0)

-- Circuit Excitation: {turns} turns @ {current_a} A
mi_addcircprop("Winding", {current_a}, 1)

-- Core Column (r=0..10mm, z=0..20mm)
mi_drawrectangle(0, 0, 10, 20)
mi_addblocklabel(5, 10)
mi_selectlabel(5, 10)
mi_setblockprop("Ferrite_N87", 1, 0, "<None>", 0, 0, 0)
mi_clearselected()

-- Winding Window (r=12..16mm, z=3..17mm)
mi_drawrectangle(12, 3, 16, 17)
mi_addblocklabel(14, 10)
mi_selectlabel(14, 10)
mi_setblockprop("Copper", 1, 0, "Winding", 0, 0, {turns})
mi_clearselected()

-- Outer Air Boundary with A=0 Dirichlet Condition (r=0..40mm, z=0..40mm)
mi_drawrectangle(0, 0, 40, 40)
mi_addblocklabel(25, 25)
mi_selectlabel(25, 25)
mi_setblockprop("Air", 1, 0, "<None>", 0, 0, 0)
mi_clearselected()

mi_addboundprop("A_zero", 0, 0, 0, 0, 0, 0, 0, 0, 0)
mi_selectsegment(40, 20)
mi_setsegmentprop("A_zero", 1, 1, 0, 0, "<None>")
mi_clearselected()
mi_selectsegment(20, 40)
mi_setsegmentprop("A_zero", 1, 1, 0, 0, "<None>")
mi_clearselected()

-- Solve and Analyze
mi_saveas("temp_inductor.fem")
mi_analyze(1)
mi_loadsolution()

-- Sample peak flux density along the core center
b_max = 0
for z_sample = 3, 17, 2 do
    vals = mo_getpointvalues(3, z_sample)
    if type(vals) == "table" then
        b1 = vals[2]
        b2 = vals[3]
    else
        a, b1, b2 = mo_getpointvalues(3, z_sample)
    end
    b_mag = sqrt(b1^2 + b2^2)
    if b_mag > b_max then
        b_max = b_mag
    end
end

i_w, v_w, flx_w = mo_getcircuitproperties("Winding")
res_fp = openfile("{safe_res}", "w")
write(res_fp, "winding_current=" .. tostring(i_w) .. "\\n")
write(res_fp, "winding_flux_linkage=" .. tostring(flx_w) .. "\\n")
if i_w ~= 0 then
    ind_w = flx_w / i_w
    write(res_fp, "inductance_h=" .. tostring(ind_w) .. "\\n")
end
write(res_fp, "peak_b_pk_tesla=" .. tostring(b_max) .. "\\n")
write(res_fp, "saturation_margin_pct=" .. tostring(((0.49 - b_max) / 0.49) * 100) .. "\\n")
closefile(res_fp)

quit()
"""
