"""Input contracts and implementation provenance; formulas remain in the existing core."""
from pathlib import Path
from typing import Annotated

from pydantic import Field

from ..engineering_lifecycle.storage import file_hash
from ..models import Model

Positive = Annotated[float, Field(gt=0, strict=True)]
Nonnegative = Annotated[float, Field(ge=0, strict=True)]


class DowellInputs(Model):
    frequency_hz: Positive
    layers: int = Field(ge=1, le=1000, strict=True)
    conductor_diameter_mm: Positive
    layer_porosity_factor: float = Field(ge=0.1, le=1, strict=True)
    r_dc_ohm: Nonnegative
    temperature_c: float = Field(ge=-40, le=250, strict=True)


class LossInputs(Model):
    part_number: str = Field(min_length=1, max_length=200)
    r_ds_on_ohm: Nonnegative
    i_rms_a: Nonnegative
    duty_cycle: float = Field(ge=0, le=1, strict=True)
    e_on_j: Nonnegative
    e_off_j: Nonnegative
    frequency_hz: Positive


class SteinmetzInputs(Model):
    material: str = Field(min_length=1, max_length=200)
    k: Positive
    alpha: Positive
    beta: Positive
    frequency_hz: Positive
    b_peak_t: Positive
    core_volume_m3: Positive
    convention: str = Field(default="empirical_khz", pattern=r"^(empirical_khz|si_hz)$")


class FlybackInputs(Model):
    vin_min_v: Positive
    vin_nom_v: Positive
    vout_v: Positive
    iout_a: Positive
    frequency_hz: Positive
    d_max: float = Field(gt=0, lt=0.8, strict=True)
    efficiency: float = Field(gt=0, le=1, strict=True)
    b_max_t: Positive
    core_ae_mm2: Positive
    v_diode_drop_v: Nonnegative


class SemiconductorThermalInputs(Model):
    part_number: str = Field(default="UNSPECIFIED", min_length=1, max_length=200)
    p_loss_w: Nonnegative
    t_ambient_c: float = Field(default=25.0, ge=-40, le=150, strict=True)
    t_j_max_c: Positive
    derating_factor: float = Field(default=0.80, gt=0, le=1, strict=True)
    r_th_jc_c_w: Nonnegative
    r_th_cs_c_w: Nonnegative
    r_th_sa_c_w: Nonnegative = 0.0


class MagneticThermalInputs(Model):
    component_name: str = Field(default="T1", min_length=1, max_length=200)
    p_core_w: Nonnegative
    p_winding_w: Nonnegative
    surface_area_cm2: Positive
    t_ambient_c: float = Field(default=25.0, ge=-40, le=150, strict=True)
    t_class_max_c: Positive = 130.0
    insulation_class: str = Field(default="Class B (130°C)", min_length=1, max_length=100)


class IPC2152ThermalInputs(Model):
    current_a: Positive
    target_delta_t_c: Positive = 10.0
    copper_thickness_oz: Positive = 1.0
    is_internal: bool = False
    layer_name: str = Field(default="F.Cu", min_length=1, max_length=50)


def catalog():
    from integrations.calculations import power_losses, thermal_sizing, transformer_design, winding_losses
    entries = {
        "dowell": (DowellInputs, winding_losses, "calculate_dowell_ac_resistance", "Dowell 1D analytical AC/DC resistance factor", ["Copper properties are implementation constants; 1D model limits apply."]),
        "losses": (LossInputs, power_losses, "calculate_semiconductor_losses", "I_rms^2 * R_ds * duty + (E_on + E_off) * f", ["Switching energies and resistance are caller-supplied; test-condition applicability is not independently verified."]),
        "steinmetz": (SteinmetzInputs, power_losses, "calculate_core_loss_steinmetz", "Implementation: k * (f_hz/1000)^alpha * B_t^beta * 1000", ["Coefficient conventions must match this implementation; no material dataset verification is inferred."]),
        "flyback": (FlybackInputs, transformer_design, "calculate_flyback_transformer_parameters", "Existing first-principles flyback sizing implementation", ["Existing model assumes ripple factor 0.8 and rounds turns; this is analytical sizing, not approved winding construction."]),
        "semiconductor_thermal": (SemiconductorThermalInputs, thermal_sizing, "calculate_semiconductor_thermal", "IPC-9592B / JEDEC electro-thermal junction and heatsink sizing", ["Thermal resistances Rth_jc and Rth_cs are caller/datasheet supplied; natural convection cooling."]),
        "magnetic_thermal": (MagneticThermalInputs, thermal_sizing, "calculate_magnetic_thermal", "McLyman / IEC 60076 magnetic component hotspot and surface thermal analysis", ["Surface area and loss figures are caller-supplied; 15% internal hotspot factor."]),
        "ipc2152_thermal": (IPC2152ThermalInputs, thermal_sizing, "calculate_ipc2152_trace_thermal", "IPC-2152 copper trace current capacity and temperature rise", ["Un-potted FR-4 substrate; internal layers derated by 50%."]),
    }
    return {name: {"model": model, "module": module, "function": function, "formula": formula, "warnings": warnings}
            for name, (model, module, function, formula, warnings) in entries.items()}


def capabilities():
    return [{"calculation": name, "input_schema": item["model"].model_json_schema(),
             "formula_reference": item["formula"], "implementation": item["module"].__name__ + "." + item["function"],
             "implementation_sha256": file_hash(Path(item["module"].__file__)), "warnings": item["warnings"],
             "unit_conventions": "Explicit input field suffixes; mm, mm2 and degrees C are retained where the existing API uses them. Outputs retain original unit-labelled fields."}
            for name, item in catalog().items()]
