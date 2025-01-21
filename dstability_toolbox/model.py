from typing import Optional

from pydantic import BaseModel
from typing_extensions import List

from .loads import Load
from .soils import SoilCollection
from .water import Waternet
from .geometry import Geometry
from .subsoil import Subsoil
from .state import StatePoint


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
    stages: List[Stage]


class Model(BaseModel):
    name: str
    soil_collection: SoilCollection
    scenarios: List[Scenario]
