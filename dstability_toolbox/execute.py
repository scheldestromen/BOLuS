from pathlib import Path

from geolib.models import DStabilityModel
import concurrent.futures
import time
import random




def batch_execute(dm_list: list[DStabilityModel]):
    for dm in dm_list:
        dm.execute()


# Example function for heavy computation
def heavy_calculation(x):
    x.execute()
    # time.sleep(1)  # Simulate computation time
    # return x * x  # Example calculation


# Parallel execution
def run_parallel_calculations(data):
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = list(executor.map(heavy_calculation, data))

    return results

# Three options
# - ThreadPoolExecutor()
# - ProcessPoolExecutor()
# - asyncio


# Example usage
if __name__ == "__main__":
    DIR = r"C:\Users\danie\OneDrive - Kentrop Development\Werkmap\02 Projecten\KD008 - WSS D-Stability tool\04 Code\dstability_tool\input_handler"

    dm_batch = []

    for i in range(1, 4):
        dm = DStabilityModel()
        dm.parse(Path(DIR + rf'\Berekening {i}.stix'))
        dm_batch.append(dm)
        print(dm.filename)

    # large_batch = dm_batch * 10
    start_time = time.time()

    results = run_parallel_calculations(dm_batch)

    # print("Results:", results)
    print(f"Time taken: {time.time() - start_time:.2f} seconds")

