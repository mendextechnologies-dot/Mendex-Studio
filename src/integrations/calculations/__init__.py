from .power_losses import (
    SemiconductorLossResult,
    CoreLossResult,
    calculate_semiconductor_losses,
    calculate_core_loss_steinmetz,
)

__all__ = [
    "SemiconductorLossResult",
    "CoreLossResult",
    "calculate_semiconductor_losses",
    "calculate_core_loss_steinmetz",
]
