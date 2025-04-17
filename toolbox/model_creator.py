"""
Creates d_stability_toolbox Model objects from the user input
"""

from typing import List, Optional

from pydantic import BaseModel

from toolbox.calculation_settings import GridSettingsSetCollection
from toolbox.geometry import (CharPointType, Geometry,
                              create_geometries, SurfaceLineCollection, CharPointsProfileCollection)
from toolbox.loads import LoadCollection
from toolbox.model import Model, Scenario, Stage
from toolbox.soils import SoilCollection
from toolbox.state import create_state_points_from_subsoil
from toolbox.subsoil import subsoil_from_soil_profiles, SoilProfileCollection, SoilProfilePositionSetCollection, add_revetment_profile_to_subsoil, RevetmentProfileBlueprintCollection
# from toolbox.water import WaternetCollection
from toolbox.water_creater import WaterLevelCollection, WaternetConfigCollection, LineOffsetMethodCollection, WaternetCreator


class GeneralSettings(BaseModel):
    """Set of general settings"""

    calculate_l_coordinates: bool
    min_soil_profile_depth: float
    execute_calculations: bool
    apply_waternet: bool
    output_dir: Optional[str] = None


class StageConfig(BaseModel):
    """Represents a user-inputted configuration of a stage.

    Attributes:
        stage_name (str): The name of the stage.
        geometry_name (str): The name of the geometry belonging to this stage.
        soil_profile_position_name (str): The name of the soil profile position belonging to this stage.
        revetment_profile_name (str): Optional. The name of the revetment profile belonging to this stage.
        apply_state_points (bool): Whether the state points should be applied to this stage.
        load_name (str): Optional.The name of the load belonging to this stage."""

    stage_name: str
    geometry_name: str
    soil_profile_position_name: str
    waternet_scenario_name: Optional[str]
    revetment_profile_name: Optional[str]
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


# TODO: Hier zit nu zowel de waternetcollection als de WaternetConfigCollection. Hoe dit netjes aan te pakken in de workflow?
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
    soil_profile_positions: SoilProfilePositionSetCollection
    water_levels: WaterLevelCollection
    waternet_configs: WaternetConfigCollection
    headline_offset_methods: LineOffsetMethodCollection
    revetment_profile_blueprints: RevetmentProfileBlueprintCollection
    loads: LoadCollection
    # waternets: WaternetCollection
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

    profile_positions = input_structure.soil_profile_positions.get_by_name(
        stage_config.soil_profile_position_name
    )

    soil_profiles_and_coords = [
        (input_structure.soil_profiles.get_by_name(position.profile_name), position.l_coord)
        for position in profile_positions.soil_profile_positions
    ]

    # Create subsoil from the surface line, soil_profiles and the transitions
    subsoil = subsoil_from_soil_profiles(
        surface_line=surface_line,
        soil_profiles=[sp[0] for sp in soil_profiles_and_coords],
        transitions=[sp[1] for sp in soil_profiles_and_coords][1:],  # Skip the first coords, it's None
        min_soil_profile_depth=input_structure.settings.min_soil_profile_depth,
    )

    if stage_config.revetment_profile_name is not None:
        revetment_profile_blueprint = input_structure.revetment_profile_blueprints.get_by_name(
            stage_config.revetment_profile_name
        )

        revetment_profile=revetment_profile_blueprint.create_revetment_profile(
                char_point_profile=geometry.char_point_profile
        )

        subsoil = add_revetment_profile_to_subsoil(
            subsoil=subsoil,
            revetment_profile=revetment_profile,
            surface_line=surface_line,
        )

    if input_structure.settings.apply_waternet:
        waternet_config = input_structure.waternet_configs.get_by_name(
            stage_config.waternet_scenario_name
        )
        waternet_creator = WaternetCreator(
            geometry=geometry,
            subsoil=subsoil,
            waternet_config=waternet_config,
            water_level_collection=input_structure.water_levels,
            offset_method_collection=input_structure.headline_offset_methods,
        )
        waternet = waternet_creator.create_waternet()

    else:
        waternet = None

    # waternet = input_structure.waternets.get_waternet(
    #     calc_name=calc_name,
    #     scenario_name=scenario_name,
    #     stage_name=stage_config.stage_name,
    # ) if input_structure.settings.apply_waternet else None

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
        waternet=waternet,
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
        A Scenario object."""
    
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
        List[Model]: A list of Model objects."""
    
    models: List[Model] = []

    # Create Geometry objects from the input
    geometries = create_geometries(
        surface_line_collection=input_structure.surface_lines,
        char_point_collection=input_structure.char_points,
        char_type_left_point=CharPointType.SURFACE_LEVEL_LAND_SIDE,  # TODO: Invoer maken voor deze parameter
        calculate_l_coordinates=input_structure.settings.calculate_l_coordinates,
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
