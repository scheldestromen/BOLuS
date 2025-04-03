from pydantic import BaseModel, model_validator
from enum import StrEnum, auto
from typing import Optional, Self

from toolbox.geometry import CharPointType
from toolbox.geometry import Geometry
from toolbox.geometry import Side
from toolbox.water import HeadLine


class WaterLevelCollection(BaseModel):
    """
    The water levels are defined by a name and a value. The water levels are location dependent.
    For example, the water level at location 1 is different from the water level at location 2.

    Attributes:
        water_levels (dict[str, dict[str, float]]): The first key is the location name, the second key is the water level name
          and the value is the water level value.

          For example:
            {
                'location 1': {
                    'polder level': 1.0,
                    'mean water level': 2.0,
                    'extreme water level T=100': 5.0,
                    'extreme water level T=1000': 6.0
                },
                'location 2': {
                    'polder level': 1.5,
                    'mean water level': 2.5,
                    'extreme water level T=100': 5.5,
                    'extreme water level T=1000': 6.5
                }
            }
    """
    water_levels: dict[str, dict[str, float]]


class WaterLevelVariableCollection(BaseModel):
    """
    The water level sets are the connection between generalized water level variables and the water levels.
    The water levels are defined in a WaterLevelCollection.

    The water levels are generalized in a set of variables, defined by a name. For example the 
    'outer water level' and the 'inner water level'. These generalizedvariables are used in methods for 
    generating waternets. Depending on the waternet scenario, it may be desired to use different
    water levels.
    
    Attributes:
        water_level_variable_sets (dict[str, dict[str, str]]): The first key is the name of water level variable set,
          the second key is the name of the water level variable and the value is the name of the water level.
          
          For example:
            {
                'daily conditions': {
                    'outer water level': 'mean water level',
                    'inner water level': 'polder level'
                },
                'extreme water level T=100': {
                    'outer water level': 'extreme water level T=100',
                    'inner water level': 'polder level'
                },
                'extreme water level T=1000': {
                    'outer water level': 'extreme water level T=1000',
                    'inner water level': 'polder level'
                }
            }
    """
    water_level_variable_sets: dict[str, dict[str, str]]


class WaternetMethodType(StrEnum):
    OFFSETS = auto()


class HeadLineConfig(BaseModel):
    name: str
    is_phreatic: bool
    water_level_set_name: str
    waternet_method: WaternetMethodType
    offset_method: Optional[str] = None


class WaternetScenario(BaseModel):
    name: str
    head_line_configs: list[HeadLineConfig]


class RefLevelType(StrEnum):
    NAP = auto()
    FIXED_LEVEL = auto()
    SURFACE_LEVEL = auto()
    RELATED_TO_OTHER_POINT = auto()  # Dit kan een helling maar ook een offset zijn.


class OffsetType(StrEnum):
    VERTICAL = auto()
    SLOPING = auto()


class WaternetOffsetPoint(BaseModel):
    point_type: CharPointType  # en CustomCharPoint in de toekomst (hoe te combineren?)
    ref_level_type: RefLevelType
    ref_level_name: Optional[str] = None
    offset_type: OffsetType
    offset_value: float

    @model_validator(mode='after')
    def validate_ref_level_name(self) -> Self:
        if self.ref_level_type == RefLevelType.FIXED_LEVEL and self.ref_level_name is None:
            raise ValueError(f"A reference level (water level) needs to be specified when the
                             reference level type is {RefLevelType.FIXED_LEVEL}")

        return self

class WaternetOffsetMethod(BaseModel):
    name_method: str
    offset_points: list[WaternetOffsetPoint]

    def create_head_line(
            self, 
            name_head_line: str,
            is_phreatic: bool,
            geometry: Geometry, 
            ref_levels: dict[str, float]  # key heeft de 'generalized' water level name
        ) -> HeadLine:
        

        # We want to start with the most outward point, so the first point should be the most outward
        # If the outward is in the positive direction, then the first point is inward and we want to reverse the order of the points
        reverse = geometry.char_point_profile.determine_l_direction_sign(Side.WATER_SIDE) == 1  # presence of l-coordinates is also checked

        char_points = [geometry.char_point_profile.get_point_by_type(offset_point.point_type) for offset_point in self.offset_points]
        char_points = sorted(char_points, key=lambda p: p.l, reverse=reverse)

        l: list[float] = []
        z: list[float] = []

        for i, char_point in enumerate(char_points):
            offset_point = next(p for p in self.offset_points if p.point_type == char_point.type)

            if offset_point.ref_level_type == RefLevelType.NAP:
                ref_level = 0.

            elif offset_point.ref_level_type == RefLevelType.FIXED_LEVEL:
                ref_level = ref_levels.get(offset_point.ref_level_name)

                if ref_level is None:
                    raise ValueError(f"Reference level '{offset_point.ref_level_name}' not found when creating the 
                                     waternet '{self.name_method}' in combination with profile '{geometry.name}'")
                
            elif offset_point.ref_level_type == RefLevelType.SURFACE_LEVEL:
                ref_level = char_point.z

            elif offset_point.ref_level_type == RefLevelType.RELATED_TO_OTHER_POINT:
                if i == 0:
                    raise ValueError(f"The head of the first outward point cannot be related to a previous point.
                                     This is the case for the waternet '{self.name_method}'")
                ref_level = char_points[i-1].z
            
            else:
                raise ValueError(f"Invalid reference level type '{offset_point.ref_level_type}'")

            if offset_point.offset_type == OffsetType.VERTICAL:
                z = ref_level + offset_point.offset_value

            elif offset_point.offset_type == OffsetType.SLOPING:
                dist = abs(char_point.l - char_points[i-1].l)
                z = ref_level - offset_point.offset_value * dist

            else:
                raise ValueError(f"Invalid offset type '{offset_point.offset_type}'")

            l.append(char_point.l)
            z.append(z)

        return HeadLine(name=name_head_line, is_phreatic=is_phreatic, l=l, z=z)
