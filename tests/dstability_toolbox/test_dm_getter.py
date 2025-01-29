import os
from pathlib import Path
from unittest import TestCase
from dstability_toolbox.dm_getter import get_waternet_by_id, get_stage_by_indices, get_soil_by_id
from geolib.models import DStabilityModel

FIXTURE_DIR = os.path.join(os.path.dirname(os.getcwd()), 'fixtures')
DSTABILITY_DIR = os.path.join(FIXTURE_DIR, 'dstability')


class TestDmGetter(TestCase):
    def setUp(self):
        self.dm = DStabilityModel()
        self.dm.parse(Path(os.path.join(DSTABILITY_DIR, 'test_1.stix')))

    def test_get_waternet_by_id(self):
        waternet_id = '45'
        waternet = get_waternet_by_id(waternet_id, self.dm)
        self.assertEqual(waternet.Id, waternet_id)

    def test_get_waternet_by_id_non_existent_id(self):
        waternet_id = 'non_existent_id'

        with self.assertRaises(ValueError):
            get_waternet_by_id(waternet_id, self.dm)

    def test_get_stage_by_indices(self):
        expected_stage_label = 'Norm'
        scenario_index = 0
        stage_index = 1
        stage = get_stage_by_indices(self.dm, scenario_index=scenario_index, stage_index=stage_index)
        self.assertEqual(stage.Label, expected_stage_label)

    def test_get_stage_by_indices_non_existent_indices(self):
        scenario_index = 0
        stage_index = 1000

        with self.assertRaises(ValueError):
            get_stage_by_indices(self.dm, scenario_index=scenario_index, stage_index=stage_index)

    def test_get_soil_by_id(self):
        expected_soil_name = 'Klei'
        soil_id = '5'
        soil = get_soil_by_id(soil_id, self.dm)
        self.assertEqual(soil.Name, expected_soil_name)

    def test_get_soil_by_id_non_existent_soil_id(self):
        soil_id = 'non_existent_soil_id'

        with self.assertRaises(ValueError):
            get_soil_by_id(soil_id, self.dm)
