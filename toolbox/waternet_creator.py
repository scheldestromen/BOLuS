from pydantic import BaseModel, model_validator, Field
from enum import StrEnum, auto
from typing import Optional, Self, Literal
from shapely.geometry import Polygon, LineString, GeometryCollection
from shapely.ops import unary_union

from toolbox.geometry import CharPointType, CharPoint
from toolbox.geometry import Geometry
from toolbox.geometry import SurfaceLine
from toolbox.geometry import Side
from toolbox.waternet import HeadLine, ReferenceLine, Waternet
from toolbox.subsoil import Subsoil
from toolbox.waternet_config import WaterLevelCollection, HeadLineMethodType, RefLineMethodType, HeadLineConfig, \
    ReferenceLineConfig, WaternetConfig, WaterLevelSetConfig
from utils.geometry_utils import get_polygon_top_or_bottom, geometry_to_polygons, offset_line, simplify_line


# TODO: Refactor ter bevordering van de leesbaarheid en herleidbaarheid
#       - methodes in mapje zetten, splitsen in scripts?


NAME_DEEP_AQUIFER = "WVP"
NAME_INTERMEDIATE_AQUIFER = "TZL"

TOP_BOTTOM_TO_DUTCH = {
    "top": "boven",
    "bottom": "onder",
}

# Used for simplifying the head line determined by interpolation from another waternet
TOLERANCE_SIMPLIFY_LINE = 0.01  # 1 cm


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


def add_outer_points_if_missing(
        l_coords: list[float],
        z_coords: list[float],
        geometry: Geometry
) -> tuple[list[float], list[float]]:
    """Add points to the line at the surface level land side and water side if they 
    are not yet present. The height of the added points is the same as the height of 
    the last known point on the given line."""

    # Get the l-values of outer characteristic points
    l_surface_level_land_side = geometry.char_point_profile.get_point_by_type(CharPointType.SURFACE_LEVEL_LAND_SIDE).l
    l_surface_level_water_side = geometry.char_point_profile.get_point_by_type(CharPointType.SURFACE_LEVEL_WATER_SIDE).l

    # Determine the last land side and water side points known on the line
    # This is based on the distance from the outer line points to the surface level points
    if abs(l_coords[0] - l_surface_level_land_side) < abs(l_coords[-1] - l_surface_level_land_side):
        index_last_land_side_point = 0
        index_last_water_side_point = -1
    else:
        index_last_land_side_point = -1
        index_last_water_side_point = 0

    # Add the points at the surface level land side and water side if they are not yet present
    if l_coords[index_last_water_side_point] != l_surface_level_water_side:
        # Check value of index for ensuring the right point order
        # If the point has index 0, then it is the first point and we need to insert it
        if index_last_water_side_point == 0:
            l_coords.insert(0, l_surface_level_water_side)
            z_coords.insert(0, z_coords[0])
        # If the point has index -1, then it is the last point and we need to append it
        else:
            l_coords.append(l_surface_level_water_side)
            z_coords.append(z_coords[-1])

    if l_coords[index_last_land_side_point] != l_surface_level_land_side:
        # Check value of index for ensuring the right point order
        # If the point has index 0, then it is the first point and we need to insert it
        if index_last_land_side_point == 0:
            l_coords.insert(0, l_surface_level_land_side)
            z_coords.insert(0, z_coords[0])
        # If the point has index -1, then it is the last point and we need to append it
        else:
            l_coords.append(l_surface_level_land_side)
            z_coords.append(z_coords[-1])

    return l_coords, z_coords


class LineOffsetMethod(BaseModel):
    name_method: str
    offset_points: list[LineOffsetPoint]

    @model_validator(mode='after')
    def validate_offset_points(self) -> Self:
        # Check for duplicate char points
        char_point_types = [p.char_point_type for p in self.offset_points]
        if len(set(char_point_types)) != len(char_point_types):
            raise ValueError(f"Duplicate characteristic points found in the offset method '{self.name_method}'. "
                             f"Please ensure all characteristic points occur only once at maximum.")

        return self

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
            # Get the z-value of the previous point - this is the last level in the list
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

    # TODO: Vervangen voor generieke functie (add_outer_points_if_missing)
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

        # Determine the sorting direction. We want to start with the most outward point
        reverse = geometry.char_point_profile.determine_l_direction_sign(
            Side.WATER_SIDE) == 1  # presence of l-coordinates is also checked

        char_points: list[CharPoint] = []

        for offset_point in self.offset_points:
            try:
                char_point = geometry.char_point_profile.get_point_by_type(offset_point.char_point_type)
                char_points.append(char_point)

            # If the characteristic point is not present, skip it
            except ValueError:
                continue

        # Get a sorted copy of the char points - equal l-values retain their order,
        # so it is upto the user to ensure that the char points are in the correct order
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


# TODO wordt niet gebruikt - Beter naar aparte module verhuizen
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
    
    The case where there already is a point at the future location is not considered.
    
    Args:
        points: list of points to shift [[l1, z1], [l2, z2], ...]
        
    Returns:
        list of points with the correct order [[l1, z1], [l2, z2], ...]
    """
    
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
    def get_ref_lines_by_name(name: str, ref_lines: list[ReferenceLine], aquifers: list[Aquifer]) -> list[ReferenceLine]:
        names: list[str] = [name]

        # The aquifer ref. lines names are altered (to have a unique name for top and bottom)
        # the modified names are added based on the aquifers original names
        if aquifers:
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
        aquifers: list[Aquifer]
        ) -> ReferenceLine:
        """Creates a reference line based on the intrusion from another reference line.
        
        A note on intrusion in case of multiple intermediate aquifers:
        --------------------------------------------------------------
        A ReferenceLineConfig with the RefLineMethodType.AQUIFER (or INTERMEDIATE_AQUIFER) generates 
        two reference lines, one for the top and one for the bottom. If this reference line is refered to 
        to apply the intrusion method on, then the appropriate reference line is based on the value 
        of the intrusion_length. If the intrusion_length is positive, then the top reference line is used, 
        if the intrusion_length is negative, then the bottom reference line is used.

        If there are multiple intermediate aquifers, then a ReferenceLineConfig with the 
        RefLineMethodType.INTERMEDIATE_AQUIFER is used for each intermediate aquifer and will
        result in four or more reference lines. In this case still the top and bottom lines
        are selected based on the value of the intrusion_length. As a result, intrusion cannot be applied
        in between intermediate aquifers.

        For now, the case with multiple intermediate aquifers where it is desired to apply the 
        intrusion method in between intermediate aquifers is not supported. Extension is possible 
        by expanding the amounts of possible aquifer methods (instead of AQUIFER and INTERMEDIATE_AQUIFER)
        or by using the information in the aquifer objects.
        """

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
        if aquifers:
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


class InterpolateHeadLineFromWaternet(BaseModel):
    """Creates a head line based on the hydraulic head along a reference line
    projected in another stage. 
    
    This is used for modelling a change in (e.g.) the 
    water level for which the subsoil has not fully adjusted yet. The reference line 
    is used for modelling the intrusion of pore pressure. The desired head along this
    ref. line is the initial head along this line. Therefore, the reference line is 
    'projected' in a previous stage and the head is determined along this line. 
    Under hydrostatic pressure, this is simply the phreatic level. The method in 
    this class comes in when the initial contion is not hydrostatic, and interpolation 
    between reference lines and head lines is needed.

    It is assumed that only the hydraulic situation is changed, not the geometry.
    The geometry is assumed equal in both stages (is also used as a reference line).
      
    Example:
        There are two stages, stage A and stage B. 
        Stage A: Represents the initial condition. It has a phreatic line (PL1), a ref. line in the aquifer 
                 (Ref. PL2) and a head line for the head in the aquifer (PL2). The surface level is the 
                 reference line for PL1.
        Stage B: Represents the changed condition. The water level is increased as has the head in the 
                 aquifer. An intrusion line is added (Ref. PL3) just above the ref. line of the aquifer. 
                 The hydraulic head along this line (PL3) is not influenced by the increased water level. 
                 Therefore the head along this line is equal to the head along this same ref. line in stage A.

        The intrusion head line (PL3) in stage B is determined by projecting the ref. line (Ref. PL3) to stage A 
        and interpolating the head along this line. The ref. line (Ref. PL3) lies between the surface level and 
        Ref. PL2 and is therefore an interpolation of PL1 and PL2.
    """

    def determine_z_bounds(self, waternet: Waternet, surface_level: SurfaceLine) -> tuple[float, float]:
        """Determines the outer z-bounds of the waternet and surface level.
        
        Returns:
            tuple[float, float]: The minimum and maximum z-values of the waternet and surface level.
        """

        z_coords: list[float] = []

        for ref_line in waternet.ref_lines:
            z_coords.extend(ref_line.z)

        for head_line in waternet.head_lines:
            z_coords.extend(head_line.z)

        for point in surface_level.points:
            z_coords.append(point.z)

        z_min = min(z_coords)
        z_max = max(z_coords)

        return z_min, z_max
    

    def collect_all_l_coords(
            self, 
            ref_line: ReferenceLine,
            waternet: Waternet, 
            surface_level: SurfaceLine
            ) -> list[float]:
        """Returns all unique l-coordinates from the waternet.
        
        The head line is determined by the reference lines it lies between and by 
        the head that belongs to these reference lines. The head line should 
        therefore be determined at every point along the horizontal axis (l-axis) 
        where the head and ref. lines of influence are defined. There could be 
        multiple ref. lines (and head lines) involved. At one point the interpolation
        could be between a ref. line (e.g. aquifer) and the surface level (e.g. open water), 
        at another point between two ref. lines. 
        
        The lines of influence are determined per point, but the necessary points are not
        known beforehand. Therefore, the l-coordinates are collected from ALL the lines 
        that could be of influence. These are the ref. lines, the head lines and the 
        surface level. Afterwards the head line is simplified.

        Args:
            ref_line: The reference line to collect the l-coordinates from.
              This is the reference line that is used to determine the head line.
            waternet: The waternet to collect the l-coordinates from.
              The head is determined from this waternet
            surface_level: The surface level to collect the l-coordinates from.
        
        Returns:
            list[float]: List of unique l-coordinates
        """

        l_coords: list[float] = []

        # Collect the l-coordinates from the ref. lines
        l_coords.extend(ref_line.l)

        for ref_line in waternet.ref_lines:
            l_coords.extend(ref_line.l)

        for head_line in waternet.head_lines:
            l_coords.extend(head_line.l)

        for point in surface_level.points:
            l_coords.append(point.l)

        # Remove duplicate l-coordinates
        l_coords = list(set(l_coords))

        # Sort the l-coordinates
        l_coords.sort()

        return l_coords

    def get_phreatic_line(self, waternet: Waternet) -> HeadLine:
        """Returns the phreatic line from the waternet.
        
        Returns:
            HeadLine: The phreatic line
        """

        phreatic_line = next((hl for hl in waternet.head_lines if hl.is_phreatic), None)

        if not phreatic_line:
            raise ValueError(
                f"No phreatic line found in the waternet"
                f"This is required for the interpolation of the head line in another stage"
                f"The following head lines are present: {', '.join([hl.name for hl in waternet.head_lines])}"
                )

        return phreatic_line

    def determine_ref_line_above_and_below(
            self, 
            l_coord: float,
            z_coord: float,
            lines: list[ReferenceLine | HeadLine | SurfaceLine],
            ) -> tuple[tuple[ReferenceLine | HeadLine | SurfaceLine | None, float | None], 
                       tuple[ReferenceLine | HeadLine | SurfaceLine | None, float | None]]:
        """Determines the ref. line below and above a given z-coordinate.
        
        Returns:
            tuple[tuple[ReferenceLine | HeadLine | SurfaceLine | None, float | None], 
                  tuple[ReferenceLine | HeadLine | SurfaceLine | None, float | None]]:
                (ref_line_below, z_below), (ref_line_above, z_above)
        """
        z_at_l: list[float] = []

        # Collect the z-coord of each (head/phreatic/ref.) line at the given l-coordinate
        for line in lines:
            # Equal l-coords are already shifted for all inputted ref/headlines
            # Equal l-coords are not allowed for SurfaceLines
            # This ensures a unique z-coord for each l-coord
            z = line.get_z_at_l(l_coord)
            z_at_l.append(z)

        # Select the relevant z-coords and sort them
        z_at_l_above = [z for z in z_at_l if z >= z_coord]
        z_at_l_below = [z for z in z_at_l if z <= z_coord]

        if z_at_l_above:
            z_above = min(z_at_l_above)
            i_z_above = z_at_l.index(z_above)
            ref_line_above = lines[i_z_above]
        else:
            z_above = None
            ref_line_above = None

        if z_at_l_below:
            z_below = max(z_at_l_below)
            i_z_below = z_at_l.index(z_below)
            ref_line_below = lines[i_z_below]
        else:
            z_below = None
            ref_line_below = None

        return (ref_line_below, z_below), (ref_line_above, z_above)

    
    def determine_head_line_from_ref_line(
            self, 
            ref_line: ReferenceLine | HeadLine | SurfaceLine, 
            ref_line_above_or_below: Literal["above", "below"],
            waternet: Waternet,
            ) -> HeadLine:
        """Determines the head line from the ref. line.
        
        Returns:
            HeadLine: The head line
        """

        # If the ref. line is a surface line, then the phreatic line is the head line
        if isinstance(ref_line, SurfaceLine):
            return self.get_phreatic_line(waternet)

        # If the ref. line is a head line (i.e. the phreatic line), then the
        # phreatic line is returned. This is a head line and reference line in one.
        if isinstance(ref_line, HeadLine):
            return ref_line

        # If the ref. line is a reference line, then the head line is determined
        # based on the position of the ref. line relative to ref. line where we
        # want to determine the head line.
        if isinstance(ref_line, ReferenceLine):
            head_line_name_top = ref_line.head_line_top
            head_line_name_bottom = ref_line.head_line_bottom

            # If the ref. line is above the ref. line where we want to determine the head line,
            # then the head line at the bottom of the ref. line has priority.
            if ref_line_above_or_below == "above":
                if head_line_name_bottom is not None:
                    head_line_name = head_line_name_bottom
                else:
                    head_line_name = head_line_name_top

            # If the ref. line is below the ref. line where we want to determine the head line,
            # then the head line at the top of the ref. line has priority.
            elif ref_line_above_or_below == "below":
                if head_line_name_top is not None:
                    head_line_name = head_line_name_top
                else:
                    head_line_name = head_line_name_bottom

            head_line = next(hl for hl in waternet.head_lines if hl.name == head_line_name)

            return head_line


    def determine_head_at_point(
            self, 
            l_coord: float, 
            z_coord: float, 
            ref_line_below: ReferenceLine | HeadLine | SurfaceLine | None, 
            z_below: float | None, 
            ref_line_above: ReferenceLine | HeadLine | SurfaceLine | None, 
            z_above: float | None,
            waternet: Waternet,
            ) -> float:
        """Determines the head at a given l-coordinate.
        
        Returns:
            float: The head at the given l-coordinate
        """

        # No ref. line above - point lies above the phreatic level, head = 0
        if ref_line_above is None:
            return 0.
        
        # No ref. line below. The point lies below the lowest ref. line, which is ref_line_above
        # The head line is determined from the ref. line above
        if ref_line_below is None:
            head_line = self.determine_head_line_from_ref_line(
                ref_line=ref_line_above,
                ref_line_above_or_below="above",
                waternet=waternet
                )
            return head_line.get_z_at_l(l_coord)

        # Both ref. lines are present - determine both head lines
        head_line_below = self.determine_head_line_from_ref_line(
            ref_line=ref_line_below,
            ref_line_above_or_below="below",
            waternet=waternet
            )
        head_below = head_line_below.get_z_at_l(l_coord)

        head_line_above = self.determine_head_line_from_ref_line(
            ref_line=ref_line_above,
            ref_line_above_or_below="above",
            waternet=waternet
            )
        head_above = head_line_above.get_z_at_l(l_coord)
        
        if head_below == head_above:
            return head_below
        
        # This is a very unlikely situation - an error is raised in case it occurs
        if z_below == z_above and head_below != head_above:
            raise ValueError(
                f"An error occurred while determining the head at point ({l_coord}, {z_coord}) at "
                f"a previous stage by interpolation. At this point the reference line {ref_line_below.name} "
                f"lies on the reference line where to determine the head by interpolation. The ref. line "
                f"{ref_line_below.name} has a different head below and above the line, so the head cannot "
                f"be determined unambiguously."
                )

        # Here the heads and z-values are all different - we determine the head by interpolation
        if z_below != z_above and head_below != head_above:
            head = head_below + (head_above - head_below) * (z_coord - z_below) / (z_above - z_below)

            return head

        raise ValueError(
            "An error occurred while determining the head by interpolation based on another stage"
        )           
            
    def create_line(
            self, 
            head_line_config: HeadLineConfig,
            ref_line: ReferenceLine, 
            interpolate_from_waternet: Waternet,
            surface_level: SurfaceLine
            ) -> HeadLine:
        """Creates a head line based on the hydraulic head along a reference line"""

        phreatic_line = self.get_phreatic_line(interpolate_from_waternet)

        head_line_l = self.collect_all_l_coords(
            ref_line=ref_line,
            waternet=interpolate_from_waternet, 
            surface_level=surface_level
            )
        head_line_z: list[float] = []

        for l_coord_ref in head_line_l:
            z_coord_ref = ref_line.get_z_at_l(l_coord_ref)

            (ref_line_below, z_below), (ref_line_above, z_above) = self.determine_ref_line_above_and_below(
                l_coord=l_coord_ref, 
                z_coord=z_coord_ref, 
                lines=[
                    *interpolate_from_waternet.ref_lines,
                    phreatic_line,
                    surface_level
                    ]
                )
            
            head = self.determine_head_at_point(
                l_coord=l_coord_ref, 
                z_coord=z_coord_ref, 
                ref_line_below=ref_line_below, 
                z_below=z_below,
                ref_line_above=ref_line_above,
                z_above=z_above,
                waternet=interpolate_from_waternet
            )

            head_line_z.append(head)

        # Simplify the head line
        head_line_l, head_line_z = simplify_line(
            x=head_line_l,
            y=head_line_z,
            tolerance=TOLERANCE_SIMPLIFY_LINE
        )

        head_line = HeadLine(
            name=head_line_config.name_head_line,
            l=head_line_l,
            z=head_line_z,
            is_phreatic=head_line_config.is_phreatic
        )

        return head_line
    

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
            (bottom_ref_line_points[0][0], soil_bottom),
            *bottom_ref_line_points, 
            (bottom_ref_line_points[-1][0], soil_bottom)
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
    water_level_set_config: WaterLevelSetConfig
    offset_method_collection: LineOffsetMethodCollection
    subsoil: Optional[Subsoil] = None
    previous_waternet: Optional[Waternet] = None    

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
    
    @model_validator(mode='after')
    def validate_previous_waternet(self) -> Self:
        waternet_methods = [
            hlc for hlc in self.waternet_config.head_line_configs
            if hlc.head_line_method_type == HeadLineMethodType.INTERPOLATE_FROM_WATERNET
            ]
        
        if waternet_methods and self.previous_waternet is None:
            raise ValueError(
                "A previous stage with a waternet scenario is required input when creating head lines"
                f"with the method '{HeadLineMethodType.INTERPOLATE_FROM_WATERNET}'. No waternet is available"
                f"for generating the head lines '{[hlc.name_head_line for hlc in waternet_methods]}'."
            )
        
        return self
    

class PhreaticLineModifier(BaseModel):
    """Factory for modifying a head line generated with an offset method, 
    representing a phreatic line"""

    geometry: Geometry
    _outward_intersection: Optional[tuple[float, float]] = None
    _inward_intersection: Optional[tuple[float, float]] = None

    def process_outward_intersection_phreatic_line(self, head_line: HeadLine) -> HeadLine:
        surface_level_outward = self.geometry.char_point_profile.get_point_by_type(
            CharPointType.SURFACE_LEVEL_WATER_SIDE)
        # With the offset method, the first point is always the most outward
        water_level_outward = next(z for l, z in zip(head_line.l, head_line.z) if l == surface_level_outward.l)

        self._outward_intersection = self.geometry.get_intersection(
            level=water_level_outward,
            from_char_point=CharPointType.DIKE_CREST_WATER_SIDE,
            to_char_point=CharPointType.SURFACE_LEVEL_WATER_SIDE,
            search_direction=Side.WATER_SIDE
        )

        if self._outward_intersection is not None:
            # Delete head line points between the intersection and the most outward point
            l_outward = surface_level_outward.l
            l_intersection = self._outward_intersection[0]

            # Two conditions, accounting for two possible geometry orientations
            # The <=/>= is to prevent double points at the intersection
            points = [(l, z) for l, z in zip(head_line.l, head_line.z)
                      if not (l_intersection <= l < l_outward
                              or l_intersection >= l > l_outward)]

            # Put the intersection at the right location
            # With the offset method, it is always the second point because
            # the first point is the most outward and we deleted all points in between
            points.insert(1, self._outward_intersection)

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
            # Delete head line points between the intersection and the last point of tkhe head line
            l_inward = surface_level_inward.l
            l_intersection = self._inward_intersection[0]

            # Two conditions, accounting for two possible geometry orientations
            # The <=/>= is to prevent double points at the intersection
            points = [(l, z) for l, z in zip(head_line.l, head_line.z)
                      if not (l_intersection <= l < l_inward
                              or l_intersection >= l > l_inward)]

            # Put the intersection at the right location
            # With the offset method, it is always the second to last point because
            # the last point is the most inward and we deleted all points in between
            points.insert(-1, self._inward_intersection)

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

        # Make shapely polygon of the surface line (possibly with offset)
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

        surface_line_l_original = [p.l for p in self.geometry.surface_line.points]
        l_surf_min = min(surface_line_l_original)
        l_surf_max = max(surface_line_l_original)

        # Create a bounding box of the surface line and phreatic line
        bbox = Polygon([
            (l_surf_min, polygon_bottom),
            (l_surf_min, polygon_top),
            (l_surf_max, polygon_top),
            (l_surf_max, polygon_bottom),
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

        elif isinstance(phreatic_polygon_corrected, GeometryCollection):
            # Ignore Points and LineStrings (LineStrings can occur in some situations, but are not logical to include)
            polygons = geometry_to_polygons(phreatic_polygon_corrected)

            if len(polygons) != 1:
                raise ValueError("Something went wrong when maximizing the phreatic line to the surface level")
            
            phreatic_line_string = get_polygon_top_or_bottom(polygons[0], top_or_bottom="top")
        
        else:
            raise ValueError("Something went wrong when maximizing the phreatic line to the surface level")

        phreatic_points = [(p[0], p[1]) for p in phreatic_line_string.coords]

        l_coords, z_coords = add_outer_points_if_missing(
            l_coords=[p[0] for p in phreatic_points],
            z_coords=[p[1] for p in phreatic_points],
            geometry=self.geometry,
        )
        head_line.l = l_coords
        head_line.z = z_coords

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
            raise ValueError("An error occurred correcting the reference lines between the "
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
    aquifers: list[Aquifer] = Field(default_factory=list)

    def create_head_lines_with_offsets(self, water_level_set: dict[str, float | None]) -> list[HeadLine]:
        head_lines: list[HeadLine] = []

        for head_line_config in self.input.waternet_config.head_line_configs:
            # Get the method to create the head line
            if head_line_config.head_line_method_type != HeadLineMethodType.OFFSETS:
                continue

            method = self.input.offset_method_collection.get_by_name(head_line_config.offset_method_name)

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

    def create_head_lines_interpolate_from_waternet(
            self,
            ref_lines: list[ReferenceLine]
            ) -> list[HeadLine]:
        
        head_lines: list[HeadLine] = []
        
        for head_line_config in self.input.waternet_config.head_line_configs:
            if head_line_config.head_line_method_type != HeadLineMethodType.INTERPOLATE_FROM_WATERNET:
                continue

            # Get the ref. line that is used to create the head line
            coupled_ref_lines = [
                rl for rl in ref_lines
                if rl.head_line_top == head_line_config.name_head_line
                or rl.head_line_bottom == head_line_config.name_head_line
            ]

            # If there is no coupled ref. line, then it is an aquifer method in 
            # a calculation where the aquifer is not present. We skip it.
            if len(coupled_ref_lines) == 0:
                continue

            if len(coupled_ref_lines) > 1:
                raise ValueError(
                    f"The head line '{head_line_config.name_head_line}' is "
                    f"assigned to multiple ref. lines in the scenario '{self.input.waternet_config.name_waternet_scenario}'."
                    f"This is not allowed when using the method '{HeadLineMethodType.INTERPOLATE_FROM_WATERNET}'." 
                    f"The ref. lines are '{[rl.name for rl in coupled_ref_lines]}'."
                )
            
            ref_line = coupled_ref_lines[0]
            
            head_line = InterpolateHeadLineFromWaternet().create_line(
                head_line_config=head_line_config,
                ref_line=ref_line,
                interpolate_from_waternet=self.input.previous_waternet,
                surface_level=self.input.geometry.surface_line
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
            self.aquifers = get_aquifers_from_subsoil(self.input.subsoil, self.input.geometry)

            # Create the reference lines per aquifer
            for aquifer in self.aquifers:
                # If there is an intermediate aquifer and a method for it, then use that method
                if aquifer.aquifer_type == AquiferType.INTERMEDIATE_AQUIFER:
                    if intermediate_aquifer_conf:
                        config = intermediate_aquifer_conf
                    else:
                        # An intermediate aquifer method is mandatory because of the way intrusion methods
                        # are implemented. It uses the (non-modified) name of the reference line as it is 
                        # given in the input. See IntrusionMethod.create_line()
                        raise ValueError(
                            f"An intermediate aquifer is present, but there is no method for it "
                            f"in the waternet scenario '{self.input.waternet_config.name_waternet_scenario}.' "
                            f"Please add a method for it."
                        )
                
                # Otherwise it is a AQUIFER, so use the method with type AQUIFER
                else:
                    if aquifer_conf:
                        config = aquifer_conf
                    else:
                        raise ValueError(
                            f"An aquifer is present, but there is no method for it "
                            f"in the waternet scenario '{self.input.waternet_config.name_waternet_scenario}.' "
                            f"Please add a method for it."
                        )

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
        if self.aquifers:
            intermediate_aquifer_present = any(
                aquifer.aquifer_type == AquiferType.INTERMEDIATE_AQUIFER 
                for aquifer in self.aquifers
            )
            deep_aquifer_present = any(
                aquifer.aquifer_type == AquiferType.AQUIFER 
                for aquifer in self.aquifers
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
                aquifers=self.aquifers
            )

            ref_lines.append(ref_line)
        
        return ref_lines

    def create_waternet(self) -> Waternet:
        # Get water levels - this is based on the geometry name since water levels are location bound
        location_water_levels = self.input.water_level_collection.get_by_name(self.input.geometry.name)

        # Check if the water levels are present in the location water levels
        for k, v in self.input.water_level_set_config.water_levels.items():
            if v is not None and v not in location_water_levels:
                raise ValueError(
                    f"The water level '{v}' used for the water level variable '{k}' was not found."
                    )

        # Rename the water levels to the generalized water level names
        water_level_set = {
            k: location_water_levels[v]
            for k, v in self.input.water_level_set_config.water_levels.items()
            if v is not None
        }

        # Create the head lines - first only with offsets
        head_lines: list[HeadLine] = []
        head_lines.extend(self.create_head_lines_with_offsets(water_level_set=water_level_set))

        # Create the reference lines - The order is important here
        ref_lines: list[ReferenceLine] = []
        
        ref_lines.extend(self.create_ref_lines_aquifers_method())
        ref_lines.extend(self.create_ref_lines_offset_method(water_level_set=water_level_set))
        ref_lines.extend(self.create_ref_lines_intrusion_method(current_ref_lines=ref_lines))

        # Correct the crossing of reference lines between the surface level and the first aquifer
        if self.aquifers:
            ref_lines = ReferenceLineCorrector.correction_surface_level_and_first_aquifer(
                waternet_creator_input=self.input,
                ref_lines=ref_lines,
                soil_bottom=self.input.subsoil.get_bottom(),
                aquifers=self.aquifers
            )
        
        # Correct between the aquifers, if there is more than one
        if len(self.aquifers) > 1:
            for i in range(len(self.aquifers) - 1):
                top_aquifer = next(aq for aq in self.aquifers if aq.order_id == i + 1)
                bottom_aquifer = next(aq for aq in self.aquifers if aq.order_id == i)

                ref_lines = ReferenceLineCorrector.correction_between_aquifers(
                    top_aquifer=top_aquifer,
                    bottom_aquifer=bottom_aquifer,
                    ref_lines=ref_lines,
                    soil_bottom=self.input.subsoil.get_bottom()
                )
                
        # Correct the ref. lines with equal l-values to ensure a correct order and
        # add outer points to the ref. lines if they are not yet present
        for ref_line in ref_lines:
            points = [[l, z] for l, z in zip(ref_line.l, ref_line.z)]
            points = shift_points_with_equal_l_values(points)
            ref_line.l = [p[0] for p in points]
            ref_line.z = [p[1] for p in points]

            ref_line.l, ref_line.z = add_outer_points_if_missing(
                l_coords=ref_line.l,
                z_coords=ref_line.z,
                geometry=self.input.geometry
            )

        # Determine head line at ref line from another stage (if applicable)
        head_lines.extend(self.create_head_lines_interpolate_from_waternet(ref_lines=ref_lines))

        # Correct the head lines with equal l-values to ensure a correct order
        for head_line in head_lines:
            points = [[l, z] for l, z in zip(head_line.l, head_line.z)]
            points = shift_points_with_equal_l_values(points)
            head_line.l = [p[0] for p in points]
            head_line.z = [p[1] for p in points]

        return Waternet(head_lines=head_lines, ref_lines=ref_lines)
