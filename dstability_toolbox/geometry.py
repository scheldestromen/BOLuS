from enum import StrEnum, auto
from math import isclose
from typing import Optional, Literal

from pydantic import BaseModel
from typing_extensions import List

from geolib.geometry.one import Point as GLPoint


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
        l: Length
    """
    x: float
    y: float
    z: float
    l: Optional[float] = None
    tolerance: float = 1e-4

    def __eq__(self, other):
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
        return ((self.x - other.x)**2 + (self.y - other.y)**2)**0.5


class CharPoint(Point):
    type: CharPointType


class ProfileLine(BaseModel):
    """Base class for SurfaceLine and CharPointProfile"""
    def check_l_coordinates_present(self):
        """Checks if the l-coordinates are present"""
        if not all(point.l is not None for point in self.points):
            raise ValueError(f"SurfaceLine {self.name} does not have (all the) l-coordinates")

    def check_l_coordinates_increasing(self):
        """Checks if the l-coordinates are monotonically increasing"""
        l_coords = [point.l for point in self.points]
        if l_coords != sorted(l_coords):
            raise ValueError(f"Profile {self.name} of type {type(self)} has "
                             f"non-monotonically increasing l-coordinates")

    def set_l_coordinates(
            self,
            left_point: Point,
            ref_point: Optional[Point] = None
    ):
        """Calculates the l-coordinates of the points.

        The l-axis is defined in the direction of the surface line
        in the x-y plane such that the surface line is defined in
        the l-z plane.

        Args:
            profile: The profile to calculate the l-coordinates for.
            left_point: The left point of the surface line. Should be
              on of the two outer points.
            ref_point: The reference point. Defines the origin of the
              l-axis. This point should be aligned with the SurfaceLine.
              If not specified then the left_point is the origin.
        """
        if ref_point:
            shift = ref_point.distance(left_point)
        else:
            shift = None

        for point in self.points:
            dist_from_left = point.distance(left_point)

            if shift:
                point.l = dist_from_left - shift


class CharPointsProfile(ProfileLine):
    """Represents the characteristic points of a profile"""
    name: str
    char_points: List[CharPoint]

    @classmethod
    def from_dict(cls, name, char_points_dict):
        """Instantiates a CharPointsProfile from a dictionary

        Points that have a value of -1 in x, y and z are not included in
        the collection

        Args:
            name: The name of the profile
            char_points_dict: The dictionary containing the characteristic points"""

        char_points = []

        for char_type in CharPointType:
            x = char_points_dict[f"x_{char_type}"]
            y = char_points_dict[f"y_{char_type}"]
            z = char_points_dict[f"z_{char_type}"]

            if x == -1 and y == -1 and z == -1:
                continue

            char_point = CharPoint(x=x, y=y, z=z, type=char_type)
            char_points.append(char_point)

        return cls(name=name, char_points=char_points)

    def get_point_by_type(self, char_type: CharPointType) -> CharPoint:
        """Returns the characteristic point of the given type"""
        for char_point in self.char_points:
            if char_point.type == char_type:
                return char_point

        raise ValueError(f"Characteristic point of type `{char_type.value}` "
                         f"was not found in profile {self.name}")


class SurfaceLine(ProfileLine):
    # Verzameling van punten behorende bij één berekening
    name: str
    points: List[Point]

    @classmethod
    def from_list(cls, name, point_list):
        """Instantiates a SurfaceLine from a flat list of points

        Args:
            name: The name of the SurfaceLine
            point_list: A flat list of points [x1, y1, z1, x2, y2, z2, ...]"""

        x = point_list[0::3]
        y = point_list[1::3]
        z = point_list[2::3]

        points = [Point(x=x, y=y, z=z) for x, y, z in zip(x, y, z)]

        return cls(name=name, points=points)


class SurfaceLineCollection(BaseModel):
    surface_lines: list[SurfaceLine]

    @classmethod
    def from_dict(cls, surface_lines_dict):
        """Parses the dictionary into a SurfaceLineCollection

        Args:
            surface_lines_dict (dict): The dictionary to parse. The keys should be the profile names
              and the values a flat list of points of that profile [x1, y1, z1, x2, y2, z2, ...]"""

        surface_lines = []

        for name, points in surface_lines_dict.items():
            surface_line = SurfaceLine.from_list(name=name, point_list=points)
            surface_lines.append(surface_line)

        return cls(surface_lines=surface_lines)

    def get_by_name(self, name: str) -> SurfaceLine:
        """Returns the SurfaceLine with the given name"""
        profile = next(
            (prof for prof in self.char_points_profiles if prof.name == name), None
        )
        if profile:
            return profile
        else:
            raise ValueError(f"Could not find profile with name {name}")

    def to_csv(self, file_path):
        """Exports the SurfaceLineCollection to a csv file"""
        raise NotImplementedError


class CharPointsProfileCollection(BaseModel):
    char_points_profiles: List[CharPointsProfile]

    @classmethod
    def from_dict(cls, char_points_dict):
        """Parses the dictionary into a CharPointsProfileCollection

        Args:
            char_points_dict: The dictionary to parse. The keys should be the
              profile names and the values dicts with the characteristic points,
              for example {x_surface_level_water_side: 0, y_surface_level_water_side:
              0, z_surface_level_water_side: 0, ...}"""

        char_point_profiles = []

        for name, char_points in char_points_dict.items():
            char_points_profile = CharPointsProfile.from_dict(name=name, char_points_dict=char_points)
            char_point_profiles.append(char_points_profile)

        return cls(char_points_profiles=char_point_profiles)

    def get_by_name(self, name: str) -> CharPointsProfile:
        """Returns the CharPointsProfile with the given name"""
        profile = next(
            (prof for prof in self.char_points_profiles if prof.name == name), None
        )
        if profile:
            return profile
        else:
            raise ValueError(f"Could not find profile with name {name}")

    def to_csv(self, file_path):
        """Exports the SurfaceLineCollection to a csv file"""
        raise NotImplementedError


class Geometry(BaseModel):
    """Represents the geometry elements belonging to a cross-section
    of a dike."""
    name: str
    surface_line: SurfaceLine
    char_point_profile: CharPointsProfile


def create_geometries(
        surface_line_collection: SurfaceLineCollection,
        char_point_collection: CharPointsProfileCollection,
        char_type_left_point: Literal[
            CharPointType.SURFACE_LEVEL_LAND_SIDE,
            CharPointType.SURFACE_LEVEL_WATER_SIDE
        ],
        char_type_ref_point: Optional[CharPointType] = None
) -> list[Geometry]:
    """Creates a list of Geometry objects.

    Args:
        surface_line_collection: The collection of surface lines
        char_point_collection: The collection of characteristic points
        char_type_left_point: The characteristic point type to use for
          the left point of the surface line. This can only be either
          of the outer points of the surface line
        char_type_ref_point: The characteristic point type to use for
          the reference point (l=0) of the surface line"""

    surf_names = [surf.name for surf in surface_line_collection.surface_lines]
    char_names = [char.name for char in char_point_collection.char_points_profiles]

    if set(surf_names) != set(char_names):
        raise ValueError(
            f"Each surface line should have a corresponding characteristic "
            f"point profile and vice versa. This is not the case."
            f"Missing in surface lines: {set(char_names) - set(surf_names)}"
            f"Missing in characteristic points: {set(surf_names) - set(char_names)}")

    geometries = []

    for surface_line in surface_line_collection.surface_lines:
        char_points_profile = char_point_collection.get_by_name(surface_line.name)

        left_point = char_points_profile.get_point_by_type(char_type_left_point)

        if char_type_ref_point:
            ref_point = char_points_profile.get_point_by_type(char_type_ref_point)
        else:
            ref_point = None

        # Set l-coordinates and check if they are increasing
        surface_line.set_l_coordinates(left_point=left_point, ref_point=ref_point)
        char_points_profile.set_l_coordinates(left_point=left_point, ref_point=ref_point)

        surface_line.check_l_coordinates_increasing()
        char_points_profile.check_l_coordinates_increasing()

        geometries.append(
            Geometry(
                name=surface_line.name,
                surface_line=surface_line,
                char_point_profile=char_points_profile
            )
        )

    return geometries


def get_geometry_by_name(name: str, geometries: List[Geometry]) -> Geometry:
    pass
