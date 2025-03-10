"""
Main module for input_handler
"""

import os
from pathlib import Path

from dstability_toolbox.execute import dm_batch_execute
from dstability_toolbox.modifier import create_d_stability_model
from dstability_toolbox.results import DStabilityResultExporter
from input_handler.creator import input_to_models
from input_handler.input_reader import ExcelInputReader, RawInputToUserInputStructure

# Werkmap dient niet gesynchroniseerd met OneDrive te zijn indien er gerekend wordt
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Rekenmap")
INPUT_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "Invoer D-Stability tool.xlsx"
)


if __name__ == "__main__":
    # Reading the Excel to RawUserInput
    raw_user_input = ExcelInputReader.read_from_file(INPUT_FILE_PATH)

    # Convert the RawInput to models. input_to_models has all the logic
    input_structure = RawInputToUserInputStructure.convert(raw_user_input)
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
