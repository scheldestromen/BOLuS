from geolib.soils import Soil as GLSoil
from geolib.models.dstability.internal import Waternet as GLWaternet
from geolib.models.dstability.internal import Stage as GLStage
from geolib.models.dstability.internal import CalculationSettings
from geolib.models import DStabilityModel


# TODO: docstring, test, en verwijderen van de andere overbodig geworden functies
def get_by_id(collection: list, item_id: str):
    if len(collection) == 0:
        raise ValueError(f"An emtpy collection was given. An item could not be found"
                         f"for id '{item_id}'")

    item = next(
        (item for item in collection if item_id == item.Id),
        None
    )

    if item is not None:
        return item

    raise ValueError(f"Item with id '{item_id}' was not found in the given collection with "
                     f"items of type {type(collection[0])}")


def get_soil_by_id(dm: DStabilityModel, soil_id: str) -> GLSoil:
    """
    Get soil by the given soil id.

    Args:
        dm: DStabilityModel
        soil_id: id of the soil

    Returns:
       The matching GEOLib Soil instance"""

    soil_collection = dm.soils

    for soil in soil_collection.Soils:
        if soil.Id == soil_id:
            return soil

    raise ValueError(f"Soil with id '{soil_id}' not found in the SoilCollection")


def get_waternet_by_id(dm: DStabilityModel, waternet_id: str) -> GLWaternet:
    """
    Get waternet by the given waternet id.

    Args:
        dm: DStabilityModel
        waternet_id: id of the soil

    Returns:
       The matching GEOLib Waternet instance"""

    waternet = next(
        (wn for wn in dm.datastructure.waternets if wn.Id == waternet_id),
        None,
    )

    if waternet is not None:
        return waternet

    raise ValueError(f"Waternet with ID '{waternet_id}' not found.")


def get_calculation_settings_by_id(dm: DStabilityModel, calc_settings_id: str) -> CalculationSettings:
    """Retrieve a calculation setting by its id from the DStabilityModel.

    Args:
        dm: DStabilityModel
        calc_settings_id: The id of the calculation setting to retrieve.

    Returns:
        The matching GEOLib CalculationSettings instance."""

    calculation_settings = dm.datastructure.calculationsettings
    calc_setting = next(
        (setting for setting in calculation_settings if calc_settings_id == setting.Id),
        None
    )

    if calc_setting is not None:
        return calc_setting

    raise ValueError(f"CalculationSetting with id '{calc_settings_id}' not found")


def get_result_by_id(dm: DStabilityModel, result_id: str):
    """Retrieve a result by its id from the DStabilityModel.

    Args:
        dm: DStabilityModel
        result_id: The id of the result to retrieve.

    Returns:
        The matching GEOLib Result instance."""

    results = dm.datastructure.results
    result = next(
        (res for res in results if result_id == res.Id),
        None
    )

    if result is not None:
        return result

    raise ValueError(f"Result with ID '{result_id}' not found.")


def get_all_calculations(dm: DStabilityModel):
    """Get all calculations from the DStabilityModel

    Args:
        dm: DStabilityModel

    Returns:
        list of PersistableCalculations"""

    return [calc for scenario in dm.scenarios for calc in scenario.Calculations]


def get_calculation_settings_by_result_id(dm: DStabilityModel, result_id: str) -> CalculationSettings:
    """Retrieve a calculation setting by its associated result ID from the DStabilityModel.

    Args:
        dm: The model containing calculation settings.
        result_id: The id of the result associated with the calculation setting to retrieve.

    Returns:
        The matching GEOLib CalculationSettings instance."""

    calculations = [calc for scenario in dm.scenarios for calc in scenario.Calculations]
    calculation = next(calc for calc in calculations if calc.ResultId == result_id)

    return get_calculation_settings_by_id(dm=dm, calc_settings_id=calculation.CalculationSettingsId)


def get_stage_by_indices(dm: DStabilityModel, stage_index: int, scenario_index: int) -> GLStage:
    """Get stage by the given scenario and stage indices

    Args:
        dm: The DStabilityModel containing stages and scenarios.
        stage_index: The index of the stage to retrieve.
        scenario_index: The index of the scenario to retrieve the stage from.

    Returns:
        The matching GEOLib Stage instance."""

    try:
        scenario = dm.datastructure.scenarios[scenario_index]
        stage = scenario.Stages[stage_index]

    except IndexError:
        raise ValueError(f"No stage/scenario found with stage_index {stage_index}"
                         f"and scenario_index {scenario_index}")

    return stage
