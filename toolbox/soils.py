# Grondsoorten
from typing import Any, List, Optional

from geolib.soils.soil import Soil as GLSoil
from pydantic import BaseModel

from utils.dict_utils import check_for_missing_keys
from utils.list_utils import check_list_of_dicts_for_duplicate_values


class Soil(BaseModel):
    """Represents a soil type.

    It is based on a GEOLib soil type with an added attribute pop for the possibility
    to apply a pre-overburden pressure per soil type.

    Attributes:
        gl_soil: The GEOLib soil object
        pop (float): The Pre-overburden pressure value for the soil
        ocr (float): The over-consolidation ratio (not implemented)
        consolidation_traffic_load (int): Percentage [0 - 100%] of consolidation traffic load
    """

    gl_soil: GLSoil
    pop: Optional[float] = None
    ocr: Optional[float] = None
    consolidation_traffic_load: Optional[int] = None


class SoilCollection(BaseModel):
    """Represents a collection of soil types.

    Attributes:
        name (str): Optional. The name of the soil collection
        soils (list): List of Soil instances
    """

    name: Optional[str] = None
    soils: List[Soil]

    def get_by_name(self, name: str) -> Soil:
        """Returns the soil with the given name"""
        soil = next((soil for soil in self.soils if soil.gl_soil.name == name), None)

        if soil is None:
            raise NameError(f"Could not find soil with name {name}")

        return soil
