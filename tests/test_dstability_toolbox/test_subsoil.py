import json
import os
from pathlib import Path
from unittest import TestCase

from geolib import DStabilityModel
from shapely import Polygon

from dstability_toolbox.geometry import Point, SurfaceLine
from dstability_toolbox.subsoil import Subsoil, SoilPolygon, SoilProfileCollection, SoilProfile, SoilLayer, \
    subsoil_from_soil_profiles
from geolib.models.dstability.internal import PersistablePoint, PersistableLayer

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURE_DIR = os.path.join(os.path.dirname(TEST_DIR), 'fixtures')
SOIL_PROFILE_COLLECTION_JSON_PATH = os.path.join(FIXTURE_DIR, 'soil_profile_collection_example.json')
DSTABILITY_DIR = os.path.join(FIXTURE_DIR, 'dstability')


class TestSoilProfile(TestCase):
    def test_check_descending_tops_true(self):
        soil_profile = SoilProfile(name='profile_1',
                                   layers=[SoilLayer(soil_type='soil_type_1', top=1),
                                           SoilLayer(soil_type='soil_type_2', top=0)])
        self.assertIsInstance(soil_profile, SoilProfile)

    def test_check_descending_tops_false(self):
        with self.assertRaises(ValueError):
            SoilProfile(name='profile_1',
                        layers=[SoilLayer(soil_type='soil_type_1', top=0),
                                SoilLayer(soil_type='soil_type_2', top=1)])


class TestSoilProfileCollection(TestCase):
    def setUp(self):
        with open(SOIL_PROFILE_COLLECTION_JSON_PATH, 'r') as f:
            self.soil_profile_collection_dict = json.load(f)

    def test_from_dict(self):
        soil_profile_collection = SoilProfileCollection.from_dict(
            soil_profile_dict=self.soil_profile_collection_dict
        )
        names = [sp.name for sp in soil_profile_collection.profiles]

        self.assertIsInstance(soil_profile_collection, SoilProfileCollection)
        self.assertEqual(len(soil_profile_collection.profiles), 3)
        self.assertEqual(names, ['Bodemprofiel 1', 'Bodemprofiel 2', 'Bodemprofiel 3'])


class TestSoilPolygon(TestCase):
    def setUp(self):
        self.gl_layer = PersistableLayer(Points=[
            PersistablePoint(X=0, Z=0),
            PersistablePoint(X=0, Z=1),
            PersistablePoint(X=1, Z=1),
            PersistablePoint(X=1, Z=0)
        ])
        self.soil_polygon = SoilPolygon(
            soil_type='test',
            points=[(0, 0), (0, 2), (2, 2), (2, 0)]
        )
        self.shapely_polygon = Polygon([(0, 0), (0, 3), (3, 3), (3, 0)])

    def test_from_geolib_layer(self):
        soil_polygon = SoilPolygon.from_geolib_layer('test', self.gl_layer)
        self.assertIsInstance(soil_polygon, SoilPolygon)
        self.assertEqual(soil_polygon.points, [(0, 0), (0, 1), (1, 1), (1, 0)])

    def test_to_shapely(self):
        shapely_polygon = self.soil_polygon.to_shapely()
        self.assertIsInstance(shapely_polygon, Polygon)
        self.assertEqual(shapely_polygon, Polygon([(0, 0), (0, 2), (2, 2), (2, 0)]))

    def test_from_shapely(self):
        soil_type = 'test'
        soil_polygon = SoilPolygon.from_shapely(soil_type, self.shapely_polygon)
        self.assertIsInstance(soil_polygon, SoilPolygon)
        self.assertEqual(soil_polygon, SoilPolygon(
            soil_type='test',
            points=[(0, 0), (0, 3), (3, 3), (3, 0)]
        ))


class TestSubsoil(TestCase):
    def test_from_geolib(self):
        dm = DStabilityModel()
        dm.parse(Path(os.path.join(DSTABILITY_DIR, 'test_1.stix')))

        scenario_index = 0
        stage_index = 1
        subsoil = Subsoil.from_geolib(dm, scenario_index, stage_index)

        self.assertIsInstance(subsoil, Subsoil)
        self.assertEqual(len(subsoil.soil_polygons), 14)


class TestSubsoilFromSoilProfiles(TestCase):
    def setUp(self):
        profile_points = [
            Point(x=8, y=6, z=0, l=0),
            Point(x=24, y=18, z=0, l=20),
            Point(x=32, y=24, z=3, l=30),
            Point(x=36, y=27, z=3, l=35),
            Point(x=48, y=36, z=0, l=50),
            Point(x=52, y=39, z=0, l=55),
            Point(x=54, y=40.5, z=-1, l=57.5),
            Point(x=56, y=42, z=-1, l=60),
            Point(x=58, y=43.5, z=0, l=62.5),
            Point(x=72, y=54, z=0, l=80),
        ]
        self.surface_line = SurfaceLine(name='test', points=profile_points)

        with open(SOIL_PROFILE_COLLECTION_JSON_PATH, 'r') as f:
            self.soil_profile_collection_dict = json.load(f)

        self.soil_profiles = SoilProfileCollection.from_dict(
            soil_profile_dict=self.soil_profile_collection_dict
        ).profiles

    def test_single_profile(self):
        subsoil = subsoil_from_soil_profiles(self.surface_line, [self.soil_profiles[0]])
        self.assertIsInstance(subsoil, Subsoil)
        self.assertEqual(len(subsoil.soil_polygons), 4)

    def test_multiple_profiles(self):
        subsoil = subsoil_from_soil_profiles(
            surface_line=self.surface_line,
            soil_profiles=self.soil_profiles,
            transitions=[20, 50]
        )
        self.assertIsInstance(subsoil, Subsoil)
        self.assertEqual(len(subsoil.soil_polygons), 14)

    def test_no_profile(self):
        with self.assertRaises(ValueError):
            subsoil_from_soil_profiles(surface_line=self.surface_line, soil_profiles=[])

    def test_non_matching_number_of_transitions(self):
        with self.assertRaises(ValueError):
            subsoil_from_soil_profiles(
                surface_line=self.surface_line,
                soil_profiles=self.soil_profiles,
                transitions=[20]  # should have 2 transitions, because there are 3 soil profiles
            )

    def test_l_not_calculated(self):
        self.surface_line.points[0].l = None

        # Not having all values for l should raise a ValueError
        with self.assertRaises(ValueError):
            subsoil_from_soil_profiles(
                surface_line=self.surface_line,
                soil_profiles=self.soil_profiles,
                transitions=[20, 50]
            )

    def test_transitions_out_of_bounds(self):
        # Should raise a ValueError, because l starts at 0
        with self.assertRaises(ValueError):
            subsoil_from_soil_profiles(
                surface_line=self.surface_line,
                soil_profiles=self.soil_profiles,
                transitions=[-20, 50]
            )

    def test_bottom_no_minimum_depth(self):
        min_layer_thickness = 1

        subsoil = subsoil_from_soil_profiles(
            surface_line=self.surface_line,
            soil_profiles=[self.soil_profiles[0]],
            thickness_bottom_layer=min_layer_thickness,
            min_soil_profile_depth=None
        )
        bottom_layer_top = self.soil_profiles[0].layers[-1].top

        z_min = min([point[1] for soil_poly in subsoil.soil_polygons for point in soil_poly.points])
        self.assertAlmostEqual(z_min, bottom_layer_top - min_layer_thickness)

    def test_bottom_with_minimum_depth(self):
        min_layer_thickness = 1
        minimum_depth = -20

        subsoil = subsoil_from_soil_profiles(
            surface_line=self.surface_line,
            soil_profiles=[self.soil_profiles[0]],
            thickness_bottom_layer=min_layer_thickness,
            min_soil_profile_depth=minimum_depth
        )

        z_min = min([point[1] for soil_poly in subsoil.soil_polygons for point in soil_poly.points])
        self.assertAlmostEqual(z_min, minimum_depth)
