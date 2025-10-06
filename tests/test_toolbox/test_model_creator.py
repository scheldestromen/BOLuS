 # from soil profile position
 # from subsoil collection

import os
from unittest import TestCase
import json

from bolus.toolbox.subsoil import SubsoilCollection, Subsoil, SubsoilInputType, SoilPolygon
from bolus.toolbox.model_creator import UserInputStructure, input_to_models

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURE_DIR = os.path.join(os.path.dirname(TEST_DIR), "fixtures")
INPUT_STRUCTURE_JSON_PATH = os.path.join(FIXTURE_DIR, "input_structure_example.json")


class TestModelCreator(TestCase):
    def setUp(self):
        with open(INPUT_STRUCTURE_JSON_PATH) as f:
            self.input_structure = UserInputStructure.model_validate(json.load(f))

    def test_input_to_models(self):
        """Large integration test"""
        input_to_models(self.input_structure)

    def test_input_to_models_with_subsoil(self):
        self.input_structure.model_configs[0].scenarios[0].stages[0].subsoil_input_type = SubsoilInputType.FROM_SUBSOIL_COLLECTION
        self.input_structure.model_configs[0].scenarios[0].stages[0].subsoil_name = "subsoil_1"
        self.input_structure.subsoils = SubsoilCollection(
            subsoils=[
                Subsoil(name="subsoil_1", soil_polygons=[SoilPolygon(soil_type="Klei siltig", points=[(0, 0), (1, 0), (1, 1), (0, 1)])])
            ]
        )
        input_to_models(self.input_structure)

