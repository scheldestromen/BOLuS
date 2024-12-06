# Grondsoorten
from typing import Optional, List

from pydantic import BaseModel
from geolib.soils.soil import Soil as GLSoil


class Soil(BaseModel):
    dm_soil: GLSoil
    pop: Optional[float]


class SoilCollection(BaseModel):
    soils: List[Soil]
