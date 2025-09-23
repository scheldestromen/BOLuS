import os
from unittest import TestCase

from geolib.models import DStabilityModel
from geolib.models.dstability.internal import \
    SoilCollection as GLSoilCollection
from geolib.soils import Soil as GLSoil

from toolbox import (CharPoint, CharPointsProfile,
                     CharPointType, Side)
from toolbox import Load
from toolbox import Model
from toolbox import (add_soil_collection, add_state_points,
                     add_uniform_load,
                     create_d_stability_model, set_subsoil,
                     set_waternet)
from toolbox import Soil, SoilCollection
from toolbox import StatePoint
from toolbox import SoilPolygon, Subsoil
from toolbox.waternet import HeadLine, ReferenceLine, Waternet

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURE_DIR = os.path.join(os.path.dirname(TEST_DIR), "fixtures")
MODEL_JSON_PATH = os.path.join(FIXTURE_DIR, "model_example.json")


class TestModifierAddSoilCollection(TestCase):
    def setUp(self):
        self.soil_collection = SoilCollection(
            soils=[
                Soil(gl_soil=GLSoil(code="Klei"), pop_mean=20, probabilistic_pop=False),
                Soil(gl_soil=GLSoil(code="Zand"), pop_mean=None, probabilistic_pop=False),
            ]
        )

    def test_add_soil_collection(self):
        dm = DStabilityModel()
        dm.datastructure.soils = GLSoilCollection(Soils=[])  # Remove default soils
        dm = add_soil_collection(self.soil_collection, dm)
        codes = [soil.Code for soil in dm.soils.Soils]

        self.assertEqual(len(dm.soils.Soils), len(self.soil_collection.soils))
        self.assertEqual(codes, ["Klei", "Zand"])


class TestModifierSetSubsoil(TestCase):
    def setUp(self):
        self.soil_collection = SoilCollection(
            soils=[
                Soil(gl_soil=GLSoil(code="Klei"), pop=20),
                Soil(gl_soil=GLSoil(code="Zand"), pop=None),
            ]
        )
        self.subsoil = Subsoil(
            soil_polygons=[
                SoilPolygon(soil_type="Klei", points=[(0, 0), (0, 1), (1, 1), (1, 0)]),
                SoilPolygon(
                    soil_type="Zand", points=[(0, 0), (0, -1), (1, -1), (1, 0)]
                ),
            ]
        )

    def test_set_subsoil(self):
        # Setup test
        scenario_index = 0
        stage_index = 0
        dm = DStabilityModel()
        add_soil_collection(self.soil_collection, dm)

        dm = set_subsoil(
            self.subsoil, dm, scenario_index=scenario_index, stage_index=stage_index
        )

        # Run test
        self.assertEqual(
            len(
                dm.datastructure.soillayers[0].SoilLayers
            ),  # There is only 1 soillayers
            len(self.subsoil.soil_polygons),
        )
        self.assertEqual(
            len(dm.datastructure.geometries[0].Layers), len(self.subsoil.soil_polygons)
        )


class TestModifierAddStatePoints(TestCase):
    def setUp(self):
        self.soil_collection = SoilCollection(
            soils=[
                Soil(gl_soil=GLSoil(code="Klei"), pop_mean=20, probabilistic_pop=False),
                Soil(gl_soil=GLSoil(code="Zand"), pop_mean=None, probabilistic_pop=False),
            ]
        )
        self.subsoil = Subsoil(
            soil_polygons=[
                SoilPolygon(soil_type="Klei", points=[(0, 0), (0, 1), (1, 1), (1, 0)]),
                SoilPolygon(
                    soil_type="Zand", points=[(0, 0), (0, -1), (1, -1), (1, 0)]
                ),
            ]
        )

    def test_add_state_points(self):
        # Setup test
        state_points = [StatePoint(x=0.5, z=0.5, pop_mean=20, probabilistic_pop=False)]
        dm = DStabilityModel()
        add_soil_collection(self.soil_collection, dm)
        set_subsoil(subsoil=self.subsoil, dm=dm, scenario_index=0, stage_index=0)
        scenario_index = 0
        stage_index = 0
        add_state_points(state_points, dm, scenario_index, stage_index)

        self.assertEqual(len(dm.datastructure.states[0].StatePoints), len(state_points))
        added_state_point = dm.datastructure.states[0].StatePoints[0]
        self.assertEqual(added_state_point.Stress.Pop, state_points[0].pop_mean)
        self.assertEqual(added_state_point.Point.X, state_points[0].x)
        self.assertEqual(added_state_point.Point.Z, state_points[0].z)


class TestModifierAddUniformLoad(TestCase):
    def setUp(self):
        char_points_outward_positive = [
            CharPoint(x=0, y=0, z=0, l=0, type=CharPointType.SURFACE_LEVEL_LAND_SIDE),
            CharPoint(x=0, y=0, z=4, l=10, type=CharPointType.DIKE_CREST_LAND_SIDE),
            CharPoint(x=0, y=0, z=4, l=20, type=CharPointType.DIKE_CREST_WATER_SIDE),
            CharPoint(x=0, y=0, z=0, l=30, type=CharPointType.SURFACE_LEVEL_WATER_SIDE),
        ]
        char_points_inward_positive = [
            CharPoint(x=0, y=0, z=0, l=30, type=CharPointType.SURFACE_LEVEL_LAND_SIDE),
            CharPoint(x=0, y=0, z=4, l=20, type=CharPointType.DIKE_CREST_LAND_SIDE),
            CharPoint(x=0, y=0, z=4, l=10, type=CharPointType.DIKE_CREST_WATER_SIDE),
            CharPoint(x=0, y=0, z=0, l=0, type=CharPointType.SURFACE_LEVEL_WATER_SIDE),
        ]
        self.char_points_profile_outward_positive = CharPointsProfile(
            name="test", points=char_points_outward_positive
        )
        self.char_points_profile_inward_positive = CharPointsProfile(
            name="test", points=char_points_inward_positive
        )

        self.soil_collection = SoilCollection(
            soils=[
                Soil(
                    gl_soil=GLSoil(name="Klei", code="Klei"),
                    consolidation_traffic_load=50,
                ),
                Soil(
                    gl_soil=GLSoil(name="Zand", code="Zand"),
                    consolidation_traffic_load=100,
                ),
            ]
        )
        self.subsoil = Subsoil(
            soil_polygons=[
                SoilPolygon(
                    soil_type="Klei", points=[(0, 0), (10, 4), (20, 4), (30, 0)]
                ),
                SoilPolygon(
                    soil_type="Zand", points=[(0, -5), (0, 0), (30, 0), (30, -5)]
                ),
            ]
        )

        dm = DStabilityModel()
        dm = add_soil_collection(self.soil_collection, dm)
        self.dm = set_subsoil(
            subsoil=self.subsoil, dm=dm, scenario_index=0, stage_index=0
        )

    def test_outward_positive_load_direction_outward(self):
        """
        inward                         outward
                       x->
                      /-------\
                     /         \
                    /           \
        l         0   10     20  30
        positive direction of l is outward -->

        x: position of load
        """
        # Setup test
        load = Load(
            name="test",
            magnitude=10,
            angle=20,
            width=5,
            position=CharPointType.DIKE_CREST_LAND_SIDE,
            direction=Side.WATER_SIDE,
        )
        add_uniform_load(
            load=load,
            soil_collection=self.soil_collection,
            char_point_profile=self.char_points_profile_outward_positive,
            dm=self.dm,
            scenario_index=0,
            stage_index=0,
        )

        # Run test
        self.assertEqual(
            self.dm.datastructure.loads[0].UniformLoads[0].Magnitude, load.magnitude
        )
        self.assertEqual(
            self.dm.datastructure.loads[0].UniformLoads[0].Spread, load.angle
        )
        self.assertEqual(self.dm.datastructure.loads[0].UniformLoads[0].Start, 10)
        self.assertEqual(self.dm.datastructure.loads[0].UniformLoads[0].End, 15)

        consolidations = [
            cons.Degree
            for cons in self.dm.datastructure.loads[0].UniformLoads[0].Consolidations
        ]
        self.assertEqual(consolidations, [50, 100])

    def test_outward_positive_load_direction_inward(self):
        """
        inward                         outward
                            <-x
                      /-------\
                     /         \
                    /           \
        l         0   10     20  30
        positive direction of l is outward -->

        x: position of load
        """
        # Setup test
        load = Load(
            name="test",
            magnitude=10,
            angle=20,
            width=5,
            position=CharPointType.DIKE_CREST_WATER_SIDE,
            direction=Side.LAND_SIDE,
        )
        add_uniform_load(
            load=load,
            soil_collection=self.soil_collection,
            char_point_profile=self.char_points_profile_outward_positive,
            dm=self.dm,
            scenario_index=0,
            stage_index=0,
        )

        # Run test
        self.assertEqual(
            self.dm.datastructure.loads[0].UniformLoads[0].Magnitude, load.magnitude
        )
        self.assertEqual(
            self.dm.datastructure.loads[0].UniformLoads[0].Spread, load.angle
        )
        self.assertEqual(self.dm.datastructure.loads[0].UniformLoads[0].Start, 15)
        self.assertEqual(self.dm.datastructure.loads[0].UniformLoads[0].End, 20)

    def test_inward_positive_load_direction_outward(self):
        """
        inward                         outward
                       x->
                      /-------\
                     /         \
                    /           \
        l         30  20     10  0
        <- positive direction of l is inward

        x: position of load
        """
        # Setup test
        load = Load(
            name="test",
            magnitude=10,
            angle=20,
            width=5,
            position=CharPointType.DIKE_CREST_LAND_SIDE,
            direction=Side.WATER_SIDE,
        )
        add_uniform_load(
            load=load,
            soil_collection=self.soil_collection,
            char_point_profile=self.char_points_profile_inward_positive,
            dm=self.dm,
            scenario_index=0,
            stage_index=0,
        )

        # Run test
        self.assertEqual(
            self.dm.datastructure.loads[0].UniformLoads[0].Magnitude, load.magnitude
        )
        self.assertEqual(
            self.dm.datastructure.loads[0].UniformLoads[0].Spread, load.angle
        )
        self.assertEqual(self.dm.datastructure.loads[0].UniformLoads[0].Start, 15)
        self.assertEqual(self.dm.datastructure.loads[0].UniformLoads[0].End, 20)

    def test_inward_positive_load_direction_inward(self):
        """
        inward                         outward
                            <-x
                      /-------\
                     /         \
                    /           \
        l         30  20     10  0
        <- positive direction of l is inward

        x: position of load
        """
        # Setup test
        load = Load(
            name="test",
            magnitude=10,
            angle=20,
            width=5,
            position=CharPointType.DIKE_CREST_WATER_SIDE,
            direction=Side.LAND_SIDE,
        )
        add_uniform_load(
            load=load,
            soil_collection=self.soil_collection,
            char_point_profile=self.char_points_profile_inward_positive,
            dm=self.dm,
            scenario_index=0,
            stage_index=0,
        )

        # Run test
        self.assertEqual(
            self.dm.datastructure.loads[0].UniformLoads[0].Magnitude, load.magnitude
        )
        self.assertEqual(
            self.dm.datastructure.loads[0].UniformLoads[0].Spread, load.angle
        )
        self.assertEqual(self.dm.datastructure.loads[0].UniformLoads[0].Start, 10)
        self.assertEqual(self.dm.datastructure.loads[0].UniformLoads[0].End, 15)


class TestSetWaternet(TestCase):
    def setUp(self):
        self.waternet = Waternet(
            calc_name="test",
            scenario_name="test",
            stage_name="test",
            head_lines=[
                HeadLine(name="PL1", is_phreatic=True, l=[0, 10], z=[2, 3]),
                HeadLine(name="PL2", is_phreatic=False, l=[0, 10], z=[1, 1]),
            ],
            ref_lines=[
                ReferenceLine(
                    name="RL2",
                    l=[0, 10],
                    z=[-2, -3],
                    head_line_top="PL2",
                    head_line_bottom="PL2",
                )
            ],
        )

    def test_set_waternet(self):
        dm = DStabilityModel()
        dm = set_waternet(
            waternet=self.waternet, dm=dm, scenario_index=0, stage_index=0
        )

        added_waternet = dm.datastructure.waternets[0]
        head_lines = added_waternet.HeadLines
        ref_lines = added_waternet.ReferenceLines
        phreatic_points = head_lines[0].Points
        ref_points = ref_lines[0].Points

        self.assertEqual(len(dm.datastructure.waternets), 1)
        self.assertEqual([p.X for p in phreatic_points], self.waternet.head_lines[0].l)
        self.assertEqual([p.Z for p in phreatic_points], self.waternet.head_lines[0].z)
        self.assertEqual([r.X for r in ref_points], self.waternet.ref_lines[0].l)
        self.assertEqual([r.Z for r in ref_points], self.waternet.ref_lines[0].z)

    def test_set_waternet_already_present(self):
        dm = DStabilityModel()
        dm = set_waternet(
            waternet=self.waternet, dm=dm, scenario_index=0, stage_index=0
        )

        with self.assertRaises(ValueError):
            set_waternet(waternet=self.waternet, dm=dm, scenario_index=0, stage_index=0)


class TestCreateDStabilityModel(TestCase):
    def setUp(self):
        with open(MODEL_JSON_PATH, "r") as f:
            self.model = Model.model_validate_json(f.read())

    def test_create_d_stability_model(self):
        """Simple integral test"""
        dm = create_d_stability_model(self.model)

        # (Mainly) assert if the numbers are correct
        self.assertIsInstance(dm, DStabilityModel)
        self.assertEqual(len(dm.scenarios), len(self.model.scenarios))
        self.assertEqual(
            len(dm.scenarios[0].Stages), len(self.model.scenarios[0].stages)
        )
        self.assertEqual(len(dm.soils.Soils), len(self.model.soil_collection.soils))
        self.assertEqual(
            len(dm.datastructure.states[0].StatePoints),
            len(self.model.scenarios[0].stages[0].state_points),
        )
        self.assertEqual(
            len(dm.datastructure.geometries[0].Layers),
            len(self.model.scenarios[0].stages[0].subsoil.soil_polygons),
        )
        self.assertEqual(
            len(dm.datastructure.loads[0].UniformLoads), 0
        )  # Hard coded test value
        self.assertEqual(
            len(dm.datastructure.loads[1].UniformLoads), 1
        )  # Hard coded test value
        self.assertEqual(
            len(dm.datastructure.waternets[0].HeadLines),
            len(self.model.scenarios[0].stages[0].waternet.head_lines),
        )
        self.assertEqual(
            len(dm.datastructure.waternets[0].ReferenceLines),
            len(self.model.scenarios[0].stages[0].waternet.ref_lines),
        )
