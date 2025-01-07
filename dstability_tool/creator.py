"""
Creates d_stability_toolbox Model objects from the user input
"""
from typing import List

from dstability_toolbox.geometry import SurfaceLineCollection, CharPointsProfileCollection, create_geometries, \
    CharPointType
from dstability_toolbox.model import Model, Scenario, Stage
from dstability_toolbox.soils import SoilCollection
from dstability_toolbox.subsoil import Subsoil, subsoil_from_soil_profiles, SoilProfileCollection
from dstability_toolbox.state import create_state_points_from_subsoil

from input_reader import RawUserInput


def input_to_models(input_structure: RawUserInput) -> List[Model]:
    """Creates Model objects from the user input"""

    # In input hoor te zitten of het om een STBI/STBU berekening gaat en bijbehorende waterspanningen
    #   Mogelijkheid is om op basis hiervan een sequence te kiezen, maar nu eerst gewoon hier.
    # Stel de benodigde invoer op voor de sequence
    # - bv. SoilCollection,
    # Niet iedere sequence gebruikt de zelfde invoer.

    surface_line_collection = SurfaceLineCollection.from_dict(input_structure.surface_lines)
    char_point_collection = CharPointsProfileCollection.from_dict(input_structure.char_points)
    soil_collection = SoilCollection.from_list(input_structure.soil_params)
    soil_profile_collection = SoilProfileCollection.from_dict(input_structure.soil_profiles)

    geometries = create_geometries(
        surface_line_collection=surface_line_collection,
        char_point_collection=char_point_collection,
        char_type_left_point=CharPointType.SURFACE_LEVEL_LAND_SIDE
    )

    # Proefberekening
    geometry = geometries[0]
    surface_line = geometry.surface_line

    subsoil = subsoil_from_soil_profiles(
        surface_line=surface_line,
        soil_profiles=soil_profile_collection.profiles,  # dit zijn er 2
        transitions=[80],
    )

    state_points = create_state_points_from_subsoil(
        subsoil=subsoil,
        soil_collection=soil_collection,
        state_type='POP'
    )

    model = Model(
        name="test_2.stix",
        soil_collection=soil_collection,
        scenarios=[
            Scenario(
                name="Basis",
                stages=[
                    Stage(
                        name="Dagelijks",
                        notes="Stage voor dagelijkse omstandigheden",
                        geometry=geometries[0],
                        subsoil=subsoil,
                        state_points=state_points
                    ),
                    Stage(
                        name="Hoogwater",
                        notes="Stage voor hoogwater",
                        geometry=geometries[0],
                        subsoil=subsoil,
                    )
                ]
            )
        ],
    )

    return [model]
