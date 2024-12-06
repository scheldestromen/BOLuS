"""
Creates d_stability_toolbox Model objects from the user input
"""
from typing import List

from dstability_toolbox.model import Model
from input_reader import RawUserInput


def input_to_models(input_structure: RawUserInput) -> List[Model]:
    """Creates Model objects from the user input"""

    # Kies de juiste sequence.
    # Stel de benodigde invoer op voor de sequence
    # - bv. SoilCollection,
    # Niet iedere sequence gebruikt de zelfde invoer.