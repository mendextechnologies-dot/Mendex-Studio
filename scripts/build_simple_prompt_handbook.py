"""Build a simple, clean, copy-paste Prompt Playbook Word Document (.docx) for developers."""
import os
import shutil
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

DOCX_OUT_PATH = r"docs\Mendex_Developer_Prompt_Handbook.docx"
ARTIFACT_DIR = r"C:\Users\Sagar\.gemini\antigravity\brain\0a1dae9f-d647-4c88-987e-ccfaaa950d01"

NAVY_BLUE = RGBColor(0x1E, 0x3A, 0x8A)
ROYAL_BLUE = RGBColor(0x25, 0x63, 0xEB)
TEXT_DARK = RGBColor(0x1E, 0x29, 0x3B)
TEXT_MUTED = RGBColor(0x47, 0x55, 0x69)
GREEN_DARK = RGBColor(0x05, 0x96, 0x69)


def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=120, bottom=120, left=180, right=180):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>'
    )
    tcPr.append(tcMar)


def add_prompt_box(doc, prompt_text):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, "EFF6FF")  # Soft blue background
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)

    # Thick Royal Blue left border + subtle border around
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}><w:top w:val="single" w:sz="6" w:space="0" w:color="BFDBFE"/><w:left w:val="single" w:sz="36" w:space="0" w:color="2563EB"/><w:bottom w:val="single" w:sz="6" w:space="0" w:color="BFDBFE"/><w:right w:val="single" w:sz="6" w:space="0" w:color="BFDBFE"/></w:tcBorders>'
    )
    tcPr.append(borders)

    p_header = cell.paragraphs[0]
    p_header.paragraph_format.space_before = Pt(0)
    p_header.paragraph_format.space_after = Pt(4)
    run_hdr = p_header.add_run("📋 COPY AND PASTE THIS EXACT PROMPT INTO CODEX / CLAUDE:")
    run_hdr.font.name = "Segoe UI"
    run_hdr.font.size = Pt(9.5)
    run_hdr.font.bold = True
    run_hdr.font.color.rgb = ROYAL_BLUE

    p_content = cell.add_paragraph()
    p_content.paragraph_format.space_before = Pt(2)
    p_content.paragraph_format.space_after = Pt(0)
    p_content.paragraph_format.line_spacing = 1.15
    run_code = p_content.add_run(prompt_text.strip())
    run_code.font.name = "Consolas"
    run_code.font.size = Pt(9.0)
    run_code.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

    p_space = doc.add_paragraph()
    p_space.paragraph_format.space_before = Pt(0)
    p_space.paragraph_format.space_after = Pt(4)


def add_stage_section(doc, stage_num, stage_title, purpose, prompt_text, what_codex_does, command_center_view):
    # Stage Heading
    p_heading = doc.add_paragraph()
    p_heading.paragraph_format.space_before = Pt(16)
    p_heading.paragraph_format.space_after = Pt(2)
    p_heading.paragraph_format.keep_with_next = True
    r_num = p_heading.add_run(f"Stage {stage_num}: ")
    r_num.font.name = "Segoe UI"
    r_num.font.size = Pt(14)
    r_num.font.bold = True
    r_num.font.color.rgb = NAVY_BLUE

    r_title = p_heading.add_run(stage_title)
    r_title.font.name = "Segoe UI"
    r_title.font.size = Pt(14)
    r_title.font.bold = True
    r_title.font.color.rgb = ROYAL_BLUE

    # Purpose
    p_purpose = doc.add_paragraph()
    p_purpose.paragraph_format.space_before = Pt(0)
    p_purpose.paragraph_format.space_after = Pt(6)
    r_pur_lbl = p_purpose.add_run("Goal: ")
    r_pur_lbl.font.bold = True
    r_pur_lbl.font.color.rgb = TEXT_DARK
    r_pur_txt = p_purpose.add_run(purpose)
    r_pur_txt.font.color.rgb = TEXT_MUTED

    # Prompt Box
    add_prompt_box(doc, prompt_text)

    # Explanation bullets
    p_what = doc.add_paragraph(style='List Bullet')
    p_what.paragraph_format.space_before = Pt(0)
    p_what.paragraph_format.space_after = Pt(2)
    r_w1 = p_what.add_run("What Codex Does Automatically: ")
    r_w1.font.bold = True
    r_w1.font.color.rgb = TEXT_DARK
    p_what.add_run(what_codex_does)

    p_ui = doc.add_paragraph(style='List Bullet')
    p_ui.paragraph_format.space_before = Pt(0)
    p_ui.paragraph_format.space_after = Pt(8)
    r_u1 = p_ui.add_run("What You See on http://localhost:5173: ")
    r_u1.font.bold = True
    r_u1.font.color.rgb = GREEN_DARK
    p_ui.add_run(command_center_view)


def build_handbook():
    doc = docx.Document()

    # 1-inch margins
    for sec in doc.sections:
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)

    # Header / Title
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(4)
    run_t = p_title.add_run("MENDEX ENGINEERING STUDIO v3.1")
    run_t.font.name = "Segoe UI"
    run_t.font.size = Pt(22)
    run_t.font.bold = True
    run_t.font.color.rgb = NAVY_BLUE

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(12)
    run_s = p_sub.add_run("The 9-Stage AI Prompt Playbook for Developers\nStep-by-Step Copy-Paste Prompts for Codex, Claude Code & Antigravity")
    run_s.font.name = "Segoe UI"
    run_s.font.size = Pt(13)
    run_s.font.color.rgb = ROYAL_BLUE

    # Comparison / Explanation Table
    p_intro = doc.add_paragraph()
    p_intro.paragraph_format.space_before = Pt(0)
    p_intro.paragraph_format.space_after = Pt(6)
    p_intro.paragraph_format.line_spacing = 1.15
    run_intro = p_intro.add_run("Why Use Codex / Claude Prompts Instead of Manual PowerShell Commands?")
    run_intro.font.size = Pt(11)
    run_intro.font.bold = True
    run_intro.font.color.rgb = NAVY_BLUE

    tbl_comp = doc.add_table(rows=3, cols=2)
    tbl_comp.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell_w = Inches(3.25)
    for row in tbl_comp.rows:
        row.cells[0].width = cell_w
        row.cells[1].width = cell_w

    # Table Header
    set_cell_background(tbl_comp.cell(0, 0), "1E3A8A")
    set_cell_background(tbl_comp.cell(0, 1), "2563EB")
    set_cell_margins(tbl_comp.cell(0, 0), top=100, bottom=100, left=140, right=140)
    set_cell_margins(tbl_comp.cell(0, 1), top=100, bottom=100, left=140, right=140)

    p0 = tbl_comp.cell(0, 0).paragraphs[0]
    r0 = p0.add_run("Manual CLI / PowerShell")
    r0.font.bold = True
    r0.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    p1 = tbl_comp.cell(0, 1).paragraphs[0]
    r1 = p1.add_run("Codex / Claude Code (Recommended)")
    r1.font.bold = True
    r1.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Row 1
    set_cell_background(tbl_comp.cell(1, 0), "F8FAFC")
    set_cell_background(tbl_comp.cell(1, 1), "EFF6FF")
    set_cell_margins(tbl_comp.cell(1, 0), top=80, bottom=80, left=120, right=120)
    set_cell_margins(tbl_comp.cell(1, 1), top=80, bottom=80, left=120, right=120)
    tbl_comp.cell(1, 0).paragraphs[0].add_run("You have to manually construct shell commands, pass JSON strings by hand, write netlists manually, and memorize tool flags.")
    tbl_comp.cell(1, 1).paragraphs[0].add_run("You paste ONE natural engineering prompt. The AI understands the electrical physics, creates files, and runs tools autonomously.")

    # Row 2
    set_cell_background(tbl_comp.cell(2, 0), "FFFFFF")
    set_cell_background(tbl_comp.cell(2, 1), "F0FDF4")
    set_cell_margins(tbl_comp.cell(2, 0), top=80, bottom=80, left=120, right=120)
    set_cell_margins(tbl_comp.cell(2, 1), top=80, bottom=80, left=120, right=120)
    tbl_comp.cell(2, 0).paragraphs[0].add_run("Slower, prone to typing errors, requires switching between 5 different tool manuals.")
    tbl_comp.cell(2, 1).paragraphs[0].add_run("10x faster. The AI handles the complete end-to-end workflow while you monitor real-time progress on http://localhost:5173.")

    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(6)
    p_sp.paragraph_format.space_after = Pt(6)

    # =========================================================================
    # THE 9 STAGES
    # =========================================================================

    # STAGE 1
    add_stage_section(
        doc,
        stage_num="1",
        stage_title="Project Initialization",
        purpose="Create the product in SQLite, generate revision R001, create the workspace, and enroll into the 9-stage engineering lifecycle.",
        prompt_text="""Start a new engineering project using the Mendex engineering lifecycle.

Product Name: SpectraVolt SV-1000
Product Code: SV-1000
Category: dc_dc_converter
Owner: Lead Power Electronics Engineer
Description: High-Voltage Isolated DC-DC Converter (24V to 1000V 100W)

Please execute Stage 1: Project Initialization using Mendex Core:
1. Call create_project to create the product record and initial revision R001.
2. Enroll the project into the canonical 9-stage engineering lifecycle.
3. Transition Stage 1 (project_initialization) to COMPLETED.
4. Report back the generated project_id and revision_id.""",
        what_codex_does="Calls `create_project` via MCP, registers product UUID, creates directory `products/<id>/revisions/<id>/`, and enrolls the 9 canonical stages.",
        command_center_view="Dashboard updates immediately: 'Authoritative Projects' becomes 1, and SV-1000 appears with a DRAFT badge and live R001 link.",
    )

    # STAGE 2
    add_stage_section(
        doc,
        stage_num="2",
        stage_title="Requirements & Electrical Specifications",
        purpose="Record the exact physical voltage, current, power, and isolation constraints. Mendex Core computes an immutable SHA-256 digest to lock the baseline.",
        prompt_text="""Continue with project SV-1000. Execute Stage 2: Requirements and Specifications.

Electrical Specification Envelope:
- Input Voltage Range: 20V to 28V DC (24V nominal)
- Output Voltage: 1000V DC regulated (±1.0% tolerance)
- Output Current: 0.1A (100W nominal output power)
- Switching Frequency: 100 kHz
- Isolation Voltage: 3000V RMS (IEC-61010-1 standard)
- Target Efficiency: ≥ 90%
- Operating Temperature: -20°C to +55°C

Actions:
1. Save this specification to the active revision using save_project_specification.
2. Record the requirements snapshot with SHA-256 digest using record_requirements.
3. Complete Stage 2 (requirements) in the lifecycle.""",
        what_codex_does="Validates SI schema units, saves typed specification to SQLite, generates SHA-256 input hash, and advances lifecycle to Stage 2 COMPLETED.",
        command_center_view="Open project detail on http://localhost:5173: the 'Specifications' tab displays all voltage, current, and power limits; Stage 2 shows COMPLETED.",
    )

    # STAGE 3
    add_stage_section(
        doc,
        stage_num="3",
        stage_title="Feasibility & Topology Selection",
        purpose="Calculate switch electrical stresses, evaluate isolated converter topologies, and select optimal semiconductor technology (SiC vs Si).",
        prompt_text="""Continue with project SV-1000. Execute Stage 3: Feasibility and Architecture Selection.

Please evaluate topology options and electrical switch stresses:
1. Evaluate High-Voltage Isolated Flyback vs Push-Pull vs LLC Resonant topologies.
2. Calculate peak primary switch voltage stress (Vin,max + (Vout+Vf)/n + Vspike).
3. Calculate secondary rectifier diode peak reverse voltage stress.
4. Recommend primary switch technology (SiC MOSFET rating) and secondary diode (SiC Schottky rating).
5. Document the feasibility findings in a feasibility report and complete Stage 3.""",
        what_codex_does="Calculates Vds,pk ≈ 211V for primary switch and Vrr ≈ 1840V for secondary diode, selects 1200V SiC MOSFET and 2000V SiC diode, and records feasibility evidence.",
        command_center_view="Lifecycle timeline advances to Stage 3 COMPLETED. Feasibility trade-off notes appear in project records.",
    )

    # STAGE 4
    add_stage_section(
        doc,
        stage_num="4",
        stage_title="Deterministic Engineering Calculations",
        purpose="Execute mathematical sizing (inductance, turns ratio), Dowell high-frequency winding loss, Steinmetz core dissipation, and IEC 61010-1 isolation spacing.",
        prompt_text="""Continue with project SV-1000. Execute Stage 4: Engineering Calculations.

Execute deterministic sizing calculations using Mendex Core:
1. Run flyback transformer sizing: calculate magnetizing inductance Lp, primary peak current, and turns ratio (Ns:Np) for DCM/boundary mode at fsw = 100 kHz, Dmax = 0.45.
2. Run Dowell winding loss analysis: calculate skin depth at 100 kHz and Dowell AC factor Fr using 40-strand triple-insulated Litz wire.
3. Run Steinmetz core loss calculation: calculate volumetric core dissipation for TDK N87 ferrite at ETD34 geometry.
4. Calculate IEC 61010-1 high-voltage basic and reinforced creepage/clearance requirements (3000V RMS).
5. Record all calculation runs to the revision database and complete Stage 4.""",
        what_codex_does="Invokes `record_calculation_run` for sizing, Dowell Fr (Fr = 1.18), Steinmetz (Pcore ≈ 1.19W), and creepage (5.0 mm slot required). All math is logged deterministically.",
        command_center_view="In Project Detail, the 'Calculations' tab immediately populates with the exact sizing outputs, formulas, and KaTeX equation readouts.",
    )

    # STAGE 5
    add_stage_section(
        doc,
        stage_num="5",
        stage_title="Design Development (CAD Synthesis)",
        purpose="Synthesize production CAD files directly in the revision workspace: KiCad 10 schematic, 2-layer PCB layout with isolation slot, and FreeCAD 3D bobbin model.",
        prompt_text="""Continue with project SV-1000. Execute Stage 5: Design Development.

Synthesize native CAD design files in the revision workspace:
1. KiCad Schematic: Create sv1000.kicad_sch including the primary SiC MOSFET (1200V), ETD34 transformer, secondary HV SiC rectifier, and isolated feedback loop.
2. KiCad PCB: Create sv1000.kicad_pcb as a 2-layer PCB layout with a physical 5.0 mm isolation milling cutout on Edge.Cuts separating primary from secondary circuits.
3. FreeCAD 3D Model: Generate a parametric 3D bobbin STEP model (etd34_bobbin.step).
4. Register all generated artifacts with register_engineering_artifact and complete Stage 5.""",
        what_codex_does="Generates `.kicad_sch`, `.kicad_pcb`, and `.step` files inside the revision directory, and registers them into the core artifact inventory.",
        command_center_view="Under 'Designs' and 'Files' tabs, all 3 CAD files appear with file sizes and 1-click 'Open in native application' buttons.",
    )

    # STAGE 6
    add_stage_section(
        doc,
        stage_num="6",
        stage_title="Physical Simulation & Solver Execution",
        purpose="Launch headless LTspice transient electrical simulation and FEMM 4.2 2D magnetostatic finite element analysis on the host.",
        prompt_text="""Continue with project SV-1000. Execute Stage 6: Simulation and Analysis.

Launch real local headless solvers via Mendex Core:
1. LTspice Simulation: Synthesize netlist simulations/flyback_circuit.net with 45% PWM gate drive, run a 2ms transient simulation, and verify output reaches 1000V with <1% ripple.
2. FEMM 4.2 FEA Magnetics: Run 2D magnetic finite element simulation on the ETD34 core and air gap, verifying peak flux density Bpk < 0.35T (below saturation).
3. Ingest simulation logs, results, and raw waveform data into Mendex Core and complete Stage 6.""",
        what_codex_does="Invokes `run_simulation` with `ltspice` and `femm`. Executes host binaries headlessly, produces `flyback_circuit.raw`, and checks 1000V regulation and Bpk < 0.35T.",
        command_center_view="The 'Simulation Center' page shows 2 SUCCEEDED jobs with exit code 0. In Project Detail, the 'Simulations' tab shows waveform results.",
    )

    # STAGE 7
    add_stage_section(
        doc,
        stage_num="7",
        stage_title="Automated Verification & Derating",
        purpose="Run automated KiCad ERC (electrical rules), PCB DRC (design rules/creepage), and IPC-9592B component stress derating audits.",
        prompt_text="""Continue with project SV-1000. Execute Stage 7: Design Verification.

Run automated rules checks and reliability audits:
1. Run headless KiCad ERC on the schematic (verify 0 errors).
2. Run headless KiCad DRC on the PCB layout (verify 0 clearance violations).
3. Perform IPC-9592B component electrical and thermal stress derating audits on the MOSFET (Vds), secondary diode (Vrr), and filter capacitor (Vdc).
4. Record all validation evidence in Mendex Core and complete Stage 7.""",
        what_codex_does="Runs `kicad-cli sch erc` and `kicad-cli pcb drc`, computes IPC-9592B stress margins (MOSFET at 17.6%, diode at 92%, cap at 66.7%), and logs evidence.",
        command_center_view="The 'Validation' tab displays a 100% green compliance summary showing 0 ERC errors, 0 DRC errors, and IPC-9592B safety passes.",
    )

    # STAGE 8
    add_stage_section(
        doc,
        stage_num="8",
        stage_title="Physical Prototype Testing Evidence",
        purpose="Ingest laboratory bench qualification measurements (oscilloscope waveforms, 3000V RMS hi-pot records, and thermal imaging) into the immutable evidence registry.",
        prompt_text="""Continue with project SV-1000. Execute Stage 8: Prototype Testing.

Attach laboratory bench qualification records to the revision evidence log:
1. Ingest 3000V RMS dielectric hi-pot insulation test certificate (leakage current < 10 µA).
2. Ingest oscilloscope switching waveform captures (drain-source voltage transients).
3. Ingest radiometric thermal imaging records confirming maximum hotspot temperature < 85°C at full 100W load.
4. Record validation evidence with cryptographic SHA-256 digests and complete Stage 8.""",
        what_codex_does="Ingests laboratory certificates and CSVs, hashes them via SHA-256, binds them to revision R001, and advances lifecycle to Stage 8 COMPLETED.",
        command_center_view="In Project Detail, the 'Validation' tab lists the formal test certificates and dielectric test proofs with SHA-256 verification badges.",
    )

    # STAGE 9
    add_stage_section(
        doc,
        stage_num="9",
        stage_title="Production Documentation & Release Dossier",
        purpose="Compile the qualified Bill of Materials with manufacturer part numbers and generate the formal print-ready Engineering Dossier.",
        prompt_text="""Continue with project SV-1000. Execute Stage 9: Documentation and Release.

Finalize production manufacturing documentation:
1. Compile the qualified Bill of Materials (bom.csv) with real manufacturer part numbers, packages, and distributor pricing.
2. Generate the formal print-ready Engineering Dossier (report.html) using generate_engineering_report.
3. Request final engineering gate review and report the completed qualification summary.""",
        what_codex_does="Creates production `bom.csv` (Wolfspeed SiC MOSFET, TDK transformer, etc.), invokes `generate_engineering_report`, and generates the dossier.",
        command_center_view="The 'Reports' tab shows the final Engineering Dossier. Clicking 'Open report' opens the high-impact executive report in your browser.",
    )

    # Save to disk
    doc.save(DOCX_OUT_PATH)
    print(f"Generated: {DOCX_OUT_PATH}")

    # Copy to Artifact directory
    if os.path.isdir(ARTIFACT_DIR):
        artifact_dest = os.path.join(ARTIFACT_DIR, "Mendex_Developer_Prompt_Handbook.docx")
        shutil.copy2(DOCX_OUT_PATH, artifact_dest)
        print(f"Copied to Artifacts: {artifact_dest}")


if __name__ == "__main__":
    build_handbook()
