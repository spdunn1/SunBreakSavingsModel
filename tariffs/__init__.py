from .pge import PGE_TARIFFS
from .sce import SCE_TARIFFS
from .sdge import SDGE_TARIFFS

REGISTRY = {}
REGISTRY.update(PGE_TARIFFS)
REGISTRY.update(SCE_TARIFFS)
REGISTRY.update(SDGE_TARIFFS)
