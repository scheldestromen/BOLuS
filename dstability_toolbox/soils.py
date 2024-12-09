# Grondsoorten
from typing import Optional, List

from pydantic import BaseModel
from pydantic.color import Color

from geolib.soils.soil import Soil as GLSoil
from geolib.soils.soil import ShearStrengthModelTypePhreaticLevel


from utils.dict_utils import check_for_missing_keys
from utils.list_utils import check_list_of_dicts_for_duplicate_values


class Soil(BaseModel):
    """Represents a soil type.

    It is based on a GEOLib soil type with an added attribute pop for the possibility
    to apply a pre-overburden pressure per soil type.

    Attributes:
        dm_soil: The DStabilityModel soil object
        pop: The Pre-overburden pressure value for the soil"""
    dm_soil: GLSoil
    pop: Optional[float]


class SoilCollection(BaseModel):
    """Represents a collection of soil types."""
    name: Optional[str] = None
    soils: List[Soil]

    @classmethod
    def from_list(cls, soil_list: list[dict]):
        """Initiates a SoilCollection from a list of soil dictionaries.

        Each dict should have keys:
          name: str
          unsaturated_weight: float
          saturated_weight: float
          strength_model_above: Literal["Shansep", "Mohr-Coulomb", "Su Table"]
          strength_model_below: Literal["Shansep", "Mohr-Coulomb", "Su Table"]
          c: float
          phi: float
          shear_stress_ratio_s: float
          strength_exponent_m: float
          color: str (hex, without #)
          pop: float

        Args:
            soil_list: list of dictionaries with the soil properties
         """
        req_keys = ["name", "unsaturated_weight", "saturated_weight", "strength_model_above",
                    "strength_model_below", "c", "phi", "shear_stress_ratio_s", "strength_exponent_m",
                    "color", "pop"]

        strength_model = {
            "Shansep": ShearStrengthModelTypePhreaticLevel.SHANSEP,
            "Mohr-Coulomb": ShearStrengthModelTypePhreaticLevel.MOHR_COULOMB,
            "Su Table": ShearStrengthModelTypePhreaticLevel.SUTABLE
        }

        soils = []

        # Check that soil names are unique
        check_list_of_dicts_for_duplicate_values(soil_list, "name")

        for soil_dict in soil_list:
            # Check that all the required keys are present
            check_for_missing_keys(soil_dict, req_keys)

            gl_soil = GLSoil()
            gl_soil.name = soil_dict["name"]
            gl_soil.code = soil_dict["name"]
            gl_soil.soil_weight_parameters.unsaturated_weight = soil_dict["unsaturated_weight"]
            gl_soil.soil_weight_parameters.saturated_weight = soil_dict["saturated_weight"]
            gl_soil.shear_strength_model_above_phreatic_level = strength_model[soil_dict["strength_model_above"]]
            gl_soil.shear_strength_model_below_phreatic_level = strength_model[soil_dict["strength_model_below"]]
            gl_soil.mohr_coulomb_parameters.cohesion.mean = soil_dict["c"]
            gl_soil.mohr_coulomb_parameters.friction_angle.mean = soil_dict["phi"]
            gl_soil.undrained_parameters.shear_strength_ratio.mean = soil_dict["shear_stress_ratio_s"]
            gl_soil.undrained_parameters.strength_increase_exponent.mean = soil_dict["strength_exponent_m"]

            if soil_dict["color"] is not None:
                gl_soil.color = soil_dict["color"]

            soil = Soil(dm_soil=gl_soil, pop=soil_dict["pop"])
            soils.append(soil)

        return cls(soils=soils)
