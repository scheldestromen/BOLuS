import json
import os
from copy import deepcopy
from unittest import TestCase

from toolbox.geometry import (CharPoint, CharPointsProfile,
                              CharPointsProfileCollection,
                              CharPointType, Point, SurfaceLine,
                              SurfaceLineCollection,
                              create_geometries)

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURE_DIR = os.path.join(os.path.dirname(TEST_DIR), "fixtures")
CHAR_POINT_JSON_PATH = os.path.join(FIXTURE_DIR, "char_point_example.json")
CHAR_COLLECTION_JSON_PATH = os.path.join(
    FIXTURE_DIR, "char_points_profile_collection_example.json"
)
SURF_COLLECTION_JSON_PATH = os.path.join(
    FIXTURE_DIR, "surface_line_collection_example.json"
)


class TestPoint(TestCase):
    def test_equal(self):
        point1 = Point(x=1, y=1, z=2)
        point2 = Point(x=1, y=1, z=2)
        self.assertEqual(point1, point2)

        point3 = Point(x=1, y=1, z=3)
        self.assertNotEqual(point1, point3)

    def test_distance(self):
        point1 = Point(x=0, y=0, z=0)
        point2 = Point(x=3, y=4, z=0)
        self.assertAlmostEqual(point1.distance(point2), 5.0)


class TestProfileLine(TestCase):
    def setUp(self):
        self.points = [
            Point(x=8, y=6, z=0),
            Point(x=24, y=18, z=0),
            Point(x=32, y=24, z=3),
            Point(x=36, y=27, z=3),
            Point(x=48, y=36, z=0),
            Point(x=52, y=39, z=0),
            Point(x=54, y=40.5, z=-1),
            Point(x=56, y=42, z=-1),
            Point(x=58, y=43.5, z=0),
            Point(x=72, y=54, z=0),
        ]
        self.expected_l_first_is_left_point = [
            0,
            20,
            30,
            35,
            50,
            55,
            57.5,
            60,
            62.5,
            80,
        ]
        self.expected_l_last_is_left_point = [80, 60, 50, 45, 30, 25, 22.5, 20, 17.5, 0]

        self.points_reversed = deepcopy(self.points).reverse()

    def test_check_l_coordinates_present_true(self):
        surface_line = SurfaceLine(
            name="test", points=[Point(x=8, y=2, z=0, l=2), Point(x=8, y=6, z=0, l=20)]
        )
        self.assertIsNone(surface_line.check_l_coordinates_present())

    def test_check_l_coordinates_present_false(self):
        surface_line = SurfaceLine(
            name="test", points=[Point(x=8, y=2, z=0), Point(x=8, y=6, z=0)]
        )

        with self.assertRaises(ValueError):
            surface_line.check_l_coordinates_present()

    def test_set_l_coordinates_first_is_left_point(self):
        surface_line = SurfaceLine(name="test", points=self.points)
        surface_line.set_l_coordinates(left_point=surface_line.points[0])
        actual_l = [p.l for p in surface_line.points]
        self.assertEqual(actual_l, self.expected_l_first_is_left_point)

    def test_set_l_coordinates_last_is_left_point(self):
        surface_line = SurfaceLine(name="test", points=self.points)
        surface_line.set_l_coordinates(left_point=surface_line.points[-1])
        actual_l = [p.l for p in surface_line.points]
        self.assertEqual(actual_l, self.expected_l_last_is_left_point)

    def test_set_coordinates_invalid_left_point(self):
        surface_line = SurfaceLine(name="test", points=self.points)

        with self.assertRaises(ValueError):
            surface_line.set_l_coordinates(left_point=surface_line.points[1])

    def test_set_l_coordinates_last_is_left_point_with_ref_point(self):
        surface_line = SurfaceLine(name="test", points=self.points)
        ref_point = self.points[3]  # l = 45, counted from the right
        surface_line.set_l_coordinates(
            left_point=surface_line.points[-1], ref_point=ref_point
        )

        actual_l = [p.l for p in surface_line.points]
        expected_l = [l - 45 for l in self.expected_l_last_is_left_point]

        self.assertEqual(actual_l, expected_l)


class TestCharPointsProfile(TestCase):
    def setUp(self):
        with open(CHAR_POINT_JSON_PATH) as f:
            self.char_points_dict = json.load(f)

    def test_from_dict(self):
        char_points_profile = CharPointsProfile.from_dict(
            name="test", char_points_dict=self.char_points_dict
        )
        self.assertEqual(char_points_profile.name, "test")
        self.assertEqual(char_points_profile.points[0].x, -95)

    def test_get_point_by_type(self):
        char_points_profile = CharPointsProfile.from_dict(
            name="test", char_points_dict=self.char_points_dict
        )
        point = char_points_profile.get_point_by_type(
            CharPointType.DIKE_CREST_WATER_SIDE
        )
        self.assertEqual(point, Point(x=-2.48, y=0, z=6.32))

    def test_get_point_by_type_not_available(self):
        char_points_profile = CharPointsProfile.from_dict(
            name="test", char_points_dict=self.char_points_dict
        )

        with self.assertRaises(ValueError):
            char_points_profile.get_point_by_type(CharPointType.BERM_CREST_WATER_SIDE)


class TestSurfaceLine(TestCase):
    def test_from_list(self):
        surface_line = SurfaceLine.from_list(
            name="test", point_list=[0, 0, 0, 1, 1, 1, 2, 2, 2]
        )
        self.assertEqual(
            surface_line.points,
            [Point(x=0, y=0, z=0), Point(x=1, y=1, z=1), Point(x=2, y=2, z=2)],
        )

    def test_from_list_incorrect_number_of_points(self):
        with self.assertRaises(ValueError):
            SurfaceLine.from_list(
                name="test", point_list=[0, 0, 0, 1, 1, 1, 2, 2, 2, 3]
            )


class TestSurfaceLineCollection(TestCase):
    def setUp(self):
        with open(SURF_COLLECTION_JSON_PATH) as f:
            self.surface_line_collection_dict = json.load(f)

        self.surface_line_collection = SurfaceLineCollection(
            surface_lines=[
                SurfaceLine(
                    name="Profile 1",
                    points=[Point(x=0, y=1, z=2), Point(x=4, y=5, z=6)],
                ),
                SurfaceLine(
                    name="Profile 2",
                    points=[Point(x=4, y=0, z=2), Point(x=6, y=7, z=8)],
                ),
            ]
        )

    def test_from_dict(self):
        surface_line_collection = SurfaceLineCollection.from_dict(
            self.surface_line_collection_dict
        )
        names = [
            surface_line.name for surface_line in surface_line_collection.surface_lines
        ]
        x = [p.x for p in surface_line_collection.surface_lines[0].points]

        self.assertEqual(len(surface_line_collection.surface_lines), 3)
        self.assertEqual(names, ["Dwarsprofiel 1", "Dwarsprofiel 2", "Dwarsprofiel 3"])
        self.assertEqual(len(x), 54)

    def test_get_by_name(self):
        name = "Profile 2"
        surface_line = self.surface_line_collection.get_by_name(name)

        self.assertEqual(surface_line.name, name)
        self.assertEqual(surface_line.points[0], Point(x=4, y=0, z=2))

    def test_get_by_name_not_available(self):
        with self.assertRaises(ValueError):
            self.surface_line_collection.get_by_name("non_existent_name")


class TestCharPointsProfileCollection(TestCase):
    def setUp(self):
        with open(CHAR_COLLECTION_JSON_PATH) as f:
            self.char_collection_dict = json.load(f)

        self.char_collection = CharPointsProfileCollection(
            char_points_profiles=[
                CharPointsProfile(
                    name="Profile 1",
                    points=[
                        CharPoint(
                            x=1, y=2, z=3, type=CharPointType.DIKE_CREST_WATER_SIDE
                        ),
                        CharPoint(
                            x=4, y=5, z=6, type=CharPointType.DIKE_CREST_LAND_SIDE
                        ),
                    ],
                ),
                CharPointsProfile(
                    name="Profile 2",
                    points=[
                        CharPoint(
                            x=10, y=11, z=12, type=CharPointType.SURFACE_LEVEL_LAND_SIDE
                        ),
                        CharPoint(
                            x=13,
                            y=14,
                            z=15,
                            type=CharPointType.SURFACE_LEVEL_WATER_SIDE,
                        ),
                    ],
                ),
            ]
        )

    def test_from_dict(self):
        char_points_profile_collection = CharPointsProfileCollection.from_dict(
            self.char_collection_dict
        )
        names = [
            char_prof.name
            for char_prof in char_points_profile_collection.char_points_profiles
        ]

        self.assertEqual(len(char_points_profile_collection.char_points_profiles), 3)
        self.assertEqual(names, ["Dwarsprofiel 1", "Dwarsprofiel 2", "Dwarsprofiel 3"])

    def test_get_by_name(self):
        name = "Profile 2"
        char_points_profile = self.char_collection.get_by_name(name)

        self.assertEqual(char_points_profile.name, name)
        self.assertEqual(
            char_points_profile.points[0],
            CharPoint(x=10, y=11, z=12, type=CharPointType.SURFACE_LEVEL_LAND_SIDE),
        )

    def test_get_by_name_not_available(self):
        with self.assertRaises(ValueError):
            self.char_collection.get_by_name("non_existent_name")


class TestGeometry(TestCase):
    def setUp(self):
        with open(CHAR_COLLECTION_JSON_PATH) as f:
            char_collection_dict = json.load(f)

        with open(SURF_COLLECTION_JSON_PATH) as f:
            surface_line_collection_dict = json.load(f)

        self.surface_line_collection = SurfaceLineCollection.from_dict(
            surface_line_collection_dict
        )
        self.char_line_collection = CharPointsProfileCollection.from_dict(
            char_collection_dict
        )

    def test_create_geometries(self):
        geometries = create_geometries(
            surface_line_collection=self.surface_line_collection,
            char_point_collection=self.char_line_collection,
            char_type_left_point=CharPointType.SURFACE_LEVEL_LAND_SIDE,
        )
        names = [geom.name for geom in geometries]

        self.assertEqual(len(geometries), 3)
        self.assertEqual(names, ["Dwarsprofiel 1", "Dwarsprofiel 2", "Dwarsprofiel 3"])

    def test_create_geometries_non_matching_names(self):
        self.surface_line_collection.surface_lines[0].name = "Non-matching name"

        with self.assertRaises(ValueError):
            create_geometries(
                surface_line_collection=self.surface_line_collection,
                char_point_collection=self.char_line_collection,
                char_type_left_point=CharPointType.SURFACE_LEVEL_LAND_SIDE,
            )
