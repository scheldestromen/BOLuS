"""
Creates d_stability_toolbox Model objects from the user input
"""

from typing import List, Optional

from pydantic import BaseModel

from dstability_toolbox.calculation_settings import GridSettingsSetCollection
from dstability_toolbox.geometry import (CharPointType, Geometry,
                                         create_geometries, SurfaceLineCollection, CharPointsProfileCollection)
from dstability_toolbox.loads import LoadCollection
from dstability_toolbox.model import Model, Scenario, Stage
from dstability_toolbox.soils import SoilCollection
from dstability_toolbox.state import create_state_points_from_subsoil
from dstability_toolbox.subsoil import subsoil_from_soil_profiles, SoilProfileCollection
from dstability_toolbox.water import WaternetCollection


class GeneralSettings(BaseModel):
    """Set of general settings"""

    min_soil_profile_depth: float
    execute_calculations: bool


class StageConfig(BaseModel):
    """Represents a user-inputted configuration of a stage.

    Attributes:
        stage_name (str): The name of the stage.
        geometry_name (str): The name of the geometry belonging to this stage.
        soil_profile_position_name (str): The name of the soil profile position belonging to this stage.
        apply_state_points (bool): Whether the state points should be applied to this stage.
        load_name (str): The name of the load belonging to this stage."""

    stage_name: str
    geometry_name: str
    soil_profile_position_name: str
    apply_state_points: bool
    load_name: Optional[str]


class ScenarioConfig(BaseModel):
    """
    Represents a user-inputted configuration of a scenario.

    Attributes:
        scenario_name (str): The name of the scenario.
        stages (list[StageConfig]): A list of stage configurations for the scenario.
        grid_settings_set_name (Optional[str]): The name of the grid settings set associated with the scenario.
    """

    scenario_name: str
    stages: list[StageConfig]
    grid_settings_set_name: Optional[str]


class ModelConfig(BaseModel):
    """
    Represents a user-inputted configuration of a model.

    Attributes:
        calc_name (str): The name of the model.
        scenarios (list[ScenarioConfig]): A list of scenario configurations for the model.
    """

    calc_name: str
    scenarios: list[ScenarioConfig]


class UserInputStructure(BaseModel):
    """Represents the user-inputted data.

    It contains collections of different types of input such as surface lines
    and soils. The attribute model_configs is a list of ModelConfig objects,
    which contain references to the other collections. For example, a
    ModelConfig object specifies which surface line to use for a certain
    calculation. This makes it possible to create a D-Stability calculation
    model with all the necessary information from the user input."""

    settings: GeneralSettings
    surface_lines: SurfaceLineCollection
    char_points: CharPointsProfileCollection
    soils: SoilCollection
    soil_profiles: SoilProfileCollection
    soil_profile_positions: dict[str, dict[str, float | None]]  # TODO: omzetten naar class
    loads: LoadCollection
    waternets: WaternetCollection
    grid_settings: GridSettingsSetCollection
    model_configs: list[ModelConfig]


def create_stage(
    stage_config: StageConfig,
    scenario_name: str,
    calc_name: str,
    geometries: List[Geometry],
    input_structure: UserInputStructure,
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
    geometry = next(
        (geom for geom in geometries if geom.name == stage_config.geometry_name), None
    )

    if geometry is None:
        raise ValueError(
            f"Could not find geometry with name {stage_config.geometry_name}"
        )

    surface_line = geometry.surface_line
    profile_positions = input_structure.soil_profile_positions[
        stage_config.soil_profile_position_name
    ]

    soil_profiles_and_coords = [
        (sp, coord)
        for name, coord in profile_positions.items()
        for sp in input_structure.soil_profiles.profiles
        if sp.name == name
    ]

    # Create subsoil from the surface line, soil_profiles and the transitions
    subsoil = subsoil_from_soil_profiles(
        surface_line=surface_line,
        soil_profiles=[sp[0] for sp in soil_profiles_and_coords],
        transitions=[sp[1] for sp in soil_profiles_and_coords][
            1:
        ],  # Skip the first coords, it's None
        min_soil_profile_depth=input_structure.settings.min_soil_profile_depth,
    )

    load = (
        input_structure.loads.get_by_name(stage_config.load_name)
        if stage_config.load_name is not None
        else None
    )

    # Create the state points
    state_points = (
        create_state_points_from_subsoil(
            subsoil=subsoil, soil_collection=input_structure.soils, state_type="POP"
        )
        if stage_config.apply_state_points
        else None
    )

    # Create the stage
    return Stage(
        name=stage_config.stage_name,
        notes="",
        geometry=geometry,
        subsoil=subsoil,
        state_points=state_points,
        load=load,
        waternet=input_structure.waternets.get_waternet(
            calc_name, scenario_name, stage_config.stage_name
        ),
    )


def create_scenario(
    scenario_config: ScenarioConfig,
    calc_name: str,
    geometries: List[Geometry],
    input_structure: UserInputStructure,
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
    stages = [
        create_stage(
            stage_config=stage,
            scenario_name=scenario_config.scenario_name,
            calc_name=calc_name,
            geometries=geometries,
            input_structure=input_structure,
        )
        for stage in scenario_config.stages
    ]

    if scenario_config.grid_settings_set_name is not None:
        grid_settings_set = input_structure.grid_settings.get_by_name(
            scenario_config.grid_settings_set_name
        )
    else:
        grid_settings_set = None

    return Scenario(
        name=scenario_config.scenario_name,
        notes="",
        stages=stages,
        grid_settings_set=grid_settings_set,
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
        char_type_left_point=CharPointType.SURFACE_LEVEL_LAND_SIDE,
    )

    # Create a Model for each calculation dictionary
    for model_config in input_structure.model_configs:
        scenarios = [
            create_scenario(
                scenario, model_config.calc_name, geometries, input_structure
            )
            for scenario in model_config.scenarios
        ]

        models.append(
            Model(
                name=model_config.calc_name,
                soil_collection=input_structure.soils,
                scenarios=scenarios,
            )
        )

    return models
