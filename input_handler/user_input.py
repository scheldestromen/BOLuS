from typing import Optional

from pydantic import BaseModel

from dstability_toolbox.calculation_settings import GridSettingsSetCollection
from dstability_toolbox.geometry import (CharPointsProfileCollection,
                                         SurfaceLineCollection)
from dstability_toolbox.loads import LoadCollection
from dstability_toolbox.soils import SoilCollection
from dstability_toolbox.subsoil import SoilProfileCollection
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
    soil_profile_positions: dict[
        str, dict[str, float | None]
    ]  # TODO: omzetten naar class
    loads: LoadCollection
    waternets: WaternetCollection
    grid_settings: GridSettingsSetCollection
    model_configs: list[ModelConfig]


def model_configs_from_list(model_config_list: list[dict]) -> list[ModelConfig]:
    return [
        ModelConfig.model_validate(model_config) for model_config in model_config_list
    ]
