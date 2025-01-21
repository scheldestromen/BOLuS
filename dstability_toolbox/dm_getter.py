from geolib.soils import Soil as GLSoil
from geolib.models.dstability.internal import Waternet as GLWaternet
from geolib.models.dstability.internal import Stage as GLStage
from geolib.models import DStabilityModel


def get_soil_by_id(soil_id: str, dm: DStabilityModel) -> GLSoil:
    """
    Get soil by the given soil id.

    Args:
        soil_id: id of the soil
        dm: DStabilityModel

    Returns:
       The GEOLib soil object
    """
    # TODO: Opnemen in geolib
    soil_collection = dm.soils

    for soil in soil_collection.Soils:
        if soil.Id == soil_id:
            return soil

    raise ValueError(f"Soil with id '{soil_id}' not found in the SoilCollection")


def get_waternet_by_id(waternet_id: str, dm: DStabilityModel) -> GLWaternet:
    """
    Get waternet by the given waternet id.

    Args:
        waternet_id: id of the soil
        dm: DStabilityModel

    Returns:
       The GEOLib Waternet object
    """
    for waternet in dm.datastructure.waternets:
        if waternet.Id == waternet_id:
            return waternet

    raise ValueError(f"Waternet with id '{waternet_id}' not found")


def get_stage_by_indices(dm: DStabilityModel, stage_index: int, scenario_index: int) -> GLStage:
    """Get stage by the given scenario and stage indices"""
    try:
        scenario = dm.datastructure.scenarios[scenario_index]
        stage = scenario.Stages[stage_index]

    except IndexError:
        raise ValueError(f"No stage/scenario found with stage_index {stage_index}"
                         f"and scenario_index {scenario_index}")

    return stage
