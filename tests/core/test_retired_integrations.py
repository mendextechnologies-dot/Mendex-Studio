"""Retired commercial tools cannot be discovered or reactivated from old settings."""
import pytest

from mendex_core.integration_contracts import ToolConfiguration
from mendex_core.service import StudioError, StudioService
from integrations.adapters.registry import ToolRegistry
from integrations.v15_connector import V15ConnectorRegistry

RETIRED = {"plecs", "matlab-simulink", "ansys-maxwell", "ansys-icepak", "solidworks"}


def test_commercial_integrations_retired_without_deleting_history(tmp_path):
    service = StudioService(tmp_path)
    payload = ToolConfiguration(license_reference="Historical review record").model_dump_json()
    with service.connection() as db:
        db.execute("INSERT INTO integration_settings VALUES (?, ?)", ("plecs", payload))
    restarted = StudioService(tmp_path)
    assert not RETIRED.intersection(t.tool_id for t in restarted.integrations.list_tools())
    assert not RETIRED.intersection(t.tool_id for t in ToolRegistry().list_descriptors())
    assert not RETIRED.intersection(c.descriptor.tool_id for c in V15ConnectorRegistry.all())
    for tool_id in RETIRED:
        with pytest.raises(StudioError, match="not registered"):
            restarted.integrations.verify(tool_id)
        with pytest.raises(StudioError, match="not registered"):
            restarted.integrations.configure(tool_id, ToolConfiguration())
    with restarted.connection() as db:
        assert db.execute("SELECT payload FROM integration_settings WHERE tool_id='plecs'").fetchone()[0] == payload
