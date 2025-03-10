from unittest import TestCase

from dstability_toolbox.geometry import CharPointType, Side
from dstability_toolbox.loads import Load, LoadCollection


class TestLoad(TestCase):
    def test_init(self):
        """Test creating a basic load with all required attributes"""
        Load(
            name="test_load",
            magnitude=10.0,
            angle=20.0,
            width=5.0,
            position=CharPointType.DIKE_CREST_LAND_SIDE,
            direction=Side.WATER_SIDE,
        )


class TestLoadCollection(TestCase):
    def setUp(self):
        self.loads = [
            Load(
                name="load1",
                magnitude=10.0,
                angle=20.0,
                width=5.0,
                position=CharPointType.DIKE_CREST_LAND_SIDE,
                direction=Side.WATER_SIDE,
            ),
            Load(
                name="load2",
                magnitude=15.0,
                angle=25.0,
                width=7.0,
                position=CharPointType.DIKE_CREST_WATER_SIDE,
                direction=Side.LAND_SIDE,
            ),
        ]
        self.collection = LoadCollection(loads=self.loads)

    def test_get_by_name(self):
        """Test retrieving a load by name"""
        load = self.collection.get_by_name("load1")
        self.assertEqual(load.name, "load1")
        self.assertEqual(load.magnitude, 10.0)

    def test_get_by_name_not_found(self):
        """Test that getting a non-existent load raises an error"""
        with self.assertRaises(NameError):
            self.collection.get_by_name("nonexistent_load")

    def test_from_list(self):
        """Test creating a load collection from a list of dictionaries"""
        loads_dicts = [
            {
                "name": "load1",
                "magnitude": 10.0,
                "angle": 20.0,
                "width": 5.0,
                "position": CharPointType.DIKE_CREST_LAND_SIDE,
                "direction": Side.WATER_SIDE,
            },
            {
                "name": "load2",
                "magnitude": 15.0,
                "angle": 25.0,
                "width": 7.0,
                "position": CharPointType.DIKE_CREST_WATER_SIDE,
                "direction": Side.LAND_SIDE,
            },
        ]

        collection = LoadCollection.from_list(loads_dicts)
        self.assertEqual(len(collection.loads), 2)
        self.assertEqual(collection.loads[0].name, "load1")
        self.assertEqual(collection.loads[1].name, "load2")
