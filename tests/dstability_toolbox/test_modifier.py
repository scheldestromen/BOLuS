import unittest
from unittest.mock import MagicMock

from geolib.models import DStabilityModel
from geolib.soils import Soil as GLSoil
from geolib.models.dstability.internal import SoilCollection as GLSoilCollection

from dstability_toolbox.modifier import (add_soil_collection, set_subsoil, add_state_points,
                                         add_uniform_load, set_waternet, create_d_stability_model)
from dstability_toolbox.soils import SoilCollection, Soil


class TestModifier(unittest.TestCase):
    def test_add_soil_collection(self):
        dm = DStabilityModel()
        dm.datastructure.soils = GLSoilCollection(Soils=[])  # Remove default soils

        soil_collection = SoilCollection(soils=[
            Soil(gl_soil=GLSoil(code='Klei'), pop=20),
            Soil(gl_soil=GLSoil(code='Zand'), pop=None)
        ])
        add_soil_collection(soil_collection, dm)
        self.assertEqual(len(dm.soils.Soils), len(soil_collection.soils))
    #
    # def test_set_subsoil(self):
    #     subsoil = MagicMock()
    #     dm = MagicMock()
    #     scenario_index = 0
    #     stage_index = 0
    #     set_subsoil(subsoil, dm, scenario_index, stage_index)
    #
    # def test_add_state_points(self):
    #     state_points = [MagicMock()]
    #     dm = MagicMock()
    #     scenario_index = 0
    #     stage_index = 0
    #     add_state_points(state_points, dm, scenario_index, stage_index)
    #
    # def test_add_uniform_load(self):
    #     load = MagicMock()
    #     soil_collection = MagicMock()
    #     char_point_profile = MagicMock()
    #     dm = MagicMock()
    #     scenario_index = 0
    #     stage_index = 0
    #     add_uniform_load(load, soil_collection, char_point_profile, dm, scenario_index, stage_index)
    #
    # def test_set_waternet(self):
    #     waternet = MagicMock()
    #     dm = MagicMock()
    #     scenario_index = 0
    #     stage_index = 0
    #     set_waternet(waternet, dm, scenario_index, stage_index)
    #
    # def test_create_d_stability_model(self):
    #     model = MagicMock()
    #     create_d_stability_model(model)
