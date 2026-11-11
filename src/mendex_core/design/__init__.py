"""Engineering Design package for Mendex Studio v1.9."""
from .ir import (
    DesignIntermediateRepresentation,
    IRComponent,
    IRPin,
    IRNet,
    IRPort,
    IRParameter,
    IRMagneticGeometry,
    ComponentType,
    PortDirection,
)
from .models import (
    EngineeringDesign,
    DesignRevision,
    DesignCandidate,
    DesignArtifact,
    ArtifactKind,
    DesignStatus,
    Requirement,
)
from .service import EngineeringDesignService
from .synthesis import CandidateSynthesisEngine
from .parametric import ParametricDesignEngine, ParametricChangeImpact
from .sync import CrossToolSyncService, SyncStatus

from .ltspice_runner import LTspiceRunner, LTspiceSimulationResult
from .femm_runner import FEMMRunner, FEMMSimulationResult
from .iteration import DesignIterationEngine, DesignIterationProposal
from .generators import KiCadPCBGenerator
from .naming import sanitize_filename, clean_title

__all__ = [
    "DesignIntermediateRepresentation",
    "IRComponent",
    "IRPin",
    "IRNet",
    "IRPort",
    "IRParameter",
    "IRMagneticGeometry",
    "ComponentType",
    "PortDirection",
    "EngineeringDesign",
    "DesignRevision",
    "DesignCandidate",
    "DesignArtifact",
    "ArtifactKind",
    "DesignStatus",
    "Requirement",
    "EngineeringDesignService",
    "CandidateSynthesisEngine",
    "ParametricDesignEngine",
    "ParametricChangeImpact",
    "CrossToolSyncService",
    "SyncStatus",
    "LTspiceRunner",
    "LTspiceSimulationResult",
    "FEMMRunner",
    "FEMMSimulationResult",
    "DesignIterationEngine",
    "DesignIterationProposal",
    "KiCadPCBGenerator",
    "sanitize_filename",
    "clean_title",
]
