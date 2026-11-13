"""Component and Material Library Service for Mendex Studio."""
from __future__ import annotations

from typing import Dict, List, Optional
from .models import ComponentRecord, MaterialRecord, MagneticCoreRecord


class ComponentLibraryService:
    """Provides querying and retrieval of verified engineering components and materials."""

    def __init__(self):
        self._components: Dict[str, ComponentRecord] = {}
        self._materials: Dict[str, MaterialRecord] = {}
        self._cores: Dict[str, MagneticCoreRecord] = {}
        self._seed_default_library()

    def _seed_default_library(self) -> None:
        """Seeds standard, verified power electronics devices and magnetic materials."""
        # MOSFETs
        c1 = ComponentRecord(
            mpn="BSC026N08NS5",
            manufacturer="Infineon",
            category="mosfet",
            description="80V 100A 2.6mOhm N-Channel OptiMOS 5 Power Transistor",
            package="TDSON-8",
            voltage_rating_v=80.0,
            current_rating_a=100.0,
            rds_on_ohm=0.0026,
            kicad_footprint="Package_SO:TDSON-8-1",
            kicad_symbol="Device:Q_NMOS_DGS",
            spice_model_name="BSC026N08NS5",
        )
        c2 = ComponentRecord(
            mpn="C3M0065090D",
            manufacturer="Wolfspeed",
            category="mosfet",
            description="900V 36A 65mOhm Silicon Carbide (SiC) Power MOSFET",
            package="TO-247-3",
            voltage_rating_v=900.0,
            current_rating_a=36.0,
            rds_on_ohm=0.065,
            kicad_footprint="Package_TO_SOT_THT:TO-247-3_Vertical",
            kicad_symbol="Device:Q_NMOS_DGS",
            spice_model_name="C3M0065090D",
        )
        # Diodes
        c3 = ComponentRecord(
            mpn="MBR20100CT",
            manufacturer="ON Semiconductor",
            category="diode",
            description="100V 20A Dual Schottky Barrier Rectifier",
            package="TO-220-3",
            voltage_rating_v=100.0,
            current_rating_a=20.0,
            kicad_footprint="Package_TO_SOT_THT:TO-220-3_Vertical",
            kicad_symbol="Device:D_Schottky_x2_KCom_AAK",
        )
        self._components[c1.mpn] = c1
        self._components[c2.mpn] = c2
        self._components[c3.mpn] = c3

        # Magnetic Materials
        m1 = MaterialRecord(
            name="N87",
            material_type="MnZn Ferrite",
            initial_permeability_ui=2200.0,
            saturation_flux_t=0.49,
            curie_temp_c=210.0,
            steinmetz_cm=16.9,
            steinmetz_alpha=1.25,
            steinmetz_beta=2.35,
            freq_min_hz=25000.0,
            freq_max_hz=500000.0,
        )
        m2 = MaterialRecord(
            name="N97",
            material_type="MnZn Ferrite (Low Loss)",
            initial_permeability_ui=2300.0,
            saturation_flux_t=0.51,
            curie_temp_c=230.0,
            steinmetz_cm=11.2,
            steinmetz_alpha=1.30,
            steinmetz_beta=2.40,
            freq_min_hz=50000.0,
            freq_max_hz=500000.0,
        )
        m3 = MaterialRecord(
            name="3F36",
            material_type="MnZn Ferrite (High-Freq)",
            initial_permeability_ui=1900.0,
            saturation_flux_t=0.38,
            curie_temp_c=220.0,
            steinmetz_cm=3.2,
            steinmetz_alpha=1.46,
            steinmetz_beta=2.75,
            freq_min_hz=100000.0,
            freq_max_hz=1000000.0,
            provenance="Ferroxcube 3F36 Datasheet",
        )
        m4 = MaterialRecord(
            name="3C90",
            material_type="MnZn Ferrite (Power)",
            initial_permeability_ui=2300.0,
            saturation_flux_t=0.40,
            curie_temp_c=230.0,
            steinmetz_cm=10.0,
            steinmetz_alpha=1.30,
            steinmetz_beta=2.50,
            freq_min_hz=25000.0,
            freq_max_hz=200000.0,
            provenance="Ferroxcube 3C90 Datasheet",
        )
        m5 = MaterialRecord(
            name="KoolMu",
            material_type="Powder Alloy (Fe-Si-Al)",
            initial_permeability_ui=125.0,
            saturation_flux_t=1.05,
            curie_temp_c=500.0,
            steinmetz_cm=42.5,
            steinmetz_alpha=1.15,
            steinmetz_beta=2.10,
            freq_min_hz=10000.0,
            freq_max_hz=500000.0,
            provenance="Magnetics Inc Kool Mµ Datasheet",
        )
        self._materials[m1.name] = m1
        self._materials[m2.name] = m2
        self._materials[m3.name] = m3
        self._materials[m4.name] = m4
        self._materials[m5.name] = m5

        # Standard Verified Magnetic Core Geometries
        core1 = MagneticCoreRecord(
            name="Planar E22/6/16",
            geometry_type="Planar E",
            ae_mm2=78.5,
            le_mm=31.5,
            ve_mm3=2470.0,
            amin_mm2=68.5,
            aw_mm2=25.5,
            manufacturer="Ferroxcube / TDK",
            provenance="Ferroxcube Planar E22 Datasheet",
        )
        core2 = MagneticCoreRecord(
            name="PQ26/20",
            geometry_type="PQ Core",
            ae_mm2=122.0,
            le_mm=46.3,
            ve_mm3=5450.0,
            amin_mm2=118.0,
            aw_mm2=43.5,
            manufacturer="TDK Epcos",
            provenance="TDK Epcos PQ26/20 Datasheet",
        )
        core3 = MagneticCoreRecord(
            name="RM8",
            geometry_type="RM Core",
            ae_mm2=64.0,
            le_mm=38.0,
            ve_mm3=2440.0,
            amin_mm2=55.0,
            aw_mm2=30.2,
            manufacturer="TDK / Ferroxcube",
            provenance="TDK RM8 Core Datasheet",
        )
        core4 = MagneticCoreRecord(
            name="EFD20",
            geometry_type="EFD Low Profile",
            ae_mm2=31.0,
            le_mm=47.0,
            ve_mm3=1460.0,
            amin_mm2=31.0,
            aw_mm2=18.0,
            manufacturer="TDK Epcos",
            provenance="TDK Epcos EFD20 Datasheet",
        )
        core5 = MagneticCoreRecord(
            name="ETD29",
            geometry_type="ETD Standard",
            ae_mm2=76.0,
            le_mm=72.0,
            ve_mm3=5470.0,
            amin_mm2=71.0,
            aw_mm2=83.0,
            manufacturer="Ferroxcube",
            provenance="Ferroxcube ETD29 Datasheet",
        )
        for c in [core1, core2, core3, core4, core5]:
            self._cores[c.name] = c

    def list_components(self, category: Optional[str] = None) -> List[ComponentRecord]:
        if category:
            return [c for c in self._components.values() if c.category.lower() == category.lower()]
        return list(self._components.values())

    def get_component(self, mpn: str) -> Optional[ComponentRecord]:
        return self._components.get(mpn)

    def list_materials(self) -> List[MaterialRecord]:
        return list(self._materials.values())

    def get_material(self, name: str) -> Optional[MaterialRecord]:
        return self._materials.get(name)

    def list_cores(self) -> List[MagneticCoreRecord]:
        return list(self._cores.values())

    def get_core(self, name: str) -> Optional[MagneticCoreRecord]:
        return self._cores.get(name)
