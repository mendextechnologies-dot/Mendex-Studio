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


def catalog():
    from integrations.calculations import power_losses, transformer_design, winding_losses
    entries = {
        "dowell": (DowellInputs, winding_losses, "calculate_dowell_ac_resistance", "Dowell 1D analytical AC/DC resistance factor", ["Copper properties are implementation constants; 1D model limits apply."]),
        "losses": (LossInputs, power_losses, "calculate_semiconductor_losses", "I_rms^2 * R_ds * duty + (E_on + E_off) * f", ["Switching energies and resistance are caller-supplied; test-condition applicability is not independently verified."]),
        "steinmetz": (SteinmetzInputs, power_losses, "calculate_core_loss_steinmetz", "Implementation: k * (f_hz/1000)^alpha * B_t^beta * 1000", ["Coefficient conventions must match this implementation; no material dataset verification is inferred."]),
        "flyback": (FlybackInputs, transformer_design, "calculate_flyback_transformer_parameters", "Existing first-principles flyback sizing implementation", ["Existing model assumes ripple factor 0.8 and rounds turns; this is analytical sizing, not approved winding construction."]),
    }
    return {name: {"model": model, "module": module, "function": function, "formula": formula, "warnings": warnings}
            for name, (model, module, function, formula, warnings) in entries.items()}


def capabilities():
    return [{"calculation": name, "input_schema": item["model"].model_json_schema(),
             "formula_reference": item["formula"], "implementation": item["module"].__name__ + "." + item["function"],
             "implementation_sha256": file_hash(Path(item["module"].__file__)), "warnings": item["warnings"],
             "unit_conventions": "Explicit input field suffixes; mm, mm2 and degrees C are retained where the existing API uses them. Outputs retain original unit-labelled fields."}
            for name, item in catalog().items()]
