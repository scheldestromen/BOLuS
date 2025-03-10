from abc import ABC, abstractmethod
from enum import Enum
from typing import Annotated, List

from geolib.models import DStabilityModel
from pydantic import BaseModel, Field

from dstability_toolbox.geometry import Geometry
from dstability_toolbox.model import Model, Stage
from dstability_toolbox.state import create_state_points_from_subsoil
from dstability_toolbox.subsoil import Subsoil
from dstability_toolbox.water import Waternet

# Deze nog even laten zitten. Nut afwegen na aan de gang te zijn gegaan met input_handler


class BaseSequence(ABC):
    # Overwegen of dit nodig is. Of met protocol? Er moet wellicht geborgd worden dat er bepaalde methods zijn

    @abstractmethod
    def run(self) -> DStabilityModel:
        """Runs the sequence"""


class NewTwoStagesModelInput(BaseModel):
    pass


class NewTwoStagesModel(BaseModel):
    """Sequence for creating a two stage D-Stability calculation

    The first stage represents the daily conditions, which (possibly) contains
    the state (stress history). The second stage represents the situation to be assessed.
    """

    stages: Annotated[List[Stage], Field(min_length=2, max_length=2)]

    def run(
        self,
        geometry: Geometry,
        subsoil: Subsoil,
        waternet: Annotated[List[Waternet], Field(min_length=2, max_length=2)],
    ) -> Model:
        # Nog niet geïmplementeerd
        pass


# Eigenlijk heb je heel veel aftakkingen over hoe je een sequence kan maken. Ook betreft 1D of 2D ondergrond etc.
#  waterspanningen...


# de module stix heeft de functionaliteiten
# De sequence heeft de logica.
# Stix kan een stage toevoegen met of zonder belastinggeschiedenis
# De sequence weet dat de eerste wel POPS heeft en de tweede niet.

# Scenario maken
# Stage dagelijks toevoegen
# Stage hoogwater toevoegen

# Gedachtes
# Ik zou ook een soort stage_sequence kunnen maken [Daily, HighWater]
# Of STBU -> [Daily, HighWater, SuddenDecrease]. Dit hangt eigenlijk alleen aan de waterspanningen.

# JSON input? Dan onafhankelijk van platform/UI

# Ander idee voor de sequence - Dit zou wellicht meer onderdeel afhankelijk moeten zijn
# Bijvoorbeeld voor de plaatsing van ondergrondprofielen, standaard op de binnenteen met twee profielen
