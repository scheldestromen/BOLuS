from typing import Optional

from pydantic import BaseModel

from .calculation_settings import GridSettingsSet
from .geometry import Geometry
from .loads import Load
from .soils import SoilCollection
from .state import StatePoint
from .subsoil import Subsoil
from .water import Waternet


class Stage(BaseModel):
    name: str
    notes: str
    geometry: Geometry
    subsoil: Subsoil
    state_points: Optional[list[StatePoint]] = None
    load: Optional[Load] = None
    waternet: Waternet


class Scenario(BaseModel):
    name: str
    notes: str = ""
    stages: list[Stage]
    grid_settings_set: Optional[GridSettingsSet]


class Model(BaseModel):
    name: str
    soil_collection: SoilCollection
    scenarios: list[Scenario]
