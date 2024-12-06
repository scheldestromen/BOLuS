from geolib import DStabilityModel
from pydantic import BaseModel
from typing_extensions import List

from geolib.geometry.one import Point

from dstability_toolbox.model import Stage, Model
from dstability_toolbox.geometry import Geometry
from dstability_toolbox.subsoil import Subsoil
from dstability_toolbox.water import Waternet

# TODO: Naam, misschien builder noemen?


def get_scenario_and_stage_index_by_label(dm: DStabilityModel, scenario: str, stage: str):
    pass


def set_geometry(geometry: Geometry, dm: DStabilityModel, scenario_index: int, stage_index: int):
    # Eerste instantie: check op bestaande geometrie, dan foutmeldingen
    # Later omgang met bestaande som: bv. door opvulmateriaal boven de gedefinieerde bodemopbouw
    pass


def set_soil_parameters(soil_collection, dm: DStabilityModel, scenario_index: int, stage_index: int):
    pass


def set_subsoil(subsoil: Subsoil, scenario_index: int, stage_index: int):
    pass


def create_state():
    pass


def set_state():
    pass


def set_waternet(waternet: Waternet, dm: DStabilityModel, scenario_index: int, stage_index: int):
    pass


def add_stage(stage: Stage):
    pass


def model_to_d_stability_model(model: Model):
    """Creates a new DStabilityModel from a Model instance"""

    dm = DStabilityModel()