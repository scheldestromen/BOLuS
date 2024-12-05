from typing import List
from pydantic import BaseModel

from dstability_toolbox.geometry import  SurfaceLine


class SoilLayer(BaseModel):
    """Representation of a 1D soil layer"""


class SoilProfile(BaseModel):
    """Representation of a 1D soil profile"""


class SoilProfileCollection(BaseModel):
    """Collection of 1D soil profiles of type SoilProfile"""
    pass


class SoilPolygon(BaseModel):
    """Representation of a 2D soil layer"""
    # TODO: Deze is misschien niet nodig, gezien geolib een gelijke heeft. Misschien ook wel.
    pass


class Subsoil(BaseModel):
    """Representation of a 2D subsoil schematization. This is a collection of (multiple)
    SoilPolygon's belonging to the same cross-sectional schematization."""
    polygons: List[SoilPolygon]


def subsoil_from_single_profile(soil_profile: SoilProfile, surface_line: SurfaceLine) -> Subsoil:
    """Creates an instance of Subsoil from a single SoilProfile."""
    # TODO: Dit is eigenlijk een bijzonder geval van 'multiple_soil_profiles'


def subsoil_from_multiple_profiles(soil_profiles: List[SoilProfile], transitions: List[float]) -> Subsoil:
    """Creates an instance of Subsoil from multiple SoilProfile's."""
    # Check lengte soil_profiles en lengte sides
