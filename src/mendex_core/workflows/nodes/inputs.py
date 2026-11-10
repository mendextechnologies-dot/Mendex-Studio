"""Input nodes: numeric, text, parameter, file, dataset, and workspace artifacts."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import hashlib

from ..contracts import NodeCategory
from ..types import PortDefinition, PortDataType, QuantityValue, FileReference, DatasetReference, ArtifactData
from ..registry import BaseNode, ExecutionContext, NodeRegistry


@NodeRegistry.register
class NumericInputNode(BaseNode):
    node_type = "numeric_input"
    category = NodeCategory.INPUT
    title = "Numeric Input"
    description = "Provides a constant scalar numeric value or quantity with units."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return []

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="value", display_name="Value", data_type=PortDataType.SCALAR, description="Numeric magnitude"),
            PortDefinition(name="quantity", display_name="Quantity", data_type=PortDataType.QUANTITY, description="Quantity with unit"),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        val = float(config.get("value", 0.0))
        unit = str(config.get("unit", "")).strip()
        q = QuantityValue(value=val, unit=unit)
        return {
            "value": val,
            "quantity": q,
        }


@NodeRegistry.register
class TextInputNode(BaseNode):
    node_type = "text_input"
    category = NodeCategory.INPUT
    title = "Text Input"
    description = "Provides a constant string or netlist/script text."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return []

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="text", display_name="Text", data_type=PortDataType.STRING),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        return {"text": str(config.get("text", ""))}


@NodeRegistry.register
class ParameterInputNode(BaseNode):
    node_type = "parameter_input"
    category = NodeCategory.INPUT
    title = "Engineering Parameter"
    description = "Named parameter with unit (e.g. Vin=24V, fsw=100kHz, L=150uH)."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return []

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="value", display_name="Value", data_type=PortDataType.SCALAR),
            PortDefinition(name="quantity", display_name="Quantity", data_type=PortDataType.QUANTITY),
            PortDefinition(name="name", display_name="Name", data_type=PortDataType.STRING),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        name = str(config.get("name", "param"))
        val = float(config.get("value", 1.0))
        unit = str(config.get("unit", ""))
        return {
            "name": name,
            "value": val,
            "quantity": QuantityValue(value=val, unit=unit),
        }


@NodeRegistry.register
class FileInputNode(BaseNode):
    node_type = "file_input"
    category = NodeCategory.INPUT
    title = "File Reference"
    description = "References an existing file in workspace or external path."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return []

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="file_ref", display_name="File", data_type=PortDataType.FILE_REF),
            PortDefinition(name="text_content", display_name="Content", data_type=PortDataType.STRING),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        raw_path = config.get("file_path", "")
        p = Path(raw_path)
        if not p.is_absolute() and context.workspace_path:
            p = Path(context.workspace_path) / p

        if not p.exists():
            raise FileNotFoundError(f"Input file not found: {raw_path}")

        data = p.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        text_content = ""
        try:
            text_content = data.decode("utf-8")
        except UnicodeDecodeError:
            text_content = f"<Binary file: {len(data)} bytes>"

        ref = FileReference(
            path=str(p),
            filename=p.name,
            sha256=sha256,
            size_bytes=len(data),
        )
        return {
            "file_ref": ref,
            "text_content": text_content,
        }


@NodeRegistry.register
class DatasetReferenceNode(BaseNode):
    node_type = "dataset_reference"
    category = NodeCategory.INPUT
    title = "Dataset Reference"
    description = "References an engineering dataset registered in the platform."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return []

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="dataset_ref", display_name="Dataset", data_type=PortDataType.DATASET_REF),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        ds_id = str(config.get("dataset_id", "default_dataset"))
        ver = str(config.get("version", "1.0"))
        tool_id = str(config.get("tool_id", "generic"))
        return {
            "dataset_ref": DatasetReference(dataset_id=ds_id, version=ver, tool_id=tool_id)
        }
