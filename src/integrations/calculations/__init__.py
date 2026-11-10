from .power_losses import (
    SemiconductorLossResult,
    CoreLossResult,
    calculate_semiconductor_losses,
    calculate_core_loss_steinmetz,
)
from .winding_losses import (
    SkinDepthResult,
    DowellLossFactorResult,
    calculate_skin_depth,
    calculate_dowell_ac_resistance,
)
from .transformer_design import (
    FlybackTransformerDesign,
    calculate_flyback_transformer_parameters,
)

__all__ = [
    "SemiconductorLossResult",
    "CoreLossResult",
    "calculate_semiconductor_losses",
    "calculate_core_loss_steinmetz",
    "SkinDepthResult",
    "DowellLossFactorResult",
    "calculate_skin_depth",
    "calculate_dowell_ac_resistance",
    "FlybackTransformerDesign",
    "calculate_flyback_transformer_parameters",
]
