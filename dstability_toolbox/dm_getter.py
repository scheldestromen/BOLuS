from typing import Any

from geolib.models import DStabilityModel
from geolib.models.dstability.internal import CalculationSettings
from geolib.models.dstability.internal import Stage as GLStage


def get_by_id(collection: list[Any], item_id: str) -> Any:
    """Get an item by its id from a collection

    Args:
        collection: The collection to search in. The collection should be a list of items with an Id attribute.
        item_id: The id of the item to search for

    Returns:
        The item with the given id"""

    if len(collection) == 0:
        raise ValueError(
            f"An emtpy collection was given. An item could not be found"
            f"for id '{item_id}'"
        )

    item = next(
        (item for item in collection if item_id == getattr(item, "Id", None)), None
    )

    if item is not None:
        return item

    raise ValueError(
        f"Item with id '{item_id}' was not found in the given collection with "
        f"items of type {type(collection[0])}"
    )


def get_all_calculations(dm: DStabilityModel):
    """Get all calculations from the DStabilityModel

    Args:
        dm: DStabilityModel

    Returns:
        list of PersistableCalculations"""

    return [calc for scenario in dm.scenarios for calc in scenario.Calculations]


def get_calculation_settings_by_result_id(
    dm: DStabilityModel, result_id: str
) -> CalculationSettings:
    """Retrieve a calculation setting by its associated result ID from the DStabilityModel.

    Args:
        dm: The model containing calculation settings.
        result_id: The id of the result associated with the calculation setting to retrieve.

    Returns:
        The matching GEOLib CalculationSettings instance."""

    calculations = [calc for scenario in dm.scenarios for calc in scenario.Calculations]
    calculation = next(calc for calc in calculations if calc.ResultId == result_id)

    return get_by_id(
        collection=dm.datastructure.calculationsettings,
        item_id=calculation.CalculationSettingsId,
    )


# TODO: voor later
# def get_soil_id_by_layer_id(dm, layer_id, scenario_index, stage_index):
#     """Functie geeft collectie van grondlagen van een stage
#
#     Args:
#         dm: DStabilityModel van d-geolib
#         stage_id: stage ID van gewenste stage
#         layer_id: layer ID van gewenste grondlaag
#
#     Returns:
#         Soil ID van het grondtype in een grondlaag"""
#
#     soil_layers = dm._get_soil_layers(scenario_index=scenario_index, stage_index=stage_index)
#
#     for soil_layer in soil_layers.SoilLayers:
#         if soil_layer.LayerId == layer_id:
#             return soil_layer.SoilId


def get_stage_by_indices(
    dm: DStabilityModel, stage_index: int, scenario_index: int
) -> GLStage:
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
        raise ValueError(
            f"No stage/scenario found with stage_index {stage_index}"
            f"and scenario_index {scenario_index}"
        )

    return stage
