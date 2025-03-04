"""
Main module for input_handler
"""
import os
from pathlib import Path

from input_reader import RawUserInput, raw_input_to_user_input_structure
from creator import input_to_models
from dstability_toolbox.modifier import create_d_stability_model
from dstability_toolbox.execute import dm_batch_execute
from dstability_toolbox.results import DStabilityResultExporter

# Werkmap dient niet gesynchroniseerd met OneDrive te zijn indien er gerekend wordt
OUTPUT_DIR = r"C:\Users\danie\Documents\Rekenmap"
INPUT_FILE_PATH = "Invoer D-Stability tool.xlsx"


if __name__ == "__main__":
    # Reading the input sheet
    raw_user_input = RawUserInput.read_from_file(INPUT_FILE_PATH)

    # Convert the input to models. input_to_models has all the logic
    input_structure = raw_input_to_user_input_structure(raw_user_input)
    models = input_to_models(input_structure)

    # Create new DStability calculations from the DStability models
    dm_dict = {model.name: create_d_stability_model(model) for model in models}

    # Export the DStabilityModels to .stix
    for name, dm in dm_dict.items():
        dm.serialize(Path(os.path.join(OUTPUT_DIR, f"{name}.stix")))

    # Run the calculations
    if input_structure.settings.execute_calculations:
        dm_list = dm_batch_execute([dm for dm in dm_dict.values()])

        # Read and export the calculation results
        exporter = DStabilityResultExporter(dm_list=dm_list)
        exporter.export_results(
            output_path=os.path.join(OUTPUT_DIR, "D-Stability Rekenresultaten.xlsx")
            )
