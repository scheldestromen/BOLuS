from typing import Optional
from pydantic import BaseModel

from .calculation_settings import GridSettingsSet
from .geometry import Geometry
from .loads import Load
from .soils import SoilCollection
from .state import StatePoint
from .subsoil import Subsoil
from .waternet import Waternet


class Stage(BaseModel):
    """
    Represents a stage of a D-Stability calculation.
    
    Attributes:
        name (str): The name of the stage
        notes (str): The notes of the stage
        geometry (Geometry): The geometry of the stage
        subsoil (Subsoil): The subsoil of the stage
        state_points (Optional[list[StatePoint]]): The state points of the stage
        load (Optional[Load]): The load of the stage
        waternet (Waternet): The waternet of the stage"""

    name: str
    notes: str
    geometry: Geometry
    subsoil: Subsoil
    state_points: Optional[list[StatePoint]] = None
    load: Optional[Load] = None
    waternet: Optional[Waternet] = None


class Scenario(BaseModel):
    """
    Represents a scenario of a D-Stability calculation.
    
    Attributes:
        name (str): The name of the scenario
        notes (str): The notes of the scenario
        stages (list[Stage]): The stages of the scenario
        grid_settings_set (Optional[GridSettingsSet]): The grid settings set of the scenario"""
    
    name: str
    notes: str = ""
    stages: list[Stage]
    grid_settings_set: Optional[GridSettingsSet]


class Model(BaseModel):
    """
    Represents a D-Stability calculation and contains all the information
    needed to create a GEOLib DStabilityModel.
    
    Attributes:
        name (str): The name of the model
        soil_collection (SoilCollection): The soil collection of the model
        scenarios (list[Scenario]): The scenarios of the model"""

    name: str
    soil_collection: SoilCollection
    scenarios: list[Scenario]
