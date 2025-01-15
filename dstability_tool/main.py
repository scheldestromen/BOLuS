"""
Main module for dstability_tool
"""
from input_reader import RawUserInput, UserInputStructure
from creator import input_to_models
from dstability_toolbox.modifier import create_d_stability_model

INPUT_FILE_PATH = "Invoer D-Stability tool.xlsx"

if __name__ == "__main__":
    # Reading the input sheet
    raw_user_input = RawUserInput.read_from_file(INPUT_FILE_PATH)

    # Convert the input to models. input_to_models has all the logic
    input_structure = UserInputStructure.from_raw_input(raw_user_input)
    models = input_to_models(input_structure)

    # Create new DStability calculations from the DStability models
    dm_dict = {model.name: create_d_stability_model(model) for model in models}

    # Export the DStabilityModels to .stix
    for name, dm in dm_dict.items():
        dm.serialize(f"{name}.stix")

    # Run the calculations

    # Read and export the calculation results

    # Space to fiddle around
    # print(input_structure.loads)
    # print(input_structure.model_dump())
    # print(input_structure.surface_lines)
    # print(input_structure.char_points)
    # print(input_structure.soils)
    # print(input_structure.soil_profiles)
    # print(input_structure)
