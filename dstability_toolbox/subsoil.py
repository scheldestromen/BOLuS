from geolib import DStabilityModel
from geolib.models.dstability.internal import PersistableLayer
from pydantic import BaseModel, model_validator
from typing import Self, Optional

from geolib.geometry.one import Point as GLPoint
from shapely.geometry import Polygon
from shapely.ops import polygonize
from shapely import unary_union, LineString

from dstability_toolbox.geometry import SurfaceLine
from dstability_toolbox.dm_getter import get_soil_by_id
from utils.geometry_utils import geometry_to_polygons


class SoilLayer(BaseModel):
    """Representation of a 1D soil layer"""
    soil_type: str
    top: float


class SoilProfile(BaseModel):
    """Representation of a 1D soil profile"""
    name: str
    layers: list[SoilLayer]

    @model_validator(mode='after')
    def check_descending_tops(self) -> Self:
        tops = [layer.top for layer in self.layers]

        if tops != sorted(tops, reverse=True):
            raise ValueError(
                f"The soil layers in the soil profile {self.name} are not in descending order. "
                f"Make sure each top is lower than the previous one."
            )

        return self


class SoilProfileCollection(BaseModel):
    """Collection of 1D soil profiles of type SoilProfile"""
    profiles: list[SoilProfile]

    @classmethod
    def from_dict(cls, soil_profile_dict: dict):
        profiles = []

        for name, layer_dicts in soil_profile_dict.items():
            layers = [SoilLayer.model_validate(layer_dict) for layer_dict in layer_dicts]
            profiles.append(SoilProfile(name=name, layers=layers))

        return cls(profiles=profiles)


class SoilPolygon(BaseModel):
    """Representation of a 2D soil layer

    Attributes:
        soil_type (str): Type of the soil
        points (list): List of tuples each representing 2D-coordinates
        dm_layer_id (str): Optional. The id of the layer in de DStabilityModel it belongs to
    """
    soil_type: str
    points: list[tuple[float, float]]
    dm_layer_id: Optional[str] = None

    @classmethod
    def from_geolib_layer(cls, soil_type: str, gl_layer: PersistableLayer) -> Self:
        """Creates a SoilPolygon from a GEOLib PersistableLayer"""
        points = [(point.X, point.Z) for point in gl_layer.Points]
        return cls(soil_type=soil_type, points=points, dm_layer_id=gl_layer.Id)

    def to_geolib_points(self) -> list[GLPoint]:
        """Returns a list of GEOLib points"""
        gl_points = [GLPoint(x=x, z=z) for x, z in self.points]
        return gl_points

    @classmethod
    def from_shapely(cls, soil_type: str, polygon: Polygon) -> Self:
        """Creates a SoilPolygon from a Shapely Polygon"""
        if not isinstance(polygon, Polygon):
            raise ValueError(f"Input must be a Shapely Polygon but is of type {type(polygon)}")

        points = list(polygon.exterior.coords)[:-1]  # Remove the repeated first point
        return cls(soil_type=soil_type, points=points)

    def to_shapely(self) -> Polygon:
        """Creates a Shapely Polygon from the SoilPolygon"""
        return Polygon(self.points)


class Subsoil(BaseModel):
    """Representation of a 2D subsoil schematization. This is a collection of (multiple)
    SoilPolygon's belonging to the same cross-sectional schematization.

    There is no check on whether soil polygons are overlapping.
    This should be implemented Subsoil and Geometry modifications are implemented

    Attributes:
        soil_polygons (list): List of SoilPolygon instances"""

    soil_polygons: list[SoilPolygon]

    @classmethod
    def from_geolib(cls, dm: DStabilityModel, scenario_index: int, stage_index: int) -> Self:
        soil_layers = dm._get_soil_layers(scenario_index=scenario_index, stage_index=stage_index)
        geometry = dm._get_geometry(scenario_index=scenario_index, stage_index=stage_index)

        soil_polygons = []

        for soil_layer in soil_layers.SoilLayers:
            soil = get_soil_by_id(soil_id=soil_layer.SoilId, dm=dm)
            layer = geometry.get_layer(id=soil_layer.LayerId)

            soil_polygon = SoilPolygon.from_geolib_layer(soil_type=soil.Code, gl_layer=layer)
            soil_polygons.append(soil_polygon)

        return cls(soil_polygons=soil_polygons)


def subsoil_from_soil_profiles(
        surface_line: SurfaceLine,
        soil_profiles: list[SoilProfile],
        transitions: Optional[list[float]] = None,
        thickness_bottom_layer: float = 5  # TODO: aanpassen naar minimale diepte?
) -> Subsoil:
    """Creates an instance of Subsoil from one or more SoilProfile objects.

    Args:
        soil_profiles: One or more SoilProfile objects
        transitions: List of transition l-coordinates. Optional in case of single profile.
          Must be in ascending order and of length len(soil_profiles) - 1
        surface_line: SurfaceLine object
        thickness_bottom_layer: The layer thickness of the bottom layer. Defaults to 5 m.
          The layer bottoms are determined by the layer underneath, but the bottom layer
          of a SoilProfile does not have that.

    """
    if transitions is None:
        transitions = []

    # Perform checks
    if len(soil_profiles) == 0:
        raise ValueError("At least one soil profile must be provided")

    if len(transitions) != len(soil_profiles) - 1:
        raise ValueError("The number of soil profiles does not match the number of transitions")

    if transitions != sorted(transitions):
        raise ValueError("The transitions of the soil profiles are not in ascending order")

    surface_line.check_l_coordinates_present()
    l_coords = [p.l for p in surface_line.points]

    # Determine the bounds of the soil profiles, which are the given transitions
    # and the minimum and maximum l-coordinates
    l_min = min(l_coords)
    l_max = max(l_coords)
    bounds = [l_min] + transitions + [l_max]

    if bounds != sorted(bounds):
        raise ValueError("One or more soil profile transitions lie beyond the surface line geometry."
                         f"The bounds are {l_min, l_max} and the transitions are {transitions}")

    geometry_points = ([(surface_line.points[0].l, -100)]
                       + [(p.l, p.z) for p in surface_line.points]
                       + [(surface_line.points[-1].l, -100)])
    geometry_polygon = Polygon(geometry_points)
    soil_polygons = []

    for i, soil_profile in enumerate(soil_profiles):
        left = bounds[i]
        right = bounds[i + 1]

        for j, layer in enumerate(soil_profile.layers):
            top = layer.top

            # If the current layer is the bottom layer then use bottom layer thickness
            if j + 1 == len(soil_profile.layers):
                bottom = top - thickness_bottom_layer
            else:
                bottom = soil_profile.layers[j + 1].top

            polygon = Polygon(
                [(left, top),
                 (right, top),
                 (right, bottom),
                 (left, bottom)]
            )

            # Adjust for the surface level
            geometry = polygon.intersection(geometry_polygon)
            polygons = geometry_to_polygons(geometry)

            for polygon in polygons:
                soil_polygon = SoilPolygon.from_shapely(soil_type=layer.soil_type, polygon=polygon)
                soil_polygons.append(soil_polygon)

    subsoil = Subsoil(soil_polygons=soil_polygons)

    return subsoil
