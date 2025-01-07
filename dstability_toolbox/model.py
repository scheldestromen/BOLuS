from typing import Optional

from pydantic import BaseModel
from typing_extensions import List

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
    # waternet: Waternet


class Scenario(BaseModel):
    name: str
    notes: str = ""
    stages: List[Stage]


class Model(BaseModel):
    name: str
    soil_collection: SoilCollection
    scenarios: List[Scenario]


# Er is een structuur nodig om de gebruikersinvoer te spiegelen, koppeling van bv. geometrie en watersp. aan één som
# Dit is een universele structuur voor het kunnen genereren van een geolib d-stability model
# Nadenken over hoe deze structuur gebruikt kan worden voor het hergebruiken van bestaande berekeningen

