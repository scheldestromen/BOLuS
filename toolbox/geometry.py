from enum import StrEnum, auto
from math import isclose
from typing import Literal, Optional

from pydantic import BaseModel
from typing_extensions import List
from shapely.geometry import LineString

# TODO: Overwegen om validatie methodes toe te voegen.
#       Als iemand zelf een Geometry maakt is het niet gegarandeerd dat deze correct is.
# TODO: Overwegen om validatie (b.v. l-coordinates) met Pydantic te doen ('after')
#       Ook overwegen om l verplicht te maken, dan hoeven we de checks niet meer te doen.
# TODO: Overwegen om logica in CharPointsProfile te checken (bv. volgorde en aanwezigheid punten)

class CharPointType(StrEnum):
    SURFACE_LEVEL_WATER_SIDE = auto()
    TOE_CANAL = auto()
    START_CANAL = auto()
    DIKE_TOE_WATER_SIDE = auto()
    BERM_CREST_WATER_SIDE = auto()
    BERM_START_WATER_SIDE = auto()
    DIKE_CREST_WATER_SIDE = auto()
    TRAFFIC_LOAD_WATER_SIDE = auto()
    TRAFFIC_LOAD_LAND_SIDE = auto()
    DIKE_CREST_LAND_SIDE = auto()
    BERM_START_LAND_SIDE = auto()
    BERM_CREST_LAND_SIDE = auto()
    DIKE_TOE_LAND_SIDE = auto()
    DITCH_START_WATER_SIDE = auto()
    DITCH_BOTTOM_WATER_SIDE = auto()
    DITCH_BOTTOM_LAND_SIDE = auto()
    DITCH_START_LAND_SIDE = auto()
    SURFACE_LEVEL_LAND_SIDE = auto()


class Side(StrEnum):
    LAND_SIDE = auto()
    WATER_SIDE = auto()


class Point(BaseModel):
    """Represents a 3D-point

    Is meant to be a point in a cross-sectional line with points
    aligned in the x-y plane (straight line). The z represents the
    surface level. The l-coordinate represents the distance on the
    l-axis with respect to a chosen reference point (e.g. the line start).
    The l-axis is defined in the direction of the cross-sectional
    line. The point is based on a GEOLib Point.

    Attributes:
        x: The x-coordinate
        y: The y-coordinate
        z: Height coordinate
        l: Length coordinate (relative to a chosen reference point)
    """

    x: float
    y: float
    z: float
    l: Optional[float] = None
    tolerance: float = 1e-4

    def __eq__(self, other: "Point") -> bool:
        if isinstance(other, Point):
            return (
                isclose(self.x, other.x, abs_tol=self.tolerance)
                and isclose(self.y, other.y, abs_tol=self.tolerance)
                and isclose(self.z, other.z, abs_tol=self.tolerance)
            )
        else:
            return NotImplemented

    def distance(self, other: "Point") -> float:
        """Calculates the distance in the x-y plane between two points"""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class CharPoint(Point):
    type: CharPointType


class ProfileLine(BaseModel):
    """Base class for SurfaceLine and CharPointProfile"""

    def check_l_coordinates_present(self):
        """Checks if the l-coordinates are present"""
        if not all(point.l is not None for point in self.points):
            raise ValueError(
                f"SurfaceLine {self.name} does not have (all the) l-coordinates"
            )

    def check_l_coordinates_increasing(self):
        """Checks if the l-coordinates are monotonically increasing"""
        l_coords = [point.l for point in self.points]
        steps = [l_coords[i + 1] - l_coords[i] for i in range(len(l_coords) - 1)]
        steps_filtered = [step for step in steps if step != 0]

        if abs(sum(steps_filtered)) != sum([abs(step) for step in steps_filtered]):
            raise ValueError(
                f"Profile {self.name} of type {type(self)} has "
                f"non-monotonically increasing or decreasing "
                f"l-coordinates"
            )

    def set_l_coordinates(self, left_point: Point, ref_point: Optional[Point] = None):
        """Calculates the l-coordinates of the points.

        The l-axis is defined in the direction of the surface line
        in the x-y plane such that the surface line is defined in
        the l-z plane. The l- and z-axis give a 2D representation
        of the 3D-cross-sectional line.

        Args:
            left_point: The left point of the surface line. Should be
              on of the two outer points.
            ref_point: The reference point. Defines the origin of the
              l-axis. This point should be aligned with the SurfaceLine.
              If not specified then the left_point is the origin."""
        
        if left_point not in [self.points[0], self.points[-1]]:
            raise ValueError(
                f"The given argument `left_point` is neither one "
                f"of the outer points of the profile with name {self.name}. "
                f"This should be the case."
            )

        if ref_point:
            shift = ref_point.distance(left_point)
        else:
            shift = 0

        for point in self.points:
            dist_from_left = point.distance(left_point)
            point.l = dist_from_left - shift

        self.check_l_coordinates_increasing()

    def set_x_as_l_coordinates(self):
        """Sets the x-coordinates as the l-coordinates"""
        for point in self.points:
            point.l = point.x
        
        self.check_l_coordinates_increasing()


class CharPointsProfile(ProfileLine):
    """Represents the characteristic points of a profile

    Attributes:
        name: The name of the profile
        points: A list CharPoint instances representing the characteristic points"""

    name: str
    points: List[CharPoint]

    @classmethod
    def from_dict(
        cls, name: str, char_points_dict: dict[str, float]
    ) -> "CharPointsProfile":
        """Instantiates a CharPointsProfile from a dictionary

        Points that have a value of -1 in x, y and z are not included in
        the collection

        Args:
            name: The name of the profile
            char_points_dict: The dictionary containing the characteristic points"""

        char_points: list[CharPoint] = []

        for char_type in CharPointType:
            x = char_points_dict[f"x_{char_type}"]
            y = char_points_dict[f"y_{char_type}"]
            z = char_points_dict[f"z_{char_type}"]

            if x == -1 and y == -1 and z == -1:
                continue

            char_point = CharPoint(x=x, y=y, z=z, type=char_type)
            char_points.append(char_point)

        return cls(name=name, points=char_points)

    def get_point_by_type(self, char_type: CharPointType) -> CharPoint:
        """Returns the characteristic point of the given type"""

        for char_point in self.points:
            if char_point.type == char_type:
                return char_point

        raise ValueError(
            f"Characteristic point of type `{char_type.value}` "
            f"was not found in profile {self.name}"
        )

    def determine_l_direction_sign(self, direction: Side) -> int:
        """Determines in which way to move along the l-axis if a displacement
        is desired in the given direction.

        The l-axis of a profile can either be defined positive towards the landside (inward)
        or towards the waterside (outward). This function determines if the absolute value of
        a displacement (d) relative to a point along the l-axis with coordinate (l_ref) should
        be added or subtracted depending on the desired direction of displacement. Such that:
        l_new = l_ref + sign * d

        Args:
            direction: Side (Side.LAND_SIDE or Side.WATER_SIDE)

        Returns:
            sign: +1 or -1

        Example:
           The l-axis is defined positive towards the landside (inward) and a displacement
           is desired towards the waterside (outward) then the absolute value of the displacement
           should be subtracted. The result is therefore -1
        """
        self.check_l_coordinates_present()

        l_inward = self.get_point_by_type(CharPointType.SURFACE_LEVEL_LAND_SIDE).l
        l_outward = self.get_point_by_type(CharPointType.SURFACE_LEVEL_WATER_SIDE).l
        inward_positive = l_inward > l_outward  # Determine the direction of the l-axis

        # Determine the sign based on the direction and the direction of the l-axis
        if (
            direction == Side.LAND_SIDE
            and inward_positive
            or direction == Side.WATER_SIDE
            and not inward_positive
        ):
            sign = +1
        else:
            sign = -1

        return sign


class SurfaceLine(ProfileLine):
    """Representation of a cross-sectional profile of a dike.

    Attributes:
        name (str): The name of the profile
        points (list): A list of Point instances representing the profile"""

    name: str
    points: List[Point]

    @classmethod
    def from_list(cls, name: str, point_list: list[float]) -> "SurfaceLine":
        """Instantiates a SurfaceLine from a flat list of points

        Args:
            name: The name of the SurfaceLine
            point_list: A flat list of points [x1, y1, z1, x2, y2, z2, ...]"""

        x = point_list[0::3]
        y = point_list[1::3]
        z = point_list[2::3]

        if not len(x) == len(y) == len(z):
            raise ValueError(
                f"An incorrect number of points is given for the surface line with"
                f"name {name}. The length of `point_list` should be dividable by "
                f"three so that every point has a x, y and z coordinate."
            )

        points = [Point(x=x, y=y, z=z) for x, y, z in zip(x, y, z)]

        return cls(name=name, points=points)


class SurfaceLineCollection(BaseModel):
    """Representation a collection of SurfaceLines.

    Attributes:
        surface_lines (list): A list of SurfaceLine instances"""

    surface_lines: list[SurfaceLine]

    def get_by_name(self, name: str) -> SurfaceLine:
        """Returns the SurfaceLine with the given name"""

        profile = next((prof for prof in self.surface_lines if prof.name == name), None)
        if profile:
            return profile
        else:
            raise ValueError(f"Could not find profile with name {name}")


class CharPointsProfileCollection(BaseModel):
    """Representation a collection of CharPointsProfiles.

    Attributes:
        char_points_profiles (list): A list of CharPointsProfile instances"""

    char_points_profiles: List[CharPointsProfile]

    def get_by_name(self, name: str) -> CharPointsProfile:
        """Returns the CharPointsProfile with the given name"""
        profile = next(
            (prof for prof in self.char_points_profiles if prof.name == name), None
        )
        if profile:
            return profile
        else:
            raise ValueError(f"Could not find profile with name {name}")


class Geometry(BaseModel):
    """Represents the geometry elements belonging to a cross-section
    of a dike.

    Attributes:
        name: The name of the geometry
        surface_line: SurfaceLine instance representing the cross-sectional profile
        char_point_profile: CharPointProfile representing the characteristic points
    """

    name: str
    surface_line: SurfaceLine
    char_point_profile: CharPointsProfile

    # TODO: Unit tests
    def get_intersection(
            self, 
            level: float, 
            from_char_point: CharPointType = CharPointType.SURFACE_LEVEL_WATER_SIDE, 
            to_char_point: CharPointType = CharPointType.SURFACE_LEVEL_LAND_SIDE, 
            search_direction: Side = Side.LAND_SIDE
        ) -> tuple[float, float] | None:
        """Returns a 2D intersection point of the surface line and the given level.
        A search area is defined by the two characteristic points. Intersections
        outside this area are not considered. The search direction is the direction
        direction is the direction in which to search for the intersection. If multiple
        intersections are found, then the search direction determines which intersection
        is returned. If the direction is Side.LAND_SIDE, then the point laying most Side.WATER_SIDE
        point is returned.

        The characteristic points should be defined.
        
        Args:
            level: The level of the intersection
            from_char_point: The characteristic point type to use for the start of the intersection.
              By default, this is CharPointType.SURFACE_LEVEL_WATER_SIDE.
            to_char_point: The characteristic point type to use for the end of the intersection.
              By default, this is CharPointType.SURFACE_LEVEL_LAND_SIDE.
            search_direction: The direction in which to search for the intersection.
              By default, this is Side.LAND_SIDE.

        Returns:
            tuple[float, float]: The 2D intersection point based on the l- and z-coordinates
            of the surface line.
        """
        
        # Checks
        self.surface_line.check_l_coordinates_present()
        self.surface_line.check_l_coordinates_increasing()
        self.char_point_profile.check_l_coordinates_present()
        self.char_point_profile.check_l_coordinates_increasing()

        # Get subsection of the surface line between the two characteristic points
        from_point = self.char_point_profile.get_point_by_type(from_char_point)
        to_point = self.char_point_profile.get_point_by_type(to_char_point)

        points: list[Point] = []

        for point in self.surface_line.points:
            # Two conditions, accounting for two possible geometry orientations
            if point.l >= from_point.l and point.l <= to_point.l:
                points.append(point)

        # Get the intersection of the surface line and the given level
        l_coords = [p.l for p in points]
        min_l = min(l_coords)
        max_l = max(l_coords)

        shapely_surface_line = LineString([(p.l, p.z) for p in points])
        shapely_level = LineString([(min_l, level), (max_l, level)])

        intersection = shapely_surface_line.intersection(shapely_level)

        # TODO: Als het maaiveld een stukje gelijk loopt met het te snijden niveau, dan is het resultaat ook een stukje lijn -> Dan lijn exploderen tot punten.
        if intersection.geom_type == 'MultiPoint':
            intersection_points = list(intersection.geoms)
        elif intersection.geom_type == 'Point':
            intersection_points = [intersection]
        else:
            raise ValueError(f"Unexpected intersection type: {intersection.geom_type}")
        
        # Determine which the direction of the l-axis is
        sign = self.char_point_profile.determine_l_direction_sign(search_direction)

        # Get the intersection point
        # If the l-axis is positive in the search direction, then the right 
        # intersection point is the one with the minimum l-coordinate
        if sign == 1:
            intersection_point = min(intersection_points, key=lambda p: p.x)
        # Otherwise, it is the intersection point with the maximum l-coordinate
        else:
            intersection_point = max(intersection_points, key=lambda p: p.x)

        # Return the intersection point
        return intersection_point.x, intersection_point.y


def create_geometries(
    surface_line_collection: SurfaceLineCollection,
    char_point_collection: CharPointsProfileCollection,
    calculate_l_coordinates: bool = True,
    char_type_left_point: Optional[
        Literal[
            CharPointType.SURFACE_LEVEL_LAND_SIDE, CharPointType.SURFACE_LEVEL_WATER_SIDE
        ]
    ] = None,
    char_type_ref_point: Optional[CharPointType] = None,

) -> list[Geometry]:
    """Creates a list of Geometry objects.

    Args:
        surface_line_collection: The collection of surface lines
        char_point_collection: The collection of characteristic points
        calculate_l_coordinates: Whether the l-coordinates should be calculated
        char_type_left_point: The characteristic point type to use for
          the left point of the surface line. This can only be either
          of the outer points of the surface line. Only used if
          calculate_l_coordinates is True.
        char_type_ref_point: The characteristic point type to use for
          the reference point (l=0) of the surface line. Only used if
          calculate_l_coordinates is True.
        """

    # If calculate_l_coordinates, then we need char_type_left_point and char_type_ref_point
    if calculate_l_coordinates:
        if char_type_left_point is None:
            raise ValueError("A left point is required if calculate_l_coordinates is True (3D-geometry)")

    surf_names = [surf.name for surf in surface_line_collection.surface_lines]
    char_names = [char.name for char in char_point_collection.char_points_profiles]

    if set(surf_names) != set(char_names):
        raise ValueError(
            f"Each surface line should have a corresponding characteristic "
            f"point profile and vice versa. This is not the case. "
            f"Missing in surface lines: {set(char_names) - set(surf_names)} "
            f"Missing in characteristic points: {set(surf_names) - set(char_names)}"
        )

    geometries: list[Geometry] = []

    for surface_line in surface_line_collection.surface_lines:
        char_points_profile = char_point_collection.get_by_name(surface_line.name)

        if char_type_ref_point:
            ref_point = char_points_profile.get_point_by_type(char_type_ref_point)
        else:
            ref_point = None

        # Set l-coordinates and check if they are increasing
        if calculate_l_coordinates:
            left_point = char_points_profile.get_point_by_type(char_type_left_point)
            surface_line.set_l_coordinates(left_point=left_point, ref_point=ref_point)
            char_points_profile.set_l_coordinates(
                left_point=left_point, ref_point=ref_point
            )
        else:
            surface_line.set_x_as_l_coordinates()
            char_points_profile.set_x_as_l_coordinates()

        geometries.append(
            Geometry(
                name=surface_line.name,
                surface_line=surface_line,
                char_point_profile=char_points_profile,
            )
        )

    return geometries
