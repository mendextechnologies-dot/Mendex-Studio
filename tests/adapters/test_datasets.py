import hashlib
import json
from pathlib import Path
import pytest

from integrations.datasets.provenance import verify_dataset_file
from integrations.datasets.switchloss_db import SwitchLossDB
from integrations.datasets.magnet_dataset import MagNetDataset


def test_switchloss_db_ingestion_and_query(tmp_path):
    csv_content = (
        "part_number,manufacturer,device_type,v_ds_rated_v,i_d_rated_a,r_ds_on_mohm,e_on_uj,e_off_uj,v_test_v,i_test_a,t_j_c\n"
        "C3M0065090D,Wolfspeed,SiC,900.0,36.0,65.0,85.0,22.0,600.0,20.0,25.0\n"
        "NVHL080N120SC1,onsemi,SiC,1200.0,28.0,80.0,120.0,35.0,800.0,20.0,25.0\n"
        "IRFB4110,Infineon,MOSFET,100.0,180.0,3.7,15.0,10.0,60.0,100.0,25.0\n"
    )
    csv_file = tmp_path / "switchloss.csv"
    csv_bytes = csv_content.encode("utf-8")
    csv_file.write_bytes(csv_bytes)
    expected_sha = hashlib.sha256(csv_bytes).hexdigest()

    db = SwitchLossDB()
    count = db.load_csv(csv_file, expected_sha256=expected_sha)
    assert count == 3

    # Query 600V+ devices
    hv_devices = db.find_devices(min_voltage=600.0)
    assert len(hv_devices) == 2
    assert {d.part_number for d in hv_devices} == {"C3M0065090D", "NVHL080N120SC1"}


def test_switchloss_canonical_fixture():
    fixture_path = Path(__file__).parents[2] / "src" / "integrations" / "datasets" / "fixtures" / "switchloss_sample.csv"
    assert fixture_path.exists()

    db = SwitchLossDB()
    count = db.load_csv(fixture_path)
    assert count >= 8

    # Ensure 1200V SiC devices are indexed
    sic_1200v = db.find_devices(min_voltage=1200.0)
    assert len(sic_1200v) >= 3


def test_magnet_dataset_ingestion_and_query(tmp_path):
    data = {
        "dataset": "MagNet Core Loss",
        "measurements": [
            {
                "material": "N87",
                "temperature_c": 25.0,
                "frequency_hz": 100000.0,
                "b_peak_t": 0.1,
                "waveform": "sinusoidal",
                "volumetric_loss_w_m3": 45000.0,
            },
            {
                "material": "3C90",
                "temperature_c": 100.0,
                "frequency_hz": 200000.0,
                "b_peak_t": 0.05,
                "waveform": "triangular",
                "volumetric_loss_w_m3": 38000.0,
            },
        ],
    }
    json_path = tmp_path / "magnet.json"
    json_bytes = json.dumps(data).encode("utf-8")
    json_path.write_bytes(json_bytes)
    sha = hashlib.sha256(json_bytes).hexdigest()

    magnet = MagNetDataset()
    count = magnet.load_json(json_path, expected_sha256=sha)
    assert count == 2

    n87_records = magnet.query(material="N87", max_freq_hz=150000.0)
    assert len(n87_records) == 1
    assert n87_records[0].volumetric_loss_w_m3 == 45000.0


def test_magnet_canonical_fixture():
    fixture_path = Path(__file__).parents[2] / "src" / "integrations" / "datasets" / "fixtures" / "magnet_sample.json"
    assert fixture_path.exists()

    magnet = MagNetDataset()
    count = magnet.load_json(fixture_path)
    assert count >= 6

    # Query N87 at high frequency
    n87 = magnet.query(material="N87", max_freq_hz=250000.0)
    assert len(n87) >= 3


def test_dataset_checksum_mismatch(tmp_path):
    dummy_file = tmp_path / "corrupted.csv"
    dummy_file.write_text("corrupted data", encoding="utf-8")
    db = SwitchLossDB()
    with pytest.raises(ValueError, match="integrity check failed"):
        db.load_csv(dummy_file, expected_sha256="0000000000000000000000000000000000000000000000000000000000000000")
