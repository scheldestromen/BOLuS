from pydantic import BaseModel, model_validator
from enum import StrEnum, auto
from typing import Optional, Self, Literal
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union

from toolbox.geometry import CharPointType, CharPoint
from toolbox.geometry import Geometry
from toolbox.geometry import Side
from toolbox.water import HeadLine, ReferenceLine, Waternet
from toolbox.subsoil import Subsoil
from utils.geometry_utils import get_polygon_top_or_bottom, geometry_to_polygons, offset_line

# TODO: Idee: Om flexibiliteit te houden - naast het genereren van de waternets - zou ik
#       een WaternetExceptions o.i.d. kunnen maken waarin specifieke correcties zijn opgegeven.
#       Deze correcties kunnen dan worden toegepast op de waternetten.

# TODO: Opgeven van stijghoogte voor TZL verplicht maken indien deze aanwezig is!!
#       Dit i.v.m. dubbelingen in de naam van de reflijnen. (belangrijk voor indrigingslengte)

# TODO: Refactor ter bevordering van de leesbaarheid en herleidbaarheid
#       - Opknippen in waternet_config en waternet_creator.
#       - water.py hernoemen naar waternet.py
#       - methodes in mapje zetten, splitsen in scripts?

NAME_DEEP_AQUIFER = "WVP"
NAME_INTERMEDIATE_AQUIFER = "TZL"

TOP_BOTTOM_TO_DUTCH = {
    "top": "boven",
    "bottom": "onder",
}


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
    Enum defining the type of ref line method."""

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


# TODO: Eigenlijk zou dit een baseclass moeten zijn, en zou deze subclasses moeten maken, dan kunnen de validaties gedeeltelijk vervallen
#       (nice-to-have)
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
    def validate_unique_names(self) -> Self:
        names = [config.name_head_line for config in self.head_line_configs]
        if len(names) != len(set(names)):
            raise ValueError("There can only be one head line with the same name. This is not the case for the waternet scenario "
                             f"'{self.name_waternet_scenario}'")
        
        if self.reference_line_configs is not None:
            names = [config.name_ref_line for config in self.reference_line_configs]
            if len(names) != len(set(names)):
                raise ValueError("There can only be one reference line with the same name. This is not the case for the waternet scenario "
                                 f"'{self.name_waternet_scenario}'")

        return self
    
    @model_validator(mode='after')
    def validate_head_line_assignment(self) -> Self:
        head_lines_configs = [hlc.name_head_line for hlc in self.head_line_configs if not hlc.is_phreatic]

        if self.reference_line_configs is not None:
            assigned_head_line_names = [config.name_head_line_top for config in self.reference_line_configs]
            assigned_head_line_names.extend([config.name_head_line_bottom for config in self.reference_line_configs])
        else:
            assigned_head_line_names = []

        non_assigned_head_line_names = set(head_lines_configs) - set(assigned_head_line_names)

        if len(non_assigned_head_line_names) > 0:
            raise ValueError("There are head lines that are not assigned to a reference line. "
                             f"This is the case for the head lines '{', '.join(non_assigned_head_line_names)}' "
                             f"in the waternet scenario '{self.name_waternet_scenario}'")
        
        return self

    @model_validator(mode='after')
    def validate_max_one_phreatic_line(self) -> Self:
        phreatic_lines = [config for config in self.head_line_configs if config.is_phreatic]

        if len(phreatic_lines) > 1:
            raise ValueError("There can only be one phreatic line. This is not the case for the waternet scenario "
                             f"'{self.name_waternet_scenario}'")

        return self
    
    @model_validator(mode='after')
    def validate_single_intrusion_ref_line_per_ref_line(self) -> Self:
        """Checks if there is only one intrusion reference line per reference line
        based on the name of the ReferenceLineConfig.

        An exception is however when the related reference line is modelled using the 
        aquifer method. In that case two reference lines are made using one 
        ReferenceLineConfig. In that case two intrusion reference lines are allowed, 
        one below the aquifer and one above the aquifer (one for every aquifer ref. line).
        """

        if self.reference_line_configs is None:
            return self
        
        intrusion_from_ref_line_names = [config.intrusion_from_ref_line for config in self.reference_line_configs
                                         if config.ref_line_method_type == RefLineMethodType.INTRUSION]

        # Get duplicate names
        duplicate_names = set([name for name in intrusion_from_ref_line_names 
                               if intrusion_from_ref_line_names.count(name) > 1])

        for dup_name in duplicate_names:
            configs = [config for config in self.reference_line_configs 
                       if config.intrusion_from_ref_line == dup_name]

            if len(configs) == 2:
                from_ref_line_config = next(
                    conf for conf in self.reference_line_configs 
                    if conf.name_ref_line == configs[0].intrusion_from_ref_line
                    )
                from_ref_line_is_aquifer = (from_ref_line_config.ref_line_method_type == RefLineMethodType.AQUIFER
                                            or from_ref_line_config.ref_line_method_type == RefLineMethodType.INTERMEDIATE_AQUIFER)
                intrusion_opposite_direction = configs[0].intrusion_length * configs[1].intrusion_length < 0

                if from_ref_line_is_aquifer and intrusion_opposite_direction:
                    continue

                raise ValueError(
                    "There can only be one intrusion ref. line per ref. line. "
                    f"This is not the case for the waternet scenario '{self.name_waternet_scenario}' "
                    f"and the reference line '{configs[0].name_ref_line}'")

        return self
    
    @model_validator(mode='after')
    def validate_aquifer_types(self) -> Self:
        ref_line_aquifer = [config for config in self.reference_line_configs 
                            if config.ref_line_method_type == RefLineMethodType.AQUIFER]
        ref_line_intermediate_aquifer = [config for config in self.reference_line_configs 
                                        if config.ref_line_method_type == RefLineMethodType.INTERMEDIATE_AQUIFER]
        
        if len(ref_line_aquifer) > 1:
            raise ValueError("There can only be one aquifer ref. line. This is not the case for the waternet scenario "
                             f"'{self.name_waternet_scenario}'")
        
        if len(ref_line_intermediate_aquifer) > 1:
            raise ValueError("There can only be one intermediate aquifer ref. line. This is not the case for the waternet scenario "
                             f"'{self.name_waternet_scenario}'")

        if len(ref_line_intermediate_aquifer) == 1 and len(ref_line_aquifer) == 0:
            raise ValueError("There must be an aquifer ref. line when there is an intermediate aquifer ref. line. "
                             f"This is not the case for the waternet scenario '{self.name_waternet_scenario}'")

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

            # For a non-zero offset slope, the head level is determined by the offset slope
            if offset_point.offset_value != 0:
                head_level = ref_level - dist / offset_point.offset_value
            # When the offset slope is 0, the head level is the same as the reference level
            else:
                head_level = ref_level

        else:
            raise ValueError(f"Invalid offset type '{offset_point.offset_type}'")

        return head_level

    @staticmethod
    def _add_outer_points_if_needed(
        head_line_l: list[float], 
        head_line_z: list[float], 
        geometry: Geometry
        ) -> tuple[list[float], list[float]]:
        """For various steps in creating the waternets, it is necessary to have the head line 
        defined at the start and end of the geometry. This function adds the outer points 
        if they are not already present.
        
        Args:
            head_line_l (list[float]): The l-coordinates of the head line
            head_line_z (list[float]): The z-coordinates of the head line
            geometry (Geometry): The geometry

        Returns:
            tuple[list[float], list[float]]: The head line including the outer points
        """
        
        # If the head line is not defined at the start or end of the geometry, then we need to add an outer point
        l_surface_level_land_side = geometry.char_point_profile.get_point_by_type(CharPointType.SURFACE_LEVEL_LAND_SIDE).l
        l_surface_level_water_side = geometry.char_point_profile.get_point_by_type(CharPointType.SURFACE_LEVEL_WATER_SIDE).l

        # The head line is created such that the most outward point is the first point
        if head_line_l[0] != l_surface_level_water_side:
            head_line_l.insert(0, l_surface_level_water_side)
            head_line_z.insert(0, head_line_z[0])

        if head_line_l[-1] != l_surface_level_land_side:
            head_line_l.append(l_surface_level_land_side)
            head_line_z.append(head_line_z[-1])

        return head_line_l, head_line_z

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
        
        l, z = self._add_outer_points_if_needed(head_line_l=l, head_line_z=z, geometry=geometry)

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
    order_id: int
    name_ref_line_original: Optional[str] = None
    name_ref_line_top: Optional[str] = None
    name_ref_line_bottom: Optional[str] = None
    name_ref_line_intrusion_top: Optional[str] = None
    name_ref_line_intrusion_bottom: Optional[str] = None


# TODO wordt niet gebruikt
class GetAquifersFromSubsoil(BaseModel):
    @staticmethod
    def _get_and_merge_aquifer_polygons(subsoil: Subsoil) -> list[Polygon]:
        # Get the aquifers from the subsoil
        soil_polygons = [sp for sp in subsoil.soil_polygons if sp.is_aquifer]
        polygons = [sp.to_shapely() for sp in soil_polygons]

        # unify attached aquifers
        union = unary_union(polygons)
        polygons = geometry_to_polygons(union)

        return polygons
    
    @staticmethod
    def _check_defined_from_start_to_end(polygon: Polygon, surf_start: float, surf_end: float) -> bool:
        pass

    @staticmethod
    def _check_intersects_surface_line(polygon: Polygon, surface_line_line_string: LineString) -> bool:
        pass

    @staticmethod
    def _check_underneath_inner_crest(polygon: Polygon, l_inner_crest: float) -> bool:
        pass

    @staticmethod
    def get_aquifer_polygons(subsoil: Subsoil, geometry: Geometry) -> list[Polygon]:
        pass
    

# TODO: Refactor t.b.v. testbaarheid
def get_aquifers_from_subsoil(subsoil: Subsoil, geometry: Geometry) -> list[Aquifer]:
    """
    Note that for subsoils with non-vertical sides, with a reverse trapazoidal shape,
    on either of the sides, the aquifers may not be correctly detected. In this case 
    an error is raised that the aquifer is not valid.
    """

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

    # If there are no aquifers, then we return an empty list
    if len(aquifer_polygons) == 0:
        return []

    # We sort the aquifers by their z-value
    aq_z_min_and_polygons = [(polygon.bounds[1], polygon) for polygon in aquifer_polygons]
    aq_z_min_and_polygons.sort()
    aquifer_polygons = [polygon for _, polygon in aq_z_min_and_polygons]

    aquifers: list[Aquifer] = []

    for i, polygon in enumerate(aquifer_polygons):
        # Assign the deepest aquifer as type AQUIFER
        if i == 0:
            aq_type = AquiferType.AQUIFER
        # Add the remaining aquifers as intermediate aquifers
        else:
            aq_type = AquiferType.INTERMEDIATE_AQUIFER

        polygon_points = [(p[0], p[1]) for p in polygon.exterior.coords[:-1]]  # skip last point
        aquifer = Aquifer(points=polygon_points, aquifer_type=aq_type, order_id=i)
        aquifers.append(aquifer)

    return aquifers


def shift_points_with_equal_l_values(points: list[list[float]]) -> list[list[float]]:
    """D-Stability determines the order of the head line 
    and reference line points based on its own logic, no matter in what order 
    the points are given. Sometimes this does not result in the 
    desired schematization.
    
    This function corrects for this by shifting the points with equal l-values
    a small distance (1 mm) so that the order of the points is always correct.
    
    The case where there already is a point at the future location is not considered."""
    
    # Determine in which direction to shift points
    # if the points are sorted in the positive direction, then the shift should be negative
    if points[0][0] < points[-1][0]:
        sign = -1
    # if the points are sorted in the negative direction, then the shift should be positive
    else:
        sign = 1

    l_coords = [p[0] for p in points]
    unique_l_coords = set(l_coords)

    for l_coord in unique_l_coords:
        dup_points = [p for p in points if p[0] == l_coord]

        for i, point in enumerate(dup_points):
            point[0] += sign * 0.001 * (len(dup_points) - i - 1)

    return points

class LineFromAquiferMethod(BaseModel):
    @staticmethod
    def create_lines(
        aquifer: Aquifer,
        ref_line_config: ReferenceLineConfig,
    ) -> tuple[ReferenceLine, ReferenceLine]:
        """Creates reference lines from an aquifer. A reference line 
        is created at the top and bottom of the aquifer."""

        polygon = Polygon(aquifer.points)

        ref_lines: list[ReferenceLine] = []

        if aquifer.order_id == 0:
            name_ref_line_base = f"{ref_line_config.name_ref_line} ({NAME_DEEP_AQUIFER}"
        else:
            name_ref_line_base = f"{ref_line_config.name_ref_line} ({NAME_INTERMEDIATE_AQUIFER}{aquifer.order_id}"

        for side in ["top", "bottom"]:
            line = get_polygon_top_or_bottom(polygon, side)
            points = [[p[0], p[1]] for p in line.coords]

            ref_line = ReferenceLine(
                l=[p[0] for p in points], 
                z=[p[1] for p in points],
                name=f"{name_ref_line_base} {TOP_BOTTOM_TO_DUTCH[side]})",
                head_line_top=ref_line_config.name_head_line_top,
                head_line_bottom=ref_line_config.name_head_line_bottom
            )
            ref_lines.append(ref_line)

        # Modify the aquifer name to have a unique name for top and bottom
        aquifer.name_ref_line_original = ref_line_config.name_ref_line
        aquifer.name_ref_line_top = f"{name_ref_line_base} {TOP_BOTTOM_TO_DUTCH['top']})"
        aquifer.name_ref_line_bottom = f"{name_ref_line_base} {TOP_BOTTOM_TO_DUTCH['bottom']})"

        return ref_lines[0], ref_lines[1]
    
class LineIntrusionMethod(BaseModel):
    @staticmethod
    def get_ref_lines_by_name(name: str, ref_lines: list[ReferenceLine], aquifers: list[Aquifer] | None) -> list[ReferenceLine]:
        names: list[str] = [name]

        # The aquifer ref. lines names are altered (to have a unique name for top and bottom)
        # the modified names are added based on the aquifers original names
        if aquifers is not None:
            names.extend([aq.name_ref_line_top for aq in aquifers if aq.name_ref_line_original == name])
            names.extend([aq.name_ref_line_bottom for aq in aquifers if aq.name_ref_line_original == name])

        # Get the reference lines that match the names
        ref_lines = [
            rl for rl in ref_lines 
            if rl.name in names
        ]
        
        # Check if there are any reference lines that match the names
        if len(ref_lines) == 0:
            raise ValueError(f"The reference line '{name}' does not exist")
        
        return ref_lines
    
    @staticmethod
    def select_appropriate_ref_line(
        intrusion_from_ref_lines: list[ReferenceLine], 
        ref_line_config: ReferenceLineConfig,
        ) -> ReferenceLine:
        """Selects the appropriate reference line to apply the intrusion to.
        This is based on the name of the reference line and the direction of the intrusion."""
        
        # If there is one, then we can use that
        if len(intrusion_from_ref_lines) == 1:
            intrusion_from_ref_line = intrusion_from_ref_lines[0]

            return intrusion_from_ref_line

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
        ref_line_config: ReferenceLineConfig,
        aquifers: list[Aquifer] | None
        ) -> ReferenceLine:
        """Creates a reference line based on the intrusion from another reference line."""

        # Get the reference line to apply the intrusion on by name
        intrusion_from_ref_lines = LineIntrusionMethod.get_ref_lines_by_name(
            name=ref_line_config.intrusion_from_ref_line, 
            ref_lines=current_ref_lines,
            aquifers=aquifers
            )

        # There could be multiple reference lines with the same name (in case of an aquifer), 
        # so we need to select the appropriate one
        intrusion_from_ref_line = LineIntrusionMethod.select_appropriate_ref_line(
            intrusion_from_ref_lines=intrusion_from_ref_lines, 
            ref_line_config=ref_line_config
            )
        
        # Create the new reference line
        ref_line_l = intrusion_from_ref_line.l
        ref_line_z = [z + ref_line_config.intrusion_length for z in intrusion_from_ref_line.z]

        ref_line = ReferenceLine(
            name=ref_line_config.name_ref_line,
            l=ref_line_l,
            z=ref_line_z,
            head_line_top=ref_line_config.name_head_line_top,
            head_line_bottom=ref_line_config.name_head_line_bottom
        )

        # Update aquifer property if there are any
        if aquifers is not None:
            aquifer = next(
                (aq for aq in aquifers 
                 if intrusion_from_ref_line.name in [aq.name_ref_line_top, aq.name_ref_line_bottom]),
                None
                )
            # If the intrusion line is related to an aquifer, then update the aquifer property
            if aquifer is not None:
                if intrusion_from_ref_line.name == aquifer.name_ref_line_top:
                    aquifer.name_ref_line_intrusion_top = ref_line_config.name_ref_line
                else:
                    aquifer.name_ref_line_intrusion_bottom = ref_line_config.name_ref_line

        return ref_line


def correct_crossing_reference_lines(
        top_ref_line: ReferenceLine, 
        bottom_ref_line: ReferenceLine, 
        soil_bottom: float,
        correct_ref_line: Literal["top", "bottom", "both"]
        ) -> tuple[ReferenceLine, ReferenceLine]:
    """Corrects the crossing of reference lines."""

    max_z = max(max(top_ref_line.z), max(bottom_ref_line.z))

    # Define a polygon where the upper reference line is the bottom of the polygon
    top_ref_line_points = [(l, z) for l, z in zip(top_ref_line.l, top_ref_line.z)]
    top_ref_line_polygon_top = Polygon(
        [
            (top_ref_line_points[0][0], max_z + 1.), 
            *top_ref_line_points, 
            (top_ref_line_points[-1][0], max_z + 1.)
        ]
    )   
    
    # Define a polygon where the lower reference line is the top of the polygon
    bottom_ref_line_points = [(l, z) for l, z in zip(bottom_ref_line.l, bottom_ref_line.z)]
    bottom_ref_line_polygon_bottom = Polygon(
        [
            (bottom_ref_line_points[0][0], soil_bottom), # - 0.01
            *bottom_ref_line_points, 
            (bottom_ref_line_points[-1][0], soil_bottom) # - 0.01
        ]
    )

    # Intersect the two polygons. If there is an intersection, then the reference lines cross each other
    intersection = top_ref_line_polygon_top.intersection(bottom_ref_line_polygon_bottom)
    intersection_polygons = geometry_to_polygons(intersection)  # points and lines are not included

    # If the lines don't intersect (actually if they don't 'overlap', touching is allowed) - return the original lines
    if len(intersection_polygons) == 1 and intersection_polygons[0].is_empty:
        return top_ref_line, bottom_ref_line
    
    # Create a polygon where the lower reference line is the bottom of the polygon
    bottom_ref_line_polygon_top = Polygon(
        [
            (bottom_ref_line_points[0][0], max_z + 1.), 
            *bottom_ref_line_points, 
            (bottom_ref_line_points[-1][0], max_z + 1.)
        ]
    )
    
    # In the following, the xxx_ref_line_polygon_top are altered for 
    #  every part where the reference lines cross each other (overlap)
    # For overlapping parts, a mask polygon is joined with both the ref polygons
    #  such that the bottom of the polygons is situated just below the soil bottom
    # The corrected ref_lines are determined by taking the bottom of the polygons
    for polygon in intersection_polygons:
        l_min = min(polygon.exterior.xy[0])
        l_max = max(polygon.exterior.xy[0])

        mask_polygon = Polygon([
            (l_min, soil_bottom - 1.), 
            (l_max, soil_bottom - 1.), 
            (l_max, max_z + 1.), 
            (l_min, max_z + 1.)
            ]
        )
        bottom_ref_line_polygon_top = unary_union([bottom_ref_line_polygon_top, mask_polygon])
        top_ref_line_polygon_top = unary_union([top_ref_line_polygon_top, mask_polygon])

    if type(bottom_ref_line_polygon_top) != Polygon or type(top_ref_line_polygon_top) != Polygon:
        raise ValueError("Something went wrong with correcting crossing reference lines"
                            "that were modelled using an intrusion length")

    # Get the bottom line of the polygons - This is the new ref line
    bottom_ref_line_line_string = get_polygon_top_or_bottom(
        polygon=bottom_ref_line_polygon_top,
        top_or_bottom="bottom"
        )
    
    top_ref_line_line_string = get_polygon_top_or_bottom(
        polygon=top_ref_line_polygon_top,
        top_or_bottom="bottom"
        )
    
    # Sort in original order if needed
    top_ref_line_coords = [list(coord) for coord in top_ref_line_line_string.coords]
    top_ref_line_l_start = top_ref_line.l[0]

    if top_ref_line_l_start != top_ref_line_coords[0][0]:
        top_ref_line_coords = top_ref_line_coords[::-1]

    bottom_ref_line_coords = [list(coord) for coord in bottom_ref_line_line_string.coords]
    bottom_ref_line_l_start = bottom_ref_line.l[0]

    if bottom_ref_line_l_start != bottom_ref_line_coords[0][0]:
        bottom_ref_line_coords = bottom_ref_line_coords[::-1]

    # Convert the line strings to reference lines
    if correct_ref_line == "top" or correct_ref_line == "both":
        top_ref_line.l = [coord[0] for coord in top_ref_line_coords]
        top_ref_line.z = [coord[1] for coord in top_ref_line_coords]
    
    if correct_ref_line == "bottom" or correct_ref_line == "both":
        bottom_ref_line.l = [coord[0] for coord in bottom_ref_line_coords]
        bottom_ref_line.z = [coord[1] for coord in bottom_ref_line_coords]
    
    return top_ref_line, bottom_ref_line


class WaternetCreatorInput(BaseModel):
    """Input for the WaternetCreator"""

    geometry: Geometry
    waternet_config: WaternetConfig
    water_level_collection: WaterLevelCollection
    offset_method_collection: LineOffsetMethodCollection
    subsoil: Optional[Subsoil] = None

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
                        "The subsoil is required input when creating reference lines"
                        "with the method 'AQUIFER' or 'INTERMEDIATE_AQUIFER'."
                    )
            
        return self


class PhreaticLineModifier(BaseModel):
    """Factory for modifying a head line representing a phreatic line"""

    geometry: Geometry
    outward_intersection: Optional[tuple[float, float]] = None
    inward_intersection: Optional[tuple[float, float]] = None

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

class ReferenceLineCorrector(BaseModel):
    """Corrects the crossing of the phreatic reference line and 
    reference lines that are modelled with an intrusion method.
    
    There are two zones where corrections can be made:
    - Zone 1: Between the surface level and the first aquifer
    - Zone 2: Between two aquifers

    What is corrected and why
    --------------------------
    An intrusion ref. line models the intrusion of water pressure from 
    another ref. line. This is a time-related phenomenon, often caused by
    a change in the boundary conditions (water levels). It is possible
    that there is an intrusion ref. line related to the phreatic ref. line
    or an intrusion ref. line related to an aquifer ref. line.

    If the intrusion is high enough, then it is possible that the 
    intrusion ref. lines cross each other. Physically, this would mean that
    the top (phreatic) and bottom (aquifer) boundary conditions interfere
    with each other, both adding to a rise (or fall) in the pore pressure. 
    
    However, if the intrusion lines are not corrected, this would lead to
    a faulty schematization of the pore water pressures. Therefore, if 
    a crossing takes place, the intrusion ref. lines are corrected in a 
    way that they no longer are of influence to the pore water pressures.
    This is done by moving the intrusion ref. lines below the bottom layer.

    The corrections are done on reference lines that are modelled with an
    intrusion method. Additionally, the phreatic ref. line is also corrected.
    Physically, this is also an intrusion phenomenon.
    """

    @staticmethod
    def get_phreatic_ref_line(
            head_line_configs: list[HeadLineConfig],
            ref_lines: list[ReferenceLine],
            ) -> ReferenceLine | None:
        """Get the phreatic reference line from the head line configs. 
        Returns None if there is no phreatic line."""

        # Get phreatic line name, if present
        phreatic_line_name = next(
            (
                config.name_head_line for config in head_line_configs
                if config.is_phreatic
            ), None)
        
        # If there is a phreatic line, then we check if it has a ref. line
        if phreatic_line_name is not None:
            # If there is, then we get it
            phreatic_ref_line = next(
                (
                    ref_line for ref_line in ref_lines
                    if (ref_line.head_line_top == phreatic_line_name or ref_line.head_line_bottom == phreatic_line_name)
                ), None)
            
        # Otherwise, there is no phreatic ref. line
        else:
            phreatic_ref_line = None

        return phreatic_ref_line
    
    @staticmethod
    def get_intrusion_ref_line_related_to_phreatic(
            reference_line_configs: list[ReferenceLineConfig],
            phreatic_ref_line: ReferenceLine,
            ref_lines: list[ReferenceLine],
            ) -> ReferenceLine | None:
        """Get the intrusion ref. line related to the phreatic ref. line.
        Returns None if there is no related intrusion ref. line.
        
        Args:
            reference_line_configs (list[ReferenceLineConfig]): The reference line configurations.
            phreatic_ref_line (ReferenceLine): The phreatic ref. line.
            ref_lines (list[ReferenceLine]): The reference lines.

        Returns:
            ReferenceLine | None: The related intrusion ref. line or None if there is no related intrusion ref. line.
        """
        
        # Check if the phreatic ref. line has a related intrusion ref. line
        intrusion_ref_line_name = next(
            (
                config.name_ref_line for config in reference_line_configs
                if config.intrusion_from_ref_line == phreatic_ref_line.name
            ), None)

        # If there is an intrusion ref. line related to the phreatic ref. line, then we get it.
        if intrusion_ref_line_name is not None:
            intrusion_ref_line_related_to_phreatic = next(
                (
                    ref_line for ref_line in ref_lines if ref_line.name == intrusion_ref_line_name
                ), None)
        # Otherwise, set it to None
        else:
            intrusion_ref_line_related_to_phreatic = None
            
        return intrusion_ref_line_related_to_phreatic

    @staticmethod
    def correction_surface_level_and_first_aquifer(
            waternet_creator_input: WaternetCreatorInput,
            ref_lines: list[ReferenceLine],
            soil_bottom: float,
            aquifers: list[Aquifer],
    ) -> list[ReferenceLine]:
        """Corrects the crossing of reference lines between the surface level and 
        the first aquifer. 
        
        In this zone (Zone 1), the correction of three reference lines is regarded:
        - The phreatic ref. line (offset method)
        - A ref. line related to the phreatic ref. line (intrusion method)
        - A ref. line related to the first aquifer top ref. line (intrusion method)

        In this zone, there are two boundary conditions, which also have a ref. line:
        - The surface level (implicitly always present in D-Stability and related to the phreatic line)
        - The first aquifer top ref. line (aquifer method)

        These are not corrected and stay in place, but are used for the corrections.

        There are four scenarios:

        Scenario 1: Phreatic ref. line and no intrusion lines
        -----------------------------------------------------
        If the phreatic ref. line and the top aquifer ref. line cross each other,
        then the phreatic ref. line is corrected to below the subsoil bottom.

        
        Scenario 2: Intrusion top aquifer, no freatic ref. line
        -------------------------------------------------------
        If the intrusion ref. line related to the top aquifer ref. line crosses
        the surface level and lies above it, then it has no effect on the waternet.

        No correction is needed in this scenario.

        
        Scenario 3: Intrusion top aquifer, phreatic ref. line, no intrusion phreatic ref. line
        -------------------------------------------------------------------------------------
        If the intrusion ref. line related to the top aquifer ref. line crosses
        the phreatic ref. line, then both the intrusion ref. line and the phreatic
        ref. line are corrected to below the subsoil bottom.

        
        Scenario 4: Intrusion top aquifer, phreatic ref. line, intrusion phreatic ref. line
        -------------------------------------------------------------------------------------
        In this case there are two sets of two lines to check, in the following order:
        - a. intrusion phreatic ref. line and intrusion top aquifer ref. line
        - b. phreatic ref. line and the top aquifer ref. line

        a. If the intrusion ref. line related to the top aquifer ref. line crosses
        the intrusion phreatic ref. line, then both the ref. lines are corrected to below
        the subsoil bottom.
        
        b. If additionallythe phreatic ref. line crosses the top aquifer ref. line, then the
        phreatic ref. line is corrected to below the subsoil bottom.

        Scenario 5: Phreatic ref. line, intrusion phreatic ref. line, no intrusion top aquifer
        ---------------------------------------------------------------------------------
        In this scenario, two checks are done:
        - a. Crossing of the phreatic intrusion ref. line with the top aquifer ref. line
        - b. Crossing of the phreatic ref. line with the top aquifer ref. line

        a. If the phreatic intrusion ref. line crosses the top aquifer ref. line, then the phreatic
        intrusion ref. line is corrected to below the subsoil bottom.

        b. If additionally the phreatic ref. line crosses the top aquifer ref. line, then the phreatic
        ref. line is corrected to below the subsoil bottom.
        
        Args:
            waternet_creator_input (WaternetCreatorInput): The waternet creator input.
            ref_lines (list[ReferenceLine]): The reference lines.
            soil_bottom (float): The deepest point of the subsoil. Used for correcting ref. lines
            aquifers (list[Aquifer]): The aquifers.

        Returns:
            list[ReferenceLine]: The corrected reference lines.
        """

        # Get the relevant ref. lines
        phreatic_ref_line = ReferenceLineCorrector.get_phreatic_ref_line(
            head_line_configs=waternet_creator_input.waternet_config.head_line_configs,
            ref_lines=ref_lines
        )

        if phreatic_ref_line is not None:
            intrusion_ref_line_related_to_phreatic = ReferenceLineCorrector.get_intrusion_ref_line_related_to_phreatic(
                reference_line_configs=waternet_creator_input.waternet_config.reference_line_configs,
                phreatic_ref_line=phreatic_ref_line,
                ref_lines=ref_lines
            )
        else:
            intrusion_ref_line_related_to_phreatic = None

        # Now we get the top most aquifer ref. line and see if it has a related intrusion ref. line
        # The top most aquifer as the highest order_id
        top_aquifer = max(aquifers, key=lambda x: x.order_id)
        top_aquifer_ref_line_top = next(rl for rl in ref_lines if rl.name == top_aquifer.name_ref_line_top)
        top_aquifer_intrusion_ref_line_top = next(
            (rl for rl in ref_lines if rl.name == top_aquifer.name_ref_line_intrusion_top),
            None
            )
        
        # Scenario 0: No phreatic ref. line and no intrusion lines - No correction needed
        if (
            phreatic_ref_line is None 
            and intrusion_ref_line_related_to_phreatic is None 
            and top_aquifer_intrusion_ref_line_top is None
            ):
            return ref_lines

        # Scenario 1: Phreatic ref. line and no intrusion lines
        elif (
            phreatic_ref_line is not None 
            and intrusion_ref_line_related_to_phreatic is None
            and top_aquifer_intrusion_ref_line_top is None
            ):
            correct_crossing_reference_lines(
                top_ref_line=phreatic_ref_line,
                bottom_ref_line=top_aquifer_ref_line_top,
                soil_bottom=soil_bottom,
                correct_ref_line="top"
            )
        
        # Scenario 2: Intrusion top aquifer, no freatic ref. line
        elif (
            phreatic_ref_line is None 
            and top_aquifer_intrusion_ref_line_top is not None
            ):
            # No correction needed. A ref. above the surface level has no effect on the waternet.
            return ref_lines
    
        # Scenario 3: Intrusion top aquifer, phreatic ref. line, no intrusion phreatic ref. line
        elif (
            phreatic_ref_line is not None 
            and intrusion_ref_line_related_to_phreatic is None
            and top_aquifer_intrusion_ref_line_top is not None
            ):
            correct_crossing_reference_lines(
                top_ref_line=phreatic_ref_line,
                bottom_ref_line=top_aquifer_intrusion_ref_line_top,
                soil_bottom=soil_bottom,
                correct_ref_line="both"
            )

        # Scenario 4: Intrusion top aquifer, phreatic ref. line, intrusion phreatic ref. line
        elif (
            phreatic_ref_line is not None 
            and intrusion_ref_line_related_to_phreatic is not None
            and top_aquifer_intrusion_ref_line_top is not None
            ):
            # Now we have two sets of two lines to check, in the following order:
            # a. intrusion phreatic ref. line and intrusion top aquifer ref. line
            # b. phreatic ref. line and the top aquifer ref. line

            # a.
            correct_crossing_reference_lines(
                top_ref_line=intrusion_ref_line_related_to_phreatic,
                bottom_ref_line=top_aquifer_intrusion_ref_line_top,
                soil_bottom=soil_bottom,
                correct_ref_line="both"
            )

            # b. - Possibly, also the phreatic ref. line and the top aquifer ref. line cross each other
            correct_crossing_reference_lines(
                top_ref_line=phreatic_ref_line,
                bottom_ref_line=top_aquifer_ref_line_top,
                soil_bottom=soil_bottom,
                correct_ref_line="top"  # Top - Aquifer ref. lines always stays in place
            )

        # Scenario 5: Phreatic ref. line, intrusion phreatic ref. line, no intrusion top aquifer
        elif (
            phreatic_ref_line is not None 
            and intrusion_ref_line_related_to_phreatic is not None
            and top_aquifer_intrusion_ref_line_top is None
            ):
            # a.
            correct_crossing_reference_lines(
                top_ref_line=intrusion_ref_line_related_to_phreatic,
                bottom_ref_line=top_aquifer_ref_line_top,
                soil_bottom=soil_bottom,
                correct_ref_line="top"
            )

            # b. - Possibly, also the phreatic ref. line and the top aquifer ref. line cross each other
            correct_crossing_reference_lines(
                top_ref_line=phreatic_ref_line,
                bottom_ref_line=top_aquifer_ref_line_top,
                soil_bottom=soil_bottom,
                correct_ref_line="top"
            )

        else:
            raise ValueError("An error occured correcting the reference lines between the "
                             "surface level and the first aquifer. ")

        return ref_lines

    @staticmethod
    def correction_between_aquifers(
            top_aquifer: Aquifer,
            bottom_aquifer: Aquifer,
            ref_lines: list[ReferenceLine],
            soil_bottom: float,
            ):
        """Corrects the crossing of the reference lines between aquifers.
        
        In this zone (Zone 2), the correction of two reference lines is regarded:
        - A ref. line related to the top aquifer bottom ref. line (intrusion method)
        - A ref. line related to the bottom aquifer top ref. line (intrusion method)

        In this zone, there are two boundary conditions, which also have a ref. line:
        - The top aquifer bottom ref. line (aquifer method)
        - The bottom aquifer top ref. line (aquifer method)

        These are not corrected and stay in place, but are used for the corrections.

        There are two scenarios:

        Scenario 1: Only a bottom aquifer intrusion ref. line
        --------------------------------------------------------
        If the bottom aquifer intrusion ref. line crosses the top aquifer, 
        then the bottom aquifer intrusion ref. line is corrected to below the subsoil bottom.

        
        Scenario 2: Only a top aquifer intrusion ref. line
        --------------------------------------------------------
        If the top aquifer intrusion ref. line crosses the bottom aquifer, 
        then the top aquifer intrusion ref. line is corrected to below the subsoil bottom.

        
        Scenario 3: Both aquifer intrusion ref. lines
        --------------------------------------------------------
        If the top aquifer intrusion ref. line crosses the bottom aquifer, 
        then both the top aquifer intrusion ref. line and the bottom aquifer
        intrusion ref. line are corrected to below the subsoil bottom.
        
        Args:
            top_aquifer (Aquifer): The top aquifer.
            bottom_aquifer (Aquifer): The bottom aquifer.
            ref_lines (list[ReferenceLine]): The reference lines.
            soil_bottom (float): The subsoil bottom.

        Returns:
            list[ReferenceLine]: The reference lines.
        """
        
        # Get bottom ref. line of top aquifer
        top_aquifer_ref_line_bottom = next(rl for rl in ref_lines if rl.name == top_aquifer.name_ref_line_bottom)
        bottom_aquifer_ref_line_top = next(rl for rl in ref_lines if rl.name == bottom_aquifer.name_ref_line_top)

        # Get the intrusion ref. lines for the aquifers (if present)
        top_aquifer_intrusion_ref_line_bottom = next(
            (rl for rl in ref_lines if rl.name == top_aquifer.name_ref_line_intrusion_bottom),
            None
            )
        bottom_aquifer_intrusion_ref_line_top = next(
            (rl for rl in ref_lines if rl.name == bottom_aquifer.name_ref_line_intrusion_top),
            None
            )

        # Scenario 0: No intrusion ref. lines - Nothing to correct
        if top_aquifer_intrusion_ref_line_bottom is None and bottom_aquifer_intrusion_ref_line_top is None:
            return ref_lines

        # Scenario 1: Only bottom aquifer intrusion ref. line
        elif (
            bottom_aquifer_intrusion_ref_line_top is not None 
            and top_aquifer_intrusion_ref_line_bottom is None
            ):
            top_ref_line = top_aquifer_ref_line_bottom
            bottom_ref_line = bottom_aquifer_intrusion_ref_line_top
            correct_ref_line = "bottom"
        
        # Scenario 2: Only top aquifer intrusion ref. line
        elif (
            bottom_aquifer_intrusion_ref_line_top is None 
            and top_aquifer_intrusion_ref_line_bottom is not None
            ):
            top_ref_line = top_aquifer_intrusion_ref_line_bottom
            bottom_ref_line = bottom_aquifer_ref_line_top
            correct_ref_line = "top"

        # Scenario 3: Both aquifer intrusion ref. lines
        elif (
            bottom_aquifer_intrusion_ref_line_top is not None 
            and top_aquifer_intrusion_ref_line_bottom is not None
            ):
            top_ref_line = top_aquifer_intrusion_ref_line_bottom
            bottom_ref_line = bottom_aquifer_intrusion_ref_line_top
            correct_ref_line = "both"

        else:
            raise ValueError("An error occured correcting the crossing of the aquifer ref. lines")
    
        # Correct the crossing of the reference lines
        correct_crossing_reference_lines(
            top_ref_line=top_ref_line,
            bottom_ref_line=bottom_ref_line,
            soil_bottom=soil_bottom,
            correct_ref_line=correct_ref_line
        )

        return ref_lines
    

class WaternetCreator(BaseModel):
    """Factory for creating a single waternet"""

    input: WaternetCreatorInput
    _aquifers: Optional[list[Aquifer]] = None

    def create_head_lines(self, water_level_set: dict[str, float | None]) -> list[HeadLine]:
        head_lines: list[HeadLine] = []

        for head_line_config in self.input.waternet_config.head_line_configs:
            # Get the method to create the head line
            if head_line_config.head_line_method_type == HeadLineMethodType.OFFSETS:
                method = self.input.offset_method_collection.get_by_name(head_line_config.offset_method_name)
            else:
                raise ValueError(f"Invalid headline method type '{head_line_config.head_line_method_type}'")

            # Create the head line
            head_line_l, head_line_z = method.create_line(geometry=self.input.geometry, ref_levels=water_level_set)
            
            head_line = HeadLine(
                name=head_line_config.name_head_line,
                is_phreatic=head_line_config.is_phreatic,
                l=head_line_l,
                z=head_line_z
            )

            # Add the point where the phreatic line intersects the surface line (if it does)
            if head_line_config.is_phreatic:
                phreatic_line_modifier = PhreaticLineModifier(geometry=self.input.geometry)
                head_line = phreatic_line_modifier.process_inward_intersection_phreatic_line(head_line)
                head_line = phreatic_line_modifier.process_outward_intersection_phreatic_line(head_line)

                # As last - maximize the headline to the surface level if requested
                if head_line_config.apply_minimal_surface_line_offset:
                    head_line = phreatic_line_modifier.apply_minimal_surface_line_offset_to_phreatic_line(
                        head_line=head_line,
                        offset=head_line_config.minimal_surface_line_offset,
                        from_char_point_type=head_line_config.minimal_offset_from_point,
                        to_char_point_type=head_line_config.minimal_offset_to_point
                    )

            head_lines.append(head_line)
        
        return head_lines

    def create_ref_lines_aquifers_method(self) -> list[ReferenceLine]:
        ref_lines: list[ReferenceLine] = []
        ref_line_configs = self.input.waternet_config.reference_line_configs
        
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
            self._aquifers = get_aquifers_from_subsoil(self.input.subsoil, self.input.geometry)

            # TODO: Aan te passen - TZL methode is verplicht bij aanwezigheid van tweede WVP --> Dit hoeft niet meer denk ik
            # Create the reference lines per aquifer
            for aquifer in self._aquifers:
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
        ref_line_configs = self.input.waternet_config.reference_line_configs
        
        for ref_line_config in ref_line_configs:
            if ref_line_config.ref_line_method_type == RefLineMethodType.OFFSETS:
                method = self.input.offset_method_collection.get_by_name(ref_line_config.offset_method_name)

                # Create the reference line
                ref_line_l, ref_line_z = method.create_line(
                    geometry=self.input.geometry,
                    ref_levels=water_level_set
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

    def create_ref_lines_intrusion_method(self, current_ref_lines: list[ReferenceLine]) -> list[ReferenceLine]:
        ref_lines: list[ReferenceLine] = []
        ref_line_configs = self.input.waternet_config.reference_line_configs

        # Check if there are intermediate aquifers
        if self._aquifers is not None:
            intermediate_aquifer_present = any(
                aquifer.aquifer_type == AquiferType.INTERMEDIATE_AQUIFER 
                for aquifer in self._aquifers
            )
            deep_aquifer_present = any(
                aquifer.aquifer_type == AquiferType.AQUIFER 
                for aquifer in self._aquifers
            )
        else:
            intermediate_aquifer_present = False
            deep_aquifer_present = False

        for ref_line_config in ref_line_configs:
            if ref_line_config.ref_line_method_type != RefLineMethodType.INTRUSION:
                continue

            intrusion_from_ref_line_config = next(
                    conf for conf in ref_line_configs
                    if conf.name_ref_line == ref_line_config.intrusion_from_ref_line
            )

            # If the intrusion from ref. line is an aquifer and but there is no deep aquifer, then skip it
            if (
                intrusion_from_ref_line_config.ref_line_method_type == RefLineMethodType.AQUIFER
                and not deep_aquifer_present
                ):
                continue

            # If the intrusion from ref. line is an intermediate aquifer and but there is no intermediate aquifer, then skip it
            if (
                intrusion_from_ref_line_config.ref_line_method_type == RefLineMethodType.INTERMEDIATE_AQUIFER
                and not intermediate_aquifer_present
                ):
                continue

            # Create the reference line               
            ref_line = LineIntrusionMethod.create_line(
                current_ref_lines=current_ref_lines,
                ref_line_config=ref_line_config,
                aquifers=self._aquifers
            )

            ref_lines.append(ref_line)
        
        return ref_lines

    def create_waternet(self) -> Waternet:
        # Get water levels - this is based on the geometry name since water levels are location bound
        location_water_levels = self.input.water_level_collection.get_by_name(self.input.geometry.name)

        # Rename the water levels to the generalized water level names
        water_level_set = {
            k: location_water_levels[v]
            for k, v in self.input.waternet_config.water_level_config.water_levels.items()
            if v is not None
        }

        # Create the head lines
        head_lines = self.create_head_lines(water_level_set=water_level_set)

        # Create the reference lines - The order is important here
        ref_lines: list[ReferenceLine] = []
        
        ref_lines.extend(self.create_ref_lines_aquifers_method())
        ref_lines.extend(self.create_ref_lines_offset_method(water_level_set=water_level_set))
        ref_lines.extend(self.create_ref_lines_intrusion_method(current_ref_lines=ref_lines))

        # Correct the crossing of reference lines between the surface level and the first aquifer
        if self._aquifers is not None:
            ref_lines = ReferenceLineCorrector.correction_surface_level_and_first_aquifer(
                waternet_creator_input=self.input,
                ref_lines=ref_lines,
                soil_bottom=self.input.subsoil.get_bottom(),
                aquifers=self._aquifers
            )
        
        # Correct between the aquifers, if there is more than one
        if self._aquifers is not None and len(self._aquifers) > 1:
            for i in range(len(self._aquifers) - 1):               
                top_aquifer = next(aq for aq in self._aquifers if aq.order_id == i + 1)
                bottom_aquifer = next(aq for aq in self._aquifers if aq.order_id == i)

                ref_lines = ReferenceLineCorrector.correction_between_aquifers(
                    top_aquifer=top_aquifer,
                    bottom_aquifer=bottom_aquifer,
                    ref_lines=ref_lines,
                    soil_bottom=self.input.subsoil.get_bottom()
                )
                
        # Finally - correct the ref. lines with equal l-values to ensure a correct order
        for ref_line in ref_lines:
            points = [[l, z] for l, z in zip(ref_line.l, ref_line.z)]
            points = shift_points_with_equal_l_values(points)
            ref_line.l = [p[0] for p in points]
            ref_line.z = [p[1] for p in points]

        return Waternet(head_lines=head_lines, ref_lines=ref_lines)
