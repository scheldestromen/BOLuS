from enum import StrEnum, auto
from typing import Optional
from pydantic import BaseModel, model_validator
import numpy as np

from utils.geometry_utils import linear_interpolation


class WaterLineType(StrEnum):
    HEADLINE = auto()
    REFERENCE_LINE = auto()


class WaterLine(BaseModel):
    """Base class for HeadLine and ReferenceLine

    The l-coordinates should be monotonically increasing, decreasing 
    or equal.
    
    Attributes:
        name (str): Name (label) of the line
        l (list[float]): List of floats for the l-coordinates
        z (list[float]): List of floats for the z-coordinates
    """

    name: str
    l: list[float]
    z: list[float]

    @model_validator(mode="after")
    def validate_equal_length_l_z(self):
        if len(self.l) != len(self.z):
            raise ValueError(
                f"l and z must have the same length. This is not the case for line {self.name} "
                f"with l-length {len(self.l)} and z-length {len(self.z)}."
                )
        
        return self

    @model_validator(mode="after")
    def validate_monotonic(self):
        """Validate if points are ordered. This is not strictly necessary for 
        D-Stability and is meant as a sanity check."""

        if not np.all(np.diff(self.l) >= 0) and not np.all(np.diff(self.l) <= 0):
            raise ValueError(
                f"Not all the l-coordinates of water line {self.name} of type {type(self)} "
                f"are monotonically increasing or decreasing. Equal values are allowed. "
                f"The l-coordinates are: {self.l}\n"
                f"The z-coordinates are: {self.z}"
            )
        
        return self

    def get_z_at_l(self, l: float) -> float:
        """Returns the z-coordinate at a given l-coordinate
        based on interpolation of the l and z coordinates.

        The l-coordinates must be monotonically increasing or decreasing.
        Equal values are NOT allowed.
        
        Args:
            l (float): The l-coordinate
            
        Returns:
            float: The interpolated z-coordinate at the given l-coordinate
            
        Raises:
            ValueError: If l is outside the range of l-coordinates.

        """

        return linear_interpolation(x=l, xp=self.l, fp=self.z)


class HeadLine(WaterLine):
    """Represents a headline
    
    Inherits all attributes from WaterLine.

    Attributes:
        is_phreatic (bool): Indicates if the headline is the phreatic line
    """

    is_phreatic: bool


class ReferenceLine(WaterLine):
    """Represents a reference line. Headlines can be assigned to it.
    
    Inherits all attributes from WaterLine.

    Attributes:
        head_line_top (str, optional): Head at top of reference line is based on the headline with this name
        head_line_bottom (str, optional): Head at bottom of reference line is based on the headline with this name
    """

    head_line_top: Optional[str] = None
    head_line_bottom: Optional[str] = None


class Waternet(BaseModel):
    """Represents the waternet for a stage in a D-Stability calculation

    Attributes:
        head_lines (list[HeadLine]): List of HeadLine
        ref_lines (list[ReferenceLine]): List of ReferenceLine
    """

    head_lines: list[HeadLine]
    ref_lines: list[ReferenceLine]


# TODO: Omschrijven naar WaternetExceptionCollection - en toevoegen WaternetException/HeadLineException/ReferenceLineException ?
# class WaternetCollection(BaseModel):
#     waternets: list[Waternet]

#     def get_waternet(
#         self, calc_name: str, scenario_name: str, stage_name: str
#     ) -> Waternet:
#         """Returns the waternet with the given calc_name, scenario_name and stage_name

#         Args:
#             calc_name: The name of the calculation
#             scenario_name: The name of the scenario
#             stage_name: The name of the stage

#         Returns:
#             The waternet with the given calc_name, scenario_name and stage_name"""

#         waternet = next(
#             (
#                 waternet
#                 for waternet in self.waternets
#                 if waternet.calc_name == calc_name
#                 and waternet.scenario_name == scenario_name
#                 and waternet.stage_name == stage_name
#             ),
#             None,
#         )
#         if waternet:
#             return waternet

#         raise ValueError(
#             f"Could not find waternet with calc_name {calc_name}, scenario_name {scenario_name} "
#             f"and stage_name {stage_name}"
#         )
