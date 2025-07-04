"""
Main module for excel_tool
"""

import os
from pathlib import Path

from toolbox.geolib_utils import dm_batch_execute
from toolbox.modifier import create_d_stability_model
from toolbox.results import DStabilityResultExporter
from toolbox.model_creator import input_to_models
from excel_tool.input_reader import ExcelInputReader, RawInputToUserInputStructure

INPUT_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "Invoer BOLuS.xlsx"
)


if __name__ == "__main__":
    abort_input = input(
        "\nBestaande berekeningen in de uitvoermap worden mogelijk overschreven indien "
        "deze dezelfde naam hebben als nieuwe berekeningen. Wilt u doorgaan?"
        "\n\nType het antwoord en druk op enter (j/n)\n"
    )

    if abort_input.lower() != "j":
        print("De tool wordt afgebroken...")
        exit()

    # Reading the Excel to RawUserInput
    raw_user_input = ExcelInputReader.read_from_file(INPUT_FILE_PATH)

    # Convert the RawUserInput to models
    input_structure = RawInputToUserInputStructure.convert(raw_user_input)

    # Output directory - must NOT be synced with OneDrive when calculations are run
    output_dir = input_structure.settings.output_dir

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Uitvoer")
    else:
        if not os.path.exists(output_dir):
            raise FileNotFoundError(f"Output directory '{output_dir}' does not exist")

    # Create the models
    models = input_to_models(input_structure)

    # Create new DStabilityModels calculations from the models
    dm_dict = {model.name: create_d_stability_model(model) for model in models}

    # Export the DStabilityModels to .stix
    for name, dm in dm_dict.items():
        dm.serialize(Path(os.path.join(output_dir, f"{name}.stix")))

    # Run the calculations
    if input_structure.settings.execute_calculations:   
        dm_list = dm_batch_execute([dm for dm in dm_dict.values()])

        # Read and export the calculation results
        exporter = DStabilityResultExporter(dm_list=dm_list)
        exporter.export_results(
            output_path=os.path.join(output_dir, "D-Stability Rekenresultaten.xlsx")
        )
