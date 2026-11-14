"""Authoritative Laboratory Test Plan & Staged Bring-Up Protocol Generator (Milestone Option 2 / G16, G17, G23).

Generates comprehensive physical test plans for high-voltage and power electronics prototypes:
1. Safety categorization (IEC 61010-1 / NFPA 70E / CAT III).
2. Laboratory equipment requirements & probe maps.
3. 4-phase bring-up protocol: Cold inspection, low-voltage aux/gate verification, staged HV ramp (10%->100%), and thermal soak.
4. Abort & hazard shutdown thresholds.
5. Attributable measurement sign-off scorecard for physical laboratory evidence collection.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID
from datetime import datetime, timezone

from ..service import StudioError
from ..evidence import digest


def generate_laboratory_test_plan(studio, revision_id: UUID | str) -> dict[str, Any]:
    """Generates an authoritative laboratory bring-up protocol and printable documentation."""
    rev_uuid = UUID(str(revision_id))
    rev = studio.get_revision(rev_uuid)
    product = studio.get_product(rev.product_id)
    spec = rev.specification
    ws_dir = studio.workspace_path(rev)

    vin_nom = getattr(spec, "vin_nom_v", 230.0) or 230.0
    vin_max = getattr(spec, "vin_max_v", vin_nom * 1.15) or (vin_nom * 1.15)
    vout = getattr(spec, "vout_v", 325.0) or 325.0
    iout = getattr(spec, "iout_a", 2.36) or 2.36
    fsw = getattr(spec, "switching_frequency_hz", 100000.0) or 100000.0
    pout = vout * iout
    topology = getattr(spec, "topology", "") or "High Voltage Power Converter"
    isolation = getattr(spec, "isolation_requirement", "") or "Galvanic Isolation"

    # Determine safety hazard classification
    max_voltage = max(vin_max, vout)
    is_high_voltage = max_voltage >= 60.0
    is_extreme_hv = max_voltage >= 500.0

    safety_category = "CAT III / High Voltage Hazard" if is_high_voltage else "Standard Bench (SELV)"
    if is_extreme_hv:
        safety_category = "CAT III / Extreme High Voltage (>500V)"

    protocol_id = f"LTP-{product.code}-{rev.revision_label}"
    created_at = datetime.now(timezone.utc).isoformat()

    # Equipment requirements
    equipment = [
        {
            "category": "Oscilloscope",
            "name": "4-Channel Digital Storage Oscilloscope (>= 100 MHz, >= 1 GSa/s)",
            "purpose": "Monitor switch node (Vsw), gate-source (Vgs), and output ripple simultaneously",
            "min_spec": "100 MHz bandwidth, 8-bit or higher ADC resolution, calibrated",
        },
        {
            "category": "Voltage Probes",
            "name": "1000:1 / 100:1 High-Voltage Differential Probe (>= 1500V CAT III)",
            "purpose": "Floating measurement across high-side switch or isolated output without ground-loop faults",
            "min_spec": ">= 1500V pk differential, 50 MHz bandwidth, 100:1 or 1000:1 attenuation",
        },
        {
            "category": "Current Measurement",
            "name": "Hall Effect or Rogowski AC/DC Current Probe (>= 10A pk)",
            "purpose": "Capture inductor/magnet pulse current (Isense) and check for saturation non-linearity",
            "min_spec": "DC to 20 MHz, <= 1% accuracy",
        },
        {
            "category": "Digital Multimeter",
            "name": "6.5-Digit True-RMS Digital Multimeter",
            "purpose": "Accurate DC rail, auxiliary rail, and insulation resistance measurement",
            "min_spec": "CAT II 1000V / CAT III 600V, calibrated within 12 months",
        },
        {
            "category": "Thermal Camera",
            "name": "Calibrated Infrared Thermal Imager (FLIR / Fluke)",
            "purpose": "Continuous non-contact thermal monitoring of primary switch, diodes, and magnetics",
            "min_spec": "Accuracy +-2 deg C, emissivity adjustable (set to 0.95 for PCB/epoxy)",
        },
        {
            "category": "Power Supply / Variac",
            "name": "Isolated Current-Limited Adjustable Power Source with Safety Contactor",
            "purpose": "Safe staged voltage injection with emergency trip capability",
            "min_spec": "Variable 0 to Vin_max, fast electronic current limit",
        },
    ]

    # Required Personal Protective Equipment (PPE)
    ppe_checklist = [
        "NFPA 70E / IEC 61010-1 Class 0 (1000V) electrical insulating safety gloves with leather protectors",
        "ANSI Z87.1 approved safety glasses with side shields / face shield for initial power-up",
        "High-voltage safety discharge stick with 10k ohm 50W ceramic dump resistor and ground clamp",
        "Insulating bench mat rated for >= 1000V working voltage beneath test station",
        "Dedicated emergency emergency power-off (EPO) button within arm's reach of operator",
        "Two-person laboratory rule (never perform high-voltage bring-up alone)",
    ]

    # Oscilloscope Test Points
    test_points = [
        {
            "channel": "CH1 (Yellow)",
            "signal": "Gate Drive V_GS",
            "test_point": "TP_GATE (Gate of primary switch Q1)",
            "reference": "TP_SRC (Source / Emitter of Q1)",
            "expected": f"Clean 0V to +15V square pulse, rise time tr < 150ns, no spurious ringing",
            "probe_type": "10:1 Passive Probe or Low-Voltage Differential",
        },
        {
            "channel": "CH2 (Blue)",
            "signal": "Switch Node V_SW / V_DS",
            "test_point": "TP_DRAIN (Drain / Collector of Q1)",
            "reference": "TP_GND_PRI (Primary Ground)",
            "expected": f"Peak voltage <= {vin_max * 1.3:.1f}V during turn-off (snubber clamped)",
            "probe_type": "100:1 / 1000:1 High-Voltage Differential Probe",
        },
        {
            "channel": "CH3 (Magenta)",
            "signal": "Inductive Current I_SENSE",
            "test_point": "R_SENSE / Actuator Loop",
            "reference": "Series loop / current clamp",
            "expected": f"Linear current ramp peaking at {iout:.2f}A without saturation curvature",
            "probe_type": "High-Frequency AC/DC Current Probe (100 mV/A)",
        },
        {
            "channel": "CH4 (Cyan)",
            "signal": "Output Voltage V_OUT",
            "test_point": "TP_VOUT (Output Terminal J2)",
            "reference": "TP_GND_SEC (Secondary Ground)",
            "expected": f"Nominal {vout:.1f}V DC, ripple pk-pk < {max(0.1, vout * 0.02):.2f}V",
            "probe_type": "10:1 Passive Probe (AC-coupled, 20 MHz BW limit)",
        },
    ]

    # Staged bring-up procedure (4 phases)
    phases = [
        {
            "phase_num": 1,
            "title": "Cold Inspection & Galvanic Isolation (Unpowered)",
            "steps": [
                {
                    "step": "1.1",
                    "action": "Visual & Microscope Inspection",
                    "detail": "Inspect all solder joints for bridges, cold solder, or solder balls. Confirm polarity of electrolytic capacitors (C4, C7) and orientation of diodes (D1-D4).",
                    "criteria": "Zero visible solder bridges; 100% correct component orientation.",
                },
                {
                    "step": "1.2",
                    "action": "Galvanic Isolation Barrier Hi-Pot / Megohmmeter Test",
                    "detail": "Apply 1000V DC between Primary Ground (PRI_GND) and Secondary Ground (SEC_GND) across the 5.0mm isolation barrier slot.",
                    "criteria": "Insulation resistance R_iso >= 100 M-Ohm; leakage current < 50 uA.",
                },
                {
                    "step": "1.3",
                    "action": "Power Rail Impedance Check",
                    "detail": "Measure unpowered resistance with DMM between VIN and GND, VOUT and GND, and auxiliary +15V/+5V rails to GND.",
                    "criteria": "No short circuits; impedance confirms uncharged capacitor states (> 100k Ohm).",
                },
            ],
        },
        {
            "phase_num": 2,
            "title": "Auxiliary Low-Voltage Power & Gate Drive Verification",
            "steps": [
                {
                    "step": "2.1",
                    "action": "Auxiliary Rail Power-Up",
                    "detail": "Apply auxiliary low voltage only (18VAC / 24VDC aux). Leave high-voltage main rail disconnected.",
                    "criteria": "+15V rail within 14.25V-15.75V (+-5%); +5V rail within 4.75V-5.25V (+-5%).",
                },
                {
                    "step": "2.2",
                    "action": "Timing Logic & Multivibrator Pulse Check",
                    "detail": "Apply test trigger pulse to input header (J1 / SW1). Monitor 74HC123 monostable pulse output.",
                    "criteria": "Deterministic pulse output with measured duration matching timing network +-10%.",
                },
                {
                    "step": "2.3",
                    "action": "Optocoupled Gate Driver Output Verification",
                    "detail": "Probe gate-emitter/source of primary switch Q1. Verify gate drive voltage swing and transition speeds.",
                    "criteria": "V_GS amplitude >= 14.0V on-state, <= 0.5V off-state; rise time tr < 150ns, fall time tf < 100ns.",
                },
            ],
        },
        {
            "phase_num": 3,
            "title": "Staged High-Voltage Ramp (Current-Limited)",
            "steps": [
                {
                    "step": "3.1",
                    "action": "10% Voltage Soak (SELV Verification)",
                    "detail": f"Inject {vin_nom * 0.10:.1f}V into main input with 100mA supply current limit. Trigger single pulse and observe switch node on CH2.",
                    "criteria": "Clean switching edge; no shoot-through current; supply current < 50mA quiescent.",
                },
                {
                    "step": "3.2",
                    "action": "25% Voltage Step & Snubber Damping",
                    "detail": f"Increase input to {vin_nom * 0.25:.1f}V. Measure peak turn-off overshoot and verify snubber damping ratio.",
                    "criteria": f"V_DS spike < {vin_nom * 0.25 * 1.35:.1f}V; ringing damped within 3 cycles.",
                },
                {
                    "step": "3.3",
                    "action": "50% Voltage Step & Magnetics Linearity",
                    "detail": f"Increase input to {vin_nom * 0.50:.1f}V. Monitor current ramp slope dI/dt with current probe on CH3.",
                    "criteria": "Linear current ramp without upward saturation curvature; peak flux within safe B_peak margin.",
                },
                {
                    "step": "3.4",
                    "action": "100% Full Nominal Voltage Bring-Up",
                    "detail": f"Increase input to nominal {vin_nom:.1f}V with rated current limit. Verify full output charging and regulation.",
                    "criteria": f"V_OUT reaches nominal {vout:.1f}V; peak current reaches {iout:.2f}A.",
                },
            ],
        },
        {
            "phase_num": 4,
            "title": "Full-Load Operating Verification & Thermal Settling",
            "steps": [
                {
                    "step": "4.1",
                    "action": "15-Minute Full-Power Soak",
                    "detail": f"Operate board under nominal conditions ({vin_nom:.1f}V in, {vout:.1f}V out, {iout:.2f}A load, {pout:.1f}W) continuously for 15 minutes.",
                    "criteria": "Stable operation with zero component failure or voltage drift > 2%.",
                },
                {
                    "step": "4.2",
                    "action": "Infrared Thermal Survey",
                    "detail": "Record case temperatures of primary switch Q1, catch diode/rectifier D1, and transformer/inductor with calibrated thermal camera.",
                    "criteria": "Case temperature Tc <= 95 deg C on semiconductors (<= 120 deg C junction Tj); magnetics hotspot <= 105 deg C (Class B limit).",
                },
                {
                    "step": "4.3",
                    "action": "Output Ripple & Noise Characterization",
                    "detail": "Measure output ripple with 20 MHz bandwidth limit and tip-and-barrel ground spring at full rated load.",
                    "criteria": f"V_OUT ripple pk-pk <= {max(0.1, vout * 0.02):.2f}V.",
                },
            ],
        },
    ]

    # Abort & Emergency Trip Criteria
    abort_criteria = [
        "Case temperature Tc exceeding 110 deg C on any power component",
        "Audible arcing, crackling, corona discharge, or smell of ozone / burnt epoxy",
        "Supply current exceeding 125% of expected operating draw",
        "Gate driver desaturation fault or abnormal waveform glitching (> 2V bounce on V_GS off-state)",
        "DC output voltage exceeding +15% overvoltage threshold",
    ]

    # Scorecard fields for recording authentic evidence
    scorecard_template = {
        "operator_name": "",
        "operator_signature": "",
        "test_date": "",
        "dmm_asset_id": "",
        "dmm_cal_expiry": "",
        "scope_asset_id": "",
        "scope_cal_expiry": "",
        "hi_pot_asset_id": "",
        "hi_pot_cal_expiry": "",
        "ambient_temp_c": 25.0,
        "measured_vin_v": None,
        "measured_vout_v": None,
        "measured_iout_peak_a": None,
        "measured_vgs_peak_v": None,
        "measured_vsw_peak_v": None,
        "measured_switch_tc_c": None,
        "measured_magnetic_tc_c": None,
        "isolation_resistance_mohm": None,
        "hi_pot_leakage_ua": None,
        "overall_result": "PENDING_PHYSICAL_EXECUTION",
    }

    # Generate Markdown documentation
    md_lines = [
        f"# Laboratory Test Plan & Staged Bring-Up Protocol: {product.name}",
        f"**Protocol ID:** `{protocol_id}` | **Project:** `{product.code}` | **Revision:** `{rev.revision_label}`",
        f"**Date Generated:** {created_at} | **Safety Category:** `{safety_category}`",
        "",
        "> [!IMPORTANT]",
        "> **Physical Laboratory Execution Gate (G16 / G17 / G23):**",
        "> Generating this protocol does **not** claim or imply that physical testing has occurred or that hardware is approved.",
        "> Authentic laboratory execution requires an accredited engineer, calibrated test assets, and signed measurement records.",
        "",
        "## 1. Operating Design Envelope & Nominal Ratings",
        f"- **Nominal Input Voltage:** {vin_nom:.1f} V (Range: {getattr(spec, 'vin_min_v', vin_nom*0.8):.1f} V to {vin_max:.1f} V)",
        f"- **Nominal Output Voltage:** {vout:.1f} V (Nominal Power: {pout:.1f} W at {iout:.2f} A)",
        f"- **Switching Frequency:** {fsw/1000.0:.1f} kHz",
        f"- **Topology:** {topology}",
        f"- **Galvanic Isolation:** {isolation}",
        "",
        "## 2. Laboratory PPE & Safety Precautions",
        *(f"- [ ] {item}" for item in ppe_checklist),
        "",
        "## 3. Required Calibrated Laboratory Instruments",
        "| Category | Instrument Description | Minimum Specification | Asset ID | Cal Due |",
        "| :--- | :--- | :--- | :--- | :--- |",
        *(f"| {eq['category']} | {eq['name']} | {eq['min_spec']} | [ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ] | [ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ] |" for eq in equipment),
        "",
        "## 4. Oscilloscope Probe Points & Acquisition Schedule",
        "| Channel | Signal | Physical PCB Test Point | Reference | Probe Type | Expected Waveform |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
        *(f"| **{tp['channel']}** | {tp['signal']} | `{tp['test_point']}` | `{tp['reference']}` | {tp['probe_type']} | {tp['expected']} |" for tp in test_points),
        "",
        "## 5. Staged Bring-Up Procedure",
    ]

    for phase in phases:
        md_lines.append(f"\n### Phase {phase['phase_num']}: {phase['title']}")
        for step in phase["steps"]:
            md_lines.append(f"#### Step {step['step']}: {step['action']}")
            md_lines.append(f"- **Detail:** {step['detail']}")
            md_lines.append(f"- **Acceptance Criteria:** {step['criteria']}")
            md_lines.append(f"- **Measured Result:** [ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ] &nbsp;&nbsp; **Verdict:** [ &nbsp; ] PASS &nbsp;&nbsp; [ &nbsp; ] FAIL\n")

    md_lines.extend([
        "## 6. Immediate Abort & Hazard Shutdown Limits",
        *(f"- ⛔ **ABORT TRIP:** {crit}" for crit in abort_criteria),
        "",
        "## 7. Attributable Physical Test Sign-Off Scorecard",
        "```",
        f"Test Station ID: ______________________    Calibration Expiry: ____________",
        f"Lead Test Engineer: ___________________    Attributable Signature: ________",
        f"Physical Test Date: ___________________    Overall Verdict: [ ] PASS  [ ] FAIL",
        f"Measured Vin: _____ V   Measured Vout: _____ V   Peak Isense: _____ A",
        f"Switch Max Tc: _____ deg C   Magnetic Max Tc: _____ deg C   R_iso: _____ MOhm",
        "```",
        "",
        "> [!NOTE]",
        "> Recorded test results must be ingested via `StudioService.measurements.record_measurement` with authentic raw oscilloscope CSV traces.",
    ])

    md_text = "\n".join(md_lines)

    # Generate print-ready HTML
    html_text = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{protocol_id} - Laboratory Test Plan & Bring-Up Protocol</title>
<style>
  @page {{ size: A4 portrait; margin: 15mm 12mm 15mm 12mm; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #0f172a; line-height: 1.45; font-size: 11pt; padding: 20px; }}
  h1 {{ color: #0f766e; border-bottom: 2px solid #0f766e; padding-bottom: 6px; font-size: 18pt; margin-top: 0; }}
  h2 {{ color: #0369a1; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px; font-size: 13pt; margin-top: 20px; page-break-after: avoid; }}
  h3 {{ color: #334155; font-size: 11pt; margin-top: 14px; page-break-after: avoid; }}
  .header-box {{ background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px; margin-bottom: 16px; }}
  .badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 9pt; font-weight: bold; }}
  .badge-danger {{ background: #ffe4e6; color: #be123c; border: 1px solid #f43f5e; }}
  .badge-info {{ background: #e0f2fe; color: #0369a1; border: 1px solid #38bdf8; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; margin-bottom: 14px; font-size: 9.5pt; }}
  th, td {{ border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; vertical-align: top; }}
  th {{ background: #f1f5f9; color: #334155; }}
  .step-box {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 4px; padding: 8px 12px; margin-bottom: 8px; }}
  .disclaimer {{ background: #fffbeb; border-left: 4px solid #f59e0b; padding: 10px 14px; color: #92400e; font-size: 9.5pt; margin-bottom: 16px; }}
  .scorecard {{ border: 2px solid #0f766e; border-radius: 6px; padding: 14px; background: #f0fdfa; margin-top: 20px; page-break-inside: avoid; }}
  @media print {{
    body {{ padding: 0; }}
    .no-print {{ display: none; }}
    .page-break {{ page-break-before: always; }}
  }}
</style>
</head>
<body>
<div class="no-print" style="margin-bottom: 16px;">
  <button onclick="window.print()" style="background: #0f766e; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer;">🖨️ Print / Save as PDF</button>
</div>

<div class="header-box">
  <h1>{product.name}</h1>
  <div style="display: flex; justify-content: space-between; align-items: center;">
    <div>
      <b>Protocol ID:</b> <code>{protocol_id}</code> | <b>Revision:</b> {rev.revision_label} | <b>Date:</b> {created_at[:10]}
    </div>
    <div>
      <span class="badge badge-danger">{safety_category}</span>
    </div>
  </div>
</div>

<div class="disclaimer">
  <b>Authoritative Physical Laboratory Testing Gate (G16 / G17 / G23):</b><br>
  This protocol governs physical laboratory testing. Generating this document does <b>not</b> claim or imply that physical testing has occurred or that hardware is approved for production.
</div>

<h2>1. Operating Design Envelope</h2>
<table>
  <tr><th>Parameter</th><th>Value</th><th>Parameter</th><th>Value</th></tr>
  <tr><td>Nominal Input Voltage</td><td>{vin_nom:.1f} V</td><td>Nominal Output Voltage</td><td>{vout:.1f} V</td></tr>
  <tr><td>Input Voltage Range</td><td>{getattr(spec, 'vin_min_v', vin_nom*0.8):.1f} V to {vin_max:.1f} V</td><td>Full Load Output Power</td><td>{pout:.1f} W ({iout:.2f} A)</td></tr>
  <tr><td>Switching Frequency</td><td>{fsw/1000.0:.1f} kHz</td><td>Topology</td><td>{topology}</td></tr>
  <tr><td>Galvanic Isolation</td><td>{isolation}</td><td>Safety Classification</td><td>{safety_category}</td></tr>
</table>

<h2>2. Oscilloscope Probe Points & Acquisition Schedule</h2>
<table>
  <tr><th>Channel</th><th>Signal</th><th>Test Point</th><th>Reference</th><th>Probe Type</th><th>Expected Waveform</th></tr>
  {"".join(f"<tr><td><b>{tp['channel']}</b></td><td>{tp['signal']}</td><td><code>{tp['test_point']}</code></td><td><code>{tp['reference']}</code></td><td>{tp['probe_type']}</td><td>{tp['expected']}</td></tr>" for tp in test_points)}
</table>

<div class="page-break"></div>

<h2>3. Staged Bring-Up Procedure</h2>
{"".join(f'''<h3>Phase {ph['phase_num']}: {ph['title']}</h3>''' + "".join(f'''<div class="step-box"><b>Step {st['step']}: {st['action']}</b><br><small style="color: #475569;">Detail: {st['detail']}</small><br><b>Acceptance Criteria:</b> {st['criteria']}<br><div style="margin-top: 6px; font-family: monospace;">[ ] PASS &nbsp;&nbsp; [ ] FAIL &nbsp;&nbsp;&nbsp;&nbsp; Measured: _________________________</div></div>''' for st in ph['steps']) for ph in phases)}

<h2>4. Immediate Abort & Hazard Shutdown Limits</h2>
<ul>
  {"".join(f"<li><b>ABORT TRIP:</b> {c}</li>" for c in abort_criteria)}
</ul>

<div class="scorecard">
  <h3 style="margin-top: 0; color: #0f766e;">Attributable Physical Test Sign-Off Scorecard</h3>
  <table style="border: none;">
    <tr><td><b>Test Station ID:</b> ____________________</td><td><b>Calibration Due:</b> ____________________</td></tr>
    <tr><td><b>Lead Test Engineer:</b> ____________________</td><td><b>Attributable Signature:</b> ____________________</td></tr>
    <tr><td><b>Physical Execution Date:</b> ____________________</td><td><b>Overall Verdict:</b> [ ] PASS &nbsp;&nbsp; [ ] FAIL</td></tr>
  </table>
  <div style="font-size: 9pt; color: #64748b; margin-top: 8px;">
    Raw oscilloscope CSV captures and thermal FLIR images must be cryptographically hashed and recorded into StudioService.measurements.
  </div>
</div>
</body>
</html>
"""

    # Persist files into revision workspace
    test_dir = ws_dir / "tests" / "laboratory_test_plan"
    test_dir.mkdir(parents=True, exist_ok=True)
    json_path = test_dir / "test_plan.json"
    md_path = test_dir / "test_plan.md"
    html_path = test_dir / "test_plan.html"

    plan_data = {
        "protocol_id": protocol_id,
        "product_id": str(product.product_id),
        "product_name": product.name,
        "product_code": product.code,
        "revision_id": str(rev.revision_id),
        "revision_label": rev.revision_label,
        "created_at": created_at,
        "safety_category": safety_category,
        "is_high_voltage": is_high_voltage,
        "operating_envelope": {
            "vin_nom_v": vin_nom,
            "vin_max_v": vin_max,
            "vout_v": vout,
            "iout_a": iout,
            "pout_w": pout,
            "fsw_hz": fsw,
            "topology": topology,
            "isolation": isolation,
        },
        "equipment_checklist": equipment,
        "ppe_checklist": ppe_checklist,
        "test_points": test_points,
        "phases": phases,
        "abort_criteria": abort_criteria,
        "scorecard_template": scorecard_template,
    }

    json_path.write_text(json.dumps(plan_data, indent=2), encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    html_path.write_text(html_text, encoding="utf-8")

    plan_digest = digest(json_path.read_bytes())

    return {
        "success": True,
        "protocol_id": protocol_id,
        "revision_id": str(rev.revision_id),
        "safety_category": safety_category,
        "is_high_voltage": is_high_voltage,
        "json_path": str(json_path.relative_to(ws_dir).as_posix()),
        "markdown_path": str(md_path.relative_to(ws_dir).as_posix()),
        "html_path": str(html_path.relative_to(ws_dir).as_posix()),
        "sha256": plan_digest,
        "markdown_content": md_text,
        "html_content": html_text,
        "test_plan": plan_data,
    }


def get_laboratory_test_plan(studio, revision_id: UUID | str) -> dict[str, Any]:
    """Retrieves existing test plan or generates one if not yet present."""
    rev_uuid = UUID(str(revision_id))
    rev = studio.get_revision(rev_uuid)
    ws_dir = studio.workspace_path(rev)
    test_dir = ws_dir / "tests" / "laboratory_test_plan"
    json_path = test_dir / "test_plan.json"
    md_path = test_dir / "test_plan.md"
    html_path = test_dir / "test_plan.html"

    if json_path.is_file() and md_path.is_file() and html_path.is_file():
        try:
            plan_data = json.loads(json_path.read_text(encoding="utf-8"))
            return {
                "success": True,
                "protocol_id": plan_data.get("protocol_id", f"LTP-{rev.revision_label}"),
                "revision_id": str(rev.revision_id),
                "safety_category": plan_data.get("safety_category", "Standard Bench (SELV)"),
                "is_high_voltage": plan_data.get("is_high_voltage", False),
                "json_path": str(json_path.relative_to(ws_dir).as_posix()),
                "markdown_path": str(md_path.relative_to(ws_dir).as_posix()),
                "html_path": str(html_path.relative_to(ws_dir).as_posix()),
                "sha256": digest(json_path.read_bytes()),
                "markdown_content": md_path.read_text(encoding="utf-8"),
                "html_content": html_path.read_text(encoding="utf-8"),
                "test_plan": plan_data,
            }
        except Exception:
            pass

    return generate_laboratory_test_plan(studio, revision_id)

