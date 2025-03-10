import concurrent.futures

from geolib.models import DStabilityModel


def dm_batch_execute(dm_list: list[DStabilityModel]):
    """Function for executing multiple DStabilityModels in parallel.
    The function uses a ProcessPoolExecutor. This is the preferred method for
    CPU-bound tasks.

    Args:
        dm_list: list of DStabilityModel instances"""

    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = list(executor.map(DStabilityModel.execute, dm_list))

    return results
