"""
Main module for dstability_tool
"""
from input_reader import RawUserInput, UserInputStructure
from creator import input_to_models
from dstability_toolbox.model import create_d_stability_models

INPUT_FILE_PATH = "Invoer D-Stability tool.xlsx"

if __name__ == "__main__":
    # Reading the input sheet
    raw_user_input = RawUserInput.read_from_file(INPUT_FILE_PATH)

    # Convert the input to models. input_to_models has al the logic
    print(type(raw_user_input))
    input_structure = UserInputStructure.from_raw_input(raw_user_input)
    # models = input_to_models(raw_user_input)


    # Create new calculations from the DStability models
    # dm_list = create_d_stability_models(models)

    # Export the DStabilityModels to .stix

    # Run the calculations

    # Read and export the calculation results

    # Space to fiddle around
    # print(input_structure.model_dump())
    print(input_structure.surface_lines)
    print(input_structure.char_points)
