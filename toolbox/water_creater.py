from pydantic import BaseModel, model_validator
from enum import StrEnum, auto
from typing import Optional, Self, Any
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union

from toolbox.geometry import CharPointType, CharPoint
from toolbox.geometry import Geometry
from toolbox.geometry import Side
from toolbox.water import HeadLine, ReferenceLine, Waternet
from toolbox.subsoil import Subsoil
from utils.geometry_utils import get_polygon_top_or_bottom, geometry_to_polygons, offset_line

# TODO: TEMP
import matplotlib.pyplot as plt


# TODO: Idee: Om flexibiliteit te houden - naast het genereren van de waternets - zou ik
#       een WaternetExceptions o.i.d. kunnen maken waarin specifieke correcties zijn opgegeven.
#       Deze correcties kunnen dan worden toegepast op de waternetten.

# TODO: Opgeven van stijghoogte voor TZL verplicht maken indien deze aanwezig is!!

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
    INTRUSION = auto()
    AQUIFER = auto()
    INTERMEDIATE_AQUIFER = auto()


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


# TODO: Eigenlijk zou dit een baseclass moeten zijn, en zou deze subclasses moeten maken, dan kunnen de validaties gedeeltelijk vervallen
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
            raise ValueError(
                f"An offset method needs to be specified when the headline method is {HeadLineMethodType.OFFSETS}")

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
    name_head_line_top: str
    name_head_line_bottom: Optional[str] = None
    ref_line_method_type: RefLineMethodType
    offset_method_name: Optional[str] = None
    intrusion_from_ref_line: Optional[str] = None
    intrusion_length: Optional[float] = None

    @model_validator(mode='after')
    def validate_ref_line_method(self) -> Self:
        if self.ref_line_method_type == RefLineMethodType.OFFSETS and self.offset_method_name is None:
            raise ValueError(
                f"An offset method needs to be specified when the ref line method is {RefLineMethodType.OFFSETS}")

        if self.ref_line_method_type == RefLineMethodType.INTRUSION:
            if self.intrusion_length is None:
                raise ValueError(f"An intrusion length needs to be specified when the reference line "
                                 f"placement method is {RefLineMethodType.INTRUSION}. This is not the case "
                                 f"for the reference line '{self.name_ref_line}'")
            
            if self.intrusion_length == 0:
                raise ValueError(f"The intrusion length cannot be 0 when the reference line "
                                 f"placement method is {RefLineMethodType.INTRUSION}. This is the case "
                                 f"for the reference line '{self.name_ref_line}'")

            if  self.intrusion_from_ref_line is None:
                raise ValueError(f"A reference line needs to be specified when the reference line "
                                 f"placement method is {RefLineMethodType.INTRUSION}. This is not the case "
                                 f"for the reference line '{self.name_ref_line}'")

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
          if there is only a phreatic line.
    """

    name_waternet_scenario: str
    water_level_config: WaterLevelConfig
    head_line_configs: list[HeadLineConfig]
    reference_line_configs: Optional[list[ReferenceLineConfig]] = None  # Optional - if there is only a phreatic line

    @model_validator(mode='after')
    def validate_head_line_assignment(self) -> Self:
        # TODO: 
        return self

    @model_validator(mode='after')
    def validate_max_one_phreatic_line(self) -> Self:
        #  - Zijn alle headlines toegekend aan een reflijn?
        return self

    @model_validator(mode='after')
    def validate_aquifer_types(self) -> Self:
        #  Max één Aquifer en max één IntermediateAquifer
        #  Als er een IntermediateAquifer is, dan moet er ook een Aquifer zijn

        return self


class WaternetConfigCollection(BaseModel):
    waternet_configs: list[WaternetConfig]

    def get_by_name(self, name: str) -> WaternetConfig:
        waternet_config = next((config for config in self.waternet_configs if config.name_waternet_scenario == name),
                               None)

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


class LineOffsetPoint(BaseModel):
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


class LineOffsetMethod(BaseModel):
    name_method: str
    offset_points: list[LineOffsetPoint]

    def _get_reference_level(
            self,
            index: int,
            offset_point: LineOffsetPoint,
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

    def _determine_level(
            self,
            index: int,
            offset_point: LineOffsetPoint,
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

    def create_line(
            self,
            geometry: Geometry,
            ref_levels: dict[str, float]  # key heeft de 'generalized' water level name
    ) -> tuple[list[float], list[float]]:

        # We want to start with the most outward point, so the first point should be the most outward
        # If the outward is in the positive direction, then the first point is inward and we want to reverse the order of the points
        reverse = geometry.char_point_profile.determine_l_direction_sign(
            Side.WATER_SIDE) == 1  # presence of l-coordinates is also checked

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

            head_level = self._determine_level(index=i, offset_point=offset_point, char_points=char_points,
                                               ref_level=ref_level)

            l.append(char_point.l)
            z.append(head_level)

        return l, z


class LineOffsetMethodCollection(BaseModel):
    offset_methods: list[LineOffsetMethod]

    def get_by_name(self, name_method: str) -> LineOffsetMethod:
        offset_method = next((method for method in self.offset_methods if method.name_method == name_method), None)

        if offset_method is None:
            raise ValueError(f"Offset method with name '{name_method}' not found")

        return offset_method


class AquiferType(StrEnum):
    AQUIFER = auto()
    INTERMEDIATE_AQUIFER = auto()


class Aquifer(BaseModel):
    points: list[tuple[float, float]]
    aquifer_type: AquiferType


# TODO wordt niet gebruikt
class GetAquifersFromSubsoil(BaseModel):
    pass
    

def get_aquifers_from_subsoil(subsoil: Subsoil, geometry: Geometry) -> list[Aquifer]:
    # Get the aquifers from the subsoil
    aquifer_polygons: list[Polygon] = []
    soil_polygons = [sp for sp in subsoil.soil_polygons if sp.is_aquifer]
    polygons = [sp.to_shapely() for sp in soil_polygons]

    # unify attached aquifers
    union = unary_union(polygons)
    polygons = geometry_to_polygons(union)
    
    # Get the surface lines bounds and round for comparison purposes
    surf_start, surf_end = sorted((geometry.surface_line.points[0].l, geometry.surface_line.points[-1].l))
    surf_start = round(surf_start, 3)
    surf_end = round(surf_end, 3)
    surface_line_line_string = LineString([(p.l, p.z) for p in geometry.surface_line.points])

    for polygon in polygons:
        # Get aquifer bounds and round for comparison purposes
        aq_l_min, aq_z_min, aq_l_max, aq_z_max = (round(value, 3) for value in polygon.bounds)

        # If the aquifer is defined from start to end, then we can
        # make it an aquifer without further ado
        if surf_start == aq_l_min and surf_end == aq_l_max:
            aquifer_polygons.append(polygon)
            continue

        # If the aquifer is NOT defined from start to end, and does not cross the surface line,
        # then it is not a valid aquifer and an error should be raised

        # TODO: Dit klopt niet. Zijkant kan schuin naar binnen lopen
        #  -> Moet niet surface_line zijn maar volgens mij de omhullende van de subsoil, incl. zijkanten
        intersect = polygon.intersects(surface_line_line_string)
        if not intersect:
            raise ValueError(
                f"An aquifer layer in geometry '{geometry.name}' is not valid. It is not "
                f"defined from the start to the end of the surface line and does not intersect "
                f"with the surface line. Please check your input."
            )
        
        # If there is an intersection, then we have a partial aquifer. For example one that is crossed
        # by the ditch or the canal. In this case we only schematize aquifers that are present underneith
        # the dike. We take the inner crest as a reference point. In case of the ditch, 
        # the aquifer part after the ditch is disregarded.
        l_inner_crest = geometry.char_point_profile.get_point_by_type(CharPointType.DIKE_CREST_LAND_SIDE).l
        check_line = LineString([(l_inner_crest, aq_z_max + 1.), (l_inner_crest, aq_z_min - 1.)])
        intersect = polygon.intersects(check_line)

        if not intersect:
            continue

        aquifer_polygons.append(polygon)

    # Finally, we determine which aquifer is the deepest and assign the aquifer type
    # In case there are multiple with the same depth, both are assigned the type AQUIFER
    aq_z_mins = [polygon.bounds[1] for polygon in aquifer_polygons]
    aq_z_min_indices = [i for i, z in enumerate(aq_z_mins) if z == min(aq_z_mins)]

    aquifers: list[Aquifer] = []

    # Add the remaining aquifers as intermediate aquifers
    for i, polygon in enumerate(aquifer_polygons):
        if i in aq_z_min_indices:
            aq_type = AquiferType.AQUIFER
        else:
            aq_type = AquiferType.INTERMEDIATE_AQUIFER

        polygon_points = [(p[0], p[1]) for p in polygon.exterior.coords[:-1]]  # skip last point
        aquifer = Aquifer(points=polygon_points, aquifer_type=aq_type)
        aquifers.append(aquifer)

    return aquifers


class LineFromAquiferMethod(BaseModel):
    @staticmethod
    def shift_points_with_equal_l_values(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        """D-Stability determines the order of the head line 
        and reference line points based on its own logic, no matter in what order 
        the points are given. Sometimes this does not result in the 
        desired schematization.
        
        This function corrects for this by shifting the points with equal l-values
        a small distance so that the order of the points is always correct."""
        
        # Determine in which direction to shift points
        # if the points are sorted in the positive, then the shift should be negative
        if points[0][0] < points[-1][0]:
            sign = -1
        # if the points are sorted in the negative, then the shift should be positive
        else:
            sign = 1

        for point in points:
            l_coords = [p[0] for p in points]

            if l_coords.count(point[0]) > 1:
                point[0] += sign * 0.001

        return points

    @staticmethod
    def create_lines(
        aquifer: Aquifer,
        ref_line_config: ReferenceLineConfig,
    ) -> tuple[ReferenceLine, ReferenceLine]:
        """Creates reference lines from an aquifer. A reference line 
        is created at the top and bottom of the aquifer."""

        polygon = Polygon(aquifer.points)

        ref_lines: list[ReferenceLine] = []

        for side in ["top", "bottom"]:
            line = get_polygon_top_or_bottom(polygon, side)
            points = [[p[0], p[1]] for p in line.coords]
            points = LineFromAquiferMethod.shift_points_with_equal_l_values(points)

            ref_line = ReferenceLine(
                l=[p[0] for p in points], 
                z=[p[1] for p in points],
                name=ref_line_config.name_ref_line,
                head_line_top=ref_line_config.name_head_line_top,
                head_line_bottom=ref_line_config.name_head_line_bottom
            )
            ref_lines.append(ref_line)

        return ref_lines[0], ref_lines[1]
    
class LineIntrusionMethod(BaseModel):
    @staticmethod
    def get_ref_lines_by_name(name: str, ref_lines: list[ReferenceLine]) -> list[ReferenceLine]:
        ref_lines = [
            rl for rl in ref_lines 
            if rl.name == name
        ]

        if len(ref_lines) == 0:
            raise ValueError(f"The reference line '{name}' does not exist")
        
        return ref_lines
    
    @staticmethod
    def select_appropriate_ref_line(
        intrusion_from_ref_lines: list[ReferenceLine], 
        ref_line_config: ReferenceLineConfig
        ) -> ReferenceLine:
        """Selects the appropriate reference line to apply the intrusion to.
        This is based on the name of the reference line and the direction of the intrusion."""
        
        # If there is one, then we can use that
        if len(intrusion_from_ref_lines) == 1:
            intrusion_from_ref_line = intrusion_from_ref_lines[0]

        # If there are multiple with the same name, then we need to find the one with the lowest and highest z
        else:
            # If positive, then we need to get the ref line with the highest z
            if ref_line_config.intrusion_length > 0:
                ref_z_maxs = [max(rl.z) for rl in intrusion_from_ref_lines]
                i_ref_z_max = ref_z_maxs.index(max(ref_z_maxs))
                intrusion_from_ref_line = intrusion_from_ref_lines[i_ref_z_max]

            # If negative, then we need to get the ref line with the lowest z
            else:
                ref_z_mins = [min(rl.z) for rl in intrusion_from_ref_lines]
                i_ref_z_min = ref_z_mins.index(min(ref_z_mins))
                intrusion_from_ref_line = intrusion_from_ref_lines[i_ref_z_min]

        return intrusion_from_ref_line
	
    @staticmethod
    def create_line(
        current_ref_lines: list[ReferenceLine], 
        ref_line_config: ReferenceLineConfig
        ) -> tuple[list[float], list[float]]:
        """Creates a reference line based on the intrusion from another reference line."""

        intrusion_from_ref_lines = LineIntrusionMethod.get_ref_lines_by_name(
            name=ref_line_config.intrusion_from_ref_line, 
            ref_lines=current_ref_lines
            )

        intrusion_from_ref_line = LineIntrusionMethod.select_appropriate_ref_line(
            intrusion_from_ref_lines, ref_line_config
            )
        
        ref_line_l = intrusion_from_ref_line.l
        ref_line_z = [z + ref_line_config.intrusion_length for z in intrusion_from_ref_line.z]

        return ref_line_l, ref_line_z
    

class WaternetCreator(BaseModel):
    """Factory for creating a single waternet"""

    geometry: Geometry
    waternet_config: WaternetConfig
    water_level_collection: WaterLevelCollection
    offset_method_collection: LineOffsetMethodCollection
    settings: WaternetSettings = WaternetSettings()  # TODO: Wordt nu niet gebruikt - herzien
    subsoil: Optional[Subsoil] = None
    _outward_intersection: Optional[tuple[float, float]] = None
    _inward_intersection: Optional[tuple[float, float]] = None

    @model_validator(mode='after')
    def validate_subsoil(self) -> Self:
        ref_line_configs = self.waternet_config.reference_line_configs

        if ref_line_configs is not None:
            aquifer_methods = [RefLineMethodType.AQUIFER, RefLineMethodType.INTERMEDIATE_AQUIFER]

            if any(config.ref_line_method_type in aquifer_methods 
                for config in ref_line_configs
                ):
                if self.subsoil is None:
                    raise ValueError(
                        "The subsoil is a required input when creating reference lines"
                        "with the method 'AQUIFER' or 'INTERMEDIATE_AQUIFER'."
                    )
            
        return self

    def process_outward_intersection_phreatic_line(self, head_line: HeadLine) -> HeadLine:
        surface_level_outward = self.geometry.char_point_profile.get_point_by_type(
            CharPointType.SURFACE_LEVEL_WATER_SIDE)
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

    def process_inward_intersection_phreatic_line(self, head_line: HeadLine) -> HeadLine:
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

    def apply_minimal_surface_line_offset_to_phreatic_line(
            self,
            head_line: HeadLine,
            offset: float,
            from_char_point_type: CharPointType,
            to_char_point_type: CharPointType
    ) -> HeadLine:
        # TODO: Docstring Aanpassen
        # TODO: wat als één van de charpunten niet bestaat? b.v. teensloot?
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
        phreatic_points = [(phreatic_points[0][0], polygon_bottom)] + phreatic_points + [
            (phreatic_points[-1][0], polygon_bottom)]
        phreatic_polygon = Polygon(phreatic_points)

        # Create a non-correction zone for the ditch, if there is one
        non_correction_zone_ditch = None
        char_point_types = [
            cp.type for cp in self.geometry.char_point_profile.points
            ]

        # Only do it if both ditch starts are present - otherwise the ditch is not well defined
        if CharPointType.DITCH_START_LAND_SIDE in char_point_types and CharPointType.DITCH_START_WATER_SIDE in char_point_types:
            # Get the points
            l_ditch_land_side = self.geometry.char_point_profile.get_point_by_type(
                CharPointType.DITCH_START_LAND_SIDE).l
            l_ditch_water_side = self.geometry.char_point_profile.get_point_by_type(
                CharPointType.DITCH_START_WATER_SIDE).l

            # Determine level phreatic line at the ditch starts
            head_ditch_land_side = next(z for l, z in zip(head_line.l, head_line.z) if l == l_ditch_land_side)
            head_ditch_water_side = next(z for l, z in zip(head_line.l, head_line.z) if l == l_ditch_water_side)

            # Get the min and the max to make it orientation independent
            l_ditch_min = min(l_ditch_land_side, l_ditch_water_side)
            l_ditch_max = max(l_ditch_land_side, l_ditch_water_side)

            # Create a non-correction zone polygon for the ditch
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
        non_correction_zone = bbox.difference(correction_zone)  # -> is either a Polygon or a MultiPolygon

        # If there is a non-correction zone for the ditch, then we merge it with the non-correction zone
        if non_correction_zone_ditch is not None:
            non_correction_zone = unary_union([non_correction_zone, non_correction_zone_ditch])

        # Merge the non-correction zone and the surface line polygon
        correction_polygon = unary_union([non_correction_zone, surface_line_polygon])

        # Determine the intersection of the correction polygon and the phreatic polygon
        phreatic_polygon_corrected = phreatic_polygon.intersection(correction_polygon)

        if isinstance(phreatic_polygon_corrected, Polygon):
            # Extract the coordinates of the corrected phreatic line
            phreatic_line_string = get_polygon_top_or_bottom(phreatic_polygon_corrected, top_or_bottom="top")
        else:
            raise ValueError("Something went wrong when maximizing the phreatic line to the surface level")

        phreatic_points = [(p[0], p[1]) for p in phreatic_line_string.coords]
        head_line.l = [p[0] for p in phreatic_points]
        head_line.z = [p[1] for p in phreatic_points]

        return head_line

    def create_head_lines(self, water_level_set: dict[str, float | None]) -> list[HeadLine]:
        head_lines: list[HeadLine] = []

        for head_line_config in self.waternet_config.head_line_configs:
            # Get the method to create the head line
            if head_line_config.head_line_method_type == HeadLineMethodType.OFFSETS:
                method = self.offset_method_collection.get_by_name(head_line_config.offset_method_name)
            else:
                raise ValueError(f"Invalid headline method type '{head_line_config.head_line_method_type}'")

            # Create the head line
            head_line_l, head_line_z = method.create_line(geometry=self.geometry, ref_levels=water_level_set)
            
            head_line = HeadLine(
                name=head_line_config.name_head_line,
                is_phreatic=head_line_config.is_phreatic,
                l=head_line_l,
                z=head_line_z
            )

            # Add the point where the phreatic line intersects the surface line (if it does)
            if head_line_config.is_phreatic:
                head_line = self.process_outward_intersection_phreatic_line(head_line)
                head_line = self.process_inward_intersection_phreatic_line(head_line)

            # As last - maximize the headline to the surface level if requested
            if head_line_config.is_phreatic and head_line_config.apply_minimal_surface_line_offset:
                head_line = self.apply_minimal_surface_line_offset_to_phreatic_line(
                    head_line=head_line,
                    offset=head_line_config.minimal_surface_line_offset,
                    from_char_point_type=head_line_config.minimal_offset_from_point,
                    to_char_point_type=head_line_config.minimal_offset_to_point
                )

            head_lines.append(head_line)
        
        return head_lines

    def create_ref_lines_aquifers_method(self) -> list[ReferenceLine]:
        ref_lines: list[ReferenceLine] = []
        ref_line_configs = self.waternet_config.reference_line_configs
        
        # Check if there are any aquifer methods - then we need to get the aquifers from the subsoil
        aquifer_conf = next(
            (
                conf for conf in ref_line_configs 
                if conf.ref_line_method_type == RefLineMethodType.AQUIFER
            ), None)
        intermediate_aquifer_conf = next(
            (
                conf for conf in ref_line_configs
                if conf.ref_line_method_type == RefLineMethodType.INTERMEDIATE_AQUIFER
            ), None)

        if aquifer_conf or intermediate_aquifer_conf:
            aquifers = get_aquifers_from_subsoil(self.subsoil, self.geometry)

            # Create the reference lines per aquifer
            for aquifer in aquifers:
                # If there is an intermediate aquifer and a method for it, then use that method
                if aquifer.aquifer_type == AquiferType.INTERMEDIATE_AQUIFER and intermediate_aquifer_conf:
                    config = intermediate_aquifer_conf
                
                # If not, each aquifer is assigned the method AQUIFER
                else:
                    config = aquifer_conf

                # Create the reference lines
                ref_line_top, ref_line_bottom = LineFromAquiferMethod.create_lines(
                    aquifer=aquifer,
                    ref_line_config=config
                )
                ref_lines.extend([ref_line_top, ref_line_bottom])
            
        return ref_lines

    def create_ref_lines_offset_method(self, water_level_set: dict[str, float | None]) -> list[ReferenceLine]:
        ref_lines: list[ReferenceLine] = []
        ref_line_configs = self.waternet_config.reference_line_configs
        
        for ref_line_config in ref_line_configs:
            if ref_line_config.ref_line_method_type == RefLineMethodType.OFFSETS:
                method = self.offset_method_collection.get_by_name(ref_line_config.offset_method_name)

                # Create the reference line
                ref_line_l, ref_line_z = method.create_line(
                    geometry=self.geometry,
                    ref_levels=water_level_set
                )

                ref_line = ReferenceLine(
                    name=ref_line_config.name_ref_line,
                    l=ref_line_l,
                    z=ref_line_z,
                    head_line_top=ref_line_config.name_head_line_top,
                    head_line_bottom=ref_line_config.name_head_line_bottom
                )
                # TODO: Als freatisch, dan corrigeren o.b.v. reflijnen in zandlaag indien aanwezig

                ref_lines.append(ref_line)

        return ref_lines

    def create_ref_lines_intrusion_method(self, current_ref_lines: list[ReferenceLine]) -> list[ReferenceLine]:
        ref_lines: list[ReferenceLine] = []
        ref_line_configs = self.waternet_config.reference_line_configs

        for ref_line_config in ref_line_configs:
            if ref_line_config.ref_line_method_type == RefLineMethodType.INTRUSION:

                # Create the reference line               
                ref_line_l, ref_line_z = LineIntrusionMethod.create_line(
                    current_ref_lines=current_ref_lines,
                    ref_line_config=ref_line_config
                )

                ref_line = ReferenceLine(
                    name=ref_line_config.name_ref_line,
                    l=ref_line_l,
                    z=ref_line_z,
                    head_line_top=ref_line_config.name_head_line_top,
                    head_line_bottom=ref_line_config.name_head_line_bottom
                )

                ref_lines.append(ref_line)

        return ref_lines

    def create_waternet(self) -> Waternet:
        # Get water levels - this is based on the geometry name since water levels are location bound
        location_water_levels = self.water_level_collection.get_by_name(self.geometry.name)

        # Rename the water levels to the generalized water level names
        water_level_set = {
            k: location_water_levels[v]
            for k, v in self.waternet_config.water_level_config.water_levels.items()
            if v is not None
        }

        # Create the head lines
        head_lines = self.create_head_lines(water_level_set=water_level_set)

        # Create the reference lines
        ref_lines: list[ReferenceLine] = []
        ref_lines.extend(self.create_ref_lines_aquifers_method())
        ref_lines.extend(self.create_ref_lines_offset_method(water_level_set=water_level_set))
        ref_lines.extend(self.create_ref_lines_intrusion_method(current_ref_lines=ref_lines))

        return Waternet(head_lines=head_lines, ref_lines=ref_lines)
