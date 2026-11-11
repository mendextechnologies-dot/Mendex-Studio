"""Intelligence nodes: physical knowledge lookup, rule advice, and solver recommendation."""
from __future__ import annotations

from typing import Any, Dict, List

from ..contracts import NodeCategory
from ..types import PortDefinition, PortDataType, QuantityValue
from ..registry import BaseNode, ExecutionContext, NodeRegistry
from ...intelligence.knowledge import EngineeringKnowledgeService


@NodeRegistry.register
class KnowledgeLookupNode(BaseNode):
    node_type = "knowledge_lookup"
    category = NodeCategory.INTELLIGENCE
    title = "Engineering Knowledge Lookup"
    description = "Retrieves material properties, formula definitions, or regulatory standard limits."

    @classmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        return []

    @classmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        return [
            PortDefinition(name="material_data", display_name="Material Data", data_type=PortDataType.ANY),
            PortDefinition(name="resistivity_ohm_m", display_name="Resistivity", data_type=PortDataType.SCALAR),
            PortDefinition(name="saturation_flux_t", display_name="Bsat (T)", data_type=PortDataType.SCALAR),
        ]

    def execute(self, inputs: Dict[str, Any], config: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        material_id = config.get("material_id", "tdk_n87")
        knowledge = EngineeringKnowledgeService()
        mat = knowledge.get_material(material_id)

        if not mat:
            return {
                "material_data": {},
                "resistivity_ohm_m": 1.68e-8,
                "saturation_flux_t": 0.40,
            }

        return {
            "material_data": mat.model_dump(),
            "resistivity_ohm_m": mat.electrical_resistivity_ohm_m,
            "saturation_flux_t": mat.magnetic_saturation_flux_density_t or 0.40,
        }
