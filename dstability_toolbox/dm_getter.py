from geolib.soils import Soil as GLSoil
from geolib.models import DStabilityModel


def get_soil_by_id(soil_id: str, dm: DStabilityModel) -> GLSoil:
    """
    Get soil by the given soil id.

    Args:
        soil_id (str): id of the soil

    Returns:
       the soil object
    """
    # TODO: Opnemen in geolib
    soil_collection = dm.soils

    for soil in soil_collection.Soils:
        if soil.Id == soil_id:
            return soil

    raise ValueError(f"Soil with id '{soil_id}' not found in the SoilCollection")

