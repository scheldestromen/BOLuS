from pydantic import BaseModel
from typing_extensions import List

from geolib.models.dstability import DStabilityModel
from geolib.models.dstability.internal import SoilCollection as GLSoilCollection

from .soils import SoilCollection
from .water import Waternet
from .geometry import Geometry
from .subsoil import Subsoil


class Stage(BaseModel):
    name: str
    notes: str
    geometry: Geometry
    subsoil: Subsoil
    # waternet: Waternet


class Scenario(BaseModel):
    name: str
    notes: str = ""
    stages: List[Stage]


class Model(BaseModel):
    name: str
    soil_collection: SoilCollection
    scenarios: List[Scenario]


# TODO: Standaard stages en scenario's eruit knikkeren
def create_d_stability_model(model: Model):
    """Creates new calculations with the given models"""
    dm = DStabilityModel()

    # Remove standard input
    dm.datastructure.soils = GLSoilCollection(Soils=[])

    # Add the soil types
    for soil in model.soil_collection.soils:
        dm.add_soil(soil.dm_soil)

    # Add the scenarios
    for scenario in model.scenarios:
        dm.add_scenario(label=scenario.name, notes=scenario.notes, set_current=True)

        for stage in scenario.stages:
            dm.add_stage(label=stage.name, notes=stage.notes, set_current=True)

            # Add subsoil
            for soil_polygon in stage.subsoil.soil_polygons:
                points = soil_polygon.to_geolib_points()
                dm.add_layer(points=points, soil_code=soil_polygon.soil_type)

    return dm

# Er is een structuur nodig om de gebruikersinvoer te spiegelen, koppeling van bv. geometrie en watersp. aan één som
# Dit is een universele structuur voor het kunnen genereren van een geolib d-stability model
# Nadenken over hoe deze structuur gebruikt kan worden voor het hergebruiken van bestaande berekeningen

