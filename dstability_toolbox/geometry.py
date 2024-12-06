from enum import StrEnum, auto

from pydantic import BaseModel
from typing_extensions import List

from geolib.geometry.one import Point


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


class CharPoint(Point):
    type: CharPointType


class CharPointsProfile(BaseModel):
    """Represents the characteristic points of a profile"""
    name: str
    char_points: List[CharPoint]

    @classmethod
    def from_dict(cls, name, char_points_dict):
        """Instantiates a CharPointsProfile from a dictionary

        Args:
            name: The name of the profile
            char_points_dict: The dictionary containing the characteristic points"""

        char_points = []

        for char_type in CharPointType:
            x = char_points_dict[f"x_{char_type}"]
            y = char_points_dict[f"y_{char_type}"]
            z = char_points_dict[f"z_{char_type}"]

            char_point = CharPoint(x=x, y=y, z=z, type=char_type)
            char_points.append(char_point)

        return cls(name=name, char_points=char_points)


class SurfaceLine(BaseModel):
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
    # o.a. t.b.v. inlezen surface_lines.csv
    surface_lines: List[SurfaceLine]

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

    def to_csv(self, file_path):
        pass

    def get_by_name(self, name):
        pass


class CharPointsProfileCollection(BaseModel):
    # t.b.v. inlezen charpoints.csv
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

    def get_by_name(self, name):
        pass


class Geometry(BaseModel):
    # Geometrie-elementen behorende bij een dwarsprofiel
    name: str
    surface_line: SurfaceLine
    char_point_set: CharPointsProfile


def create_geometries(
        surface_line_collection: SurfaceLineCollection,
        char_point_collection: CharPointsProfileCollection
) -> List[Geometry]:
    # Inlezen surfacelines en charpoints
    # Check of iedere naam in beide voorkomt
    pass


def get_geometry_by_name(name: str, geometries: List[Geometry]) -> Geometry:
    pass


def geometries_to_csv(self):
    # In geval van geometrie wijzigingen
    pass
