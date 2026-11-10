from integrations.generators.femm_generator import generate_femm_transformer_script
from integrations.generators.freecad_generator import generate_freecad_bobbin_script
from integrations.generators.modelica_generator import generate_openmodelica_flyback_script


def test_femm_generator_output():
    script = generate_femm_transformer_script(
        core_type="ETD49",
        primary_turns=30,
        secondary_turns=800,
        primary_current_a=3.0,
        air_gap_mm=0.8,
        frequency_hz=120000.0,
    )
    assert "newdocument(0)" in script
    assert "120000.0" in script
    assert "Ferrite_N87" in script
    assert "mi_analyze(1)" in script


def test_freecad_generator_output():
    script = generate_freecad_bobbin_script(
        flange_od_mm=35.0,
        core_id_mm=18.0,
        height_mm=28.0,
        output_step_path="bobbin_etd.step",
    )
    assert "import FreeCAD" in script
    assert "Part.makeCylinder" in script
    assert "Part.export" in script
    assert "bobbin_etd.step" in script


def test_modelica_generator_output():
    script = generate_openmodelica_flyback_script(
        vin_v=28.0,
        vout_target_v=1200.0,
        f_sw_hz=150000.0,
    )
    assert "loadModel(Modelica);" in script
    assert "model FlybackConverter" in script
    assert "simulate(FlybackConverter" in script
