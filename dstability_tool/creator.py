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

from input_reader import UserInputStructure


def input_to_models(input_structure: UserInputStructure) -> List[Model]:
    """Creates Model objects from the user input"""
    models: List[Model] = []

    # Create Geometry objects from the input
    geometries = create_geometries(
        surface_line_collection=input_structure.surface_lines,
        char_point_collection=input_structure.char_points,
        char_type_left_point=CharPointType.SURFACE_LEVEL_LAND_SIDE
    )

    # Create a Model for each calculation dictionary
    for calc_config in input_structure.calc_configs:
        scenarios = []

        for scenario in calc_config["scenarios"]:
            stages = []

            for stage in scenario["stages"]:
                geometry = next((geom for geom in geometries if geom.name == stage["geometry"]), None)

                if geometry is None:
                    raise ValueError(f"Could not find geometry with name {stage['geometry']}")

                surface_line = geometry.surface_line
                profile_positions = input_structure.soil_profile_positions[stage["profile_position_name"]]

                soil_profiles_and_coords = [
                    (sp, coord) for name, coord in profile_positions.items()
                    for sp in input_structure.soil_profiles.profiles
                    if sp.name == name
                ]

                # Create the subsoil from the surfaceline, soil_profiles and the positions
                # TODO: Dit kan efficienter want sommige stages hebben dezelfde subsoil. Geen prio
                subsoil = subsoil_from_soil_profiles(
                    surface_line=surface_line,
                    soil_profiles=[sp[0] for sp in soil_profiles_and_coords],
                    transitions=[sp[1] for sp in soil_profiles_and_coords][1:],  # Skip the first coords, it's None
                )
                if stage["load_name"] is not None:
                    load = input_structure.loads.get_by_name(stage["load_name"])

                else:
                    load = None

                # Create the state points
                if stage["apply_state_points"]:
                    state_points = create_state_points_from_subsoil(
                        subsoil=subsoil,
                        soil_collection=input_structure.soils,
                        state_type='POP'
                    )
                else:
                    state_points = None

                # Create the stage
                stages.append(
                    Stage(
                        name=stage["stage_name"],
                        notes="",
                        geometry=geometry,
                        subsoil=subsoil,
                        state_points=state_points,
                        load=load,
                        waternet=input_structure.waternets.get_waternet(
                            calc_config["calc_name"],
                            scenario['scenario_name'],
                            stage['stage_name'])
                    ))

            scenarios.append(Scenario(
                name=scenario["scenario_name"],
                notes="",
                stages=stages
            ))

        models.append(
            Model(
                name=calc_config["calc_name"],
                soil_collection=input_structure.soils,
                scenarios=scenarios
            )
        )

    return models
