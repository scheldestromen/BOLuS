"""
Creates State objects
"""
from typing import Literal


from pydantic import BaseModel

from dstability_toolbox.soils import SoilCollection
from dstability_toolbox.subsoil import Subsoil
from utils.geometry_utils import determine_point_in_polygon


class StatePoint(BaseModel):
    """Representation of a state point in 2D

    Attributes:
        x (float): The x-coordinate of the state point
        z (float): The z-coordinate of the state point
        pop (float): The pre-overburden pressure of the state point
    """
    x: float
    z: float
    pop: float


def create_state_points_from_subsoil(
        subsoil: Subsoil,
        soil_collection: SoilCollection,
        state_type: Literal['POP', 'OCR'] = 'POP'  # 'Yield Stress' not because it is defined at a coordinate
) -> list[StatePoint]:
    """Creates a state point for every layer in the subsoil for which state
    parameters were given."""

    if state_type == 'POP':
        state_soil_names = [soil.gl_soil.name for soil in soil_collection.soils if soil.pop is not None]

    else:
        raise NotImplementedError('OCR state not implemented yet')

    state_polygons = [soil_poly for soil_poly in subsoil.soil_polygons if soil_poly.soil_type in state_soil_names]
    state_points = []

    for soil_polygon in state_polygons:
        polygon = soil_polygon.to_shapely()
        x, z = determine_point_in_polygon(polygon)
        soil = soil_collection.get_by_name(soil_polygon.soil_type)
        state_point = StatePoint(x=x, z=z, pop=soil.pop)
        state_points.append(state_point)

    return state_points
