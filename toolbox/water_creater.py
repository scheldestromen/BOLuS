from pydantic import BaseModel, model_validator
from dataclasses import field
from enum import StrEnum, auto
from typing import Optional, Self

from toolbox.geometry import CharPointType, CharPoint
from toolbox.geometry import Geometry
from toolbox.geometry import Side
from toolbox.water import HeadLine, ReferenceLine, Waternet


# TODO: Idee: Om flexibiliteit te houden - naast het genereren van de waternets - zou ik 
#       een WaternetExceptions o.i.d. kunnen maken waarin specifieke correcties zijn opgegeven.
#       Deze correcties kunnen dan worden toegepast op de waternetten.


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
                    'extreme water level': 5.0,
                },
                'location 2': {
                    'polder level': 1.5,
                    'mean water level': 2.5,
                    'extreme water level': 5.5,
                }
            }"""
    
    water_levels: dict[str, dict[str, float | None]]

    def get_by_name(self, name: str) -> dict[str, float | None]:
        water_level_dict = self.water_levels.get(name)

        if water_level_dict is None:
            raise ValueError(f"Water level with name '{name}' not found")

        return water_level_dict


class HeadLineMethodType(StrEnum):
    """
    Enum defining the type of headline method.
    Currently, only the OFFSETS method is implemented."""	

    OFFSETS = auto()


class WaterLevelConfig(BaseModel):
    """
    A WaterLevelConfig is the connection between the generalized water level variables
    used in the head_line_configs and the names of the actual water levels that should 
    be used, as they are defined in the WaterLevelCollection.

    For example:
        Two generalized water level variables could be defined: 
        - 'outer water level' 
        - 'inner water level'

        The waternet scenario 'daily conditions' could use two water levels:
        - 'mean water level'
        - 'polder level'

        The WaterLevelConfig could be defined as follows:

            WaterLevelConfig(
                name_waternet_scenario='daily conditions',
                water_levels={
                    'outer water level': 'mean water level',
                    'inner water level': 'polder level'
                }
            )"""

    name_waternet_scenario: str
    water_levels: dict[str, str | None]


class HeadLineConfig(BaseModel):
    name_head_line: str
    is_phreatic: bool
    head_line_method_type: HeadLineMethodType = HeadLineMethodType.OFFSETS
    head_line_method_name: Optional[str] = None

    @model_validator(mode='after')
    def validate_head_line_method(self) -> Self:
        if self.head_line_method_type == HeadLineMethodType.OFFSETS and self.head_line_method_name is None:
            raise ValueError(f"An offset method needs to be specified when the headline method is {HeadLineMethodType.OFFSETS}")

        return self
    
class ReferenceLineConfig(BaseModel):
    pass


class WaternetConfig(BaseModel):
    """A WaternetConfig is the blueprint for creating a waternet.
    
    Attributes:
        name (str): The name of the waternet configuration
        water_level_config (WaterLevelConfig): The water level configuration. 
          This is the connection between the water levels used in the waternet and
          the generalized water level variables used in the head_line_configs.
        head_line_configs (list[HeadLineConfig]): The head line configurations.
          These are the methods for creating the head lines.
        reference_line_configs (list[ReferenceLineConfig]): The reference line configurations.
          These are the methods for creating the reference lines.
    """

    name_waternet_scenario: str
    water_level_config: WaterLevelConfig
    head_line_configs: list[HeadLineConfig]
    reference_line_configs: list[ReferenceLineConfig] = field(default_factory=list)  # TODO: vervangen na implementatie


class WaternetConfigCollection(BaseModel):
    waternet_configs: list[WaternetConfig]

    def get_by_name(self, name: str) -> WaternetConfig:
        waternet_config = next((config for config in self.waternet_configs if config.name_waternet_scenario == name), None)
    
        if waternet_config is None:
            raise ValueError(f"Waternet config with name '{name}' not found")

        return waternet_config


class RefLevelType(StrEnum):
    NAP = auto()
    FIXED_LEVEL = auto()
    SURFACE_LEVEL = auto()
    RELATED_TO_OTHER_POINT = auto()  # Dit kan een helling maar ook een offset zijn.


class OffsetType(StrEnum):
    VERTICAL = auto()
    SLOPING = auto()


class HeadLineOffsetPoint(BaseModel):
    char_point_type: CharPointType  # en CustomCharPoint in de toekomst (hoe te combineren?)
    ref_level_type: RefLevelType
    ref_level_name: Optional[str] = None
    offset_type: OffsetType
    offset_value: float

    @model_validator(mode='after')
    def validate_ref_level_name(self) -> Self:
        if self.ref_level_type == RefLevelType.FIXED_LEVEL and self.ref_level_name is None:
            raise ValueError(f"A reference level (water level) needs to be specified when the"
                             f"reference level type is {RefLevelType.FIXED_LEVEL}")

        return self


class HeadLineOffsetMethod(BaseModel):
    name_method: str
    offset_points: list[HeadLineOffsetPoint]

    # TODO: Refactor
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

        char_points: list[CharPoint] = []

        for offset_point in self.offset_points:
            try:
                char_point = geometry.char_point_profile.get_point_by_type(offset_point.char_point_type)
                char_points.append(char_point)

            # If the character point is not present, skip it
            except ValueError:
                continue

        char_points = sorted(char_points, key=lambda p: p.l, reverse=reverse)

        l: list[float] = []
        z: list[float] = []

        for i, char_point in enumerate(char_points):
            offset_point = next(p for p in self.offset_points if p.char_point_type == char_point.type)

            if offset_point.ref_level_type == RefLevelType.NAP:
                ref_level = 0.

            elif offset_point.ref_level_type == RefLevelType.FIXED_LEVEL:
                ref_level = ref_levels.get(offset_point.ref_level_name)

                if ref_level is None:
                    raise ValueError(f"Reference level '{offset_point.ref_level_name}' not found when creating the " 
                                     f"waternet '{self.name_method}' in combination with profile '{geometry.name}'")
                
            elif offset_point.ref_level_type == RefLevelType.SURFACE_LEVEL:
                ref_level = char_point.z

            elif offset_point.ref_level_type == RefLevelType.RELATED_TO_OTHER_POINT:
                if i == 0:
                    raise ValueError(f"The head of the first outward point cannot be related to a previous point. "
                                     f"This is the case for the waternet '{self.name_method}'")
                ref_level = z[-1]
            
            else:
                raise ValueError(f"Invalid reference level type '{offset_point.ref_level_type}'")

            if offset_point.offset_type == OffsetType.VERTICAL:
                z_i = ref_level + offset_point.offset_value

            elif offset_point.offset_type == OffsetType.SLOPING:
                dist = abs(char_point.l - char_points[i-1].l)
                z_i = ref_level - dist / offset_point.offset_value

            else:
                raise ValueError(f"Invalid offset type '{offset_point.offset_type}'")

            l.append(char_point.l)
            z.append(z_i)

        return HeadLine(name=name_head_line, is_phreatic=is_phreatic, l=l, z=z)


class HeadLineOffsetMethodCollection(BaseModel):
    offset_methods: list[HeadLineOffsetMethod]

    def get_by_name(self, name_method: str) -> HeadLineOffsetMethod:
        offset_method = next((method for method in self.offset_methods if method.name_method == name_method), None)

        if offset_method is None:
            raise ValueError(f"Offset method with name '{name_method}' not found")

        return offset_method


def create_waternet(
        geometry: Geometry,
        waternet_config: WaternetConfig,
        water_level_collection: WaterLevelCollection,
        headline_offset_method_collection: HeadLineOffsetMethodCollection,
    ) -> Waternet:

    head_lines: list[HeadLine] = []
    ref_lines: list[ReferenceLine] = []

    # Get water levels - this is based on the geometry name since water levels are location bound
    location_water_levels = water_level_collection.get_by_name(geometry.name)
    water_level_set = {
        k: location_water_levels[v] 
        for k, v in waternet_config.water_level_config.water_levels.items() 
        if v is not None
    }
    
    for head_line_config in waternet_config.head_line_configs:
        if head_line_config.head_line_method_type == HeadLineMethodType.OFFSETS:
            method = headline_offset_method_collection.get_by_name(head_line_config.head_line_method_name)
        else:
            raise ValueError(f"Invalid headline method type '{head_line_config.head_line_method_type}'")
        
        head_line = method.create_head_line(
            name_head_line=head_line_config.name_head_line,
            is_phreatic=head_line_config.is_phreatic,
            geometry=geometry,
            ref_levels=water_level_set
        )

        if head_line_config.is_phreatic:
            intersection = geometry.get_intersection(
                level=head_line.z[0],  # With the offset method, the first point is the most outward
                from_char_point=CharPointType.DIKE_CREST_WATER_SIDE,
                to_char_point=CharPointType.SURFACE_LEVEL_WATER_SIDE,
                search_direction=Side.WATER_SIDE
            )
            if intersection is not None:
                head_line.l.append(intersection[0])
                head_line.z.append(intersection[1])
        
        head_lines.append(head_line)
    
    for ref_line_config in waternet_config.reference_line_configs:
        pass

    return Waternet(head_lines=head_lines, ref_lines=ref_lines)
