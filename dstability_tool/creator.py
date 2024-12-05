"""
Creates d_stability_toolbox Model objects from the user input
"""
from typing import List

from dstability_toolbox.model import Model
from input_reader import InputStructure


def input_to_models(input_structure: InputStructure) -> List[Model]:
    """Creates Model objects from the user input"""
