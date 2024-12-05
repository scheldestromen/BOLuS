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
    # Karakteristieke punten behorende tot één dwarsprofiel
    name: str
    char_points: List[CharPoint]


class GeometryElementCollection(BaseModel):
    # Idee om from_csv en get_set_by_name gezamenlijk te gebruiken
    pass


class SurfaceLine(BaseModel):
    # Verzameling van punten behorende bij één berekening
    name: str
    points: List[Point]


class SurfaceLineCollection(BaseModel):
    # o.a. t.b.v. inlezen surface_lines.csv
    surface_lines: List[SurfaceLine]

    # TODO: verder uitdenken - Bv gebruik csv vs. Excel i.r.t. de Excel-module en invoersheet. Eigenlijk import
    #       helemaal scheiden
    @classmethod
    def from_json(cls):
        pass

    def to_csv(self, file_path):
        pass

    def get_by_name(self, name):
        pass


class CharPointsProfileCollection(BaseModel):
    # t.b.v. inlezen charpoints.csv
    char_points_profiles: List[CharPointsProfile]

    @classmethod
    def from_csv(cls, file_path):
        pass

    @classmethod
    def from_excel(cls, file_path):
        pass

    def to_csv(self, file_path):
        pass

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
