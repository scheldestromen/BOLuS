from pydantic import BaseModel, model_validator
from dataclasses import field
from enum import StrEnum, auto
from typing import Optional, Self
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union

from toolbox.geometry import CharPointType, CharPoint
from toolbox.geometry import Geometry
from toolbox.geometry import Side
from toolbox.water import HeadLine, ReferenceLine, Waternet
from utils.geometry_utils import get_polygon_top_side, offset_line

# TODO: TEMP
import matplotlib.pyplot as plt

# TODO: Idee: Om flexibiliteit te houden - naast het genereren van de waternets - zou ik 
#       een WaternetExceptions o.i.d. kunnen maken waarin specifieke correcties zijn opgegeven.
#       Deze correcties kunnen dan worden toegepast op de waternetten.

# TODO: Invoer maken - voor nu standaard op True
class WaternetSettings(BaseModel):
    maximize_phreatic_line_to_surface_level: bool = True

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
    
class RefLineMethodType(StrEnum):
    """
    Enum defining the type of ref line method.
    Currently, only the OFFSETS method is implemented."""

    OFFSETS = auto()
    AQUIFER = auto()
    INTERMEDIATE_AQUIFER = auto()  # At least this is better than 'in-between sand layer'


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
    offset_method_name: Optional[str] = None
    apply_minimal_surface_line_offset: Optional[bool] = None
    minimal_surface_line_offset: Optional[float] = None
    minimal_offset_from_point: Optional[CharPointType] = None
    minimal_offset_to_point: Optional[CharPointType] = None

    @model_validator(mode='after')
    def validate_head_line_method(self) -> Self:
        if self.head_line_method_type == HeadLineMethodType.OFFSETS and self.offset_method_name is None:
            raise ValueError(f"An offset method needs to be specified when the headline method is {HeadLineMethodType.OFFSETS}")

        return self

    @model_validator(mode='after')
    def validate_minimal_surface_line_offset(self) -> Self:
        if self.apply_minimal_surface_line_offset and not self.is_phreatic:
            raise ValueError("A minimal surface line offset can only be applied to a phreatic line")

        if self.apply_minimal_surface_line_offset:
            if self.minimal_surface_line_offset is None:
                raise ValueError("A value for the minimal surface line offset needs to "
                                 "be specified when the apply_minimal_surface_line_offset is True")

            if self.minimal_offset_from_point is None or self.minimal_offset_to_point is None:
                raise ValueError("Two characteristic points need to be specified when "
                                 "applying a minimal offset of the phreatic line from the surface line")
            
        return self

class ReferenceLineConfig(BaseModel):
    name_ref_line: str
    ref_line_method_type: RefLineMethodType
    offset_method_name: Optional[str] = None
    name_head_line_top: str
    name_head_line_bottom: Optional[str] = None

    @model_validator(mode='after')
    def validate_ref_line_method(self) -> Self:
        if self.ref_line_method_type == RefLineMethodType.OFFSETS and self.offset_method_name is None:
            raise ValueError(f"An offset method needs to be specified when the ref line method is {RefLineMethodType.OFFSETS}")

        return self


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
          These are the methods for creating the reference lines. This is optional 
          if there are only phreatic lines.
    """

    name_waternet_scenario: str
    water_level_config: WaterLevelConfig
    head_line_configs: list[HeadLineConfig]
    reference_line_configs: Optional[list[ReferenceLineConfig]] = None  # Optional - if there is only a phreatic line

    @model_validator(mode='after')
    def waternet_config_validator(self) -> Self:
        # TODO: 
        #  - Zijn alle headlines toegekend?

        return self

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

    def _get_reference_level(
        self, 
        index: int,
        offset_point: HeadLineOffsetPoint,
        char_points: list[CharPoint], 
        ref_levels: dict[str, float],
        z: list[float],
        geometry_name: str
        ) -> float:

        if offset_point.ref_level_type == RefLevelType.NAP:
            ref_level = 0.

        elif offset_point.ref_level_type == RefLevelType.FIXED_LEVEL:
            ref_level = ref_levels.get(offset_point.ref_level_name)

            if ref_level is None:
                raise ValueError(f"Reference level '{offset_point.ref_level_name}' not found when creating the " 
                                f"waternet '{self.name_method}' in combination with profile '{geometry_name}'")
            
        elif offset_point.ref_level_type == RefLevelType.SURFACE_LEVEL:
            ref_level = char_points[index].z

        elif offset_point.ref_level_type == RefLevelType.RELATED_TO_OTHER_POINT:
            if index == 0:
                raise ValueError(f"The head of the first outward point cannot be related to a previous point. "
                                f"This is the case for the waternet '{self.name_method}'")
            ref_level = z[-1]
        
        else:
            raise ValueError(f"Invalid reference level type '{offset_point.ref_level_type}'")

        return ref_level

    def _determine_head_level(
            self, 
            index: int, 
            offset_point: HeadLineOffsetPoint, 
            char_points: list[CharPoint], 
            ref_level: float
        ) -> float:

        if offset_point.offset_type == OffsetType.VERTICAL:
            head_level = ref_level + offset_point.offset_value

        elif offset_point.offset_type == OffsetType.SLOPING:
            dist = abs(char_points[index].l - char_points[index - 1].l)
            head_level = ref_level - dist / offset_point.offset_value

        else:
            raise ValueError(f"Invalid offset type '{offset_point.offset_type}'")
            
        return head_level

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

            ref_level = self._get_reference_level(
                index=i,
                offset_point=offset_point,
                char_points=char_points,
                ref_levels=ref_levels,
                z=z,
                geometry_name=geometry.name
            )

            head_level = self._determine_head_level(
                index=i,
                offset_point=offset_point,
                char_points=char_points,
                ref_level=ref_level
            )

            l.append(char_point.l)
            z.append(head_level)

        return HeadLine(name=name_head_line, is_phreatic=is_phreatic, l=l, z=z)


class HeadLineOffsetMethodCollection(BaseModel):
    offset_methods: list[HeadLineOffsetMethod]

    def get_by_name(self, name_method: str) -> HeadLineOffsetMethod:
        offset_method = next((method for method in self.offset_methods if method.name_method == name_method), None)

        if offset_method is None:
            raise ValueError(f"Offset method with name '{name_method}' not found")

        return offset_method


# TODO: Heroverwegen private methods, volgens mij is dat niet nodig
class WaternetCreator(BaseModel):
    geometry: Geometry
    waternet_config: WaternetConfig
    water_level_collection: WaterLevelCollection
    headline_offset_method_collection: HeadLineOffsetMethodCollection
    settings: WaternetSettings = WaternetSettings() # TODO: Invoer maken - voor nu standaard op True
    _outward_intersection: Optional[tuple[float, float]] = None
    _inward_intersection: Optional[tuple[float, float]] = None

    def _process_outward_intersection(self, head_line: HeadLine) -> HeadLine:
        surface_level_outward = self.geometry.char_point_profile.get_point_by_type(CharPointType.SURFACE_LEVEL_WATER_SIDE)
        water_level_outward = next(z for l, z in zip(head_line.l, head_line.z) if l == surface_level_outward.l)
        
        self._outward_intersection = self.geometry.get_intersection(
            level=water_level_outward,  # With the offset method, the first point is the most outward
            from_char_point=CharPointType.DIKE_CREST_WATER_SIDE,
            to_char_point=CharPointType.SURFACE_LEVEL_WATER_SIDE,
            search_direction=Side.WATER_SIDE
        )

        if self._outward_intersection is not None:
            # Delete head line points between the intersection and the first point of the head line
            l_outward = surface_level_outward.l
            l_intersection = self._outward_intersection[0]

            # Two conditions, accounting for two possible geometry orientations
            # The <=/>= is to prevent double points at the intersection
            points = [(l, z) for l, z in zip(head_line.l, head_line.z) 
                           if not (l_intersection <= l < l_outward
                                   or l_intersection >= l > l_outward)]

            points.append(self._outward_intersection)
            points.sort(key=lambda p: p[0])

            head_line.l = [p[0] for p in points]
            head_line.z = [p[1] for p in points]

        return head_line

    def _process_inward_intersection(self, head_line: HeadLine) -> HeadLine:
        surface_level_inward = self.geometry.char_point_profile.get_point_by_type(CharPointType.SURFACE_LEVEL_LAND_SIDE)
        water_level_inward = next(z for l, z in zip(head_line.l, head_line.z) if l == surface_level_inward.l)

        # If there is no free water surface, then we leave the head line as is
        if surface_level_inward.z >= water_level_inward:
            return head_line
        
        # Get the intersection point most inward (LAND_SIDE)
        self._inward_intersection = self.geometry.get_intersection(
            level=water_level_inward,  # With the offset method, the last point is the most inward
            from_char_point=CharPointType.SURFACE_LEVEL_LAND_SIDE,
            to_char_point=CharPointType.DIKE_CREST_LAND_SIDE,
            search_direction=Side.WATER_SIDE
        )

        if self._inward_intersection is not None:
            # Delete head line points between the intersection and the last point of the head line
            l_inward = surface_level_inward.l
            l_intersection = self._inward_intersection[0]

            # Two conditions, accounting for two possible geometry orientations
            # The <=/>= is to prevent double points at the intersection
            points = [(l, z) for l, z in zip(head_line.l, head_line.z) 
                           if not (l_intersection <= l < l_inward
                                   or l_intersection >= l > l_inward)]

            points.append(self._inward_intersection)
            points.sort(key=lambda p: p[0])

            head_line.l = [p[0] for p in points]
            head_line.z = [p[1] for p in points]

        return head_line

    def _apply_minimal_surface_line_offset_to_phreatic_line(
            self, 
            head_line: HeadLine, 
            offset: float,
            from_char_point_type: CharPointType,
            to_char_point_type: CharPointType
        ) -> HeadLine:
        # TODO: Aanpassen
        """Applies a minimal surface line offset to the phreatic line.
        
        If the phreatic line lies above the surface level, then the phreatic line is set 
        to the surface level. This is to prevent an unrealistic phreatic line. However,
        for free water surfaces, this correction should not be and is not applied.

        In case there is a free water surface at both sides of the dike:
          The correction is applied between the intersection points of the free water 
          surface and the surface line.

        In case there is one free water surface:
          The correction is applied between the intersection point of the free water 
          surface and the surface line and with the outer surface line point on the 
          other side of the dike (CharPointType.SURFACE_LEVEL_LAND_SIDE or 
          CharPointType.SURFACE_LEVEL_WATER_SIDE).

        In case there is no free water surface:
          The correction is applied to the whole surface line.

        The correction is never applied to a ditch defined by character points.
        This is also a free water surface.

        How:
          - Create a Shapely Polygon of the surface line in the part to correct.
          - Modify the surface line polygon as a work-around to exclude the ditch 
            (we increase the z-values of the surface line to above the phreatic line)
          - Create a Shapely Polygon of the phreatic line in the part to correct.
          - Determine on which part of the phreatic line the correction should be applied and 
            modify both polygons to include only the part to correct.
          - Determine the intersection (overlapping area) of the two polygons. The top part
            of the intersection is the corrected phreatic line.
        """
       
        # Get the surface line from the geometry
        surface_line_points = [(p.l, p.z) for p in self.geometry.surface_line.points]

        # If there is an offset, then offset the surface line
        if offset != 0.:
            surface_line_string = LineString(surface_line_points)
            surface_line_string_offset = offset_line(
                line=surface_line_string, 
                offset=offset, 
                above_or_below="below"
            )
            surface_line_points = [(p[0], p[1]) for p in surface_line_string_offset.coords]
        
        # Extract the l and z coordinates
        surface_line_l = [p[0] for p in surface_line_points]
        surface_line_z = [p[1] for p in surface_line_points]
        
        # Determine the bounds of the surface line and phreatic line together
        z_min = min(surface_line_z + head_line.z)
        z_max = max(surface_line_z + head_line.z)

        # Determine the bounds of the helper polygons (slightly larger)
        polygon_bottom = z_min - 1.
        polygon_top = z_max + 1.

        # Make shapely polygon of the surface line
        surface_line_points = [
                (surface_line_l[0], polygon_bottom),
                *list(zip(surface_line_l, surface_line_z)),
                (surface_line_l[-1], polygon_bottom)
        ]
        surface_line_polygon = Polygon(surface_line_points)

        # Create a polygon of the phreatic line
        phreatic_points = [(l, z) for l, z in zip(head_line.l, head_line.z)]
        phreatic_points = [(phreatic_points[0][0], polygon_bottom)] + phreatic_points + [(phreatic_points[-1][0], polygon_bottom)]
        phreatic_polygon = Polygon(phreatic_points)

        # Create a non-correction zone for the ditch, if there is one
        non_correction_zone_ditch = None
        char_point_types = [cp.type for cp in self.geometry.char_point_profile.points]

        # Only do it if both ditch starts are present - otherwise the ditch is not well defined
        if CharPointType.DITCH_START_LAND_SIDE in char_point_types and CharPointType.DITCH_START_WATER_SIDE in char_point_types:
            # Get the points
            l_ditch_land_side = self.geometry.char_point_profile.get_point_by_type(CharPointType.DITCH_START_LAND_SIDE).l
            l_ditch_water_side = self.geometry.char_point_profile.get_point_by_type(CharPointType.DITCH_START_WATER_SIDE).l

            # Determine level phreatic line at the ditch starts
            head_ditch_land_side = next(z for l, z in zip(head_line.l, head_line.z) if l == l_ditch_land_side)
            head_ditch_water_side = next(z for l, z in zip(head_line.l, head_line.z) if l == l_ditch_water_side)

            # Get the min and the max to make it orientation independent
            l_ditch_min = min(l_ditch_land_side, l_ditch_water_side)
            l_ditch_max = max(l_ditch_land_side, l_ditch_water_side)

            # Create a non-correction zone polygon for the ditch
            # The +0.001 and -0.001 makes the zone slightly smaller
            # This is to get a proper order of the phreatic points later on
            ditch_points = [
                (l_ditch_min, polygon_bottom), 
                (l_ditch_min, head_ditch_land_side), 
                (l_ditch_max, head_ditch_water_side), 
                (l_ditch_max, polygon_bottom),
            ]
            non_correction_zone_ditch = Polygon(ditch_points)

        # Determine the bounds where the correction should be applied
        # There are two pairs of bounds:
        # - The inputted bounds (from_char_point_type and to_char_point_type)
        # - The bounds determined by the intersection points of the free water surface (if present)

        # We make polygons for both zones and check if there is an overlap
        from_char_point = self.geometry.char_point_profile.get_point_by_type(from_char_point_type).l
        to_char_point = self.geometry.char_point_profile.get_point_by_type(to_char_point_type).l

        # Get the min and the max to make it orientation independent
        l_input_min = min(from_char_point, to_char_point)
        l_input_max = max(from_char_point, to_char_point)

        # Create a polygon of the inputted bounds
        correction_zone_input = Polygon([
            (l_input_min, polygon_bottom),
            (l_input_min, polygon_top),
            (l_input_max, polygon_top),
            (l_input_max, polygon_bottom),
        ])

        # Create a polygon of the bounds determined by the intersection points of the free water surface (if present)
        # If there is no intersection, then the natural bounds are used (outer most points)
        if self._outward_intersection is None:
            outward_bound = self.geometry.char_point_profile.get_point_by_type(CharPointType.SURFACE_LEVEL_WATER_SIDE).l
        else:
            outward_bound = self._outward_intersection[0]

        if self._inward_intersection is None:
            inward_bound = self.geometry.char_point_profile.get_point_by_type(CharPointType.SURFACE_LEVEL_LAND_SIDE).l
        else:
            inward_bound = self._inward_intersection[0]
        
        # Get the min and the max to make it orientation independent
        l_intersection_min = min(outward_bound, inward_bound)
        l_intersection_max = max(outward_bound, inward_bound)

        # Create the correctoin zone polygon for the intersection points with the free water surface
        correction_zone_intersects = Polygon([
            (l_intersection_min, polygon_bottom),
            (l_intersection_min, polygon_top),
            (l_intersection_max, polygon_top),
            (l_intersection_max, polygon_bottom),
        ])

        # Determine the intersection of the two polygons
        correction_zone = correction_zone_input.intersection(correction_zone_intersects)

        # If there is no overlap, then we leave the head line as is
        if not isinstance(correction_zone, Polygon):
            return head_line

        # Create a bounding box of the surface line and phreatic line
        bbox = Polygon([
            (surface_line_l[0], polygon_bottom),
            (surface_line_l[0], polygon_top),
            (surface_line_l[-1], polygon_top),
            (surface_line_l[-1], polygon_bottom),
        ])

        # Create a non-correction zone by subtracting the correction zone from the bounding box
        non_correction_zone = bbox.difference(correction_zone)  # -> is eighter a Polygon or a MultiPolygon

        # If there is a non-correction zone for the ditch, then we merge it with the non-correction zone
        if non_correction_zone_ditch is not None:
            non_correction_zone = unary_union([non_correction_zone, non_correction_zone_ditch])

        # Merge the non-correction zone and the surface line polygon
        correction_polygon = unary_union([non_correction_zone, surface_line_polygon])

        # Determine the intersection of the correction polygon and the phreatic polygon
        phreatic_polygon_corrected = phreatic_polygon.intersection(correction_polygon)

        if isinstance(phreatic_polygon_corrected, Polygon):
            # Extract the coordinates of the corrected phreatic line
            phreatic_line_string = get_polygon_top_side(phreatic_polygon_corrected)
        else:
            raise ValueError("Something went wrong when maximizing the phreatic line to the surface level")
        
        phreatic_points = [(p[0], p[1]) for p in phreatic_line_string.coords]
        head_line.l = [p[0] for p in phreatic_points]
        head_line.z = [p[1] for p in phreatic_points]

        return head_line

    def create_waternet(self) -> Waternet:
        head_lines: list[HeadLine] = []
        ref_lines: list[ReferenceLine] = []

        # Get water levels - this is based on the geometry name since water levels are location bound
        location_water_levels = self.water_level_collection.get_by_name(self.geometry.name)
        water_level_set = {
            k: location_water_levels[v] 
            for k, v in self.waternet_config.water_level_config.water_levels.items()
            if v is not None
        }
        
        for head_line_config in self.waternet_config.head_line_configs:
            # Get the method to create the head line
            if head_line_config.head_line_method_type == HeadLineMethodType.OFFSETS:
                method = self.headline_offset_method_collection.get_by_name(head_line_config.offset_method_name)
            else:
                raise ValueError(f"Invalid headline method type '{head_line_config.head_line_method_type}'")
            
            # Create the head line
            head_line = method.create_head_line(
                name_head_line=head_line_config.name_head_line,
                is_phreatic=head_line_config.is_phreatic,
                geometry=self.geometry,
                ref_levels=water_level_set
            )

            # Add the point where the phreatic line intersects the outer slope (if so)
            if head_line_config.is_phreatic:
                head_line = self._process_outward_intersection(head_line)
                head_line = self._process_inward_intersection(head_line)
            
            # As last - maximize the headline to the surface level if requested
            if head_line_config.is_phreatic and head_line_config.apply_minimal_surface_line_offset:
                head_line = self._apply_minimal_surface_line_offset_to_phreatic_line(
                    head_line=head_line, 
                    offset=head_line_config.minimal_surface_line_offset,
                    from_char_point_type=head_line_config.minimal_offset_from_point, 
                    to_char_point_type=head_line_config.minimal_offset_to_point
                )

            head_lines.append(head_line)
    
        # Create the reference lines 
        for ref_line_config in self.waternet_config.reference_line_configs:
            pass

        return Waternet(head_lines=head_lines, ref_lines=ref_lines)
