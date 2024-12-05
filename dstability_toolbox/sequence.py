from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel
from typing_extensions import List

from geolib.models import DStabilityModel


# TODO: Deze nog even laten zitten? Nut afwegen na aan de gang te zijn gegaan met dstability_tool

class BaseSequence(ABC):
    # TODO: is dit nodig? Of met protocol? Er moet wellicht geborgd worden dat er bepaalde methods zijn

    @abstractmethod
    def run(self) -> DStabilityModel:
        """Runs the sequence"""


class InitiateTwoStages(BaseModel):
    """Sequence for creating a two stage D-Stability calculation

    The first stage represents the daily conditions, which (possibly) contains the state (stress history).
    The second stage represents the situation to be assessed."""

    # de module stix heeft de functionaliteiten
    # De sequence heeft de logica.
    # Stix kan een stage toevoegen met of zonder belastinggeschiedenis
    # De sequence weet dat de eerste wel POPS heeft en de tweede niet.

    # Scenario maken
    # Stage dagelijks toevoegen
    # Stage hoogwater toevoegen

# TODO: Ik zou ook een soort stage_sequence kunnen maken [Daily, HighWater]
#       Of STBU -> [Daily, HighWater, SuddenDecrease]. Dit hangt eigenlijk alleen aan de waterspanningen.


# TODO: JSON input? Dan onafhankelijk van platform/UI
