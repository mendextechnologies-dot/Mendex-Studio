"""Canonical explicit engineering inputs shared by MCP, CLI and controller."""
from typing import Annotated
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

Positive = Annotated[float, Field(gt=0, strict=True)]


class DesignGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    workspace_id: str = Field(min_length=1, validation_alias=AliasChoices("workspace_id", "project_id"))
    title: str = Field(min_length=1)
    category: str = "dc_dc_converter"
    vin_nom: Positive
    vout: Positive
    iout: Positive
    fsw_hz: Positive
    ripple_v: Positive
    vin_min: Positive | None = None
    vin_max: Positive | None = None
    isolation_v: Positive | None = None
    generate_artifacts: bool = Field(default=True, strict=True)
    product_id: str | None = None
