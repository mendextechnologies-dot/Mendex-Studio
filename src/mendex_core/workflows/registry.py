"""Extensible registry and base classes for visual engineering workflow nodes."""
from __future__ import annotations

import abc
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from pydantic import BaseModel, ConfigDict

from .contracts import NodeCategory
from .types import PortDefinition, PortDataType


class ExecutionContext(BaseModel):
    """Runtime context passed to nodes during workflow execution."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    workspace_id: Optional[str] = None
    workspace_path: Optional[str] = None
    product_id: Optional[str] = None
    run_id: str
    service: Any = None  # Reference to StudioService if available
    logger: Optional[Callable[[str], None]] = None

    def log(self, message: str) -> None:
        if self.logger:
            self.logger(message)


class BaseNode(abc.ABC):
    """Abstract base class for all engineering workflow nodes."""
    node_type: str = "base"
    category: NodeCategory = NodeCategory.INPUT
    title: str = "Base Node"
    description: str = ""

    @classmethod
    @abc.abstractmethod
    def get_input_ports(cls) -> List[PortDefinition]:
        """Define incoming data ports for this node."""
        return []

    @classmethod
    @abc.abstractmethod
    def get_output_ports(cls) -> List[PortDefinition]:
        """Define outgoing data ports for this node."""
        return []

    @abc.abstractmethod
    def execute(
        self,
        inputs: Dict[str, Any],
        config: Dict[str, Any],
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute node computation deterministically."""
        raise NotImplementedError


class NodeRegistry:
    """Singleton registry holding all available engineering node types."""
    _instance: Optional[NodeRegistry] = None
    _nodes: Dict[str, Type[BaseNode]] = {}

    def __new__(cls) -> NodeRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._nodes = {}
        return cls._instance

    @classmethod
    def register(cls, node_cls: Type[BaseNode]) -> Type[BaseNode]:
        registry = cls()
        registry._nodes[node_cls.node_type] = node_cls
        return node_cls

    @classmethod
    def get(cls, node_type: str) -> Optional[Type[BaseNode]]:
        return cls()._nodes.get(node_type)

    @classmethod
    def list_nodes(cls) -> List[Type[BaseNode]]:
        return list(cls()._nodes.values())

    @classmethod
    def list_by_category(cls, category: NodeCategory) -> List[Type[BaseNode]]:
        return [n for n in cls()._nodes.values() if n.category == category]

    @classmethod
    def get_port_catalog(cls) -> Dict[str, Tuple[List[PortDefinition], List[PortDefinition]]]:
        """Returns map of node_type -> (input_ports, output_ports)."""
        catalog = {}
        for ntype, ncls in cls()._nodes.items():
            catalog[ntype] = (ncls.get_input_ports(), ncls.get_output_ports())
        return catalog
