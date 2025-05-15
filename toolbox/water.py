from enum import StrEnum, auto
from typing import Optional
from pydantic import BaseModel, model_validator


class WaterLineType(StrEnum):
    HEADLINE = auto()
    REFERENCE_LINE = auto()


class WaterLine(BaseModel):
    """Base class for HeadLine and ReferenceLine

    l and z are automatically sorted by the values in l.
    
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
                f"l and z must have the same length. This is not the case for line {self.name}."
                )
        
        return self

    @model_validator(mode="after")
    def validate_order(self):
        if self.l != sorted(self.l):
            # Create pairs of (l, z), sort by l, and unpack back into separate lists
            coords = sorted(zip(self.l, self.z), key=lambda p: p[0])
            l_coords, z_coords = zip(*coords)
            self.l = list(l_coords)
            self.z = list(z_coords)
        
        return self
    
    def get_z_at_l(self, l: float) -> float:
        """Returns the z-coordinate at a given l-coordinate
        based on interpolation of the l and z coordinates.
        
        Args:
            l (float): The l-coordinate
            
        Returns:
            float: The interpolated z-coordinate at the given l-coordinate
            
        Raises:
            ValueError: If l is outside the range of l-coordinates
        """
        
        # Check if l is within range
        if l < min(self.l) or l > max(self.l):
            raise ValueError(
                f"l-coordinate {l} is outside the range of l-coordinates [{min(self.l)}, {max(self.l)}] "
                f"for WaterLine {self.name}"
                )
        
        # If l exactly matches a point, return that point's z-coordinate
        if l in self.l:
            return self.z[self.l.index(l)]

        # Find the index of the segment that contains l
        # Since l-coordinates are sorted, we can find the right segment easily
        for i in range(len(self.l) - 1):
            if self.l[i] < l < self.l[i + 1]:
                # Linear interpolation formula: z = z1 + (z2 - z1) * (l - l1) / (l2 - l1)
                l1, l2 = self.l[i], self.l[i + 1]
                z1, z2 = self.z[i], self.z[i + 1]
                
                # Handle case where l1 and l2 are the same (avoid division by zero)
                if l1 == l2:
                    return z1
                
                # Perform linear interpolation
                return z1 + (z2 - z1) * (l - l1) / (l2 - l1)
        
        # In case no segment is found, raise an error (could be if the coords are altered after initialization)
        raise ValueError(
            f"Could not interpolate z at l-coordinate {l} for WaterLine {self.name}"
            )


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
