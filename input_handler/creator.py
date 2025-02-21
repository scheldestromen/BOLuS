"""
Creates d_stability_toolbox Model objects from the user input
"""
from typing import List

from dstability_toolbox.geometry import create_geometries, CharPointType, Geometry
from dstability_toolbox.model import Model, Scenario, Stage
from dstability_toolbox.subsoil import subsoil_from_soil_profiles
from dstability_toolbox.state import create_state_points_from_subsoil

from input_handler.user_input import UserInputStructure, ScenarioConfig, StageConfig


def create_stage(
    stage_config: StageConfig,
    scenario_name: str,
    calc_name: str,
    geometries: List[Geometry],
    input_structure: UserInputStructure
) -> Stage:
    """
    Creates a Stage object from the provided input.

    Args:
        stage_config: Stage configuration.
        scenario_name: The name of the scenario.
        calc_name: The name of the calculation.
        geometries: A list of Geometry objects.
        input_structure: The user-provided input structure.

    Returns:
        A Stage object.
    """
    geometry = next((geom for geom in geometries if geom.name == stage_config.geometry_name), None)

    if geometry is None:
        raise ValueError(f"Could not find geometry with name {stage_config.geometry_name}")

    surface_line = geometry.surface_line
    profile_positions = input_structure.soil_profile_positions[stage_config.soil_profile_position_name]

    soil_profiles_and_coords = [
        (sp, coord) for name, coord in profile_positions.items()
        for sp in input_structure.soil_profiles.profiles
        if sp.name == name
    ]

    # Create subsoil from the surface line, soil_profiles and the transitions
    subsoil = subsoil_from_soil_profiles(
        surface_line=surface_line,
        soil_profiles=[sp[0] for sp in soil_profiles_and_coords],
        transitions=[sp[1] for sp in soil_profiles_and_coords][1:],  # Skip the first coords, it's None
        min_soil_profile_depth=input_structure.settings.min_soil_profile_depth
    )

    load = input_structure.loads.get_by_name(stage_config.load_name) if stage_config.load_name is not None else None

    # Create the state points
    state_points = create_state_points_from_subsoil(
        subsoil=subsoil,
        soil_collection=input_structure.soils,
        state_type='POP'
    ) if stage_config.apply_state_points else None

    # Create the stage
    return Stage(
        name=stage_config.stage_name,
        notes="",
        geometry=geometry,
        subsoil=subsoil,
        state_points=state_points,
        load=load,
        waternet=input_structure.waternets.get_waternet(
            calc_name,
            scenario_name,
            stage_config.stage_name)
    )


def create_scenario(
    scenario_config: ScenarioConfig,
    calc_name: str,
    geometries: List[Geometry],
    input_structure: UserInputStructure
) -> Scenario:
    """
    Creates a Scenario object from the provided input.

    Args:
        scenario_config: Scenario configuration.
        calc_name: The name of the calculation.
        geometries: A list of Geometry objects.
        input_structure: The user-provided input structure.

    Returns:
        A Scenario object.
    """
    stages = [create_stage(stage_config=stage, scenario_name=scenario_config.scenario_name, calc_name=calc_name,
                           geometries=geometries, input_structure=input_structure) for stage in scenario_config.stages]

    if scenario_config.grid_settings_set_name is not None:
        grid_settings_set = input_structure.grid_settings.get_by_name(scenario_config.grid_settings_set_name)
    else:
        grid_settings_set = None

    return Scenario(
        name=scenario_config.scenario_name,
        notes="",
        stages=stages,
        grid_settings_set=grid_settings_set
    )


def input_to_models(input_structure: UserInputStructure) -> List[Model]:
    """Converts user input into a list of Model objects.

    Args:
        input_structure: The user-provided input structure

    Returns:
        List[Model]: A list of Model objects.
    """
    models: List[Model] = []

    # Create Geometry objects from the input
    geometries = create_geometries(
        surface_line_collection=input_structure.surface_lines,
        char_point_collection=input_structure.char_points,
        char_type_left_point=CharPointType.SURFACE_LEVEL_LAND_SIDE
    )

    # Create a Model for each calculation dictionary
    for model_config in input_structure.model_configs:
        scenarios = [
            create_scenario(scenario, model_config.calc_name, geometries, input_structure)
            for scenario in model_config.scenarios
        ]

        models.append(
            Model(
                name=model_config.calc_name,
                soil_collection=input_structure.soils,
                scenarios=scenarios
            )
        )

    return models
