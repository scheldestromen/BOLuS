from pydantic import BaseModel
from typing_extensions import List

from .water import Waternet
from .geometry import Geometry
from .subsoil import Subsoil


class Stage(BaseModel):
    name: str
    notes: str
    geometry: Geometry
    subsoil: Subsoil
    waternet: Waternet


class Scenario(BaseModel):
    name: str
    notes: str
    stages: List[Stage]


class Model(BaseModel):
    name: str
    scenarios: List[Scenario]


def create_d_stability_models(models: List[Model]):
    """Creates new calculations with the given models"""

# Er is een structuur nodig om de gebruikersinvoer te spiegelen, koppeling van bv. geometrie en watersp. aan één som
# Dit is een universele structuur voor het kunnen genereren van een geolib d-stability model
# Nadenken over hoe deze structuur gebruikt kan worden voor het hergebruiken van bestaande berekeningen

