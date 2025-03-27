from typing import Optional

from geolib.soils.soil import Soil as GLSoil
from geolib.models.dstability.internal import PersistableShadingTypeEnum
from pydantic import BaseModel


class Soil(BaseModel):
    """Represents a soil type.

    It is based on a GEOLib soil type with an added attribute pop for the possibility
    to apply a pre-overburden pressure per soil type.

    Attributes:
        gl_soil: The GEOLib soil object
        pop_mean (float): The Pre-overburden pressure value for the soil
        pop_std (float): The standard deviation of the Pre-overburden pressure value for the soil
        probabilistic_pop (bool): Whether the Pre-overburden pressure value is probabilistic
        ocr (float): The over-consolidation ratio (not implemented)
        consolidation_traffic_load (int): Percentage [0 - 100%] of consolidation traffic load
    """

    gl_soil: GLSoil
    pop_mean: Optional[float] = None
    pop_std: Optional[float] = None
    probabilistic_pop: Optional[bool] = None
    ocr: Optional[float] = None
    consolidation_traffic_load: Optional[int] = None
    color: Optional[str] = None
    pattern: Optional[PersistableShadingTypeEnum] = None


class SoilCollection(BaseModel):
    """Represents a collection of soil types.

    Attributes:
        name (str): Optional. The name of the soil collection
        soils (list): List of Soil instances
    """

    name: Optional[str] = None
    soils: list[Soil]

    def get_by_name(self, name: str) -> Soil:
        """Returns the soil with the given name"""
        soil = next((soil for soil in self.soils if soil.gl_soil.name == name), None)

        if soil is None:
            raise NameError(f"Could not find soil with name {name}")

        return soil
