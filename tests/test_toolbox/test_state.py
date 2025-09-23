from unittest import TestCase

from geolib.soils import Soil as GLSoil

from toolbox import Soil, SoilCollection
from toolbox import create_state_points_from_subsoil
from toolbox import SoilPolygon, Subsoil


class TestState(TestCase):
    def setUp(self):
        self.subsoil = Subsoil(
            soil_polygons=[
                SoilPolygon(soil_type="Klei", points=[(0, 0), (0, 1), (1, 1), (1, 0)]),
                SoilPolygon(
                    soil_type="Zand", points=[(0, 0), (0, -1), (1, -1), (1, 0)]
                ),
            ]
        )

    def test_create_state_points_from_subsoil(self):
        self.soil_collection = SoilCollection(
            soils=[
                Soil(gl_soil=GLSoil(name="Klei"), pop_mean=20, probabilistic_pop=False),
                Soil(gl_soil=GLSoil(name="Zand"), pop_mean=None),
            ]
        )

        state_points = create_state_points_from_subsoil(
            subsoil=self.subsoil, soil_collection=self.soil_collection, state_type="POP"
        )
        self.assertEqual(len(state_points), 1)
        self.assertEqual(state_points[0].pop_mean, 20)
        self.assertEqual(state_points[0].x, 0.5)
        self.assertEqual(state_points[0].z, 0.5)

    def test_create_state_points_from_subsoil_with_no_state_soils(self):
        self.soil_collection = SoilCollection(
            soils=[
                Soil(gl_soil=GLSoil(name="Klei"), pop_mean=None),
                Soil(gl_soil=GLSoil(name="Zand"), pop_mean=None),
            ]
        )
        state_points = create_state_points_from_subsoil(
            self.subsoil, self.soil_collection
        )
        self.assertEqual(len(state_points), 0)
