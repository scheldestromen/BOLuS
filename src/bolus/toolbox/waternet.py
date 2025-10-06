from enum import StrEnum, auto
from typing import Optional, Self
from pydantic import BaseModel, model_validator
import numpy as np

from bolus.utils.geometry_utils import linear_interpolation


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

    @classmethod
    def from_list(cls, name: str, point_list: list[float]) -> Self:
        """Instantiates a WaterLine from a flat list of points

        Args:
            name: The name of the SurfaceLine
            point_list: A flat list of points [l1, z1, l2, z2, ...]"""

        l = point_list[0::2]
        z = point_list[1::2]

        if not len(l) == len(z):
            raise ValueError(
                f"An incorrect number of points is given for the water line with"
                f"name {name}. The length of `point_list` should be dividable by "
                f"two so that every point has a l and z coordinate."
            )

        return cls(name=name, l=l, z=z)


class WaterLineCollection(BaseModel):
    water_lines: list[WaterLine]

    def get_by_name(self, name: str) -> WaterLine:
        """Returns the waterline with the given name

        Args:
            name: The name of the waterline

        Returns:
            The water line with the given name"""

        water_line = next(
            (water_line for water_line in self.water_lines if water_line.name == name),
            None,
        )

        if water_line:
            return water_line
 
        raise ValueError(f"Could not find water line with name '{name}'")


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
