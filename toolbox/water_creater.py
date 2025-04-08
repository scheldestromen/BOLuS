from pydantic import BaseModel, model_validator
from dataclasses import field
from enum import StrEnum, auto
from typing import Optional, Self
from shapely.geometry import Polygon
from shapely.ops import unary_union

from toolbox.geometry import CharPointType, CharPoint
from toolbox.geometry import Geometry
from toolbox.geometry import Side
from toolbox.water import HeadLine, ReferenceLine, Waternet


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


class WaternetCreator(BaseModel):
    geometry: Geometry
    waternet_config: WaternetConfig
    water_level_collection: WaterLevelCollection
    headline_offset_method_collection: HeadLineOffsetMethodCollection
    settings: WaternetSettings
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

            head_line.l = [p[0] for p in points]
            head_line.z = [p[1] for p in points]

            # Add intersection point after deletion
            head_line.l.append(self._outward_intersection[0])
            head_line.z.append(self._outward_intersection[1])

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

            head_line.l = [p[0] for p in points]
            head_line.z = [p[1] for p in points]

            # Add intersection point after deletion
            head_line.l.append(self._inward_intersection[0])
            head_line.z.append(self._inward_intersection[1])

        return head_line

    def _maximize_phreatic_line_to_surface_level(self, head_line: HeadLine) -> HeadLine:
        """Maximizes the phreatic line to the surface level.
        
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
        surface_line = self.geometry.surface_line
        surface_line_l = [p.l for p in surface_line.points]
        surface_line_z = [p.z for p in surface_line.points]
        
        # Determine the bottom of the polygon (good as long as it is below every point)
        polygon_bottom = min(surface_line_z + head_line.z) - 1.

        # Make shapely polygon of the surface line
        surf_points = [
            (surface_line_l[0], polygon_bottom),
            *list(zip(surface_line_l, surface_line_z)),
            (surface_line_l[-1], polygon_bottom)
        ]
        surface_line_polygon = Polygon(surf_points)

        # Modify the surface line polygon as a work-around to exclude the ditch
        char_point_types = [cp.type for cp in self.geometry.char_point_profile.points]

        # Only do it if both ditch starts are present - otherwise the ditch is not well defined
        if CharPointType.DITCH_START_LAND_SIDE in char_point_types and CharPointType.DITCH_START_WATER_SIDE in char_point_types:
            # Get the points
            l_ditch_land_side = self.geometry.char_point_profile.get_point_by_type(CharPointType.DITCH_START_LAND_SIDE).l
            l_ditch_water_side = self.geometry.char_point_profile.get_point_by_type(CharPointType.DITCH_START_WATER_SIDE).l

            # Determine level phreatic line at the ditch starts
            head_ditch_land_side = next(z for l, z in zip(head_line.l, head_line.z) if l == l_ditch_land_side)
            head_ditch_water_side = next(z for l, z in zip(head_line.l, head_line.z) if l == l_ditch_water_side)

            # Create a polygon of the ditch
            ditch_points = [
                (l_ditch_land_side, polygon_bottom), 
                (l_ditch_land_side, head_ditch_land_side), 
                (l_ditch_water_side, head_ditch_water_side), 
                (l_ditch_water_side, polygon_bottom),
            ]
            ditch_polygon = Polygon(ditch_points)

            # Make a union of the surface line polygon and the ditch helper-polygon
            surface_line_polygon = unary_union([surface_line_polygon, ditch_polygon])
    
        # Create a polygon of the phreatic line
        phreatic_points = [
            (l, z) for l, z in zip(head_line.l, head_line.z)
            if l not in surface_line_l
        ]
        phreatic_points = [(phreatic_points[0], polygon_bottom)] + phreatic_points + [(phreatic_points[-1], polygon_bottom)]
        phreatic_polygon = Polygon(phreatic_points)
         

        # Determine the part where the correction should be applied
        # First, check if there are free water surfaces (outward and inward)
        if self._outward_intersection is None:
            outward_bound = self.geometry.char_point_profile.get_point_by_type(CharPointType.SURFACE_LEVEL_WATER_SIDE).l
        else:
            outward_bound = self._outward_intersection[0]

        if self._inward_intersection is None:
            inward_bound = self.geometry.char_point_profile.get_point_by_type(CharPointType.SURFACE_LEVEL_LAND_SIDE).l
        else:
            inward_bound = self._inward_intersection[0]
        
        # Make shapely polygon of the surface line
        # TODO: HIER GEBLEVEN

        
        if not phreatic_points:
            return head_line  # No points to correct
        
        # Filter the surface line points that are within the correction range
        # Add points at the boundaries if they don't exist
        surface_points = []
        
        # Add start boundary point if needed
        if start_l not in surface_line_l:
            # Interpolate z value at start_l
            for i in range(len(surface_line_l) - 1):
                if surface_line_l[i] <= start_l <= surface_line_l[i + 1]:
                    ratio = (start_l - surface_line_l[i]) / (surface_line_l[i + 1] - surface_line_l[i])
                    z_start = surface_line_z[i] + ratio * (surface_line_z[i + 1] - surface_line_z[i])
                    surface_points.append((start_l, z_start))
                    break
        
        # Add all surface points within range
        for l, z in zip(surface_line_l, surface_line_z):
            if start_l <= l <= end_l:
                surface_points.append((l, z))
        
        # Add end boundary point if needed
        if end_l not in surface_line_l:
            # Interpolate z value at end_l
            for i in range(len(surface_line_l) - 1):
                if surface_line_l[i] <= end_l <= surface_line_l[i + 1]:
                    ratio = (end_l - surface_line_l[i]) / (surface_line_l[i + 1] - surface_line_l[i])
                    z_end = surface_line_z[i] + ratio * (surface_line_z[i + 1] - surface_line_z[i])
                    surface_points.append((end_l, z_end))
                    break
        
        # Sort points by l-coordinate
        surface_points.sort(key=lambda p: p[0])
        phreatic_points.sort(key=lambda p: p[0])
        
        # Create the corrected phreatic line
        corrected_phreatic_points = []
        
        for l, z in phreatic_points:
            # Find the surface level at this l-coordinate
            surface_z = None
            for i in range(len(surface_points) - 1):
                if surface_points[i][0] <= l <= surface_points[i + 1][0]:
                    ratio = (l - surface_points[i][0]) / (surface_points[i + 1][0] - surface_points[i][0])
                    surface_z = surface_points[i][1] + ratio * (surface_points[i + 1][1] - surface_points[i][1])
                    break
            
            if surface_z is not None:
                # Take the minimum of phreatic line and surface level
                corrected_z = min(z, surface_z)
                corrected_phreatic_points.append((l, corrected_z))
            else:
                corrected_phreatic_points.append((l, z))
        
        # Update the phreatic line with the corrected points
        # First, keep the points outside the correction range
        new_l = [l for l, z in zip(head_line.l, head_line.z) if l < start_l or l > end_l]
        new_z = [z for l, z in zip(head_line.l, head_line.z) if l < start_l or l > end_l]
        
        # Add the corrected points
        for l, z in corrected_phreatic_points:
            new_l.append(l)
            new_z.append(z)
        
        # Sort by l-coordinate
        sorted_points = sorted(zip(new_l, new_z), key=lambda p: p[0])
        head_line.l = [p[0] for p in sorted_points]
        head_line.z = [p[1] for p in sorted_points]
        
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
                method = self.headline_offset_method_collection.get_by_name(head_line_config.head_line_method_name)
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
            if head_line_config.is_phreatic and self.settings.maximize_phreatic_line_to_surface_level:
                head_line = self._maximize_head_line_to_surface_level(head_line)

            head_lines.append(head_line)
    
        # Create the reference lines
        for ref_line_config in self.waternet_config.reference_line_configs:
            pass

        return Waternet(head_lines=head_lines, ref_lines=ref_lines)
