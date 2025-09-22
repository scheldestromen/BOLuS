import json
import os
from unittest import TestCase

from geolib.models.dstability.analysis import (
    DStabilityBishopBruteForceAnalysisMethod, DStabilitySlipPlaneConstraints,
    DStabilityUpliftVanParticleSwarmAnalysisMethod)
from geolib.models.dstability.internal import OptionsType

from bolus.toolbox.calculation_settings import (BishopBruteForce,
                                                GridSettingsSet,
                                                GridSettingsSetCollection,
                                                SlipPlaneModel,
                                                UpliftVanParticleSwarm)
from bolus.toolbox.geometry import (CharPoint, CharPointsProfile,
                                    CharPointType, Side)

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURE_DIR = os.path.join(os.path.dirname(TEST_DIR), "fixtures")
GRID_SETTINGS_SET_COLLECTION_JSON_PATH = os.path.join(
    FIXTURE_DIR, "grid_settings_set_collection_example.json"
)


class TestGridSettings(TestCase):
    def setUp(self):
        self.bishop_bruteforce = BishopBruteForce(
            grid_setting_name="Bishop",
            slip_plane_model=SlipPlaneModel.BISHOP_BRUTE_FORCE,
            grid_position=CharPointType.DIKE_CREST_LAND_SIDE,
            grid_direction=Side.LAND_SIDE,
            grid_offset_horizontal=1.0,
            grid_offset_vertical=2.0,
            grid_points_horizontal=10,
            grid_points_vertical=11,
            grid_points_per_m=2,
            tangent_line_position=CharPointType.DIKE_TOE_LAND_SIDE,
            tangent_line_offset=-1.0,
            tangent_line_count=12,
            tangent_lines_per_m=3,
            move_grid=True,
            apply_minimum_slip_plane_dimensions=True,
            minimum_slip_plane_depth=2.5,
            minimum_slip_plane_length=5.0,
            apply_constraint_zone_a=True,
            zone_a_position=CharPointType.DIKE_CREST_LAND_SIDE,
            zone_a_direction=Side.WATER_SIDE,
            zone_a_width=3.0,
            apply_constraint_zone_b=False,
            zone_b_position=None,
            zone_b_direction=None,
            zone_b_width=None
        )

        self.uplift_van_particle_swarm = UpliftVanParticleSwarm(
            grid_setting_name="Uplift",
            slip_plane_model=SlipPlaneModel.UPLIFT_VAN_PARTICLE_SWARM,
            grid_1_position=CharPointType.DIKE_CREST_WATER_SIDE,
            grid_1_direction=Side.WATER_SIDE,
            grid_1_offset_horizontal=2.0,
            grid_1_offset_vertical=3.0,
            grid_1_width=12,
            grid_1_height=13,
            grid_2_position=CharPointType.DIKE_TOE_WATER_SIDE,
            grid_2_direction=Side.WATER_SIDE,
            grid_2_offset_horizontal=5.0,
            grid_2_offset_vertical=6.0,
            grid_2_height=7.0,
            grid_2_width=8.0,
            tangent_area_position=CharPointType.DIKE_TOE_LAND_SIDE,
            tangent_area_offset=-2.0,
            height_tangent_area=10.0,
            search_mode=OptionsType.DEFAULT,
            apply_minimum_slip_plane_dimensions=True,
            minimum_slip_plane_depth=2.5,
            minimum_slip_plane_length=5.0,
            apply_constraint_zone_a=True,
            zone_a_position=CharPointType.DIKE_CREST_LAND_SIDE,
            zone_a_direction=Side.WATER_SIDE,
            zone_a_width=3.0,
            apply_constraint_zone_b=False,
            zone_b_position=None,
            zone_b_direction=None,
            zone_b_width=None
        )

        self.char_points_profile = CharPointsProfile(
            name="Profile 1",
            points=[
                CharPoint(
                    x=0, y=0, z=0, l=0, type=CharPointType.SURFACE_LEVEL_LAND_SIDE
                ),
                CharPoint(x=0, y=0, z=0, l=5, type=CharPointType.DIKE_TOE_LAND_SIDE),
                CharPoint(x=0, y=0, z=4, l=10, type=CharPointType.DIKE_CREST_LAND_SIDE),
                CharPoint(
                    x=0, y=0, z=4, l=20, type=CharPointType.DIKE_CREST_WATER_SIDE
                ),
                CharPoint(
                    x=0, y=0, z=0, l=30, type=CharPointType.SURFACE_LEVEL_WATER_SIDE
                ),
            ],
        )

    def test_slip_plane_constraints_to_geolib(self):
        constraints = self.bishop_bruteforce.slip_plane_constraints_to_geolib(
            self.char_points_profile
        )
        self.assertIsInstance(constraints, DStabilitySlipPlaneConstraints)


class TestUpliftVanParticleSwarm(TestCase):
    def setUp(self):
        self.uplift_van_particle_swarm = UpliftVanParticleSwarm(
            grid_setting_name="test",
            slip_plane_model=SlipPlaneModel.UPLIFT_VAN_PARTICLE_SWARM,
            apply_minimum_slip_plane_dimensions=True,
            minimum_slip_plane_depth=3.0,
            minimum_slip_plane_length=6.0,
            apply_constraint_zone_a=True,
            zone_a_position=CharPointType.DIKE_CREST_WATER_SIDE,
            zone_a_direction=Side.WATER_SIDE,
            zone_a_width=4.0,
            apply_constraint_zone_b=True,
            zone_b_position=CharPointType.DIKE_CREST_LAND_SIDE,
            zone_b_direction=Side.LAND_SIDE,
            zone_b_width=5.0,
            grid_1_position=CharPointType.DIKE_CREST_LAND_SIDE,
            grid_1_direction=Side.LAND_SIDE,
            grid_1_offset_horizontal=1,
            grid_1_offset_vertical=2,
            grid_1_width=3,
            grid_1_height=4,
            grid_2_position=CharPointType.DIKE_TOE_LAND_SIDE,
            grid_2_direction=Side.LAND_SIDE,
            grid_2_offset_horizontal=5,
            grid_2_offset_vertical=5,
            grid_2_width=7,
            grid_2_height=8,
            tangent_area_position=CharPointType.DIKE_TOE_LAND_SIDE,
            tangent_area_offset=-1.0,
            height_tangent_area=10,
            search_mode=OptionsType.THOROUGH,
        )

        self.char_points_profile = CharPointsProfile(
            name="Profile 1",
            points=[
                CharPoint(
                    x=0, y=0, z=0, l=0, type=CharPointType.SURFACE_LEVEL_LAND_SIDE
                ),
                CharPoint(x=0, y=0, z=0, l=5, type=CharPointType.DIKE_TOE_LAND_SIDE),
                CharPoint(x=0, y=0, z=4, l=10, type=CharPointType.DIKE_CREST_LAND_SIDE),
                CharPoint(
                    x=0, y=0, z=4, l=20, type=CharPointType.DIKE_CREST_WATER_SIDE
                ),
                CharPoint(
                    x=0, y=0, z=0, l=30, type=CharPointType.SURFACE_LEVEL_WATER_SIDE
                ),
            ],
        )

    def test_to_geolib(self):
        uv_method = self.uplift_van_particle_swarm.to_geolib(self.char_points_profile)

        self.assertIsInstance(uv_method, DStabilityUpliftVanParticleSwarmAnalysisMethod)

        area_a = uv_method.search_area_a
        area_b = uv_method.search_area_b
        constraints = uv_method.slip_plane_constraints

        self.assertAlmostEqual(area_a.height, 4)
        self.assertAlmostEqual(area_a.width, 3)
        self.assertAlmostEqual(area_a.top_left.x, 6)
        self.assertAlmostEqual(area_a.top_left.z, 10)

        self.assertAlmostEqual(area_b.height, 8)
        self.assertAlmostEqual(area_b.width, 7)
        self.assertAlmostEqual(area_b.top_left.x, -7)
        self.assertAlmostEqual(area_b.top_left.z, 13)

        self.assertTrue(constraints.is_zone_a_constraints_enabled)
        self.assertAlmostEqual(constraints.x_left_zone_a, 20)
        self.assertAlmostEqual(constraints.width_zone_a, 4)

        self.assertTrue(constraints.is_zone_b_constraints_enabled)
        self.assertAlmostEqual(constraints.x_left_zone_b, 5)
        self.assertAlmostEqual(constraints.width_zone_b, 5)

        self.assertTrue(constraints.is_size_constraints_enabled)
        self.assertAlmostEqual(constraints.minimum_slip_plane_length, 6.0)
        self.assertAlmostEqual(constraints.minimum_slip_plane_depth, 3.0)


class TestBishopBruteForce(TestCase):
    def setUp(self):
        self.bishop_brute_force = BishopBruteForce(
            grid_setting_name="test",
            slip_plane_model=SlipPlaneModel.BISHOP_BRUTE_FORCE,
            apply_minimum_slip_plane_dimensions=True,
            minimum_slip_plane_depth=3.0,
            minimum_slip_plane_length=6.0,
            apply_constraint_zone_a=True,
            zone_a_position=CharPointType.DIKE_CREST_WATER_SIDE,
            zone_a_direction=Side.WATER_SIDE,
            zone_a_width=4.0,
            apply_constraint_zone_b=True,
            zone_b_position=CharPointType.DIKE_CREST_LAND_SIDE,
            zone_b_direction=Side.LAND_SIDE,
            zone_b_width=5.0,
            grid_position=CharPointType.DIKE_CREST_LAND_SIDE,
            grid_direction=Side.LAND_SIDE,
            grid_offset_horizontal=1.0,
            grid_offset_vertical=2.0,
            grid_points_horizontal=10,
            grid_points_vertical=11,
            grid_points_per_m=5,
            tangent_line_position=CharPointType.DIKE_TOE_LAND_SIDE,
            tangent_line_offset=-1.0,
            tangent_line_count=7,
            tangent_lines_per_m=2,
            move_grid=True,
        )

        self.char_points_profile = CharPointsProfile(
            name="Profile 1",
            points=[
                CharPoint(
                    x=0, y=0, z=0, l=0, type=CharPointType.SURFACE_LEVEL_LAND_SIDE
                ),
                CharPoint(x=0, y=0, z=0, l=5, type=CharPointType.DIKE_TOE_LAND_SIDE),
                CharPoint(x=0, y=0, z=4, l=10, type=CharPointType.DIKE_CREST_LAND_SIDE),
                CharPoint(
                    x=0, y=0, z=4, l=20, type=CharPointType.DIKE_CREST_WATER_SIDE
                ),
                CharPoint(
                    x=0, y=0, z=0, l=30, type=CharPointType.SURFACE_LEVEL_WATER_SIDE
                ),
            ],
        )

    def test_to_geolib(self):
        search_grid = self.bishop_brute_force.to_geolib(self.char_points_profile)

        self.assertIsInstance(search_grid, DStabilityBishopBruteForceAnalysisMethod)
        self.assertAlmostEqual(search_grid.search_grid.bottom_left.x, 7.2)
        self.assertAlmostEqual(search_grid.search_grid.bottom_left.z, 6)
        self.assertAlmostEqual(search_grid.search_grid.number_of_points_in_x, 10)
        self.assertAlmostEqual(search_grid.search_grid.number_of_points_in_z, 11)
        self.assertAlmostEqual(search_grid.search_grid.space, 1 / 5)
        self.assertAlmostEqual(search_grid.extrapolate_search_space, True)
        self.assertAlmostEqual(search_grid.bottom_tangent_line_z, -4.)
        self.assertAlmostEqual(search_grid.number_of_tangent_lines, 7)
        self.assertAlmostEqual(search_grid.space_tangent_lines, 1 / 2)


class TestGridSettingsSets(TestCase):
    def setUp(self):
        self.grid_settings = [
            BishopBruteForce(
                grid_setting_name="Bishop",
                slip_plane_model=SlipPlaneModel.BISHOP_BRUTE_FORCE,
                apply_minimum_slip_plane_dimensions=True,
                minimum_slip_plane_depth=3.0,
                minimum_slip_plane_length=6.0,
                apply_constraint_zone_a=True,
                zone_a_position=CharPointType.DIKE_CREST_WATER_SIDE,
                zone_a_direction=Side.WATER_SIDE,
                zone_a_width=4.0,
                apply_constraint_zone_b=True,
                zone_b_position=CharPointType.DIKE_CREST_LAND_SIDE,
                zone_b_direction=Side.LAND_SIDE,
                zone_b_width=5.0,
                grid_position=CharPointType.DIKE_CREST_LAND_SIDE,
                grid_direction=Side.LAND_SIDE,
                grid_offset_horizontal=1.0,
                grid_offset_vertical=2.0,
                grid_points_horizontal=10,
                grid_points_vertical=11,
                grid_points_per_m=5,
                tangent_line_position=CharPointType.DIKE_TOE_LAND_SIDE,
                tangent_line_offset=-1.0,
                tangent_line_count=7,
                tangent_lines_per_m=2,
                move_grid=True,
            ),
            UpliftVanParticleSwarm(
                grid_setting_name="Uplift",
                slip_plane_model=SlipPlaneModel.UPLIFT_VAN_PARTICLE_SWARM,
                apply_minimum_slip_plane_dimensions=True,
                minimum_slip_plane_depth=3.0,
                minimum_slip_plane_length=6.0,
                apply_constraint_zone_a=True,
                zone_a_position=CharPointType.DIKE_CREST_WATER_SIDE,
                zone_a_direction=Side.WATER_SIDE,
                zone_a_width=4.0,
                apply_constraint_zone_b=True,
                zone_b_position=CharPointType.DIKE_CREST_LAND_SIDE,
                zone_b_direction=Side.LAND_SIDE,
                zone_b_width=5.0,
                grid_1_position=CharPointType.DIKE_CREST_LAND_SIDE,
                grid_1_direction=Side.LAND_SIDE,
                grid_1_offset_horizontal=1,
                grid_1_offset_vertical=2,
                grid_1_width=3,
                grid_1_height=4,
                grid_2_position=CharPointType.DIKE_TOE_LAND_SIDE,
                grid_2_direction=Side.LAND_SIDE,
                grid_2_offset_horizontal=5,
                grid_2_offset_vertical=5,
                grid_2_width=7,
                grid_2_height=8,
                tangent_area_position=CharPointType.DIKE_TOE_LAND_SIDE,
                tangent_area_offset=-1.5,
                height_tangent_area=10,
                search_mode=OptionsType.THOROUGH,
            ),
        ]

    def test_init(self):
        grid_settings_set = GridSettingsSet(
            name="test", grid_settings=self.grid_settings
        )

        self.assertEqual(grid_settings_set.name, "test")
        self.assertEqual(len(grid_settings_set.grid_settings), 2)
        self.assertIsInstance(grid_settings_set.grid_settings[0], BishopBruteForce)
        self.assertIsInstance(
            grid_settings_set.grid_settings[1], UpliftVanParticleSwarm
        )

    def test_init_duplicate_name(self):
        self.grid_settings[0].grid_setting_name = "Uplift"

        with self.assertRaises(ValueError):
            self.grid_settings_set = GridSettingsSet(
                name="test", grid_settings=self.grid_settings
            )


class TestGridSettingsSetCollection(TestCase):
    def setUp(self):
        with open(GRID_SETTINGS_SET_COLLECTION_JSON_PATH) as f:
            self.grid_settings_set_collection_dict = json.load(f)
            self.grid_settings_set_collection = (
                GridSettingsSetCollection.model_validate(
                    self.grid_settings_set_collection_dict
                )
            )

        grid_settings_set_list = self.grid_settings_set_collection_dict[
            "grid_settings_sets"
        ]
        self.input_dict = {
            di["name"]: di["grid_settings"] for di in grid_settings_set_list
        }

    def test_get_by_name(self):
        collection_from_json = GridSettingsSetCollection.model_validate(
            self.grid_settings_set_collection
        )
        name = "STBI"
        grid_settings_set = collection_from_json.get_by_name(name=name)

        self.assertIsInstance(grid_settings_set, GridSettingsSet)
        self.assertEqual(len(grid_settings_set.grid_settings), 3)
        self.assertEqual(grid_settings_set.name, name)

    def test_get_by_name_not_found(self):
        collection_from_json = GridSettingsSetCollection.model_validate(
            self.grid_settings_set_collection
        )
        name = "non-existent-name"
        with self.assertRaises(ValueError):
            collection_from_json.get_by_name(name=name)
