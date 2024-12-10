from pydantic import BaseModel, model_validator
from typing import Self, Optional

from geolib.geometry.one import Point as GLPoint
from shapely.geometry import Polygon

from dstability_toolbox.geometry import SurfaceLine, Point


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
    """Representation of a 2D soil layer"""
    soil_type: str
    points: list[tuple[float, float]]

    def to_geolib_points(self) -> list[GLPoint]:
        """Returns a list of GEOLib points"""
        gl_points = [GLPoint(x=x, z=z) for x, z in self.points]
        return gl_points

    @classmethod
    def from_shapely(cls, soil_type: str, polygon: Polygon) -> Self:
        """Creates a SoilPolygon from a Shapely Polygon"""
        if not isinstance(polygon, Polygon):
            raise ValueError(f"Input must be a Shapely Polygon but is of type {type(polygon)}")

        points = list(polygon.exterior.coords)[:-1]  # Remove repeated first point
        return cls(soil_type=soil_type, points=points)

    def to_shapely(self) -> Polygon:
        """Creates a Shapely Polygon from the SoilPolygon"""
        return Polygon(self.points)


class Subsoil(BaseModel):
    """Representation of a 2D subsoil schematization. This is a collection of (multiple)
    SoilPolygon's belonging to the same cross-sectional schematization."""
    soil_polygons: list[SoilPolygon]

    # TODO: Validate non-overlapping?


def subsoil_from_soil_profiles(
        surface_line: SurfaceLine,
        soil_profiles: list[SoilProfile],
        transitions: Optional[list[float]] = None,
        thickness_bottom_layer: float = 5
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

    if len(soil_profiles) != len(transitions) - 1:
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
        raise ValueError("One or more soil profile transitions lie beyond the surface line geometry")

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

            polygon = SoilPolygon(
                soil_type=layer.soil_type,
                points=[(left, top),
                        (right, top),
                        (right, bottom),
                        (left, bottom)]
            )

            soil_polygons.append(polygon)

    sub_soil = process_shared_polygon_points_in_subsoil(
        Subsoil(soil_polygons=soil_polygons)
    )

    return sub_soil


def add_shared_points_to_polygon(polygon: Polygon, polygons: list[Polygon]) -> Polygon:
    for other_poly in polygons:
        intersect = polygon.intersection(other_poly)

        # TODO: geometry_utils afmaken
        # intersect bepalen met andere polys
        # Intersect exploderen naar punten
        # Poly exploderen naar lijnen
        # Per lijnstuk punt toevoegen (wat als meerdere punten, pythagoras?)
        # Polygon bouwen
        # En door.

    return polygon


def process_shared_polygon_points_in_subsoil(subsoil: Subsoil) -> Subsoil:
    """
    Iterates through all soil polygons in the subsoil. For each soil polygon
    it checks if there are any other polygons that share the same points. If so,
    it adds the shared points to the polygon. This is necessary for creating
    valid geometries with GEOLib.

    Args:
        subsoil: A Subsoil object

    Returns:
        A Subsoil object with corrected polygons
    """
    soil_types = [poly.soil_type for poly in subsoil.soil_polygons]
    polygons = [poly.to_shapely() for poly in subsoil.soil_polygons]

    corrected_soil_polygons = []

    for soil_type, polygon in zip(soil_types, polygons):
        other_polygons = [poly for poly in polygons if poly != polygon]
        corrected_polygon = add_shared_points_to_polygon(polygon, other_polygons)

        corrected_soil_polygons.append(
            SoilPolygon.from_shapely(soil_type=soil_type, polygon=corrected_polygon)
        )

    return Subsoil(soil_polygons=corrected_soil_polygons)
