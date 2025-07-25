from typing import Optional, Self

from geolib.soils.soil import Soil as GLSoil
from geolib.models.dstability.internal import PersistableShadingTypeEnum
from pydantic import BaseModel, model_validator

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
        color (str): The color of the soil. The color must contain the opacity such that the format is #AARRGGBB in which 
          AA is the opacity.
        pattern (PersistableShadingTypeEnum): The pattern of the soil
    """

    gl_soil: GLSoil
    pop_mean: Optional[float] = None
    pop_std: Optional[float] = None
    probabilistic_pop: Optional[bool] = None
    ocr: Optional[float] = None
    consolidation_traffic_load: Optional[int] = None
    color: Optional[str] = None
    pattern: Optional[PersistableShadingTypeEnum] = None

    @model_validator(mode="after")
    def required_fields(self) -> Self:
        if self.pop_mean is not None and self.probabilistic_pop is None:
            self.probabilistic_pop = False
            
        if self.probabilistic_pop is True and self.pop_std is None:
            raise ValueError("pop_std must be provided if probabilistic_pop is True")
        
        return self


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
