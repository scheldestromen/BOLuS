import os
from pathlib import Path
from unittest import TestCase

from geolib.models import DStabilityModel
from geolib.models.dstability.internal import CalculationSettings

from dstability_toolbox.dm_getter import (
    get_all_calculations, get_by_id, get_calculation_settings_by_result_id,
    get_stage_by_indices)

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURE_DIR = os.path.join(os.path.dirname(TEST_DIR), "fixtures")
DSTABILITY_DIR = os.path.join(FIXTURE_DIR, "dstability")


class TestDmGetter(TestCase):
    def setUp(self):
        self.dm = DStabilityModel()
        self.dm.parse(Path(os.path.join(DSTABILITY_DIR, "test_1.stix")))

    def test_get_waternet_by_id(self):
        waternet_id = "47"
        waternet = get_by_id(collection=self.dm.waternets, item_id=waternet_id)
        self.assertEqual(waternet.Id, waternet_id)

    def test_get_waternet_by_id_non_existent_id(self):
        waternet_id = "non_existent_id"

        with self.assertRaises(ValueError):
            get_by_id(collection=self.dm.waternets, item_id=waternet_id)

    def test_get_stage_by_indices(self):
        expected_stage_label = "Norm"
        scenario_index = 0
        stage_index = 1
        stage = get_stage_by_indices(
            self.dm, scenario_index=scenario_index, stage_index=stage_index
        )
        self.assertEqual(stage.Label, expected_stage_label)

    def test_get_stage_by_indices_non_existent_indices(self):
        scenario_index = 0
        stage_index = 1000

        with self.assertRaises(ValueError):
            get_stage_by_indices(
                self.dm, scenario_index=scenario_index, stage_index=stage_index
            )

    def test_get_soil_by_id(self):
        expected_soil_name = "Klei"
        soil_id = "7"
        soil = get_by_id(collection=self.dm.soils.Soils, item_id=soil_id)
        self.assertEqual(soil.Name, expected_soil_name)

    def test_get_soil_by_id_non_existent_soil_id(self):
        soil_id = "non_existent_soil_id"

        with self.assertRaises(ValueError):
            get_by_id(collection=self.dm.soils.Soils, item_id=soil_id)

    def test_get_calculation_settings_by_id(self):
        calc_setting = get_by_id(
            collection=self.dm.datastructure.calculationsettings, item_id="75"
        )
        self.assertIsInstance(calc_setting, CalculationSettings)

    def test_get_calculation_settings_by_id_not_found(self):
        with self.assertRaises(ValueError):
            get_by_id(
                collection=self.dm.datastructure.calculationsettings, item_id="666"
            )

    def test_get_by_id_not_a_collection(self):
        with self.assertRaises(ValueError):
            get_by_id(collection=["item1", "item2"], item_id="2")

    def test_get_by_id_empty_collection(self):
        with self.assertRaises(ValueError):
            get_by_id(collection=[], item_id="2")

    def test_get_calculation_settings_by_result_id(self):
        calc_settings = get_calculation_settings_by_result_id(
            dm=self.dm, result_id="79"
        )
        self.assertIsInstance(calc_settings, CalculationSettings)
        self.assertEqual(calc_settings.Id, "76")

    def test_get_all_calculations(self):
        calcs = get_all_calculations(self.dm)
        self.assertEqual(len(calcs), 3)
