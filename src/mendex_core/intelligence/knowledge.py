"""Mendex Engineering Intelligence — Knowledge Service.

Provides versioned, provenance-tracked technical references, verified mathematical formulas,
material datasets, and engineering standard metadata.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class FormulaRecord(BaseModel):
    formula_id: str
    name: str
    category: str
    latex: str
    description: str
    inputs: Dict[str, str]  # symbol -> description with SI unit
    output: Dict[str, str]  # symbol -> description with SI unit
    reference_source: str
    provenance: str
    accuracy_tolerance: float = 0.05  # 5% typical analytical tolerance


class MaterialRecord(BaseModel):
    material_id: str
    name: str
    material_type: str  # "ferrite", "iron_powder", "sic", "gan", "copper"
    properties: Dict[str, float]
    units: Dict[str, str]
    manufacturer_or_source: str
    notes: str = ""


class StandardProfile(BaseModel):
    standard_id: str
    title: str
    organization: str  # "IEC", "IEEE", "UL", "IPC"
    scope: str
    rules: Dict[str, str]
    reference_link: str = ""


class EngineeringKnowledgeService:
    """Canonical repository for engineering equations, materials, and standards."""

    def __init__(self):
        self._formulas: Dict[str, FormulaRecord] = {}
        self._materials: Dict[str, MaterialRecord] = {}
        self._standards: Dict[str, StandardProfile] = {}
        self._initialize_knowledge_base()

    def _initialize_knowledge_base(self):
        # 1. Verified Analytical Formulas
        self.register_formula(FormulaRecord(
            formula_id="EQ-DOWELL-01",
            name="Dowell AC Winding Loss Factor",
            category="magnetics",
            latex=r"F_R = \xi \left[ \frac{\sinh(2\xi) + \sin(2\xi)}{\cosh(2\xi) - \cos(2\xi)} + \frac{2(m^2 - 1)}{3} \frac{\sinh(\xi) - \sin(\xi)}{\cosh(\xi) + \cos(\xi)} \right]",
            description="Evaluates high-frequency AC copper resistance increase due to skin and proximity effects in multi-layer windings.",
            inputs={"h": "Conductor thickness (m)", "delta": "Skin depth (m)", "m": "Number of layers per portion"},
            output={"F_R": "AC-to-DC resistance ratio (dimensionless)"},
            reference_source="P. L. Dowell, 'Effects of eddy currents in transformer windings', Proc. IEE, 1966.",
            provenance="Verified analytical closed-form equation; verified in src/integrations/calculations/dowell.py",
        ))

        self.register_formula(FormulaRecord(
            formula_id="EQ-SKIN-01",
            name="Conductor Skin Depth",
            category="electromagnetics",
            latex=r"\delta = \sqrt{\frac{\rho}{\pi \cdot f \cdot \mu_0 \cdot \mu_r}}",
            description="Skin depth of electromagnetic fields penetrating a conductive medium.",
            inputs={"rho": "Resistivity (Ohm*m)", "f": "Frequency (Hz)", "mu_r": "Relative permeability (dimensionless)"},
            output={"delta": "Skin depth (m)"},
            reference_source="Classical Electrodynamics, J.D. Jackson",
            provenance="Fundamental physics formulation.",
        ))

        self.register_formula(FormulaRecord(
            formula_id="EQ-FLYBACK-LP",
            name="CCM Flyback Primary Inductance",
            category="power_electronics",
            latex=r"L_p = \frac{V_{in,min}^2 \cdot D_{max}^2}{2 \cdot P_{out} \cdot f_{sw} \cdot K_{RF}}",
            description="Calculates minimum primary magnetizing inductance to sustain continuous conduction mode (CCM).",
            inputs={"Vin_min": "Minimum input voltage (V)", "D_max": "Maximum duty ratio", "P_out": "Output power (W)", "f_sw": "Switching frequency (Hz)", "K_RF": "Ripple factor (dimensionless)"},
            output={"L_p": "Primary inductance (H)"},
            reference_source="Fundamentals of Power Electronics, R.W. Erickson",
            provenance="Verified converter topology sizing.",
        ))

        self.register_formula(FormulaRecord(
            formula_id="EQ-STEINMETZ-01",
            name="Modified Steinmetz Volumetric Core Loss",
            category="magnetics",
            latex=r"P_v = C_m \cdot f^\alpha \cdot B_{max}^\beta",
            description="Calculates volumetric power loss density in soft magnetic cores under sinusoidal excitation.",
            inputs={"f": "Frequency (Hz)", "B_max": "Peak AC flux density (T)", "C_m": "Steinmetz coefficient", "alpha": "Frequency exponent", "beta": "Flux density exponent"},
            output={"P_v": "Volumetric loss density (W/m^3)"},
            reference_source="Charles Proteus Steinmetz (1892), validated against Princeton MagNet dataset.",
            provenance="Empirical fitting model parameterization.",
        ))

        self.register_formula(FormulaRecord(
            formula_id="EQ-RESONANT-LC",
            name="LC Series/Parallel Resonance Frequency",
            category="circuit_theory",
            latex=r"f_0 = \frac{1}{2\pi \sqrt{L \cdot C}}",
            description="Calculates natural resonant undamped angular frequency for LC circuits.",
            inputs={"L": "Inductance (H)", "C": "Capacitance (F)"},
            output={"f_0": "Resonant frequency (Hz)"},
            reference_source="Linear Circuit Analysis",
            provenance="Standard mathematical definition.",
        ))

        # 2. Material Datasets
        self.register_material(MaterialRecord(
            material_id="MAT-FERRITE-N87",
            name="Epcos / TDK N87 Ferrite",
            material_type="ferrite",
            properties={
                "initial_permeability": 2200.0,
                "saturation_flux_density_25C": 0.49,  # T
                "saturation_flux_density_100C": 0.39, # T
                "curie_temperature_C": 210.0,
                "resistivity_ohm_m": 10.0,
                "steinmetz_cm": 16.7,
                "steinmetz_alpha": 1.35,
                "steinmetz_beta": 2.40,
            },
            units={
                "initial_permeability": "dimensionless",
                "saturation_flux_density_25C": "T",
                "saturation_flux_density_100C": "T",
                "curie_temperature_C": "deg_C",
                "resistivity_ohm_m": "Ohm*m",
            },
            manufacturer_or_source="TDK Electronics Material Data Sheet 2024",
            notes="Standard power ferrite for switched-mode power supplies up to 500 kHz.",
        ))

        self.register_material(MaterialRecord(
            material_id="MAT-SIC-C3M0065090D",
            name="Wolfspeed C3M0065090D SiC MOSFET",
            material_type="sic",
            properties={
                "v_ds_rated": 900.0,
                "i_d_cont_25C": 36.0,
                "r_ds_on_25C": 0.065,   # Ohm
                "r_ds_on_150C": 0.110,  # Ohm
                "q_g_total": 45e-9,      # C
                "e_on_600V_20A": 142e-6, # J
                "e_off_600V_20A": 68e-6, # J
            },
            units={
                "v_ds_rated": "V",
                "i_d_cont_25C": "A",
                "r_ds_on_25C": "Ohm",
                "r_ds_on_150C": "Ohm",
                "q_g_total": "C",
                "e_on_600V_20A": "J",
                "e_off_600V_20A": "J",
            },
            manufacturer_or_source="Wolfspeed C3M0065090D Rev C Datasheet",
            notes="Third-generation 900V SiC power MOSFET for high-frequency converters.",
        ))

        # 3. Standards Profiles
        self.register_standard(StandardProfile(
            standard_id="STD-IEC-62368-1",
            title="Audio/video, information and communication technology equipment - Safety requirements",
            organization="IEC",
            scope="Electrical safety, insulation coordination, electrical clearance and creepage distances.",
            rules={
                "reinforced_insulation_230V_pollution_2": "Clearance >= 3.0 mm, Creepage >= 5.0 mm (Material Group IIIa)",
                "basic_insulation_230V_pollution_2": "Clearance >= 1.5 mm, Creepage >= 2.5 mm",
                "touch_current_limit_es1": "<= 0.5 mA RMS or 2.0 mA DC",
            },
            reference_link="https://webstore.iec.ch/publication/67584",
        ))

        self.register_standard(StandardProfile(
            standard_id="STD-IPC-2221B",
            title="Generic Standard on Printed Board Design",
            organization="IPC",
            scope="Conductor spacing, current carrying capacity, track heating limits.",
            rules={
                "bare_conductor_external_0_50V": "Minimum clearance 0.13 mm",
                "bare_conductor_external_51_100V": "Minimum clearance 0.25 mm",
                "bare_conductor_external_101_300V": "Minimum clearance 0.40 mm",
                "bare_conductor_external_301_500V": "Minimum clearance 0.75 mm",
            },
            reference_link="https://www.ipc.org/ipc-2221b",
        ))

    def register_formula(self, formula: FormulaRecord):
        self._formulas[formula.formula_id] = formula

    def get_formula(self, formula_id: str) -> Optional[FormulaRecord]:
        return self._formulas.get(formula_id)

    def list_formulas(self, category: Optional[str] = None) -> List[FormulaRecord]:
        if category:
            return [f for f in self._formulas.values() if f.category == category]
        return list(self._formulas.values())

    def register_material(self, material: MaterialRecord):
        self._materials[material.material_id] = material

    def get_material(self, material_id: str) -> Optional[MaterialRecord]:
        return self._materials.get(material_id)

    def list_materials(self, material_type: Optional[str] = None) -> List[MaterialRecord]:
        if material_type:
            return [m for m in self._materials.values() if m.material_type == material_type]
        return list(self._materials.values())

    def register_standard(self, standard: StandardProfile):
        self._standards[standard.standard_id] = standard

    def get_standard(self, standard_id: str) -> Optional[StandardProfile]:
        return self._standards.get(standard_id)

    def list_standards(self) -> List[StandardProfile]:
        return list(self._standards.values())
