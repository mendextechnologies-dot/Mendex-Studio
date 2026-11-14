"""Regression test for P0-1: Verifying AI agents over MCP cannot register reviewers or record reviews."""
import pytest
from mendex_core.mcp.server import MendexMCPServer
from mendex_core.service import StudioError, StudioService


def test_mcp_tools_exclude_write_reviews(tmp_path):
    server = MendexMCPServer(data_root=tmp_path)
    tool_names = [tool["name"] for tool in server.tools_schema]

    # Must NOT expose write review tools to AI agents
    assert "register_authorized_reviewer" not in tool_names
    assert "record_human_review" not in tool_names

    # Read-only and request review operations MUST still be present
    assert "get_review_package" in tool_names
    assert "list_authorized_reviewers" in tool_names
    assert "get_stage_review_history" in tool_names
    assert "request_stage_review" in tool_names


def test_mcp_blocks_attempted_register_reviewer(tmp_path):
    server = MendexMCPServer(data_root=tmp_path)

    # Even if an AI agent attempts to invoke register_authorized_reviewer directly
    with pytest.raises(StudioError) as exc:
        server._dispatch_tool(
            "register_authorized_reviewer",
            {
                "id": "jdoe",
                "name": "John Doe",
                "email": "jdoe@example.com",
                "roles": ["lead_engineer"],
                "secret": "secure_secret_123",
            },
        )
    assert exc.value.code == "FORBIDDEN"
    assert "AI agents and MCP clients cannot execute" in str(exc.value)


def test_mcp_blocks_attempted_record_human_review(tmp_path):
    server = MendexMCPServer(data_root=tmp_path)

    with pytest.raises(StudioError) as exc:
        server._dispatch_tool(
            "record_human_review",
            {
                "revision_id": "00000000-0000-0000-0000-000000000000",
                "stage_id": "requirements",
                "attempt": 1,
                "reviewer_id": "jdoe",
                "secret": "secure_secret_123",
                "decision": "APPROVED",
                "comments": "Agent attempting sign-off",
                "idempotency_key": "00000000-0000-0000-0000-000000000001",
            },
        )
    assert exc.value.code == "FORBIDDEN"
    assert "AI agents and MCP clients cannot execute" in str(exc.value)
